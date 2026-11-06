Pregunta de investigación: ¿Cuánto se recuperaron la producción y el empleo del Perú después de la caída de 2020, y qué tan desigual era la pobreza entre zonas urbanas y rurales y entre departamentos en 2024?

Trabaja como agente de investigación socioeconómica, en este orden:

1. Plan. Antes de usar herramientas, escribe un plan breve: qué fuente responde cada parte de la pregunta y qué indicadores vas a construir.
2. BCRP, con las herramientas del MCP bcrp. Busca con buscar_series una serie del PBI real y una del empleo formal. Obtén sus cifras de 2019 a 2024 con resumen y comparar_periodos (2019 frente a 2024) y haz un gráfico con graficar_serie. Cada cifra va con su código de serie, periodo y URL de la fuente.
3. ENAHO 2024, con las skills del proyecto. Usa limpiando-enaho, graficando-enaho para el área y para el departamento, y mapeando-enaho.
4. Contrasta: revisa que las cifras de ENAHO pasen las validaciones de salidas/validacion.txt y que las del BCRP salgan de las herramientas, no de memoria.
5. Escribe informes/informe_final.md con estas secciones:
   1. Pregunta de investigación: tema, objetivo y delimitación.
   2. Fuentes y metodología: datos, procesamiento e indicadores.
   3. Resultados: al menos 3 hallazgos, cada uno con sus cifras.
   4. Visualizaciones: el gráfico del BCRP, un gráfico de ENAHO y el mapa, con rutas relativas (../figuras/..., ../mapas/...).
   5. Interpretación: los patrones principales.
   6. Limitaciones: cobertura temporal, calidad de los datos y alcance de las conclusiones.
   7. Reproducibilidad: scripts, archivos, códigos de serie y comandos.

Reglas:
- Toda cifra del informe debe poder rastrearse: código de serie del BCRP o archivo de salidas/.
- No calcules a mano ni completes con lo que recuerdes. Si una herramienta falla o no encuentra datos, dilo en Limitaciones.
- Las series del BCRP son nacionales y la ENAHO es un corte de 2024: describe asociaciones, nunca causas.
- Escribe en español, con frases claras, sin mencionar al asistente que hizo el trabajo.
