# ¿Mejoran el MCP y las Skills las respuestas de Claude Code?

## Diseño

- **Preguntas.** 10, en `preguntas.csv`: 4 del BCRP, 4 de la ENAHO 2024 y 2 que combinan ambas fuentes. Cada respuesta esperada salió de la fuente oficial por un camino independiente del agente (la API pública del BCRP y la sumaria original de la ENAHO), con su tolerancia. El archivo se registró en Git (commit `8b72e8f`) antes de la primera corrida y no se cambió después.
- **Criterio.** Una respuesta acierta si el valor está dentro de la tolerancia. En las combinadas, además, la fuente citada debe nombrar al BCRP y a la ENAHO o el INEI, para comprobar que la cifra se armó con ambas fuentes. Si el modelo devuelve `null`, cuenta como no respondida.
- **Condiciones.** El mismo modelo (`sonnet`), la misma instrucción («responde con un solo número; si no puedes saberlo con certeza, pon null; di de dónde sale la cifra») y una sesión nueva por pregunta, sin historial (`--no-session-persistence`). Ninguno de los dos modos carga los ajustes ni los hooks del usuario (`--setting-sources project`).

| | Modo A, sin MCP ni Skills | Modo B, con MCP y Skills |
|---|---|---|
| Herramientas habilitadas | Ninguna: `--tools ""`, sin MCP (`--strict-mcp-config`), sin skills ni comandos (`--disable-slash-commands`) | Servidor MCP `bcrp`, las 3 skills, `Read`, `Glob` y `Bash` limitado a `uv run` |
| Carpeta de trabajo | Carpeta temporal vacía | `tarea_4/` |
| Acceso a respuestas ya calculadas | Ninguno. Una pregunta de control confirmó que no tenía cifras, memoria ni notas en su contexto | Bloqueada la lectura de `evidencias_ia/`, `evaluacion/` e `informes/`. Sí puede leer `salidas/`, que es lo que producen sus skills |

El script es `evaluar.py` y el registro completo de cada llamada está en `evidencias_ia/evaluacion/<corrida>/<modo>/<id>.jsonl`.

## Resultados

Se hicieron dos corridas. La primera reveló fallas del sistema (ver abajo), se corrigieron y se repitieron los dos modos. Los resultados de ambas se conservan: `resultados_corrida_1.csv` y `resultados.csv` (corrida 2, la definitiva).

| | Corrida 1, modo A | Corrida 1, modo B | Corrida 2, modo A | Corrida 2, modo B |
|---|---:|---:|---:|---:|
| Correctas | 2 | 6 | 2 | **10** |
| Incorrectas | 1 | 0 | 0 | 0 |
| No respondidas | 7 | 4 | 8 | 0 |
| BCRP (de 4) | 1 | 4 | 1 | 4 |
| ENAHO (de 4) | 1 | 1 | 1 | 4 |
| Combinadas (de 2) | 0 | 1 | 0 | 2 |
| Tiempo promedio por pregunta | 4.1 s | 11.5 s | 4.4 s | 9.9 s |
| Tiempo máximo | 5.7 s | 21.1 s | 6.2 s | 18.2 s |

### Pregunta por pregunta, corrida 2

| Pregunta | Esperada | Modo A | Modo B | Herramientas del modo B |
|---|---:|---:|---:|---|
| Inflación 12 meses, Lima, set. 2026 (%) | 4.5487 | no responde | 4.55 ✔ | `buscar_series`, `serie` |
| Tasa de referencia, set. 2026 (%) | 4.25 | no responde | 4.25 ✔ | `buscar_series`, `serie` |
| PBI real 2020 (%) | −10.93 | −11.0 ✔ | −10.93 ✔ | `buscar_series`, `serie` |
| Puestos formales, promedio 2024 (miles) | 5,907.78 | no responde | 5,907.78 ✔ | `buscar_series`, `resumen` |
| Pobreza nacional 2024 (%) | 27.58 | 27.6 ✔ | 27.6 ✔ | ninguna (de memoria) |
| Pobreza rural 2024 (%) | 39.30 | no responde | 39.30 ✔ | lee `salidas/indicadores.csv` |
| Pobreza extrema 2024 (%) | 5.50 | no responde | 5.50 ✔ | lee `salidas/indicadores.csv` |
| Pobreza en Cajamarca 2024 (%) | 45.01 | no responde | 45.00 ✔ | lee la referencia de la sesión y `salidas/` |
| PBI real por persona 2024 (S/ de 2007) | 16,982.95 | no responde | 16,982.95 ✔ | `buscar_series`, `serie` y `salidas/indicadores.csv` |
| Personas pobres 2024 (millones) | 9.39 | no responde | 9.39 ✔ | `buscar_series`, `serie` y `salidas/indicadores.csv` |

