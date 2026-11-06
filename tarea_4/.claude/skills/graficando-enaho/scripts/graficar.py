"""Grafica la pobreza monetaria por área, sexo, edad o departamento desde la base de personas."""
import argparse
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

COLOR = "#B5451B"
TRAMOS = [0, 18, 30, 45, 60, 200]
NOMBRES_TRAMOS = ["0 a 17 años", "18 a 29 años", "30 a 44 años", "45 a 59 años", "60 años a más"]
# cómo se nombra cada grupo dentro del título
EN_TITULO = {"Rural": "el área rural", "Urbana": "el área urbana", "Mujeres": "las mujeres", "Hombres": "los hombres",
             **{t: f"el grupo de {t}" for t in NOMBRES_TRAMOS}}


def grupos(df, por):
    """Devuelve la serie de grupos, el texto del eje y si conserva su orden natural."""
    if por == "area":
        return df.urbano.map({True: "Urbana", False: "Rural"}), "área de residencia", False
    if por == "sexo":
        return df.p207.map({1: "Hombres", 2: "Mujeres"}), "sexo", False
    if por == "departamento":
        return df.nombre_departamento, "departamento", False
    edad = pd.cut(df.p208a, TRAMOS, right=False, labels=NOMBRES_TRAMOS)
    return edad, "grupo de edad", True


def pobreza_por_grupo(df, grupo):
    """Porcentaje de personas pobres por grupo, siempre ponderado con facpob07."""
    t = pd.DataFrame({"g": grupo, "w": df.facpob07, "wp": df.facpob07 * df.pobre}).dropna(subset=["g"])
    r = t.groupby("g", observed=True)[["w", "wp"]].sum()
    return 100 * r.wp / r.w


def titulo(valores, texto, anio):
    """Título analítico: dice qué grupo tiene más pobreza, cuánto y la brecha en puntos."""
    alto, bajo = valores.idxmax(), valores.idxmin()
    n_alto, n_bajo = EN_TITULO.get(alto, alto), EN_TITULO.get(bajo, bajo)
    brecha = valores.max() - valores.min()
    if brecha < 1:   # una diferencia menor a un punto no se presenta como brecha
        return textwrap.fill(f"Por {texto}, la pobreza es similar: {valores.max():.1f}% en {n_alto} y "
                             f"{valores.min():.1f}% en {n_bajo}. Perú, {anio}", 75)
    return textwrap.fill(f"Por {texto}, la pobreza es mayor en {n_alto} ({valores.max():.1f}%) que en {n_bajo} "
                         f"({valores.min():.1f}%): una brecha de {brecha:.1f} puntos. Perú, {anio}", 75)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # La consola de Windows no usa UTF-8
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anio", type=int, required=True)
    p.add_argument("--por", choices=["area", "sexo", "edad", "departamento"], required=True)
    p.add_argument("--salidas", type=Path, default=Path("salidas"))
    p.add_argument("--figuras", type=Path, default=Path("figuras"))
    a = p.parse_args()

    ruta = a.salidas / f"personas_{a.anio}.parquet"
    if not ruta.exists():
        sys.exit(f"ERROR: falta {ruta}. Usa primero la skill limpiando-enaho.")
    df = pd.read_parquet(ruta)
    nacional = 100 * (df.facpob07 * df.pobre).sum() / df.facpob07.sum()
    grupo, texto, orden_natural = grupos(df, a.por)
    valores = pobreza_por_grupo(df, grupo)
    if not orden_natural:
        valores = valores.sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(8, 1.8 + 0.42 * len(valores) if len(valores) > 6 else 2.2 + 0.7 * len(valores)))
    y = range(len(valores))
    barras = ax.barh(y, valores.values, color=COLOR)
    ax.bar_label(barras, labels=[f"{v:.1f}%" for v in valores.values], padding=4, fontsize=9,
                 bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax.axvline(nacional, color="#333333", linestyle="--", linewidth=1)
    ax.text(nacional, len(valores) - 0.45, f" Perú {nacional:.1f}%", fontsize=8, color="#333333", va="bottom")
    ax.set_yticks(y, labels=valores.index)
    ax.set_ylim(len(valores) - 0.3, -0.6)
    ax.set_xlim(0, valores.max() * 1.15)
    ax.xaxis.set_visible(False)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.set_title(titulo(valores, texto, a.anio), loc="left", fontsize=11, pad=20)
    ax.text(0, 1.01, "% de personas en situación de pobreza monetaria. Línea punteada: promedio nacional",
            transform=ax.transAxes, fontsize=8.5, color="#555555")
    fig.text(0.01, 0.01, f"Fuente: INEI, ENAHO {a.anio} (módulos 34 y 02). Estimaciones ponderadas con facpob07.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))

    a.figuras.mkdir(exist_ok=True)
    salida = a.figuras / f"pobreza_por_{a.por}_{a.anio}.png"
    fig.savefig(salida, dpi=200)
    print(f"Perú: {nacional:.1f}%")
    for nombre, valor in valores.items():
        print(f"{nombre}: {valor:.1f}%")
    print(f"Guardado: {salida}")


if __name__ == "__main__":
    main()
