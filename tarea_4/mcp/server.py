"""Servidor MCP del BCRP: buscar, bajar, resumir, comparar periodos y graficar series oficiales.

    uv run pytest mcp                  # 8 pruebas del curso + 2 de comparar_periodos
    uv run mcp/server.py               # el servidor, por stdio (así lo lanza .mcp.json)

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import json
import re
import time
import unicodedata
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI.parent / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. No calcules a mano: "
    "cita siempre el código de la serie y el periodo."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "sep": 9,
         "oct": 10, "nov": 11, "dic": 12}


def _fecha_api(fecha, frecuencia, final):
    """De "2025-01", "2025-T1", "2026-10-01" o "2025" al formato que pide la API según la frecuencia."""
    fecha = str(fecha).strip()
    anio = fecha[:4]
    if not re.fullmatch(r"\d{4}(-(T?\d{1,2})(-\d{1,2})?)?", fecha):
        raise ToolError(f"Fecha no válida {fecha!r}. Usen 2025-01 (mensual), 2025-T1, 2026-10-01 (diaria) o 2025.")
    if frecuencia == "Anual":
        return anio
    if frecuencia == "Diaria":
        return fecha if len(fecha) == 10 else (f"{anio}-12-31" if final else f"{anio}-01-01")
    if len(fecha) == 4:   # solo el año: todo el año
        return f"{anio}-{12 if frecuencia == 'Mensual' else 4}" if final else f"{anio}-1"
    return f"{anio}-{int(fecha[5:7].lstrip('T'))}"


def _periodo(nombre, frecuencia):
    """De "Ene.2025", "01.Oct.26", "T1.25" o "2025" a "2025-01", "2026-10-01", "2025-T1" o "2025"."""
    partes = nombre.split(".")
    if frecuencia == "Mensual":
        return f"{partes[1]}-{MESES[partes[0][:3].lower()]:02d}"
    if frecuencia == "Diaria":
        return f"20{partes[2]}-{MESES[partes[1][:3].lower()]:02d}-{int(partes[0]):02d}"
    if frecuencia == "Trimestral":
        return f"20{partes[1]}-{partes[0]}"
    return nombre


@cache
def _bajar(url):
    """Pide una URL a la API. Si responde HTML (exceso de pedidos), espera y reintenta; lo bajado queda en caché."""
    for intento in range(4):
        r = httpx.get(url, timeout=60)
        try:
            return json.loads(r.content.decode("latin-1"))
        except json.JSONDecodeError:
            time.sleep(2 * (intento + 1))
    raise ToolError(f"El BCRP no respondió con datos para {url}. Intenten de nuevo en unos segundos.")


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos de una serie del BCRP entre dos fechas. Úsenla después de buscar_series.

    Fechas según la frecuencia de la serie: "2025-01" (mensual), "2025-T1" (trimestral), "2026-10-01" (diaria)
    o "2025" (anual; en las demás un año solo significa el año completo). Ejemplo: serie("PN01273PM", "2024-01",
    "2024-12"). Devuelve el código, el nombre, la frecuencia, los datos [{periodo, valor}] y la URL de la fuente.
    Los periodos sin dato ("n.d.") se omiten.
    """
    ficha = _ficha(codigo)
    frec = ficha["frecuencia"]
    url = f"{API}/{codigo}/json/{_fecha_api(desde, frec, False)}/{_fecha_api(hasta, frec, True)}"
    datos = [{"periodo": _periodo(p["name"], frec), "valor": float(p["values"][0])}
             for p in _bajar(url).get("periods", []) if p["values"][0] not in ("n.d.", "")]
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": frec, "datos": datos, "fuente": url}


