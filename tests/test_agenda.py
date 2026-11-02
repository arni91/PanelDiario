"""Tests de la agenda (datos.py): los enlaces largos como "lugar" se acortan."""

import sys
from pathlib import Path

from panel_diario import datos


def test_enlace_largo_se_acorta_al_dominio():
    url = "https://preply.com/es/classroom/abc123?lesson=987654321&token=" + "x" * 200
    texto, enlace = datos.resumir_lugar(url)
    assert texto == "🔗 preply.com"
    assert enlace == url


def test_quita_www():
    assert datos.resumir_lugar("https://www.zoom.us/j/123")[0] == "🔗 zoom.us"


def test_lugar_normal_no_cambia():
    assert datos.resumir_lugar("Oficina del centre") == ("Oficina del centre", "")


def test_lugar_vacio():
    assert datos.resumir_lugar("") == ("", "")