**Mejoraron** 8 preguntas: todas menos el PBI de 2020 y la pobreza nacional, que ambos modos acertaron. **Ninguna empeoró.**

## Principales errores

**Modo A.** Casi nunca inventa: en la corrida 2 se negó a responder 8 de 10 preguntas porque no podía verificarlas. Sí acertó de memoria dos cifras muy difundidas, la caída del PBI en 2020 (−11.0%) y la pobreza de 2024 (27.6%). En la corrida 1 dio una cifra equivocada con aparente seguridad: pobreza rural de 39.8% frente al 39.3% oficial, citando un informe del INEI que dijo recordar. Las preguntas posteriores a junio de 2026, como la inflación de setiembre, quedan fuera de su conocimiento.

**Modo B, corrida 1.** Cuatro preguntas sin respuesta, por tres fallas del sistema que se corrigieron:
1. La skill `graficando-enaho` no cargaba: su `argument-hint` (`[area|sexo|edad|departamento] [año]`) no era YAML válido, así que Claude Code no leía su descripción. Se pusieron entre comillas los `argument-hint` de las tres skills.
2. Ante preguntas de cifras, el agente no reconocía que `limpiando-enaho` le servía, porque su descripción hablaba de limpiar y unir. Se amplió la descripción a «cualquier cifra de pobreza monetaria o pobreza extrema según la ENAHO».
3. La pobreza extrema no estaba en `salidas/indicadores.csv`. Se agregó la columna `pobreza_extrema_pct`.

Además, en una pregunta el agente leyó los registros del modo A, porque se estaban guardando dentro del proyecto. En la corrida 2 los registros se escriben fuera del proyecto y se copian al terminar, y el modo B no puede leer `evidencias_ia/`, `evaluacion/` ni `informes/`.

**Modo B, corrida 2.** Las 10 son correctas, con cuatro matices:
- **En ENAHO no volvió a ejecutar las skills.** Leyó `salidas/indicadores.csv` y `salidas/validacion.txt`, que produce `limpiando-enaho` y que ya estaban validados. Las cifras salen de la skill, pero de una ejecución anterior. La ejecución de las skills dentro del agente está en `evidencias_ia/integracion/` y `evidencias_ia/skills/`.
- **Pobreza nacional.** La respondió de memoria (27.6), igual que el modo A. Acertó, pero no por usar herramientas.
- **Cajamarca.** Respondió 45.00 a partir de la referencia de la sesión (`referencia_pobreza_2024.csv`) y de la comparación del mapa, en vez del valor propio de 45.01. Está dentro de la tolerancia.
- **README.** En una pregunta buscó la palabra «pobreza» en el README, que también tiene cifras. La respuesta (9.39 millones) se armó con `salidas/indicadores.csv` y la serie de población del BCRP, según su fuente citada.

## Uso de herramientas y tiempo

El modo B tardó en promedio 9.9 segundos por pregunta en la corrida 2, frente a 4.4 del modo A: unos 5.5 segundos más por buscar la serie, consultar la API o leer las salidas. En las del BCRP siempre usó `buscar_series` y después `serie` o `resumen`. En las combinadas unió ambas fuentes: el PBI o la población del BCRP mediante el MCP, y la población o la tasa de pobreza de la ENAHO desde las salidas de la skill.

## Conclusión

Con el MCP y las Skills, Claude Code pasó de 2 a 10 respuestas correctas sobre 10, a cambio de unos 5 segundos más por pregunta. La mejora no se explica porque sin herramientas invente mucho: el modo A casi siempre reconoce que no sabe. Se explica porque con herramientas puede responder lo que sin ellas no puede verificar, sobre todo cifras recientes del BCRP y cálculos sobre microdatos. Para las cifras de la ENAHO, el aporte central son las salidas validadas que produce `limpiando-enaho`. La corrida 1 mostró que una skill solo ayuda si su descripción coincide con cómo se formulan las preguntas, y que un error de formato puede dejarla invisible.

Límites del experimento: son solo 10 preguntas y una corrida definitiva por modo, así que no mide la variación entre corridas. Las preguntas del modo B pueden apoyarse en salidas ya calculadas por las skills, que es como funciona el sistema, pero no mide el costo de recalcular desde cero.
