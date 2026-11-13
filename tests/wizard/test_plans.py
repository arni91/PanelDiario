"""Tests del paso «Plans» del asistente (wizard/plans.py)."""

import pytest

from panel_diario.catalog import interests
from panel_diario.wizard import plans


def test_opciones_con_todos_los_interesos() -> None:
    assert [i["id"] for i in plans.options()["interessos"]] == list(interests.INTERESTS)


def test_interesos_y_palabras_propias_a_20_km_de_casa() -> None:
    respuesta = {"activa": True, "interessos": ["lgtbi"], "paraules": ["jazz", " "]}
    assert plans.build(respuesta)["plans"] == {
        "activa": True,
        "radi_km": 20,
        "dies": 7,
        "interessos": ["lgtbi"],
        "paraules": ["jazz"],
    }


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"activa": True, "interessos": ["drag", "feminisme"], "paraules": ["jazz"]}
    assert plans.current_choices(plans.build(respuesta)) == respuesta


def test_sin_nada_configurado() -> None:
    assert plans.current_choices({}) == {"activa": False, "interessos": [], "paraules": []}


def test_interes_desconocido_se_explica() -> None:
    with pytest.raises(ValueError, match="interessos"):
        plans.build({"activa": True, "interessos": ["opera_xinesa"]})
