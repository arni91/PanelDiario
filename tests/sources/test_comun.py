"""Tests de las utilidades comunes de las fuentes (sources/comun.py)."""

from datetime import date, datetime

import pytest

from panel_diario.sources import comun


@pytest.mark.parametrize(
    ("dia", "texto"),
    [(date(2026, 11, 22), "dg 22/11"), (datetime(2026, 1, 5, 21, 0), "dl 5/1")],
)
def test_dia_curt(dia: date, texto: str) -> None:
    assert comun.dia_curt(dia) == texto


def test_normalizar_sin_acentos_ni_mayusculas() -> None:
    assert comun.normalizar("Gràcia") == "gracia"
