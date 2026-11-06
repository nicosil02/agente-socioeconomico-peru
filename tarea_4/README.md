# Agente de investigación socioeconómica del Perú

Tarea 4 de Python Intermedio. Un agente en Claude Code que responde preguntas sobre la economía y la pobreza del Perú con datos oficiales: consulta las series del BCRP mediante un servidor MCP propio y procesa los microdatos de la ENAHO 2024 del INEI mediante tres Skills.

## 1. Objetivo

Que las respuestas sobre indicadores peruanos salgan de herramientas que consultan y procesan las fuentes oficiales, no de lo que el modelo recuerda. Cada cifra debe poder rastrearse hasta un código de serie del BCRP o un archivo de `salidas/`, y otra persona debe poder repetir el proceso.

## 2. Arquitectura

```text
Pregunta en lenguaje natural
        │
        ▼
Claude Code (agente) ──────────────┬───────────────────────────────┐
        │                          │                               │
        ▼                          ▼                               ▼
Servidor MCP bcrp            Skills de ENAHO                 Informe
(mcp/server.py)              (.claude/skills/)               (informes/informe_final.md)
  buscar_series                limpiando-enaho  → salidas/
  serie                        graficando-enaho → figuras/
  resumen                      mapeando-enaho   → mapas/
  comparar_periodos
  graficar_serie → figuras/
        │                          │
        ▼                          ▼
API del BCRP                 ENAHO 2024 (módulos 34 y 02) y GeoJSON departamental
```

El servidor MCP se conecta a Claude Code con `.mcp.json`. Las Skills están en `.claude/skills/` y Claude Code las activa cuando el pedido coincide con su descripción. Los cálculos los hace Python; el modelo elige las herramientas, interpreta y redacta.

## 3. Herramientas del servidor MCP

| Tipo | Nombre | Qué hace |
|---|---|---|
| Herramienta | `buscar_series(texto, frecuencia, limite)` | Busca entre las 17 mil series del catálogo del BCRP por palabras clave |
| Herramienta | `serie(codigo, desde, hasta)` | Descarga los datos de una serie y normaliza los periodos (`2025-01`, `2025-T1`, `2026-10-01`, `2025`) |
| Herramienta | `resumen(codigo, desde, hasta)` | Primero, último, cambio, variación %, promedio, máximo y mínimo |
| Herramienta propia | `comparar_periodos(codigo, desde_a, hasta_a, desde_b, hasta_b)` | Compara una serie entre dos intervalos y da la diferencia de promedios |
| Herramienta propia | `graficar_serie(codigo, desde, hasta, titulo, marcar)` | Guarda en `figuras/` el gráfico de una serie con su código, unidades y fuente |
| Recurso | `bcrp://serie/{codigo}` | Ficha de la serie: nombre, frecuencia, inicio y última actualización |
| Prompt | `informe(tema)` | Pide un informe que cite código, periodo y fuente de cada cifra |

Todas devuelven la URL de la API del BCRP de la que salen los datos. Un código inexistente o un periodo sin datos dan un error explícito.

## 4. Skills

| Skill | Qué hace | Salidas |
|---|---|---|
| `limpiando-enaho` | Descarga los módulos si faltan, lee la sumaria y el módulo de miembros con las llaves como texto, filtra residentes habituales, une personas y hogares con `validate="m:1"`, construye pobreza, área y departamento con factores de expansión, y valida 19 condiciones. Si falla una esencial, se detiene sin guardar | `salidas/validacion.txt`, `salidas/indicadores.csv`, `salidas/personas_2024.parquet` |
| `graficando-enaho` | Gráficos de pobreza ponderada por área, sexo, edad o departamento, con título analítico, unidad, promedio nacional y fuente | `figuras/pobreza_por_<corte>_2024.png` |
| `mapeando-enaho` | Coropleta departamental unida por `ubigeo[:2]` y `FIRST_IDDP`, con 25 unidades, Lima y Callao separados, y comparación con la referencia de la sesión | `mapas/pobreza_departamento.png`, `salidas/mapa_vs_referencia_2024.csv` |

Graficar y mapear ejecutan antes `limpiando-enaho` si no existe la base procesada.

**Validación de ENAHO 2024** (`salidas/validacion.txt`):

