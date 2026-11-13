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


def test_distancia() -> None:
    assert round(comun.distancia_km(41.3874, 2.1686, 41.9794, 2.8214)) == 85  # Barcelona-Girona en línea recta


@pytest.mark.parametrize(("texto", "valor"), [("1,744", 1.744), ("41.47", 41.47), ("", None), (None, None)])
def test_numero_con_coma_o_punto(texto: object, valor: float | None) -> None:
    assert comun.numero(texto) == valor
