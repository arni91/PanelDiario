"""Tests del paso «El teu dia a dia» del asistente (wizard/daily.py)."""

import pytest

from panel_diario.wizard import daily


def test_la_provincia_sale_de_la_ciudad_sin_preguntar_nada() -> None:
    cfg = daily.build({"carburants": True}, city_province="Girona")
    assert cfg["carburants"] == {"activa": True, "provincia": "17"}


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"llum": True, "aire": False, "carburants": True}
    assert daily.current_choices(daily.build(respuesta, city_province="València")) == respuesta


def test_sin_nada_configurado() -> None:
    assert daily.current_choices({}) == {"llum": False, "aire": False, "carburants": False}


def test_sin_carburantes_no_hace_falta_provincia() -> None:
    cfg = daily.build({"llum": True}, city_province="Perpinyà")
    assert cfg["llum"] == {"activa": True} and cfg["carburants"]["activa"] is False


def test_carburantes_fuera_de_espana_se_explica() -> None:
    with pytest.raises(ValueError, match="Espanya"):
        daily.build({"carburants": True}, city_province="Perpinyà")