| Indicador | Resultado | Referencia |
|---|---:|---:|
| Pobreza monetaria nacional | 27.58% | 27.6% |
| Pobreza urbana | 24.81% | 24.8% |
| Pobreza rural | 39.30% | 39.3% |
| Residentes habituales | 108,664 | 108,664 |
| Unidades territoriales | 25 | 25 |

La pobreza se mide sobre los miembros del hogar (`p204 == 1`), que son los que cuenta `mieperho` en la sumaria, como hace el INEI. Con solo los residentes habituales sale 27.53%, también dentro de la tolerancia de 0.1 puntos; se reporta como control.

## 5. Fuentes y datos

| Fuente | Datos | Enlace |
|---|---|---|
| INEI | ENAHO 2024, módulo 34 (sumaria) | <https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip> |
| INEI | ENAHO 2024, módulo 02 (miembros del hogar) | <https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip> |
| Repositorio del curso | Límites departamentales | <https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson> |
| BCRP | Series estadísticas | <https://estadisticas.bcrp.gob.pe/estadisticas/series/> |

Los microdatos y el catálogo del BCRP se guardan en `datos/`, que Git ignora. Se descargan con:

```bash
uv run .claude/skills/limpiando-enaho/scripts/descargar.py --anio 2024 --modulos 34 02 --limites
```

## 6. Instalación

