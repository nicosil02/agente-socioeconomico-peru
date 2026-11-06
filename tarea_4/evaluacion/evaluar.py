"""¿Mejoran el MCP y las Skills las respuestas de Claude Code? Las mismas 10 preguntas en dos modos.

    uv run evaluacion/evaluar.py                     # los dos modos, con sonnet
    uv run evaluacion/evaluar.py --modos A --modelo haiku

Modo A, sin MCP ni Skills: claude -p sin ninguna herramienta, sin servidores MCP, sin skills ni comandos, sin los
ajustes de usuario y desde una carpeta temporal vacía. No puede leer archivos del proyecto con respuestas calculadas.
Modo B, con MCP y Skills: claude -p desde tarea_4/, con el servidor bcrp de .mcp.json, las skills de .claude/skills/,
y Read, Glob y Bash limitado a "uv run" para que las skills ejecuten sus scripts. Tampoco carga ajustes de usuario
y no puede leer evidencias_ia/, evaluacion/ ni informes/, donde hay respuestas ya calculadas; sí lee las salidas/
que producen sus skills.

Cada pregunta se hace en una sesión nueva y sin guardar historial, con la misma instrucción y el mismo modelo.
Escribe evaluacion/resultados.csv y el registro completo de cada llamada en
evidencias_ia/evaluacion/<corrida>/<modo>/<id>.jsonl. Los registros se escriben primero fuera del proyecto y se copian
al terminar, para que ninguna llamada pueda leer las respuestas de otra.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
REGISTROS = RAIZ / "evidencias_ia" / "evaluacion"
TEMPORAL = Path(tempfile.mkdtemp(prefix="evaluacion_registros_"))
ESQUEMA = {"type": "object", "required": ["valor", "fuente"],
           "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                          "fuente": {"type": "string"}}}
INSTRUCCION = ("Responde con un solo número en «valor», en la unidad que pide la pregunta. Si no puedes saberlo "
               "con certeza, pon valor null: no estimes. En «fuente» di de dónde sale la cifra.\n\n")
VACIA = Path(tempfile.mkdtemp(prefix="evaluacion_modo_A_"))
MODOS = {
    "A": {"cwd": VACIA, "args": ["--tools", "", "--strict-mcp-config", "--disable-slash-commands",
                                 "--setting-sources", "project"],
          "herramientas": "ninguna (sin herramientas integradas, sin MCP, sin skills, carpeta vacía)"},
    "B": {"cwd": RAIZ, "args": ["--tools", "Skill,Read,Glob,Bash", "--strict-mcp-config",
                                "--mcp-config", str(RAIZ / ".mcp.json"), "--setting-sources", "project",
                                "--allowedTools", "mcp__bcrp,Skill,Read,Glob,Bash(uv run *)",
                                "--disallowedTools", "Read(./evidencias_ia/**),Read(./evaluacion/**),Read(./informes/**)"],
          "herramientas": "MCP bcrp, skills limpiando/graficando/mapeando-enaho, Read, Glob y Bash(uv run *)"},
}


def preguntar(q, modo, modelo):
    """Hace una pregunta en una sesión nueva y devuelve la respuesta, las herramientas usadas y el tiempo."""
    cmd = ["claude", "-p", INSTRUCCION + q.pregunta, "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo, *MODOS[modo]["args"]]
    t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=900,
                              cwd=MODOS[modo]["cwd"], stdin=subprocess.DEVNULL)
        texto, error = proc.stdout, ("" if proc.returncode == 0 else proc.stderr[-300:])
    except subprocess.TimeoutExpired:
        texto, error = "", "sin respuesta en 15 minutos"
    segundos = round(time.time() - t, 1)
    carpeta = TEMPORAL / modo
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{q.id}.jsonl").write_text(texto, encoding="utf-8")

    herramientas, final = [], {}
    for linea in texto.splitlines():
        try:
            e = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "assistant":
            herramientas += [c["name"] for c in e["message"]["content"] if c.get("type") == "tool_use"
                             and c["name"] not in ("ToolSearch", "StructuredOutput")]   # no son consultas
        if e.get("type") == "result":
            final = e
    r = final.get("structured_output") or {}
    if not final:
        error = error or "sin evento de resultado"
    usadas = sorted({h.replace("mcp__bcrp__", "mcp:") for h in herramientas})
    return {"valor": r.get("valor"), "unidad_respuesta": r.get("unidad", ""), "fuente": r.get("fuente", ""),
            "herramientas": "; ".join(usadas), "llamadas": len(herramientas), "segundos": segundos,
            "turnos": final.get("num_turns"), "error": error}


def calificar(q, r):
    """acierta si el valor está dentro de la tolerancia; en las combinadas, además, la fuente cita ambas fuentes."""
    if r["valor"] is None:
        return "no responde"
    if abs(r["valor"] - q.verdad) > q.tolerancia:
        return "se equivoca"
    if q.tipo == "Combinada":
        fuente = r["fuente"].upper()
        if "BCRP" not in fuente or not ("ENAHO" in fuente or "INEI" in fuente):
            return "se equivoca"
    return "acierta"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=list(MODOS))
    p.add_argument("--modelo", default="sonnet")
    p.add_argument("--paralelo", type=int, default=4)
    p.add_argument("--corrida", default="corrida_2", help="carpeta de evidencias_ia/evaluacion/ para los registros")
    a = p.parse_args()

    preguntas = pd.read_csv(AQUI / "preguntas.csv")
    casos = [(q, m) for m in a.modos for q in preguntas.itertuples()]
    print(f"{len(casos)} llamadas a claude -p con {a.modelo}...")
    with ThreadPoolExecutor(a.paralelo) as ex:
        respuestas = list(ex.map(lambda c: preguntar(c[0], c[1], a.modelo), casos))

    filas = [{"id": q.id, "tipo": q.tipo, "modo": m, "modelo": a.modelo, "pregunta": q.pregunta,
              "respuesta_esperada": q.verdad, "unidad": q.unidad, "tolerancia": q.tolerancia,
              "respuesta_generada": r["valor"], "fuente_citada": r["fuente"], "herramientas_usadas": r["herramientas"],
              "herramientas_habilitadas": MODOS[m]["herramientas"], "resultado": calificar(q, r),
              "segundos": r["segundos"], "turnos": r["turnos"], "llamadas_a_herramientas": r["llamadas"],
              "error": r["error"]} for (q, m), r in zip(casos, respuestas)]
    res = pd.DataFrame(filas)
    shutil.copytree(TEMPORAL, REGISTROS / a.corrida, dirs_exist_ok=True)
    anterior = AQUI / "resultados.csv"
    if anterior.exists() and set(a.modos) != set(MODOS):   # al correr un solo modo se conserva el otro
        viejo = pd.read_csv(anterior)
        res = pd.concat([viejo[~viejo.modo.isin(a.modos)], res], ignore_index=True)
    res.to_csv(anterior, index=False, encoding="utf-8")

    print("\n" + res.pivot(index="id", columns="modo", values="respuesta_generada").to_string())
    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos_promedio"] = res.groupby("modo").segundos.mean().round(1)
    print("\n" + tabla.to_string())
