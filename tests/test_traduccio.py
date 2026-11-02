"""Tests de la traducción de noticias (datos.py). El traductor se simula: no se usa internet.

Regla: las noticias en catalán o castellano se quedan como están; las de otros idiomas
(inglés, francés...) se traducen al castellano.
"""

import types
from typing import Any

import pytest

from panel_diario import datos

# texto original -> (idioma que detecta el traductor, traducción al castellano)
DICCIONARI = {
    "AI agents are coming": ("en", "Llegan los agentes de IA"),
    "Séisme au Tibet": ("fr", "Terremoto en el Tíbet"),
    "Terremoto en el Tíbet": ("es", "Terremoto en el Tíbet"),
    "Festa major al parc": ("ca", "Fiesta mayor en el parque"),
}


@pytest.fixture(autouse=True)
def traductor_fals(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    datos._TRADUCCIONS.clear()
    crides: list[str] = []

    def get(url: str, params: dict[str, str], **k: Any) -> types.SimpleNamespace:
        crides.append(params["q"])
        if params["q"] == "ERROR":
            raise RuntimeError("sin conexión")
        idioma, traduccion = DICCIONARI.get(params["q"], ("en", params["q"]))
        # Mismo formato que el traductor: [[["traducción", "original", ...]], None, "idioma detectado"]
        return types.SimpleNamespace(json=lambda: [[[traduccion, params["q"]]], None, idioma])

    monkeypatch.setattr(datos, "_get", get)
    return crides


def test_traduce_y_guarda_en_memoria(traductor_fals: list[str]) -> None:
    assert datos.traduir("AI agents are coming", "es") == "Llegan los agentes de IA"
    assert datos.traduir("AI agents are coming", "es") == "Llegan los agentes de IA"
    assert traductor_fals == ["AI agents are coming"]  # la segunda vez no lo vuelve a pedir


def test_conserva_el_original_si_el_idioma_detectado_se_conserva(traductor_fals: list[str]) -> None:
    assert datos.traduir("Festa major al parc", "es", conservar=("ca", "es")) == "Festa major al parc"


def test_ingles_y_frances_al_castellano_catalan_y_castellano_igual(traductor_fals: list[str]) -> None:
    salida = {
        "mundo": [
            {"titulo": "Séisme au Tibet", "idioma": "", "resumen": ""},
            {"titulo": "Terremoto en el Tíbet", "idioma": "", "resumen": ""},
            {"titulo": "ERROR", "idioma": "", "resumen": ""},
        ],
        "cultura": [{"titulo": "Festa major al parc", "idioma": "", "resumen": ""}],
        "tecnologia": [{"titulo": "AI agents are coming", "idioma": "", "resumen": ""}],
    }
    datos.traduir_noticies(salida, {})
    assert salida["mundo"][0]["titulo"] == "Terremoto en el Tíbet"  # francés -> castellano
    assert salida["mundo"][1]["titulo"] == "Terremoto en el Tíbet"  # castellano: igual
    assert salida["mundo"][2]["titulo"] == "ERROR"  # error: se queda el original
    assert salida["cultura"][0]["titulo"] == "Festa major al parc"  # catalán: igual
    assert salida["tecnologia"][0]["titulo"] == "Llegan los agentes de IA"  # inglés -> castellano


def test_fuente_con_idioma_conocido_no_pasa_por_el_traductor(traductor_fals: list[str]) -> None:
    salida = {"cultura": [{"titulo": "Festa major al parc", "idioma": "ca", "resumen": "Dissabte"}]}
    datos.traduir_noticies(salida, {})
    assert salida["cultura"][0]["titulo"] == "Festa major al parc"
    assert traductor_fals == []


def test_traduccion_desactivada(traductor_fals: list[str]) -> None:
    salida = {"mundo": [{"titulo": "AI agents are coming", "idioma": ""}]}
    datos.traduir_noticies(salida, {"traduccio": {"activa": False}})
    assert salida["mundo"][0]["titulo"] == "AI agents are coming" and traductor_fals == []
