# Ejecución integrada del agente

Una sola ejecución de Claude Code en modo no interactivo, con el pedido de `pedido.md`, el servidor MCP de `.mcp.json` y las skills de `.claude/skills/`. El registro completo, evento por evento, está en `ejecucion_agente.jsonl`.

```bash
claude -p "$(cat evidencias_ia/integracion/pedido.md)" --output-format stream-json --verbose --strict-mcp-config --mcp-config .mcp.json --allowedTools "mcp__bcrp,Skill,Read,Write,Edit,Glob,Bash(uv run *)"
```

- Herramientas MCP distintas: 5 (buscar_series, comparar_periodos, graficar_serie, resumen, serie), en 13 llamadas.
- Skills distintas: 3 (limpiando-enaho, graficando-enaho, mapeando-enaho).
- Duración: 138 segundos, 35 turnos. Resultado: success.

| # | Herramienta | Argumentos |
|---|---|---|
| 1 | `Bash` | `{"command": "cd \"C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4\" && ls -R \| grep -v \"^$\" \| head -80 && cat CLAUDE.md 2>/dev/null \| head -60 && cat evidenc` |
| 2 | `Glob` | `{"pattern": "**/*", "path": "C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4"}` |
| 3 | `mcp__bcrp__buscar_series` | `{"texto": "pbi", "frecuencia": "Anual"}` |
| 4 | `mcp__bcrp__buscar_series` | `{"texto": "empleo formal"}` |
| 5 | `mcp__bcrp__buscar_series` | `{"texto": "producto bruto interno 2007", "frecuencia": "Anual"}` |
| 6 | `Bash` | `{"command": "cd \"C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4\" && ls; ls salidas figuras mapas informes scripts datos 2>&1; ls .claude/skills; cat salidas` |
| 7 | `mcp__bcrp__serie` | `{"codigo": "PM04860AA", "desde": "2019", "hasta": "2024"}` |
| 8 | `mcp__bcrp__resumen` | `{"codigo": "PM04860AA", "desde": "2019", "hasta": "2024"}` |
| 9 | `mcp__bcrp__resumen` | `{"codigo": "PM04860AA", "desde": "2019", "hasta": "2020"}` |
| 10 | `mcp__bcrp__comparar_periodos` | `{"codigo": "PM04860AA", "desde_a": "2019", "hasta_a": "2019", "desde_b": "2024", "hasta_b": "2024"}` |
| 11 | `mcp__bcrp__resumen` | `{"codigo": "PN31879GM", "desde": "2019-01", "hasta": "2024-12"}` |
| 12 | `mcp__bcrp__comparar_periodos` | `{"codigo": "PN31879GM", "desde_a": "2019-01", "hasta_a": "2019-12", "desde_b": "2024-01", "hasta_b": "2024-12"}` |
| 13 | `mcp__bcrp__comparar_periodos` | `{"codigo": "PN31879GM", "desde_a": "2019-01", "hasta_a": "2019-12", "desde_b": "2020-01", "hasta_b": "2020-12"}` |
| 14 | `mcp__bcrp__resumen` | `{"codigo": "PM04860AA", "desde": "2019", "hasta": "2021"}` |
| 15 | `mcp__bcrp__graficar_serie` | `{"codigo": "PM04860AA", "desde": "2019", "hasta": "2024", "marcar": "2020", "titulo": "El PBI real cayó 10.9% en 2020 y en 2024 estaba 7.1% por encima de 2019"}` |
| 16 | `mcp__bcrp__graficar_serie` | `{"codigo": "PN31879GM", "desde": "2019-01", "hasta": "2024-12", "marcar": "2020-05", "titulo": "El empleo formal tocó su mínimo en mayo de 2020 y en 2024 promedió 12.2% más que en ` |
| 17 | `Skill` | `{"skill": "limpiando-enaho"}` |
| 18 | `Bash` | `{"command": "cd \"C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4\" && uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024", "description": "R` |
| 19 | `Skill` | `{"skill": "graficando-enaho"}` |
| 20 | `Bash` | `{"command": "cd \"C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4\" && uv run .claude/skills/graficando-enaho/scripts/graficar.py --anio 2024 --por area && uv ` |
| 21 | `Read` | `{"file_path": "figuras/pobreza_por_area_2024.png"}` |
| 22 | `Read` | `{"file_path": "figuras/pobreza_por_departamento_2024.png"}` |
| 23 | `Read` | `{"file_path": "figuras/bcrp_PM04860AA_2019_2024.png"}` |
| 24 | `Skill` | `{"skill": "mapeando-enaho"}` |
| 25 | `Bash` | `{"command": "cd \"C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4\" && uv run .claude/skills/mapeando-enaho/scripts/mapear.py --anio 2024; head -30 salidas/map` |
| 26 | `Read` | `{"file_path": "mapas/pobreza_departamento.png"}` |
| 27 | `Read` | `{"file_path": "informes/verificar_cifras.py"}` |
| 28 | `Bash` | `{"command": "cd \"C:/Users/Usuario/Documents/GitHub/agente-socioeconomico-peru/tarea_4\" && uv run informes/verificar_cifras.py", "description": "Run independent verification of re` |
| 29 | `Write` | `{"file_path": "informes/informe_final.md"}` |

La primera llamada a Bash fue rechazada por el permiso (`grep` no estaba autorizado) y el agente siguió con `Glob`. Al final ejecutó `informes/verificar_cifras.py`, el script de verificación independiente, para contrastar sus cifras.

`manejo_errores.jsonl` registra una segunda ejecución, solo con el MCP, en la que se piden una serie inexistente y un año sin datos: el agente informa el error de la herramienta y no da cifras.
