"""Tests del precio medio de los carburantes (sources/carburants.py). El Ministerio se simula."""

import types
from typing import Any

import pytest

from panel_diario.sources import carburants, comun

CFG = {"carburants": {"activa": True, "provincia": "17"}}


def _gasolinera(g95: str, g98: str, diesel: str) -> dict:
    return {"Precio Gasolina 95 E5": g95, "Precio Gasolina 98 E5": g98, "Precio Gasoleo A": diesel}


GASOLINERAS = [
    _gasolinera("1,500", "1,700", "1,400"),
    _gasolinera("1,600", "", "1,500"),  # no vende 98: no cuenta en su media
    _gasolinera("1,700", "1,800", ""),
]


@pytest.fixture
def ministerio(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    urls: list[str] = []

    def get(url: str, **k: Any) -> types.SimpleNamespace:
        urls.append(url)
        return types.SimpleNamespace(json=lambda: {"ListaEESSPrecio": GASOLINERAS})

    monkeypatch.setattr(comun, "get", get)
    return urls


def test_media_de_cada_combustible_en_la_provincia(ministerio: list[str]) -> None:
    r = carburants.obtener_carburants(CFG)
    assert ministerio == [carburants.API.format(province="17")]  # una sola petición
    assert r == {
        "provincia": "Girona",
        "preus": [
            {"nom": "Gasolina 95", "mitjana": 1.6, "gasolineres": 3},
            {"nom": "Gasolina 98", "mitjana": 1.75, "gasolineres": 2},
            {"nom": "Dièsel", "mitjana": 1.45, "gasolineres": 2},
        ],
    }


def test_combustible_que_no_vende_nadie() -> None:
    preus = carburants.averages([_gasolinera("1,500", "", "")])
    assert preus[1] == {"nom": "Gasolina 98", "mitjana": None, "gasolineres": 0}


@pytest.mark.parametrize(
    "carb",
    [
        {},
        {"activa": False, "provincia": "17"},
        {"activa": True, "provincia": "99"},
    ],
)
def test_sin_configurar_no_sale_a_internet(carb: dict) -> None:
    assert carburants.obtener_carburants({"carburants": carb}) == {"sin_configurar": True}
