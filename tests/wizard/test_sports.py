"""Tests del paso de deportes del asistente (wizard/sports.py). ESPN se simula."""

import types
from typing import Any

import pytest
import requests

from panel_diario.catalog import sports as catalogo
from panel_diario.sources import comun
from panel_diario.wizard import sports

EQUIPO = {"lliga": "soccer/esp.1", "id": "83", "nom": "Equip d'exemple"}


def _respuesta(*equipos: tuple[int, str]) -> types.SimpleNamespace:
    datos = {"sports": [{"leagues": [{"teams": [{"team": {"id": i, "displayName": n}} for i, n in equipos]}]}]}
    return types.SimpleNamespace(json=lambda: datos)


def test_desplegable_con_deportes_de_equipos_y_de_motor() -> None:
    o = sports.options()
    assert [e["id"] for e in o["esports"]] == [*catalogo.SPORTS, *catalogo.MOTOR]
    assert {e["id"]: e["tipus"] for e in o["esports"]}["motogp"] == "motor"
    assert {e["id"]: e["tipus"] for e in o["esports"]}["futbol"] == "equips"
    assert o["lligues"][0] == {"path": "soccer/esp.1", "nom": "LaLiga"}


def test_todos_los_equipos_del_deporte_sin_elegir_competicion(monkeypatch: pytest.MonkeyPatch) -> None:
    """El mismo equipo en la liga y en la Champions sale una vez, con su liga; el resto, por orden."""
    por_liga = {
        "soccer/esp.1": _respuesta((83, "Barcelona"), (86, "Real Madrid")),
        "soccer/uefa.champions": _respuesta((83, "Barcelona"), (5, "Ajax")),
    }
    pedidas: list[str] = []

    def get(url: str, **k: Any) -> types.SimpleNamespace:
        path = url.split("/sports/")[1].removesuffix("/teams")
        pedidas.append(path)
        return por_liga.get(path, _respuesta())

    monkeypatch.setattr(comun, "get", get)
    equipos = sports.teams("futbol")
    assert [(e["nom"], e["lliga"]) for e in equipos] == [
        ("Ajax", "soccer/uefa.champions"),
        ("Barcelona", "soccer/esp.1"),
        ("Real Madrid", "soccer/esp.1"),
    ]
    assert equipos[1]["competicio"] == "LaLiga"
    assert sorted(pedidas) == sorted(lg.path for lg in catalogo.leagues_of("futbol"))


def test_fuera_del_futbol_el_mismo_id_en_dos_ligas_son_dos_equipos(monkeypatch: pytest.MonkeyPatch) -> None:
    def get(url: str, **k: Any) -> types.SimpleNamespace:
        return _respuesta((3, "Equip NBA")) if "/nba/" in url else _respuesta((3, "Equip WNBA"))

    monkeypatch.setattr(comun, "get", get)
    assert [e["nom"] for e in sports.teams("basquet")] == ["Equip NBA", "Equip WNBA"]


def test_una_competicion_caida_no_deja_sin_equipos(monkeypatch: pytest.MonkeyPatch) -> None:
    def get(url: str, **k: Any) -> types.SimpleNamespace:
        if "esp.1" not in url:
            raise requests.ConnectionError("sin conexión")
        return _respuesta((83, "Barcelona"))

    monkeypatch.setattr(comun, "get", get)
    assert [e["nom"] for e in sports.teams("futbol")] == ["Barcelona"]


def test_si_no_responde_ninguna_se_explica(monkeypatch: pytest.MonkeyPatch) -> None:
    def get(url: str, **k: Any) -> types.SimpleNamespace:
        raise requests.ConnectionError("sin conexión")

    monkeypatch.setattr(comun, "get", get)
    with pytest.raises(RuntimeError, match="ESPN"):
        sports.teams("hoquei")


@pytest.mark.parametrize("esport", ["cricket", "f1", ""])
def test_deporte_sin_equipos_no_sale_a_internet(esport: str) -> None:
    with pytest.raises(ValueError):
        sports.teams(esport)


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"equips": [EQUIPO], "f1": True, "motogp": True}
    assert sports.current_choices(sports.build(respuesta)) == respuesta


def test_solo_motogp_vale() -> None:
    assert sports.build({"motogp": True}) == {"esports": {"equips": [], "f1": False, "motogp": True}}


def test_sin_deportes_en_config() -> None:
    assert sports.current_choices({}) == {"equips": [], "f1": False, "motogp": False}


@pytest.mark.parametrize(
    "respuesta",
    [
        {"equips": [], "f1": False, "motogp": False},
        {"equips": [{**EQUIPO, "lliga": "cricket/ipl"}]},
        {"equips": [{**EQUIPO, "id": ""}]},
        {"equips": [{**EQUIPO, "nom": " "}]},
    ],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        sports.build(respuesta)
