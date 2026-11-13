"""Tests del estado y la caché del panel (state.py)."""

import json
from pathlib import Path

import pytest

from panel_diario import VERSION, state


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    ruta = tmp_path / "cache.json"
    monkeypatch.setattr(state, "CACHE", ruta)
    return ruta


def test_arranca_con_la_cache_de_la_misma_version(cache: Path) -> None:
    cache.write_text(json.dumps({"version": VERSION, "secciones": {"llum": {"ara": 0.1}}, "leidos": ["u"]}))
    assert state.Estado().datos["secciones"] == {"llum": {"ara": 0.1}}


def test_la_cache_de_otra_version_no_se_pinta(cache: Path) -> None:
    # Una versión anterior puede haber guardado una sección con otro formato (p. ej. los carburantes
    # con "gasolineres"): si su fuente falla al arrancar, el panel no la sabría pintar.
    viejo = {"secciones": {"carburants": {"gasolineres": []}}, "errores": {"x": "y"}, "leidos": ["u"]}
    cache.write_text(json.dumps(viejo))
    datos = state.Estado().datos
    assert datos["secciones"] == {} and datos["errores"] == {}
    assert datos["leidos"] == ["u"]  # lo leído no depende del formato de las secciones


def test_la_cache_guarda_su_version(cache: Path) -> None:
    e = state.Estado()
    e.guardar()
    assert json.loads(cache.read_text())["version"] == VERSION


def test_cache_ilegible_se_ignora(cache: Path) -> None:
    cache.write_text("{no es json")
    assert state.Estado().datos["secciones"] == {}
