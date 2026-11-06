"""Si una validación esencial falla, limpiar.py debe detenerse y no guardar la base.

    uv run pytest .claude/skills/limpiando-enaho/scripts/test_limpiar.py
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import limpiar  # noqa: E402

DATOS = Path(__file__).parents[4] / "datos"


@pytest.mark.skipif(not list(DATOS.glob("*-Modulo34.zip")), reason="faltan los microdatos en datos/")
def test_una_falla_detiene_y_no_guarda(tmp_path, monkeypatch):
    oficial = {**limpiar.OFICIAL[2024], "pobreza": 30.0}   # referencia que no se puede cumplir
    monkeypatch.setitem(limpiar.OFICIAL, 2024, oficial)
    monkeypatch.setattr(sys, "argv", ["limpiar.py", "--anio", "2024", "--datos", str(DATOS), "--salidas", str(tmp_path)])
    with pytest.raises(SystemExit, match="ERROR"):
        limpiar.main()
    assert "[FALLA] Pobreza nacional" in (tmp_path / "validacion.txt").read_text(encoding="utf-8")
    assert not (tmp_path / "personas_2024.parquet").exists()
