"""Tests de MotoGP (sources/motogp.py). La API de motogp.com se simula: no se usa internet."""

import types
from typing import Any

import pytest

from panel_diario.sources import comun, motogp

TEMPORADA = "t26"
EVENTOS = [
    {"id": "e3", "name": "GRAND PRIX OF PORTUGAL", "date_end": "2026-11-22", "status": "NOT-STARTED", "test": False},
    {"id": "e1", "name": "GRAND PRIX OF MALAYSIA", "date_end": "2026-11-01", "status": "FINISHED", "test": False},
    {"id": "e2", "name": "GRAND PRIX OF QATAR", "date_end": "2026-11-08", "status": "FINISHED", "test": False},
    {"id": "t1", "name": "TEST ", "date_end": "2026-11-30", "status": "NOT-STARTED", "test": True},
]


class MotoGPFalso:
    def __init__(self, eventos: list[dict], con_carrera: bool = True) -> None:
        self.eventos = eventos
        self.con_carrera = con_carrera
        self.sesiones_pedidas: list[dict] = []

    def __call__(self, url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        path = url.removeprefix(motogp.API)
        datos: Any
        if path == "seasons":
            datos = [{"id": "t25", "current": False}, {"id": TEMPORADA, "current": True}]
        elif path == "events":
            assert params == {"seasonUuid": TEMPORADA}
            datos = self.eventos
        elif path == "categories":
            datos = [{"id": "moto2", "legacy_id": 2}, {"id": "motogp", "legacy_id": 3}]
        elif path == "sessions":
            self.sesiones_pedidas.append(params or {})
            datos = [{"id": "spr", "type": "SPR"}] + ([{"id": "rac", "type": "RAC"}] if self.con_carrera else [])
        elif path == "session/rac/classification":
            datos = {"classification": [{"rider": {"full_name": "Pilot A"}}, {"rider": {"full_name": "Pilot B"}}]}
        else:
            raise AssertionError(path)
        return types.SimpleNamespace(json=lambda: datos)


def test_proximo_gp_y_ganador_de_la_carrera_del_ultimo(monkeypatch: pytest.MonkeyPatch) -> None:
    falso = MotoGPFalso(EVENTOS)
    monkeypatch.setattr(comun, "get", falso)
    r = motogp.obtener_motogp()
    assert r["proxim"] == {"nom": "Grand Prix of Portugal", "data": "dg 22/11"}  # no el test, aunque no se ha corrido
    assert r["ultim"] == {"nom": "Grand Prix of Qatar", "guanyador": "Pilot A"}
    assert falso.sesiones_pedidas == [{"eventUuid": "e2", "categoryUuid": "motogp"}]  # la categoría MotoGP


def test_fin_de_temporada_sin_proximo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", MotoGPFalso([e for e in EVENTOS if e["status"] == "FINISHED"]))
    r = motogp.obtener_motogp()
    assert r["proxim"] is None and r["ultim"]["guanyador"] == "Pilot A"


def test_sin_carrera_larga_no_hay_ganador(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", MotoGPFalso(EVENTOS, con_carrera=False))
    assert motogp.obtener_motogp()["ultim"] is None


def test_nombre_del_gp() -> None:
    assert motogp.gp_name("GRAND PRIX OF VALENCIA ") == "Grand Prix of Valencia"
