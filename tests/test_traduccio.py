"""Tests de la traducción (fuentes/traduccion.py). El traductor se simula: no se usa internet.

Regla: las noticias en catalán o castellano se quedan como están; las de otros idiomas
(inglés, francés...) se traducen al catalán. Si no se puede, se queda el original.
"""

import json
import logging
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import requests

from panel_diario.fuentes import comun, traduccion

# texto original -> (idioma que detecta el traductor, traducción al catalán)
DICCIONARI = {
    "AI agents are coming": ("en", "Arriben els agents d'IA"),
    "Séisme au Tibet": ("fr", "Terratrèmol al Tibet"),
    "Terremoto en el Tíbet": ("es", "Terratrèmol al Tibet"),
    "Festa major al parc": ("ca", "Festa major al parc"),
}


def _http_error(estado: int) -> requests.HTTPError:
    r = requests.Response()
    r.status_code = estado
    return requests.HTTPError(f"{estado} Client Error", response=r)


class TraductorFals:
    """Sustituye a comun.get. `fallos` decide, por número de petición (1, 2...), si esa petición falla."""

    def __init__(self) -> None:
        self.peticiones: list[list[str]] = []
        self.fallos: Callable[[int], Exception | None] = lambda n: None
        self.respuesta: Callable[[list[str]], Any] | None = None

    def __call__(self, url: str, params: dict[str, Any], **k: Any) -> types.SimpleNamespace:
        q = list(params["q"])
        self.peticiones.append(q)
        error = self.fallos(len(self.peticiones))
        if error:
            raise error
        if self.respuesta:
            datos = self.respuesta(q)
        else:
            # Mismo formato que translate_a/t con sl=auto: [[traducción, idioma detectado], ...]
            datos = [[DICCIONARI.get(t, ("en", f"CA {t}"))[1], DICCIONARI.get(t, ("en", ""))[0]] for t in q]
        return types.SimpleNamespace(json=lambda: datos)

    @property
    def textos_pedidos(self) -> list[str]:
        return [t for p in self.peticiones for t in p]


@pytest.fixture(autouse=True)
def traductor(monkeypatch: pytest.MonkeyPatch) -> TraductorFals:
    fals = TraductorFals()
    monkeypatch.setattr(comun, "get", fals)
    monkeypatch.setattr(traduccion, "_memoria", traduccion.MemoriaTraduccions())
    monkeypatch.setattr(traduccion, "_pausa_hasta", 0.0)
    return fals


