"""Arma la base de personas de la ENAHO y la valida contra las cifras oficiales.

Entra: datos/<codigo>-Modulo34.zip y datos/<codigo>-Modulo02.zip
Sale: salidas/personas_<anio>.parquet, salidas/indicadores.csv y salidas/validacion.txt
Si falla una validación esencial, escribe validacion.txt con la falla y termina en ERROR sin guardar la base.
"""
import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

LLAVES = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES + ["codperso"]
OFICIAL = {2024: {"pobreza": 27.6, "urbana": 24.8, "rural": 39.3, "extrema": 5.5, "hogares": 33691,
                  "filas": 117721, "residentes": 108664}}
TOLERANCIA = 0.1
DEPARTAMENTOS = {"01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
                 "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
                 "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
                 "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura", "21": "Puno",
                 "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali"}


def leer(modulo, dta, datos):
    """Lee el .dta del año pedido sin importar el código del zip que lo trae."""
    for ruta in sorted(datos.glob(f"*-Modulo{modulo}.zip")):
        with zipfile.ZipFile(ruta) as z:
            for nombre in z.namelist():
                if nombre.rsplit("/", 1)[-1].lower() == dta:
                    with z.open(nombre) as f:
                        return pd.read_stata(io.BytesIO(f.read()), convert_categoricals=False)
    sys.exit(f"ERROR: falta {dta} en {datos}/. Descarga el módulo {modulo} de ese año.")


def normalizar(df):
    """Pasa las columnas a minúscula. La del año llega como aÑo y sin una codificación fija."""
    df.columns = [re.sub(r"^a.{1,2}o$", "anio", c.lower()) for c in df.columns]
    return df


def tasa(df, condicion, peso):
    return 100 * df.loc[condicion, peso].sum() / df[peso].sum()


