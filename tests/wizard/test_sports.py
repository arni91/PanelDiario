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


def test_los_equipos_de_ligas_femeninas_se_distinguen_por_el_nombre(monkeypatch: pytest.MonkeyPatch) -> None:
    def get(url: str, **k: Any) -> types.SimpleNamespace:
        return _respuesta((19483, "Barcelona")) if "esp.w.1" in url else _respuesta((83, "Barcelona"))

    monkeypatch.setattr(comun, "get", get)
    equipos = {e["id"]: e["nom"] for e in sports.teams("futbol")}
    assert equipos == {"83": "Barcelona", "19483": "Barcelona (femení)"}


def test_fuera_del_futbol_el_mismo_id_en_dos_ligas_son_dos_equipos(monkeypatch: pytest.MonkeyPatch) -> None:
    def get(url: str, **k: Any) -> types.SimpleNamespace:
        return _respuesta((3, "Equip NBA")) if "/nba/" in url else _respuesta((3, "Equip WNBA"))

    monkeypatch.setattr(comun, "get", get)
    assert [e["nom"] for e in sports.teams("basquet")] == ["Equip NBA", "Equip WNBA (femení)"]


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


# --- «Un altre…»: buscar cualquier equipo por su nombre ---


def _buscador(*equipos: dict) -> dict:
    otros = {"type": "article", "contents": [{"displayName": "Una notícia"}]}
    return {"results": [otros, {"type": "team", "contents": list(equipos)}]}


CELTIC = {
    "uid": "s:600~t:256",
    "displayName": "Celtic",
    "sport": "soccer",
    "defaultLeagueSlug": "sco.1",
    "subtitle": "SPFL",
}
LEINSTER = {"uid": "s:300~t:25924", "displayName": "Leinster", "sport": "rugby", "defaultLeagueSlug": "270557"}
SIN_LIGA = {"uid": "s:200~t:2252", "displayName": "Equip de criquet", "sport": "cricket"}


def test_buscar_solo_ofrece_equipos_con_partidos(monkeypatch: pytest.MonkeyPatch) -> None:
    def get(url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        if url == sports.SEARCH_URL:
            assert params is not None and params["query"] == "celtic"
            datos: dict = _buscador(CELTIC, LEINSTER, SIN_LIGA)
        elif "teams/256/" in url:  # el Celtic tiene calendario; el Leinster, vacío
            partido = {
                "id": "1",
                "date": "2026-11-22T15:00Z",
                "competitions": [
                    {
                        "status": {"type": {"completed": False}},
                        "competitors": [
                            {"team": {"id": "256", "displayName": "Celtic"}},
                            {"team": {"id": "9", "displayName": "Rival"}},
                        ],
                    }
                ],
            }
            datos = {"events": [partido]}
        else:
            datos = {"events": []}
        return types.SimpleNamespace(json=lambda: datos)

    monkeypatch.setattr(comun, "get", get)
    assert sports.search_teams(" celtic ") == [
        {"id": "256", "nom": "Celtic", "lliga": "soccer/sco.1", "competicio": "SPFL"}
    ]


def test_buscar_con_pocas_letras_no_sale_a_internet() -> None:
    with pytest.raises(ValueError, match="3 lletres"):
        sports.search_teams("ab")


def test_un_equipo_de_un_altre_guarda_su_competicion() -> None:
    celtic = {"lliga": "soccer/sco.1", "id": "256", "nom": "Celtic", "competicio": "SPFL"}
    assert sports.build({"equips": [celtic]})["esports"]["equips"] == [celtic]
    # Los del catálogo no la necesitan: su competición ya está en catalog/sports.py
    assert "competicio" not in sports.build({"equips": [{**EQUIPO, "competicio": "LaLiga"}]})["esports"]["equips"][0]


# --- Lo que se guarda ---


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
        {"equips": [{**EQUIPO, "lliga": "../../otra-web"}]},
        {"equips": [{**EQUIPO, "lliga": "soccer"}]},
        {"equips": [{**EQUIPO, "id": ""}]},
        {"equips": [{**EQUIPO, "id": "83?x=1"}]},
        {"equips": [{**EQUIPO, "nom": " "}]},
    ],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        sports.build(respuesta)
