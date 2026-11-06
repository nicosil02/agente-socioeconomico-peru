---
name: mapeando-enaho
description: Hace el mapa del Perú con la pobreza monetaria por departamento a partir de la ENAHO y el GeoJSON de límites, uniendo por código y validando los 25 departamentos contra la referencia de la sesión. Úsala cuando pidan un mapa, coropleta o comparación de la pobreza por departamento o región.
argument-hint: "[año]"
---
# Mapear la ENAHO

1. Toma el año del pedido. Si no lo dice, usa el de la única salidas/personas_*.parquet. Si no hay ninguna o hay varias, pregúntalo.
2. Si no existe salidas/personas_<año>.parquet, ejecuta primero la skill limpiando-enaho con ese año y sigue cuando termine sin ERROR.
3. Si falta datos/peru_departamental_simple.geojson, corre: uv run .claude/skills/limpiando-enaho/scripts/descargar.py --anio <año> --modulos 34 02 --limites
4. Corre exactamente: uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py --anio <año>
5. Si el script termina en ERROR, detente y muestra el mensaje. Nunca unas por nombre para arreglarlo.
6. Abre mapas/pobreza_departamento.png y revisa que se lea bien antes de responder.
7. Responde con los departamentos de mayor y menor pobreza, la diferencia máxima con la referencia y la ruta del mapa.

## Reglas que el script ya cumple y no se cambian

- Une por código, ubigeo[:2] con FIRST_IDDP como texto. Nunca por nombre, porque APURIMAC no es Apurímac.
- Exige 25 departamentos y ninguno sin dato.
- Compara cada departamento con scripts/referencia_pobreza_2024.csv, la referencia de la sesión, y guarda la tabla en salidas/mapa_vs_referencia_<año>.csv. Si alguno difiere en 0.1 puntos o más, termina en ERROR.
- Un color de claro a oscuro, desde 0. Nunca arcoíris.
- Leyenda con la unidad, % de personas.
- Lima (15) y Callao (07) van separados, con su valor escrito porque Callao casi no se ve.
