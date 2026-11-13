"""Tests del catálogo de interesos de los planes (catalog/interests.py)."""

import pytest

from panel_diario.catalog import interests
from panel_diario.sources import comun


def _finds(interest: str, text: str) -> bool:
    i = interests.INTERESTS[interest]
    return bool(interests.pattern(i.keywords).search(comun.normalizar(text)))


@pytest.mark.parametrize(
    ("interest", "text"),
    [
        ("lgtbi", "Festival de cinema LGTBIQ+"),
        ("lgtbi", "Una nit queer al Raval"),
        ("lgtbi", "Persones trans i memòria"),
        ("electronica", "Sessió de DJ i música electrònica"),
        ("performance", "Art d'acció i performance"),
        ("drag", "Show de drag queens"),
        ("feminisme", "Jornades feministes"),
        ("underground", "Música experimental i noise"),
        ("art_contemporani", "Nova exposició al MACBA"),
    ],
)
def test_encuentra_cada_interes(interest: str, text: str) -> None:
    assert _finds(interest, text)


@pytest.mark.parametrize(
    ("interest", "text"),
    [
        ("lgtbi", "Transport públic gratuït"),  # "trans" solo como palabra entera
        ("electronica", "Concert a la Casa de la Música"),  # "house" no está dentro de "casa"
        ("drag", "La llegenda del drac"),
        ("art_contemporani", "Disseny contemporani"),  # "contemporani" solo no basta
    ],
)
def test_no_confunde_palabras_parecidas(interest: str, text: str) -> None:
    assert not _finds(interest, text)


def test_palabra_propia_sin_acentos_ni_caracteres_especiales() -> None:
    p = interests.pattern([interests.own_word(" Cinema Japonès (VOSE) ")])
    assert p.search(comun.normalizar("Cicle de cinema japonès (VOSE) a la Filmoteca"))
