"""Tests de la borsa (sources/markets.py). Yahoo Finance se simula: no se usa internet."""

import types
from typing import Any

import pytest
import requests

from panel_diario.sources import comun, markets

CHART = {
    "^IBEX": {"regularMarketPrice": 102.0, "chartPreviousClose": 100.0, "currency": "EUR", "regularMarketTime": 0},
    "^GSPC": {"regularMarketPrice": 95.0, "chartPreviousClose": 100.0, "currency": "USD", "regularMarketTime": 0},
}
GANADORAS = [
    {"symbol": "AAA", "shortName": "Empresa A  ", "regularMarketPrice": 10.0, "regularMarketChangePercent": 22.81},
    {"symbol": "BBB", "regularMarketPrice": 5.0, "regularMarketChangePercent": 12.0},
]


def _yahoo_falso(caidos: set[str] | None = None) -> Any:
    def get(url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        if "screener" in url:
            datos: dict = {"finance": {"result": [{"quotes": GANADORAS}]}}
        else:
            symbol = url.rsplit("/", 1)[1]
            if symbol in (caidos or set()):
                raise requests.ConnectionError("sin conexión")
            datos = {"chart": {"result": [{"meta": {**CHART[symbol], "shortName": "Nombre Yahoo"}}]}}
        return types.SimpleNamespace(json=lambda: datos)

    return get


@pytest.fixture(autouse=True)
def yahoo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", _yahoo_falso())


def test_indices_con_variacion_del_dia_y_nombre_del_catalogo() -> None:
    b = markets.obtener_borsa({"borsa": {"indexs": ["^IBEX", "^GSPC"]}})
    assert [(i["nom"], i["canvi_pct"], i["moneda"]) for i in b["indexs"]] == [
        ("IBEX 35", 2.0, "EUR"),
        ("S&P 500", -5.0, "USD"),
    ]


def test_listas_del_dia() -> None:
    b = markets.obtener_borsa({"borsa": {"moviments": ["day_gainers", "no-existe"]}})
    assert len(b["moviments"]) == 1
    lista = b["moviments"][0]
    assert lista["nombre"] == "Les que més pugen"
    assert lista["valors"][0] == {"simbol": "AAA", "nom": "Empresa A", "preu": 10.0, "canvi_pct": 22.81}
    assert lista["valors"][1]["nom"] == "BBB"  # sin nombre: el símbolo


def test_sin_configurar() -> None:
    assert markets.obtener_borsa({}) == {"sin_configurar": True}
    assert markets.obtener_borsa({"borsa": {"indexs": [], "moviments": []}}) == {"sin_configurar": True}


def test_un_indice_caido_no_tapa_los_demas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", _yahoo_falso(caidos={"^GSPC"}))
    b = markets.obtener_borsa({"borsa": {"indexs": ["^IBEX", "^GSPC"]}})
    assert [i["simbol"] for i in b["indexs"]] == ["^IBEX"]


def test_si_caen_todos_se_lanza_para_conservar_el_ultimo_dato(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", _yahoo_falso(caidos={"^IBEX"}))
    with pytest.raises(RuntimeError, match="Yahoo"):
        markets.obtener_borsa({"borsa": {"indexs": ["^IBEX"]}})


def test_variacion_con_cierre_anterior_cero() -> None:
    assert markets.change_pct(10.0, 0.0) == 0.0
