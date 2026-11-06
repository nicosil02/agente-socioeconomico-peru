# Evidencias del uso de inteligencia artificial

El proyecto se desarrolló con Claude Code. La conversación completa de desarrollo está exportada en `conversacion_desarrollo.md`, en orden cronológico, con correos, teléfonos y la ruta del usuario ocultos.

| Etapa | Dónde está en la conversación | Evidencias adicionales |
|---|---|---|
| Lectura del enunciado y estructura del repositorio | Primeros mensajes: «Volviendo a las tareas del diplomado…» y «La estructura es esa de acuerdo con lo planteado por el issue?» | — |
| Servidor MCP (Parte 1) | Desde «Pero ya está corroborado que el MCP sigue la lógica…» hasta el PR #5 | `mcp/pruebas.txt`: las 10 pruebas del servidor y la de la limpieza |
| Skills de ENAHO (Parte 2) | Desde el primer «Continua» hasta el PR #6 | `skills/coordinacion_mapa.jsonl` (pedido en lenguaje natural que ejecuta limpieza y mapa) y `skills/invocacion_graficos.jsonl` (invocación directa) |
| Integración y agente (Parte 3) | Desde «1 pero que sea más clara» hasta el PR #7 | `integracion/pedido.md`, `integracion/ejecucion_agente.jsonl`, `integracion/ejecucion_resumen.md` y `integracion/manejo_errores.jsonl` |
| Evaluación (Parte 4) | Desde la creación de `preguntas.csv` hasta el PR de la Parte 4 | `evaluacion/corrida_1/` y `evaluacion/corrida_2/`: el registro completo de cada una de las 40 llamadas y la consola |

Los archivos `.jsonl` son la salida `stream-json` de Claude Code: cada línea es un evento (mensaje, llamada a herramienta o resultado).
