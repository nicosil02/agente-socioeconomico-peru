"""El contrato del servidor: si estas pruebas pasan, Claude Code y evaluar.py pueden usarlo.

    uv run pytest -q

Llaman al servidor en memoria, igual que lo haría Claude Code, y piden datos reales al BCRP.
"""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp


async def _con_cliente(f):
    async with Client(mcp) as c:
        return await f(c)


def llamar(herramienta, **args):
    return asyncio.run(_con_cliente(lambda c: c.call_tool(herramienta, args))).data


def test_buscar_encuentra_el_ipc():
    r = llamar("buscar_series", texto="ipc 12 meses", limite=5)
    assert "PN01273PM" in [x["codigo"] for x in r]
    assert {"codigo", "nombre", "frecuencia"} <= r[0].keys()


def test_cuatro_herramientas_como_minimo():
    nombres = {t.name for t in asyncio.run(_con_cliente(lambda c: c.list_tools()))}
    assert {"buscar_series", "serie", "resumen"} <= nombres
    assert len(nombres) >= 4, "falta su herramienta propia"


def test_serie_mensual():
    r = llamar("serie", codigo="PN01271PM", desde="2025-01", hasta="2025-12")
    assert len(r["datos"]) == 12
    assert r["datos"][0]["periodo"] == "2025-01"
    assert r["datos"][2]["valor"] == pytest.approx(0.81, abs=0.01)   # IPC de Lima, marzo de 2025
    assert r["fuente"].startswith("https://estadisticas.bcrp.gob.pe")


def test_serie_diaria():
    r = llamar("serie", codigo="PD04638PD", desde="2026-10-01", hasta="2026-10-15")
    assert r["datos"][0]["periodo"] == "2026-10-01"
    assert r["datos"][-1] == {"periodo": "2026-10-15", "valor": pytest.approx(3.428, abs=0.001)}


def test_resumen_sin_cuentas_a_mano():
    r = llamar("resumen", codigo="PN01273PM", desde="2025-12", hasta="2026-09")
    assert r["primero"]["valor"] == pytest.approx(1.51, abs=0.01)
    assert r["ultimo"]["valor"] == pytest.approx(4.55, abs=0.01)
    assert r["maximo"]["periodo"] == "2026-09"
    assert {"cambio", "variacion_pct", "promedio", "minimo"} <= r.keys()


def test_codigo_inexistente_da_un_error_claro():
    with pytest.raises(ToolError, match="XX999"):
        llamar("serie", codigo="XX999", desde="2025-01", hasta="2025-02")


def test_un_recurso():
    async def contar(c):
        return len(await c.list_resources()) + len(await c.list_resource_templates())
    assert asyncio.run(_con_cliente(contar)) >= 1


def test_un_prompt():
    assert len(asyncio.run(_con_cliente(lambda c: c.list_prompts()))) >= 1


# Pruebas propias: comparar_periodos

def test_comparar_periodos_con_cifras_oficiales():
    # verdades de evaluacion/preguntas.csv, revisadas en estadisticas.bcrp.gob.pe: inflación a 12 meses de Lima
    r = llamar("comparar_periodos", codigo="PN01273PM",
               desde_a="2025-12", hasta_a="2025-12", desde_b="2026-09", hasta_b="2026-09")
    assert r["periodo_a"]["promedio"] == pytest.approx(1.5088, abs=0.01)
    assert r["periodo_b"]["promedio"] == pytest.approx(4.5487, abs=0.01)
    assert r["diferencia_promedio"] == pytest.approx(4.5487 - 1.5088, abs=0.02)
    # un año solo en una serie mensual es el año completo
    r = llamar("comparar_periodos", codigo="PN01271PM", desde_a="2024", hasta_a="2024", desde_b="2025", hasta_b="2025")
    assert r["periodo_a"]["n"] == r["periodo_b"]["n"] == 12
    assert r["periodo_b"]["primero"]["periodo"] == "2025-01"


def test_comparar_periodos_sin_datos_da_error_claro():
    with pytest.raises(ToolError, match="PN01273PM"):
        llamar("comparar_periodos", codigo="PN01273PM",
               desde_a="1900-01", hasta_a="1900-12", desde_b="2025-01", hasta_b="2025-12")
    with pytest.raises(ToolError, match="Fecha no válida"):
        llamar("comparar_periodos", codigo="PN01273PM",
               desde_a="enero 2024", hasta_a="2024-12", desde_b="2025-01", hasta_b="2025-12")