Requiere [uv](https://docs.astral.sh/uv/), Claude Code con sesión iniciada e internet.

```bash
git clone https://github.com/nicosil02/agente-socioeconomico-peru
cd agente-socioeconomico-peru/tarea_4
uv sync
```

## 7. Conectar el MCP a Claude Code

`.mcp.json` ya declara el servidor:

```json
{"mcpServers": {"bcrp": {"command": "uv", "args": ["run", "mcp/server.py"]}}}
```

Abran `claude` dentro de `tarea_4/` y acepten el servidor del proyecto cuando lo pregunte. Con `/mcp` debe aparecer `bcrp` conectado con sus cinco herramientas. Prueben el recurso con `@bcrp:bcrp://serie/PN01273PM` y el prompt con `/mcp__bcrp__informe inflación`.

## 8. Reproducir el procesamiento y las pruebas

Desde `tarea_4/`:

```bash
# Pruebas del servidor MCP: 8 originales y 2 propias
uv run pytest -q mcp                                         # 10 passed

# Prueba de que la limpieza se detiene si falla una validación
uv run pytest -q .claude/skills/limpiando-enaho/scripts/test_limpiar.py

# ENAHO
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
uv run .claude/skills/graficando-enaho/scripts/graficar.py --anio 2024 --por area
uv run .claude/skills/graficando-enaho/scripts/graficar.py --anio 2024 --por sexo
uv run .claude/skills/graficando-enaho/scripts/graficar.py --anio 2024 --por departamento
uv run .claude/skills/mapeando-enaho/scripts/mapear.py --anio 2024

# Verificación independiente de las cifras del informe
uv run informes/verificar_cifras.py

# Evaluación con y sin MCP y Skills
uv run evaluacion/evaluar.py
```

## 9. Resultados de la evaluación

Las mismas 10 preguntas (4 del BCRP, 4 de la ENAHO y 2 combinadas), con respuestas verificadas en las fuentes oficiales antes de correr, en dos modos y con el mismo modelo (`sonnet`). El detalle está en `evaluacion/comparacion.md` y cada respuesta en `evaluacion/resultados.csv`.

| | Sin MCP ni Skills | Con MCP y Skills |
|---|---:|---:|
| Correctas | 2/10 | **10/10** |
| No respondidas | 8 | 0 |
| Incorrectas | 0 | 0 |
| Tiempo promedio por pregunta | 4.4 s | 9.9 s |

Sin herramientas, Claude Code casi siempre reconoce que no puede verificar la cifra y no responde; solo acierta dos datos muy difundidos. Con el MCP y las Skills responde todas, citando el código de serie o el archivo de `salidas/`. Una primera corrida dio 2 frente a 6 y destapó tres fallas que se corrigieron: un `argument-hint` mal formado que ocultaba `graficando-enaho`, una descripción de `limpiando-enaho` que no cubría preguntas de cifras y la falta de la pobreza extrema en `indicadores.csv`. Sus resultados se conservan en `evaluacion/resultados_corrida_1.csv`.

## 10. Limitaciones y problemas encontrados

- **Diferentes niveles de agregación.** Las series del BCRP son nacionales y la ENAHO es un corte de 2024; el informe describe asociaciones, no causas.
- **Estimaciones sin intervalos.** Las tasas de la ENAHO son puntuales; diferencias pequeñas entre departamentos o por sexo pueden no ser significativas. Por eso el gráfico por sexo dice "similar" cuando la brecha es menor a un punto.
- **Base de la pobreza.** El filtro de residentes habituales del enunciado da 108,664 personas y 27.53% de pobreza; la cifra oficial (27.6%) se reproduce sobre los miembros del hogar. Se documentan ambas.
- **API del BCRP.** Cuando recibe muchos pedidos seguidos responde una página HTML en vez de datos. El servidor reintenta y guarda en caché, pero una corrida puede fallar si la API está caída; en una ocasión fallaron todas las pruebas por eso y pasaron al reintentar.
- **Empleo formal.** `PN31879GM` cuenta puestos de trabajo formales, no personas ni empleo informal.
- **Aislamiento del modo sin herramientas.** `--bare` exige una API key, así que el modo A se aisló con una carpeta vacía, sin herramientas, sin MCP, sin skills ni comandos y sin ajustes de usuario. Una pregunta de prueba confirmó que no tenía cifras ni memoria en su contexto.

## 11. Ejemplo de una ejecución completa

`evidencias_ia/integracion/ejecucion_resumen.md` describe una ejecución real con el pedido de `evidencias_ia/integracion/pedido.md`:

```bash
claude -p "$(cat evidencias_ia/integracion/pedido.md)" --output-format stream-json --verbose \
  --strict-mcp-config --mcp-config .mcp.json \
  --allowedTools "mcp__bcrp,Skill,Read,Write,Edit,Glob,Bash(uv run *)"
```

En una sola ejecución el agente usó 5 herramientas del MCP y las 3 Skills, y escribió `informes/informe_final.md`. La pregunta fue:

> ¿Cuánto se recuperaron la producción y el empleo del Perú después de la caída de 2020, y qué tan desigual era la pobreza entre zonas urbanas y rurales y entre departamentos en 2024?

Principales resultados: el PBI real cayó 10.93% en 2020 y en 2024 era 7.14% mayor que en 2019; el empleo formal promedio de 2024 superó en 12.23% al de 2019; la pobreza rural (39.30%) superaba a la urbana (24.81%) por 14.5 puntos; y por departamento iba de 6.0% en Ica a 45.0% en Cajamarca. La sección 8 del informe verifica ocho cifras por un camino independiente.

## 12. Evidencias del uso de inteligencia artificial

El proyecto se desarrolló con Claude Code. `evidencias_ia/` contiene:

| Carpeta | Contenido |
|---|---|
| `evidencias_ia/conversacion_desarrollo.md` | Exportación completa de la conversación de desarrollo: servidor MCP, Skills, integración, evaluación, correcciones e informe. Se ocultaron correos y datos personales |
| `evidencias_ia/README.md` | Índice: en qué parte de la conversación está cada etapa |
| `evidencias_ia/mcp/` | Salida de las pruebas del servidor y de la limpieza |
| `evidencias_ia/skills/` | Activación de las Skills por lenguaje natural (`coordinacion_mapa.jsonl`) e invocación directa (`invocacion_graficos.jsonl`) |
| `evidencias_ia/integracion/` | Pedido, registro completo y resumen de la ejecución integrada, y prueba de manejo de errores |
| `evidencias_ia/evaluacion/` | Registro de cada llamada de la evaluación, por corrida y modo, y la salida de consola |

## Estructura

```text
tarea_4/
├── README.md, pyproject.toml, uv.lock, .mcp.json, .gitignore
├── mcp/                 server.py, test_server.py
├── .claude/skills/      limpiando-enaho, graficando-enaho, mapeando-enaho
├── datos/               microdatos y catálogo (ignorados por Git)
├── salidas/             validacion.txt, indicadores.csv, mapa_vs_referencia_2024.csv
├── figuras/  mapas/
├── evaluacion/          preguntas.csv, evaluar.py, resultados.csv, resultados_corrida_1.csv, comparacion.md
├── informes/            informe_final.md, verificar_cifras.py
└── evidencias_ia/       mcp/, skills/, integracion/, evaluacion/
```