@pytest.fixture(autouse=True)
def esperas(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Las esperas entre reintentos se apuntan en vez de dormir: los tests no tardan."""
    apuntadas: list[float] = []
    monkeypatch.setattr(traduccion.time, "sleep", apuntadas.append)
    return apuntadas


def _noticia(titulo: str, idioma: str = "", resumen: str = "") -> dict:
    return {"titulo": titulo, "idioma": idioma, "resumen": resumen}


# --- Caso normal -----------------------------------------------------------


def test_otros_idiomas_al_catalan_catalan_y_castellano_igual(traductor: TraductorFals) -> None:
    salida = {
        "mundo": [_noticia("Séisme au Tibet"), _noticia("Terremoto en el Tíbet")],
        "cultura": [_noticia("Festa major al parc")],
        "tecnologia": [_noticia("AI agents are coming")],
    }
    traduccion.traduir_noticies(salida, {})  # sin "traduccio": por defecto, al catalán
    assert salida["mundo"][0]["titulo"] == "Terratrèmol al Tibet"  # francés -> catalán
    assert salida["mundo"][1]["titulo"] == "Terremoto en el Tíbet"  # castellano: igual
    assert salida["cultura"][0]["titulo"] == "Festa major al parc"  # catalán: igual
    assert salida["tecnologia"][0]["titulo"] == "Arriben els agents d'IA"  # inglés -> catalán
    assert len(traductor.peticiones) == 1  # todos en un solo lote


def test_traduce_tambien_el_resumen(traductor: TraductorFals) -> None:
    salida = {"mundo": [_noticia("AI agents are coming", resumen="Séisme au Tibet")]}
    traduccion.traduir_noticies(salida, {})
    assert salida["mundo"][0]["resumen"] == "Terratrèmol al Tibet"


def test_fuente_con_idioma_conocido_no_pasa_por_el_traductor(traductor: TraductorFals) -> None:
    salida = {"cultura": [_noticia("Festa major al parc", idioma="ca", resumen="Dissabte")]}
    traduccion.traduir_noticies(salida, {})
    assert salida["cultura"][0]["titulo"] == "Festa major al parc"
    assert traductor.peticiones == []


def test_traduccion_desactivada(traductor: TraductorFals) -> None:
    salida = {"mundo": [_noticia("AI agents are coming")]}
    traduccion.traduir_noticies(salida, {"traduccio": {"activa": False}})
    assert salida["mundo"][0]["titulo"] == "AI agents are coming"
    assert traductor.peticiones == []


def test_idioma_destino_de_config(traductor: TraductorFals, monkeypatch: pytest.MonkeyPatch) -> None:
    destinos: list[str] = []

    def get(url: str, params: dict[str, Any], **k: Any) -> types.SimpleNamespace:
        destinos.append(params["tl"])
        return types.SimpleNamespace(json=lambda: [["Llegan los agentes de IA", "en"]])

    monkeypatch.setattr(comun, "get", get)
    salida = {"mundo": [_noticia("AI agents are coming")]}
    traduccion.traduir_noticies(salida, {"traduccio": {"idioma": "es", "conservar": ["es"]}})
    assert destinos == ["es"] and salida["mundo"][0]["titulo"] == "Llegan los agentes de IA"


# --- Memoria (en memoria y en disco) -----------------------------------------


def test_un_texto_se_pide_una_sola_vez(traductor: TraductorFals) -> None:
    for _ in range(2):
        salida = {"mundo": [_noticia("AI agents are coming"), _noticia("AI agents are coming")]}
        traduccion.traduir_noticies(salida, {})
        assert salida["mundo"][1]["titulo"] == "Arriben els agents d'IA"
    assert traductor.textos_pedidos == ["AI agents are coming"]


def test_memoria_en_disco_sobrevive_a_un_reinicio(traductor: TraductorFals, tmp_path: Path) -> None:
    ruta = tmp_path / "traduccions.json"
    traduccion.configurar_memoria(ruta)
    traduccion.traduir_textos(["AI agents are coming"], "ca")
    assert ruta.exists()
    traduccion.configurar_memoria(ruta)  # como si el panel se reiniciara
    assert traduccion.traduir_textos(["AI agents are coming"], "ca") == {
        "AI agents are coming": "Arriben els agents d'IA"
    }
    assert len(traductor.peticiones) == 1


def test_memoria_guarda_el_idioma_y_respeta_un_cambio_de_conservar(traductor: TraductorFals) -> None:
    assert traduccion.traduir_textos(["Terremoto en el Tíbet"], "ca", ["ca", "es"]) == {
        "Terremoto en el Tíbet": "Terremoto en el Tíbet"
    }
    # Si el castellano deja de conservarse, la memoria ya tiene la traducción: no se vuelve a pedir
    assert traduccion.traduir_textos(["Terremoto en el Tíbet"], "ca", ["ca"]) == {
        "Terremoto en el Tíbet": "Terratrèmol al Tibet"
    }
    assert len(traductor.peticiones) == 1


def test_memoria_ilegible_empieza_de_cero(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    ruta = tmp_path / "traduccions.json"
    ruta.write_text("{esto no es JSON", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="panel"):
        memoria = traduccion.MemoriaTraduccions(ruta)
    assert memoria.get("ca", "x") is None and "ilegible" in caplog.text


def test_memoria_con_filas_de_otro_formato_empieza_de_cero(tmp_path: Path) -> None:
    ruta = tmp_path / "traduccions.json"
    ruta.write_text(json.dumps([["ca", "solo dos campos"]]), encoding="utf-8")
    assert traduccion.MemoriaTraduccions(ruta).get("ca", "solo dos campos") is None


def test_memoria_olvida_las_mas_antiguas(tmp_path: Path) -> None:
    memoria = traduccion.MemoriaTraduccions(tmp_path / "m.json", maximo=2)
    for t in ("a", "b", "c"):
        memoria.put("ca", t, t.upper(), "en")
    assert memoria.get("ca", "a") is None and memoria.get("ca", "c") == ("C", "en")


def test_memoria_sin_cambios_no_escribe(tmp_path: Path) -> None:
    ruta = tmp_path / "m.json"
    traduccion.MemoriaTraduccions(ruta).desar()
    assert not ruta.exists()


# --- Lotes -------------------------------------------------------------------


def test_lotes_por_caracteres_y_por_numero_de_textos() -> None:
    assert traduccion.lotes(["aaaa", "bbbb", "cc"], max_caracteres=8) == [["aaaa", "bbbb"], ["cc"]]
    assert traduccion.lotes(["a", "b", "c"], max_textos=2) == [["a", "b"], ["c"]]


def test_lotes_casos_limite() -> None:
    assert traduccion.lotes([]) == []
    # Un texto más largo que el límite va solo en su lote (no se pierde)
    assert traduccion.lotes(["x" * 50, "y"], max_caracteres=10) == [["x" * 50], ["y"]]


def test_muchos_textos_van_en_varios_lotes_seguidos(traductor: TraductorFals) -> None:
    textos = [f"Headline number {i:03d} " + "x" * 80 for i in range(100)]
    resultado = traduccion.traduir_textos(textos, "ca")
    assert all(v.startswith("CA ") for v in resultado.values())
    assert 3 <= len(traductor.peticiones) <= 5  # ~10.000 caracteres en lotes de 3.000
    assert traductor.textos_pedidos == textos  # cada texto una vez, en orden


def test_textos_vacios_no_se_piden(traductor: TraductorFals) -> None:
    assert traduccion.traduir_textos(["", "   "], "ca") == {}
    assert traductor.peticiones == []


# --- Errores: 429 y otros ------------------------------------------------------


def test_429_reproducido_cuarenta_titulares_con_limite_de_tres_peticiones(traductor: TraductorFals) -> None:
    """El fallo real: con una petición por titular, Google responde 429 a partir de pocas peticiones."""
    traductor.fallos = lambda n: _http_error(429) if n > 3 else None
    salida = {"mundo": [_noticia(f"Headline number {i}") for i in range(40)]}
    traduccion.traduir_noticies(salida, {"traduccio": {"idioma": "ca"}})
    assert all(nt["titulo"].startswith("CA ") for nt in salida["mundo"])
    assert len(traductor.peticiones) <= 3


def test_429_puntual_reintenta_con_espera_exponencial(traductor: TraductorFals, esperas: list[float]) -> None:
    traductor.fallos = lambda n: _http_error(429) if n <= 2 else None
    assert traduccion.traduir_textos(["AI agents are coming"], "ca") == {
        "AI agents are coming": "Arriben els agents d'IA"
    }
    assert esperas == [1.0, 2.0]


def test_error_5xx_tambien_se_reintenta(traductor: TraductorFals, esperas: list[float]) -> None:
    traductor.fallos = lambda n: _http_error(503) if n == 1 else None
    assert (
        traduccion.traduir_textos(["AI agents are coming"], "ca")["AI agents are coming"] == "Arriben els agents d'IA"
    )
    assert esperas == [1.0]


def test_429_persistente_deja_el_original_y_hace_una_pausa(
    traductor: TraductorFals, esperas: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    traductor.fallos = lambda n: _http_error(429)
    textos = [f"Headline {i} " + "x" * 200 for i in range(30)]  # varios lotes
    with caplog.at_level(logging.WARNING, logger="panel"):
        resultado = traduccion.traduir_textos(textos, "ca")
    assert resultado == {t: t for t in textos}  # el original, sin excepción
    assert esperas == [1.0, 2.0, 4.0]
    assert len(traductor.peticiones) == 4  # solo el primer lote (1 + 3 reintentos): no se insiste con el resto
    assert "30 textos sin traducir" in caplog.text
    # Durante la pausa no se vuelve a llamar al traductor
    traduccion.traduir_textos(["AI agents are coming"], "ca")
    assert len(traductor.peticiones) == 4


def test_error_4xx_no_se_reintenta(traductor: TraductorFals, esperas: list[float]) -> None:
    traductor.fallos = lambda n: _http_error(404)
    assert traduccion.traduir_textos(["AI agents are coming"], "ca") == {"AI agents are coming": "AI agents are coming"}
    assert esperas == [] and len(traductor.peticiones) == 1


def test_fallo_de_red_en_un_lote_no_impide_los_siguientes(traductor: TraductorFals) -> None:
    traductor.fallos = lambda n: requests.ConnectionError("sin conexión") if n == 1 else None
    textos = [f"Headline {i} " + "x" * 200 for i in range(30)]
    resultado = traduccion.traduir_textos(textos, "ca")
    traducidos = [t for t in textos if resultado[t].startswith("CA ")]
    assert 0 < len(traducidos) < len(textos)  # el primer lote se queda en original; los demás, traducidos
    assert resultado[textos[0]] == textos[0]


def test_el_log_no_incluye_la_url_con_los_textos(traductor: TraductorFals, caplog: pytest.LogCaptureFixture) -> None:
    # Las excepciones de requests llevan la URL completa (con todos los titulares) en su texto
    url = "https://translate.googleapis.com/translate_a/t?q=Secret+headline"
    traductor.fallos = lambda n: requests.HTTPError(
        f"429 Too Many Requests for url: {url}", response=_http_error(429).response
    )
    with caplog.at_level(logging.INFO, logger="panel"):
        traduccion.traduir_textos(["Secret headline"], "ca")
    assert "HTTP 429" in caplog.text and "Secret" not in caplog.text


@pytest.mark.parametrize(
    "respuesta",
    [
        lambda q: {"error": "formato nuevo"},  # no es una lista
        lambda q: [["solo una"]] * len(q),  # filas sin idioma
        lambda q: [["Una", "en"]] * (len(q) + 1),  # no cuadra con lo pedido
    ],
)
def test_respuesta_con_formato_inesperado_deja_el_original(
    traductor: TraductorFals, respuesta: Callable[[list[str]], Any]
) -> None:
    traductor.respuesta = respuesta
    assert traduccion.traduir_textos(["AI agents are coming"], "ca") == {"AI agents are coming": "AI agents are coming"}


def test_traduccion_vacia_deja_el_original(traductor: TraductorFals) -> None:
    traductor.respuesta = lambda q: [["  ", "en"] for _ in q]
    assert traduccion.traduir_textos(["AI agents are coming"], "ca") == {"AI agents are coming": "AI agents are coming"}