def _resumir(s):
    datos = s["datos"]
    if not datos:
        raise ToolError(f"La serie {s['codigo']} no tiene datos en ese periodo ({s['fuente']}).")
    valores = [d["valor"] for d in datos]
    primero, ultimo = datos[0], datos[-1]
    cambio = ultimo["valor"] - primero["valor"]
    return {"codigo": s["codigo"], "nombre": s["nombre"], "frecuencia": s["frecuencia"], "n": len(datos),
            "primero": primero, "ultimo": ultimo, "cambio": round(cambio, 4),
            "variacion_pct": round(100 * cambio / primero["valor"], 4) if primero["valor"] else None,
            "promedio": round(sum(valores) / len(valores), 4),
            "maximo": max(datos, key=lambda d: d["valor"]), "minimo": min(datos, key=lambda d: d["valor"]),
            "fuente": s["fuente"]}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resume una serie del BCRP entre dos fechas: primero, último, cambio, variación %, promedio, máximo y mínimo.

    Úsenla siempre que haya que calcular algo; no hagan cuentas a mano. Fechas como en serie. El cambio es último
    menos primero, en las unidades de la serie; variacion_pct es ese cambio sobre el primer valor. Máximo y mínimo
    vienen con su periodo.
    """
    return _resumir(serie(codigo, desde, hasta))


@mcp.tool(annotations=SOLO_LECTURA)
def comparar_periodos(codigo: str, desde_a: str, hasta_a: str, desde_b: str, hasta_b: str) -> dict:
    """Compara una serie del BCRP entre dos intervalos: el resumen de cada uno y en cuánto cambió el promedio.

    Úsenla para preguntas de antes y después, por ejemplo la inflación de 2019 frente a la de 2022, o el PBI antes
    y después de 2020: comparar_periodos("PN01273PM", "2019-01", "2019-12", "2022-01", "2022-12"). Devuelve
    periodo_a y periodo_b (como resumen), diferencia_promedio (b menos a, en las unidades de la serie) y
    variacion_promedio_pct (esa diferencia sobre el promedio de a).
    """
    a, b = resumen(codigo, desde_a, hasta_a), resumen(codigo, desde_b, hasta_b)
    dif = b["promedio"] - a["promedio"]
    return {"codigo": codigo, "nombre": a["nombre"], "periodo_a": a, "periodo_b": b,
            "diferencia_promedio": round(dif, 4),
            "variacion_promedio_pct": round(100 * dif / a["promedio"], 4) if a["promedio"] else None}


@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def graficar_serie(codigo: str, desde: str, hasta: str, titulo: str, marcar: str | None = None) -> dict:
    """Grafica una serie del BCRP entre dos fechas y guarda el PNG en figuras/. Devuelve la ruta y el resumen.

    titulo: una frase que diga lo que muestra el gráfico, por ejemplo "El PBI cayó 10.9% en 2020 y en 2022 ya
    superaba su nivel de 2019". Las cifras del título deben salir de resumen o comparar_periodos, no de memoria.
    marcar: periodo opcional que se resalta con una línea vertical en series mensuales, trimestrales o diarias,
    por ejemplo "2020-04". En las anuales no se usa: se grafican en barras y cada año ya se distingue.
    El gráfico lleva el nombre y el código de la serie, las unidades y la fuente.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = serie(codigo, desde, hasta)
    if not s["datos"]:
        raise ToolError(f"La serie {codigo} no tiene datos en ese periodo ({s['fuente']}).")
    periodos = [d["periodo"] for d in s["datos"]]
    valores = [d["valor"] for d in s["datos"]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if s["frecuencia"] == "Anual":
        barras = ax.bar(periodos, valores, color="#1F4E79")
        ax.bar_label(barras, labels=[f"{v:,.1f}" for v in valores], fontsize=8, padding=2)
    else:
        ax.plot(periodos, valores, color="#1F4E79", linewidth=1.6)
        paso = max(1, len(periodos) // 8)
        ax.set_xticks(range(0, len(periodos), paso), [periodos[i] for i in range(0, len(periodos), paso)],
                      rotation=45, ha="right")
    if marcar in periodos and s["frecuencia"] != "Anual":   # en barras anuales la caída ya se ve
        ax.axvline(periodos.index(marcar), color="#B5451B", linestyle="--", linewidth=1)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(titulo, loc="left", fontsize=11)
    unidades = re.findall(r"\(([^()]*)\)", s["nombre"])
    ax.set_ylabel(unidades[-1] if unidades else s["nombre"].split(" - ")[-1], fontsize=9)
    fig.text(0.01, 0.01, f"Fuente: BCRP, serie {codigo} ({s['nombre']}), {periodos[0]} a {periodos[-1]}.",
             fontsize=7, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    carpeta = AQUI.parent / "figuras"
    carpeta.mkdir(exist_ok=True)
    ruta = carpeta / f"bcrp_{codigo}_{periodos[0]}_{periodos[-1]}.png"
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    return {"ruta": str(ruta.relative_to(AQUI.parent)).replace("\\", "/"), "resumen": _resumir(s)}


@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> str:
    """Ficha de una serie del BCRP: nombre, categoría, frecuencia, desde cuándo hay datos y última actualización."""
    return json.dumps(_ficha(codigo), ensure_ascii=False)


@mcp.prompt
def informe(tema: str) -> str:
    """Pide un informe breve de un tema con series oficiales del BCRP, citando código y periodo de cada cifra."""
    return (f"Prepara un informe breve sobre «{tema}» con series oficiales del BCRP.\n"
            "1. Busca las series con buscar_series y elige las más pertinentes; di por qué.\n"
            "2. Obtén las cifras con resumen, serie o comparar_periodos. No calcules nada a mano.\n"
            "3. Para cada cifra cita el código de la serie, el periodo y la URL de la fuente.\n"
            "4. Si una herramienta falla o no hay datos, dilo; no estimes.\n"
            "5. Describe los patrones sin afirmar causalidad.")


if __name__ == "__main__":
    mcp.run()
