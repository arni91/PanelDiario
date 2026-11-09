"""Tests del paso de borsa del asistente (wizard/markets.py)."""

import pytest

from panel_diario.catalog import markets as catalogo
from panel_diario.wizard import markets


def test_opciones_con_todos_los_indices_y_listas() -> None:
    o = markets.options()
    assert len(o["indexs"]) == len(catalogo.INDICES)
    assert o["indexs"][0] == {"simbol": "^IBEX", "nom": "IBEX 35", "grup": "Europa"}
    assert [m["id"] for m in o["moviments"]] == list(catalogo.MOVERS)


def test_sin_borsa_en_config_propone_la_seleccion_por_defecto() -> None:
    assert markets.current_choices({}) == {
        "indexs": ["^IBEX", "^STOXX50E", "^GSPC", "^IXIC"],
        "moviments": ["day_gainers", "day_losers"],
    }


def test_lo_guardado_se_recupera() -> None:
    respuesta = {"indexs": ["^GSPC", "BTC-USD"], "moviments": ["most_actives"]}
    assert markets.current_choices(markets.build(respuesta)) == respuesta


@pytest.mark.parametrize(
    "respuesta",
    [{"indexs": ["^INVENTADO"]}, {"moviments": ["no-existe"]}, {"indexs": [], "moviments": []}],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        markets.build(respuesta)
