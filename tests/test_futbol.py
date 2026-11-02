"""Tests de los partidos del equipo configurado (datos.obtener_futbol).

football-data.org se sustituye por una respuesta inventada (mock): no se usa internet.
"""

import types
from typing import Any

import pytest

from panel_diario import datos

CFG = {"futbol": {"nombre": "Equip d'exemple", "football_data_api_key": "clave-falsa", "team_id": 1}}


def partido(fecha: str, estado: str, local_id: int, visitante_id: int, goles: tuple[int, int] | None = None) -> dict:
    return {
        "utcDate": fecha,
        "status": estado,
        "homeTeam": {"id": local_id, "shortName": f"Equip {local_id}"},
        "awayTeam": {"id": visitante_id, "shortName": f"Equip {visitante_id}"},
        "competition": {"name": "Primera Division"},
        "score": {"fullTime": {"home": goles[0], "away": goles[1]} if goles else {}},
    }


def con_respuesta(monkeypatch: pytest.MonkeyPatch, partidos: list[dict]) -> list[tuple[str, Any]]:
    pedidos: list[tuple[str, Any]] = []

    def get_falso(url: str, **kw: Any) -> types.SimpleNamespace:
        pedidos.append((url, kw.get("headers")))
        return types.SimpleNamespace(json=lambda: {"matches": partidos})

    monkeypatch.setattr(datos, "_get", get_falso)
    return pedidos


def test_proximos_y_ultimo_desde_el_punto_de_vista_del_equipo(monkeypatch: pytest.MonkeyPatch) -> None:
    pedidos = con_respuesta(
        monkeypatch,
        [
            partido("2026-10-20T19:00:00Z", "FINISHED", 2, 1, goles=(0, 3)),  # fuera: gana 3-0
            partido("2026-11-10T19:00:00Z", "TIMED", 1, 3),
            partido("2026-11-03T19:00:00Z", "TIMED", 4, 1),
        ],
    )
    r = datos.obtener_futbol(CFG)
    assert pedidos[0][0].endswith("/teams/1/matches")
    assert pedidos[0][1] == {"X-Auth-Token": "clave-falsa"}
    assert r["nombre"] == "Equip d'exemple"
    assert [p["rival"] for p in r["proximos"]] == ["Equip 4", "Equip 3"]  # ordenados por fecha
    assert r["ultimo"]["goles_equipo"] == 3 and r["ultimo"]["goles_rival"] == 0
    assert r["ultimo"]["competicion"] == "Lliga"


def test_sin_clave_no_llama_a_la_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(datos, "_get", lambda *a, **k: pytest.fail("no debe llamar a la API"))
    cfg = {"futbol": {"nombre": "Equip", "football_data_api_key": " ", "team_id": 1}}
    assert datos.obtener_futbol(cfg) == {"sin_clave": True, "nombre": "Equip"}


def test_sin_equipo_no_llama_a_la_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(datos, "_get", lambda *a, **k: pytest.fail("no debe llamar a la API"))
    cfg = {"futbol": {"football_data_api_key": "clave-falsa"}}
    assert datos.obtener_futbol(cfg) == {"sin_equipo": True, "nombre": "Futbol"}
