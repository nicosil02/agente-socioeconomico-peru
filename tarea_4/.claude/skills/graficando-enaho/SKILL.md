---
name: graficando-enaho
description: Crea gráficos de barras de la pobreza monetaria del Perú con la ENAHO por área urbana y rural, sexo, grupo de edad o departamento, ponderados con el factor de expansión. Úsala cuando pidan graficar, comparar o visualizar la pobreza o la ENAHO.
argument-hint: "[area|sexo|edad|departamento] [año]"
---
# Graficar la ENAHO

1. Toma el año del pedido. Si no lo dice, usa el de la única salidas/personas_*.parquet. Si no hay ninguna o hay varias, pregúntalo.
2. Si no existe salidas/personas_<año>.parquet, ejecuta primero la skill limpiando-enaho con ese año y sigue cuando termine sin ERROR.
3. Elige el corte según la pregunta: area, sexo, edad o departamento. Si piden varios, corre el script una vez por corte.
4. Corre exactamente: uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --anio <año> --por <corte>
5. Abre el PNG y revisa que se lea bien antes de responder.
6. Responde con las cifras que imprimió el script y la ruta en figuras/.

## Reglas que el script ya cumple y no se cambian

- Pondera siempre con facpob07.
- Barras que empiezan en cero y ordenadas. La edad conserva su orden natural.
- Un solo color, el valor escrito en cada barra y una línea punteada con el promedio nacional.
- Título analítico: dice qué grupo tiene más pobreza y la brecha en puntos; si la brecha es menor a un punto, dice que es similar.
- Subtítulo con la unidad: % de personas en situación de pobreza monetaria.
- Nota al pie con la fuente, INEI y ENAHO del año, y la ponderación.
- PNG a 200 dpi en figuras/.

Si piden otro corte, haz un script nuevo que cumpla las mismas reglas.
