"""Tests de los deportes (sources/sports.py). ESPN se simula: no se usa internet."""

import types
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import requests

from panel_diario.sources import comun, sports

AHORA = datetime.now(UTC)


def _iso(dias: float) -> str:
    return (AHORA + timedelta(days=dias)).strftime("%Y-%m-%dT%H:%MZ")


def _partido(id_: str, dias: float, rival: str, en_casa: bool, goles: tuple | None = None, liga: str = "") -> dict:
    jugado = goles is not None
    nuestro = {"homeAway": "home" if en_casa else "away", "team": {"id": "83", "displayName": "Equip"}}
    otro = {"homeAway": "away" if en_casa else "home", "team": {"id": "9", "displayName": rival}}
    if goles is not None:
        nuestro["score"] = {"displayValue": str(goles[0])}
        otro["score"] = {"displayValue": str(goles[1])}
    return {
        "id": id_,
        "date": _iso(dias),
        "league": {"name": liga} if liga else {},
        "competitions": [{"status": {"type": {"completed": jugado}}, "competitors": [nuestro, otro]}],
    }


JUGADOS = [_partido("1", -10, "Rival A", True, (1, 1), "Spanish LALIGA"), _partido("2", -3, "Rival B", False, (2, 0))]
PENDIENTES = [_partido("4", 9, "Rival D", True), _partido("3", 2, "Rival C", False, liga="UEFA Champions League")]
F1 = {
    "leagues": [
        {
            "calendar": [
                {"label": "GP passat", "endDate": _iso(-5)},
                {"label": "GP Exemple", "endDate": _iso(6)},
            ]
        }
    ],
    "events": [
        {
            "name": "GP passat",
            "competitions": [
                {
                    "status": {"type": {"completed": True}},
                    "competitors": [
                        {"winner": False, "athlete": {"displayName": "Pilot B"}},
                        {"winner": True, "athlete": {"displayName": "Pilot A"}},
                    ],
                },
            ],
        }
    ],
}


class EspnFalso:
    def __init__(self) -> None:
        self.caidos: set[str] = set()
        self.urls: list[str] = []

    def __call__(self, url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        self.urls.append(url + ("?fixture" if params else ""))
        if any(c in url for c in self.caidos):
            raise requests.ConnectionError("sin conexión")
        if "racing/f1" in url:
            datos: dict = F1
        elif params and params.get("fixture"):
            datos = {"events": PENDIENTES + JUGADOS[-1:]}  # se repite uno: no debe salir dos veces
        else:
            datos = {"events": JUGADOS}
        return types.SimpleNamespace(json=lambda: datos)


@pytest.fixture
def espn(monkeypatch: pytest.MonkeyPatch) -> EspnFalso:
    falso = EspnFalso()
    monkeypatch.setattr(comun, "get", falso)
    return falso


BARCA = {"lliga": "soccer/esp.1", "id": "83", "nom": "Equip d'exemple"}


def test_proximos_partidos_ordenados_y_ultimo_resultado(espn: EspnFalso) -> None:
    equipo = sports.obtener_esports({"esports": {"equips": [BARCA]}})["equips"][0]
    assert equipo["nom"] == "Equip d'exemple" and equipo["esport"] == "futbol"
    assert [(p["rival"], p["local"], p["competicio"]) for p in equipo["proxims"]] == [
        ("Rival C", False, "UEFA Champions League"),
        ("Rival D", True, "LaLiga"),  # sin liga en el partido: la del catálogo
    ]
    u = equipo["ultim"]
    assert (u["rival"], u["gols_equip"], u["gols_rival"], u["resultat"]) == ("Rival B", 2, 0, "v")


def test_futbol_junta_todas_las_competiciones_y_otros_deportes_su_liga(espn: EspnFalso) -> None:
    nba = {"lliga": "basketball/nba", "id": "2", "nom": "Equip NBA"}
    sports.obtener_esports({"esports": {"equips": [BARCA, nba]}})
    assert espn.urls[0].endswith("soccer/all/teams/83/schedule")
    assert any(u.endswith("soccer/all/teams/83/schedule?fixture") for u in espn.urls)
    assert espn.urls[-1].endswith("basketball/nba/teams/2/schedule")


def test_resultados() -> None:
    assert sports.result({"gols_equip": 1, "gols_rival": 1}) == "e"
    assert sports.result({"gols_equip": 0, "gols_rival": 3}) == "d"
    assert sports.result({"gols_equip": None, "gols_rival": 3}) == ""


def test_nombre_de_la_competicion_sin_el_pais() -> None:
    assert sports.competition_name({"league": {"name": "Spanish LALIGA"}}, "") == "LALIGA"
    assert sports.competition_name({}, "NBA") == "NBA"


def test_formula1_proximo_gp_y_ganador_del_ultimo(espn: EspnFalso) -> None:
    f1 = sports.obtener_esports({"esports": {"f1": True}})["f1"]
    assert f1["proxim"]["nom"] == "GP Exemple"
    assert f1["ultim"] == {"nom": "GP passat", "guanyador": "Pilot A"}


def test_sin_configurar() -> None:
    assert sports.obtener_esports({}) == {"sin_configurar": True}


def test_un_equipo_caido_no_tapa_lo_demas(espn: EspnFalso) -> None:
    espn.caidos = {"teams/83"}
    r = sports.obtener_esports({"esports": {"equips": [BARCA], "f1": True}})
    assert r["equips"] == [] and r["f1"]["proxim"]


def test_si_cae_todo_se_lanza_para_conservar_el_ultimo_dato(espn: EspnFalso) -> None:
    espn.caidos = {"espn.com"}
    with pytest.raises(RuntimeError, match="ESPN"):
        sports.obtener_esports({"esports": {"equips": [BARCA], "f1": True}})
