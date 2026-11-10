"""Tests del paso «El teu dia a dia» del asistente (wizard/daily.py)."""

import pytest

from panel_diario.catalog import fuel
from panel_diario.wizard import daily


def test_opciones() -> None:
    o = daily.options()
    assert [c["id"] for c in o["carburants"]] == list(fuel.PRODUCTS)
    assert len(o["provincies"]) == 52 and o["provincies"][0]["nom"] == "Àlaba"  # por orden alfabético
    assert o["radis"] == list(daily.RADIUS_KM)


def test_la_provincia_sale_de_la_ciudad() -> None:
    cfg = daily.build({"carburants": True, "producte": "gasoil"}, city_province="Girona")
    assert cfg["carburants"] == {"activa": True, "provincia": "17", "producte": "gasoil", "radi_km": 10}


def test_una_provincia_elegida_manda_sobre_la_de_la_ciudad() -> None:
    cfg = daily.build({"carburants": True, "provincia": "08"}, city_province="Girona")
    assert cfg["carburants"]["provincia"] == "08"


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"llum": True, "aire": False, "carburants": True, "producte": "glp", "provincia": "46", "radi_km": 20}
    assert daily.current_choices(daily.build(respuesta, city_province="")) == respuesta


def test_sin_nada_configurado() -> None:
    assert daily.current_choices({}) == {
        "llum": False,
        "aire": False,
        "carburants": False,
        "producte": "gasolina95",
        "provincia": "",
        "radi_km": 10,
    }


def test_sin_gasolineras_no_hace_falta_provincia() -> None:
    cfg = daily.build({"llum": True}, city_province="Perpinyà")
    assert cfg["llum"] == {"activa": True} and cfg["carburants"]["activa"] is False


@pytest.mark.parametrize(
    "respuesta",
    [
        {"carburants": True},  # ciudad sin provincia reconocible y sin elegir ninguna
        {"carburants": True, "provincia": "99"},
        {"carburants": True, "provincia": "17", "producte": "queroseno"},
        {"carburants": True, "provincia": "17", "radi_km": 7},
    ],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        daily.build(respuesta, city_province="Perpinyà")
