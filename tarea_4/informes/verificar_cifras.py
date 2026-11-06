"""Verifica cifras del informe por un camino independiente del agente.

    uv run informes/verificar_cifras.py

BCRP: pide los datos directo a la API pública, sin pasar por mcp/server.py.
ENAHO: recalcula desde los .dta originales, sin usar la base ni los scripts de las skills.
"""
import io
import json
import sys
import zipfile

import httpx
import pandas as pd

API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"


def bcrp(codigo, desde, hasta):
    """Devuelve {periodo de la API: valor} tal como lo publica el BCRP."""
    url = f"{API}/{codigo}/json/{desde}/{hasta}"
    datos = json.loads(httpx.get(url, timeout=60).content.decode("latin-1"))
    return {p["name"]: float(p["values"][0]) for p in datos["periods"] if p["values"][0] != "n.d."}, url


def dta(zip_, nombre):
    with zipfile.ZipFile(zip_) as z:
        ruta = next(n for n in z.namelist() if n.lower().endswith(nombre))
        df = pd.read_stata(io.BytesIO(z.read(ruta)), convert_categoricals=False)
    df.columns = df.columns.str.lower()
    return df


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for codigo, desde, hasta in [("PM04863AA", "2019", "2024"), ("PM04860AA", "2019", "2024"),
                                 ("PN31879GM", "2019-1", "2024-12")]:
        valores, url = bcrp(codigo, desde, hasta)
        print(f"BCRP {codigo} {url}")
        claves = list(valores)
        for k in (claves if len(claves) <= 6 else [claves[0], claves[-1]]):
            print(f"  {k}: {valores[k]:,.4f}")
        if len(claves) > 6:
            dic19 = [v for k, v in valores.items() if k.endswith("2019")]
            dic24 = [v for k, v in valores.items() if k.endswith("2024")]
            print(f"  promedio 2019: {sum(dic19) / len(dic19):,.4f}  promedio 2024: {sum(dic24) / len(dic24):,.4f}")

    # ENAHO: pobreza ponderada por personas desde la sumaria (factor07 por mieperho), método del INEI
    s = dta("datos/966-Modulo34.zip", "sumaria-2024.dta")
    s["w"] = s.factor07 * s.mieperho
    s["pobre"] = s.pobreza <= 2
    s["area"] = s.estrato.le(5).map({True: "Urbana", False: "Rural"})
    s["dpto"] = s.ubigeo.str[:2]

    def tasa(d):
        return 100 * d.loc[d.pobre, "w"].sum() / d.w.sum()

    print(f"ENAHO pobreza nacional: {tasa(s):.2f}%")
    for area, d in s.groupby("area"):
        print(f"ENAHO pobreza {area}: {tasa(d):.2f}%")
    por_dpto = s.groupby("dpto").apply(tasa, include_groups=False).sort_values()
    print(f"ENAHO departamentos: {len(por_dpto)}; menor {por_dpto.index[0]} {por_dpto.iloc[0]:.2f}%, "
          f"mayor {por_dpto.index[-1]} {por_dpto.iloc[-1]:.2f}%")


if __name__ == "__main__":
    main()
