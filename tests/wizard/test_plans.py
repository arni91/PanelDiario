"""Tests del paso «Plans» del asistente (wizard/plans.py)."""

import pytest

from panel_diario.catalog import interests
from panel_diario.wizard import plans


def test_opciones_con_todos_los_interesos() -> None:
    assert [i["id"] for i in plans.options()["interessos"]] == list(interests.INTERESTS)


def test_ciudad_propia_e_interesos() -> None:
    respuesta = {"activa": True, "ciutat": " Barcelona ", "interessos": ["lgtbi"], "paraules": ["jazz", " "]}
    assert plans.build(respuesta, weather_city="Sant Cugat del Vallès")["plans"] == {
        "activa": True,
        "ciutat": "Barcelona",
        "dies": 7,
        "interessos": ["lgtbi"],
        "paraules": ["jazz"],
    }


def test_sin_ciudad_propia_la_del_tiempo() -> None:
    assert plans.build({"activa": True}, weather_city="Girona")["plans"]["ciutat"] == "Girona"


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"activa": True, "ciutat": "Barcelona", "interessos": ["drag", "feminisme"], "paraules": ["jazz"]}
    assert plans.current_choices(plans.build(respuesta, weather_city="")) == respuesta


def test_sin_nada_configurado() -> None:
    assert plans.current_choices({}) == {"activa": False, "ciutat": "", "interessos": [], "paraules": []}


@pytest.mark.parametrize(
    "respuesta",
    [
        {"activa": True},  # sin ciudad propia ni del tiempo
        {"activa": True, "ciutat": "Barcelona", "interessos": ["opera_xinesa"]},
    ],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        plans.build(respuesta, weather_city="")
