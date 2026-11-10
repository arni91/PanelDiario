"""Tests de las gasolineras más baratas (sources/carburants.py). El Ministerio se simula."""

import types
from typing import Any

import pytest

from panel_diario.sources import carburants, comun

UBICACION = {"lat": 41.98, "lon": 2.82}
CFG = {"carburants": {"activa": True, "provincia": "17", "producte": "gasoil", "radi_km": 10}, "ubicacion": UBICACION}


def _gasolinera(rotulo: str, precio: str, lat: str, lon: str) -> dict:
    return {
        "Rótulo": rotulo,
        "Dirección": "CARRER MAJOR, 1",
        "Localidad": "GIRONA",
        "PrecioProducto": precio,
        "Latitud": lat,
        "Longitud (WGS84)": lon,
    }


GASOLINERAS = [
    _gasolinera("CARA", "1,650", "41,980000", "2,830000"),
    _gasolinera("BARATA LLUNY", "1,400", "42,500000", "2,820000"),  # a unos 58 km: fuera del radio
    _gasolinera("BARATA", "1,500", "41,970000", "2,820000"),
    _gasolinera("MITJANA", "1,550", "41,990000", "2,800000"),
    _gasolinera("IGUAL PERO MES LLUNY", "1,500", "41,900000", "2,820000"),
    _gasolinera("SENSE PREU", "", "41,980000", "2,820000"),
]


@pytest.fixture
def ministerio(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    urls: list[str] = []

    def get(url: str, **k: Any) -> types.SimpleNamespace:
        urls.append(url)
        return types.SimpleNamespace(json=lambda: {"ListaEESSPrecio": GASOLINERAS})

    monkeypatch.setattr(comun, "get", get)
    return urls


def test_las_mas_baratas_dentro_del_radio(ministerio: list[str]) -> None:
    r = carburants.obtener_carburants(CFG)
    assert ministerio == [carburants.API.format(province="17", product="4")]  # gasoil = producto 4
    assert [g["nom"] for g in r["gasolineres"]] == [
        "Barata",
        "Igual Pero Mes Lluny",
        "Mitjana",
    ]  # a igual precio, la más cercana
    assert r["gasolineres"][0] == {
        "nom": "Barata",
        "adreca": "Carrer Major, 1",
        "localitat": "Girona",
        "preu": 1.5,
        "km": 1.1,  # 0,01° de latitud
    }
    assert r["producte"] == "Gasoil" and r["total"] == 4 and r["mitjana"] == 1.55


def test_sin_gasolineras_cerca(ministerio: list[str]) -> None:
    r = carburants.obtener_carburants({**CFG, "ubicacion": {"lat": 40.0, "lon": -3.0}})
    assert r["gasolineres"] == [] and r["mitjana"] is None


@pytest.mark.parametrize(
    "carb",
    [
        {},
        {"activa": False, "provincia": "17", "producte": "gasoil"},
        {"activa": True, "provincia": "99", "producte": "gasoil"},
        {"activa": True, "provincia": "17", "producte": "queroseno"},
    ],
)
def test_sin_configurar_no_sale_a_internet(carb: dict) -> None:
    assert carburants.obtener_carburants({"carburants": carb, "ubicacion": UBICACION}) == {"sin_configurar": True}


def test_distancia() -> None:
    assert round(carburants.distance_km(41.3874, 2.1686, 41.9794, 2.8214)) == 85  # Barcelona-Girona en línea recta