def indicadores(base, anio):
    """Pobreza y pobreza extrema ponderadas, nacional, por área, sexo y departamento, con población expandida y muestra."""
    cortes = {"nacional": pd.Series("Perú", index=base.index),
              "area": base.urbano.map({True: "Urbana", False: "Rural"}),
              "sexo": base.p207.map({1: "Hombres", 2: "Mujeres"}),
              "departamento": base.departamento + " " + base.nombre_departamento}
    filas = []
    for corte, grupo in cortes.items():
        for nombre, g in base.groupby(grupo):
            filas.append({"anio": anio, "corte": corte, "grupo": nombre,
                          "pobreza_pct": round(tasa(g, g.pobre, "facpob07"), 2),
                          "pobreza_extrema_pct": round(tasa(g, g.pobreza == 1, "facpob07"), 2),
                          "poblacion_expandida": round(g.facpob07.sum()), "personas_muestra": len(g)})
    return pd.DataFrame(filas)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # La consola de Windows no usa UTF-8
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anio", type=int, required=True)
    p.add_argument("--datos", type=Path, default=Path("datos"))
    p.add_argument("--salidas", type=Path, default=Path("salidas"))
    a = p.parse_args()

    sumaria = normalizar(leer("34", f"sumaria-{a.anio}.dta", a.datos))
    miembros = normalizar(leer("02", f"enaho01-{a.anio}-200.dta", a.datos))

    pruebas = []   # (nombre, aprobada, esencial)
    lineas = [f"ENAHO {a.anio}", f"Hogares en la sumaria: {len(sumaria):,}",
              f"Filas del módulo de miembros: {len(miembros):,}"]

    def probar(nombre, ok, esencial=True):
        pruebas.append((nombre, bool(ok), esencial))

    def cerrar():
        """Escribe validacion.txt y termina en ERROR si falló alguna prueba esencial."""
        texto = lineas + ["", "Validaciones:"] + [
            f"[{'OK' if ok else 'FALLA'}] {n}{'' if esencial else ' (control, no detiene)'}" for n, ok, esencial in pruebas]
        a.salidas.mkdir(exist_ok=True)
        (a.salidas / "validacion.txt").write_text("\n".join(texto) + "\n", encoding="utf-8")
        print("\n".join(texto))
        fallas = [n for n, ok, esencial in pruebas if esencial and not ok]
        if fallas:
            sys.exit(f"ERROR: no pasó la validación: {'; '.join(fallas)}. No se guardó la base.")

    llaves_texto = all(pd.api.types.is_string_dtype(d[c]) for d in (sumaria, miembros) for c in LLAVES)
    probar("Llaves conglome, vivienda y hogar leídas como texto, con sus ceros iniciales", llaves_texto)
    probar("Ningún hogar repetido en la sumaria", not sumaria.duplicated(LLAVES).any())
    probar("Ninguna persona repetida en el módulo de miembros", not miembros.duplicated(LLAVES_PERSONA).any())

    # Residente habitual, con la condición de la sesión. La pobreza del INEI se mide sobre los miembros
    # del hogar, p204 == 1, que son exactamente los que cuenta mieperho (ver reference.md).
    miembros["residente"] = ((miembros.p204 == 1) & (miembros.p205 == 2)) | (
        (miembros.p204 == 2) & (miembros.p206 == 1)
    )
    residentes = miembros[miembros.residente]
    personas = miembros[miembros.p204 == 1]
    por_hogar = personas.groupby(LLAVES).size().reindex(sumaria.set_index(LLAVES).index, fill_value=0)
    probar("mieperho igual al conteo de miembros p204 == 1 en cada hogar",
           (por_hogar.values == sumaria.mieperho.values).all())

    columnas = LLAVES + ["ubigeo", "dominio", "estrato", "pobreza", "mieperho", "factor07"]
    try:
        base = personas[LLAVES_PERSONA + ["residente", "p203", "p207", "p208a", "facpob07"]].merge(
            sumaria[columnas], on=LLAVES, how="left", validate="m:1")
        base_res = residentes[LLAVES_PERSONA + ["facpob07"]].merge(
            sumaria[columnas], on=LLAVES, how="left", validate="m:1")
    except pd.errors.MergeError as e:
        probar(f"Unión personas-hogares m:1 ({e})", False)
        cerrar()
    probar("Unión m:1 sin perder ni duplicar personas",
           len(base) == len(personas) and len(base_res) == len(residentes))
    probar("Todas las personas encuentran su hogar en la sumaria", base.pobreza.notna().all())
    probar("Ubigeo de 6 dígitos en todas las personas", base.ubigeo.str.len().eq(6).all())

    base["departamento"] = base.ubigeo.str[:2]
    base["nombre_departamento"] = base.departamento.map(DEPARTAMENTOS)
    base["urbano"] = base.estrato <= 5
    base["pobre"] = base.pobreza <= 2
    base["anio"] = a.anio
    base_res["pobre"] = base_res.pobreza <= 2
    probar("25 códigos territoriales, del 01 al 25", set(base.departamento) == set(DEPARTAMENTOS))
    probar("Factor facpob07 completo y positivo", base.facpob07.notna().all() and (base.facpob07 > 0).all())
    probar("facpob07 igual al factor07 del hogar en cada miembro",
           (base.facpob07 - base.factor07).abs().max() < 1e-6)

    sumaria["peso"] = sumaria.factor07 * sumaria.mieperho
    pobreza_sumaria = tasa(sumaria, sumaria.pobreza <= 2, "peso")
    pobreza_personas = tasa(base, base.pobre, "facpob07")
    pobreza_residentes = tasa(base_res, base_res.pobre, "facpob07")
    urbana = tasa(base[base.urbano], base.pobre[base.urbano], "facpob07")
    rural = tasa(base[~base.urbano], base.pobre[~base.urbano], "facpob07")
    extrema = tasa(sumaria, sumaria.pobreza == 1, "peso")
    sin_ponderar = 100 * base.pobre.mean()
    lineas += [
        f"Residentes habituales: {len(residentes):,}",
        f"Miembros del hogar, base de la pobreza: {len(base):,}",
        f"Población expandida (suma de facpob07): {base.facpob07.sum():,.0f}",
        f"Pobreza con la sumaria, factor07 por mieperho: {pobreza_sumaria:.2f}%",
        f"Pobreza con personas, facpob07: {pobreza_personas:.2f}%",
        f"Pobreza con residentes habituales, facpob07: {pobreza_residentes:.2f}%",
        f"Pobreza urbana: {urbana:.2f}%",
        f"Pobreza rural: {rural:.2f}%",
        f"Pobreza extrema: {extrema:.2f}%",
        f"Pobreza sin ponderar, solo para mostrar el efecto del factor: {sin_ponderar:.2f}%",
    ]

    oficial = OFICIAL.get(a.anio)
    if oficial is None:
        lineas.append(f"Sin cifras oficiales cargadas para {a.anio}. Base NO validada contra el INEI.")
    else:
        def cerca(x, ref):
            return abs(x - ref) < TOLERANCIA
        probar(f"Pobreza nacional con la sumaria a menos de {TOLERANCIA} pp de {oficial['pobreza']}%",
               cerca(pobreza_sumaria, oficial["pobreza"]))
        probar(f"Pobreza nacional con personas a menos de {TOLERANCIA} pp de {oficial['pobreza']}%",
               cerca(pobreza_personas, oficial["pobreza"]))
        probar(f"Pobreza con residentes habituales a menos de {TOLERANCIA} pp de {oficial['pobreza']}%",
               cerca(pobreza_residentes, oficial["pobreza"]), esencial=False)
        probar(f"Pobreza urbana a menos de {TOLERANCIA} pp de {oficial['urbana']}%", cerca(urbana, oficial["urbana"]))
        probar(f"Pobreza rural a menos de {TOLERANCIA} pp de {oficial['rural']}%", cerca(rural, oficial["rural"]))
        probar(f"Pobreza extrema a menos de {TOLERANCIA} pp de {oficial['extrema']}%",
               cerca(extrema, oficial["extrema"]))
        probar(f"{oficial['hogares']:,} hogares en la sumaria", len(sumaria) == oficial["hogares"])
        probar(f"{oficial['filas']:,} filas en el módulo de miembros", len(miembros) == oficial["filas"])
        probar(f"{oficial['residentes']:,} residentes habituales", len(residentes) == oficial["residentes"])
        lineas.append(f"Referencia INEI {a.anio}: pobreza {oficial['pobreza']}%, urbana {oficial['urbana']}%, "
                      f"rural {oficial['rural']}%, residentes {oficial['residentes']:,}")
    cerrar()

    base.to_parquet(a.salidas / f"personas_{a.anio}.parquet", index=False)
    indicadores(base, a.anio).to_csv(a.salidas / "indicadores.csv", index=False, encoding="utf-8")
    print(f"Guardado: {a.salidas / f'personas_{a.anio}.parquet'} y {a.salidas / 'indicadores.csv'}")


if __name__ == "__main__":
    main()
