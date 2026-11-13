"""Tests del catálogo de carburantes (catalog/fuel.py)."""

import pytest

from panel_diario.catalog import fuel


def test_las_52_provincias_con_su_codigo() -> None:
    assert len(fuel.PROVINCES) == 52
    assert all(len(pid) == 2 and pid.isdigit() for pid in fuel.PROVINCES)


@pytest.mark.parametrize(
    ("nombre", "codigo"),
    [
        ("Girona", "17"),
        ("gerona", "17"),
        ("València", "46"),
        ("Valencia", "46"),
        ("Saragossa", "50"),
        ("Illes Balears", "07"),
        (" Bizkaia ", "48"),
    ],
)
def test_reconoce_la_provincia_en_varios_idiomas(nombre: str, codigo: str) -> None:
    assert fuel.find_province(nombre) == codigo


def test_provincia_desconocida() -> None:
    assert fuel.find_province("Gironès") is None
    assert fuel.find_province("") is None


def test_gasolina_95_98_y_diesel_sin_repetir() -> None:
    assert [p.name for p in fuel.PRODUCTS] == ["Gasolina 95", "Gasolina 98", "Dièsel"]
    campos = [p.ministry_field for p in fuel.PRODUCTS]
    assert len(campos) == len(set(campos))
