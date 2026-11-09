"""Tests del paso de deportes del asistente (wizard/sports.py). ESPN se simula."""

import types
from typing import Any

import pytest

from panel_diario.catalog import sports as catalogo
from panel_diario.sources import comun
from panel_diario.wizard import sports

EQUIPO = {"lliga": "soccer/esp.1", "id": "83", "nom": "Equip d'exemple"}


def test_opciones_con_deportes_y_competiciones() -> None:
    o = sports.options()
    assert [e["id"] for e in o["esports"]] == list(catalogo.SPORTS)
    assert o["lligues"][0] == {"path": "soccer/esp.1", "nom": "LaLiga", "esport": "futbol"}
    assert {lg["esport"] for lg in o["lligues"]} == set(catalogo.SPORTS)  # cada deporte tiene competiciones


def test_equipos_de_una_competicion_ordenados(monkeypatch: pytest.MonkeyPatch) -> None:
    equipos = [{"team": {"id": 2, "displayName": "Zeta"}}, {"team": {"id": 1, "displayName": "Alfa"}}]
    datos = {"sports": [{"leagues": [{"teams": equipos}]}]}

    def get(url: str, **k: Any) -> types.SimpleNamespace:
        assert url.endswith("/sports/soccer/esp.1/teams")
        return types.SimpleNamespace(json=lambda: datos)

    monkeypatch.setattr(comun, "get", get)
    assert sports.teams("soccer/esp.1") == [{"id": "1", "nom": "Alfa"}, {"id": "2", "nom": "Zeta"}]


def test_competicion_desconocida_no_sale_a_internet() -> None:
    with pytest.raises(ValueError):
        sports.teams("cricket/ipl")


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"equips": [EQUIPO], "f1": True}
    assert sports.current_choices(sports.build(respuesta)) == respuesta


def test_sin_deportes_en_config() -> None:
    assert sports.current_choices({}) == {"equips": [], "f1": False}


@pytest.mark.parametrize(
    "respuesta",
    [
        {"equips": [], "f1": False},
        {"equips": [{**EQUIPO, "lliga": "cricket/ipl"}]},
        {"equips": [{**EQUIPO, "id": ""}]},
        {"equips": [{**EQUIPO, "nom": " "}]},
    ],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        sports.build(respuesta)
