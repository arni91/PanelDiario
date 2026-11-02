"""Tests de la agenda (datos.py): los enlaces largos como "lugar" se acortan."""

from panel_diario.fuentes import agenda


def test_enlace_largo_se_acorta_al_dominio() -> None:
    url = "https://preply.com/es/classroom/abc123?lesson=987654321&token=" + "x" * 200
    texto, enlace = agenda.resumir_lugar(url)
    assert texto == "🔗 preply.com"
    assert enlace == url


def test_quita_www() -> None:
    assert agenda.resumir_lugar("https://www.zoom.us/j/123")[0] == "🔗 zoom.us"


def test_lugar_normal_no_cambia() -> None:
    assert agenda.resumir_lugar("Oficina del centre") == ("Oficina del centre", "")


def test_lugar_vacio() -> None:
    assert agenda.resumir_lugar("") == ("", "")
