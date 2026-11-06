"""Hace el mapa de pobreza por departamento uniendo siempre por código, nunca por nombre."""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

GEOJSON = "peru_departamental_simple.geojson"
REFERENCIA = {2024: Path(__file__).parent / "referencia_pobreza_2024.csv"}
TOLERANCIA = 0.1


def pobreza_departamental(df):
    t = df.assign(wp=df.facpob07 * df.pobre).groupby("departamento")[["facpob07", "wp"]].sum()
    return (100 * t.wp / t.facpob07).rename("pobreza").reset_index()


def unir(limites, pobreza):
    """Une por código como texto y exige 25 departamentos con dato."""
    limites = limites.assign(departamento=limites.FIRST_IDDP.astype(str).str.zfill(2))
    mapa = limites.merge(pobreza, on="departamento", how="left", validate="1:1")
    if len(mapa) != 25 or mapa.pobreza.isna().any():
        faltan = mapa.loc[mapa.pobreza.isna(), "NOMBDEP"].tolist()
        sys.exit(f"ERROR: se esperaban 25 departamentos con dato. Filas {len(mapa)}, sin dato {faltan}.")
    return mapa


def validar(mapa, anio, salidas):
    """Compara cada departamento con la referencia de la sesión y guarda la tabla en salidas/."""
    if anio not in REFERENCIA:
        print(f"Sin referencia para {anio}. Mapa NO validado.")
        return
    ref = pd.read_csv(REFERENCIA[anio], dtype={"ccdd": str})
    t = mapa.merge(ref, left_on="departamento", right_on="ccdd", validate="1:1")
    dif = (t.pobreza - t.pobreza_pct).abs()
    pd.DataFrame({"departamento": t.ccdd, "nombre": t.NOMBDEP, "pobreza_calculada": t.pobreza.round(2),
                  "pobreza_referencia": t.pobreza_pct, "diferencia": (t.pobreza - t.pobreza_pct).round(2)}
                 ).to_csv(salidas / f"mapa_vs_referencia_{anio}.csv", index=False, encoding="utf-8")
    if len(t) != 25 or dif.max() >= TOLERANCIA:
        sys.exit(f"ERROR: el mapa no replica la referencia. Diferencia máxima {dif.max():.2f} puntos.")
    print(f"Validado contra la referencia: diferencia máxima {dif.max():.2f} puntos.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # La consola de Windows no usa UTF-8
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anio", type=int, required=True)
    p.add_argument("--datos", type=Path, default=Path("datos"))
    p.add_argument("--salidas", type=Path, default=Path("salidas"))
    p.add_argument("--mapas", type=Path, default=Path("mapas"))
    a = p.parse_args()

    ruta = a.salidas / f"personas_{a.anio}.parquet"
    if not ruta.exists():
        sys.exit(f"ERROR: falta {ruta}. Usa primero la skill limpiando-enaho.")
    if not (a.datos / GEOJSON).exists():
        sys.exit(f"ERROR: falta {a.datos / GEOJSON}. Corre: uv run .claude/skills/limpiando-enaho/scripts/descargar.py --anio 2024 --modulos 34 02 --limites")

    mapa = unir(gpd.read_file(a.datos / GEOJSON), pobreza_departamental(pd.read_parquet(ruta)))

    a.salidas.mkdir(exist_ok=True)
    validar(mapa, a.anio, a.salidas)

    nombres = pd.read_parquet(ruta, columns=["departamento", "nombre_departamento"]).drop_duplicates()
    mapa = mapa.merge(nombres, on="departamento", how="left", validate="1:1")
    alto, bajo = mapa.loc[mapa.pobreza.idxmax()], mapa.loc[mapa.pobreza.idxmin()]
    lima, callao = (mapa.set_index("departamento").loc[c] for c in ("15", "07"))

    fig, ax = plt.subplots(figsize=(7, 9))
    mapa.plot(
        column="pobreza", cmap="Oranges", vmin=0, ax=ax, edgecolor="white", linewidth=0.5, legend=True,
        legend_kwds={"label": "Pobreza monetaria, % de personas", "shrink": 0.5},
    )
    ax.set_axis_off()
    ax.set_title(f"La pobreza monetaria va de {bajo.pobreza:.1f}% en {bajo.nombre_departamento} a "
                 f"{alto.pobreza:.1f}% en {alto.nombre_departamento}\nPobreza por departamento, Perú {a.anio}",
                 fontsize=12, loc="left")
    ax.text(0.02, 0.12, f"Lima (15): {lima.pobreza:.1f}%\nCallao (07): {callao.pobreza:.1f}%",
            transform=ax.transAxes, fontsize=9, color="#333333")
    fig.text(0.02, 0.02, f"Fuente: INEI, ENAHO {a.anio} (módulos 34 y 02), estimaciones ponderadas con facpob07. "
             "Límites: GeoJSON departamental del curso.", fontsize=7.5, color="#555555")

    a.mapas.mkdir(exist_ok=True)
    salida = a.mapas / "pobreza_departamento.png"
    fig.savefig(salida, dpi=200, bbox_inches="tight")
    for _, fila in mapa.sort_values("pobreza", ascending=False).iterrows():
        print(f"{fila.departamento} {fila.NOMBDEP}: {fila.pobreza:.1f}%")
    print(f"Guardado: {salida}")


if __name__ == "__main__":
    main()
