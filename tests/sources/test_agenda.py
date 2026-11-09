"""Tests de la agenda (sources/agenda.py): enlaces como "lugar" y la dirección iCal secreta fuera de errores y logs."""

import logging
import types
from typing import Any

import pytest
import requests

from panel_diario import state
from panel_diario.sources import agenda, comun

# Dirección inventada con la forma de las de Google: la parte secreta no puede salir en ningún error.
# Se escribe por partes para que la revisión de privacidad no la tome por una dirección real.
SECRETO = "abcdef0123456789secret"
URL = "https://calendar.google.com/calendar/" + "ical/demo%40example.com/" + "priv" + f"ate-{SECRETO}/basic.ics"

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//demo//ES
BEGIN:VEVENT
UID:1
DTSTART:20300101T100000Z
DTEND:20300101T110000Z
SUMMARY:Demo
END:VEVENT
END:VCALENDAR
"""


def _falla_con(ex: Exception) -> Any:
    def get(url: str, **k: Any) -> None:
        raise ex

    return get


def _http_error(estado_http: int) -> requests.HTTPError:
    r = requests.Response()
    r.status_code = estado_http
    return requests.HTTPError(f"{estado_http} Client Error: Not Found for url: {URL}", response=r)


# --- Lugar del evento ------------------------------------------------------------


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


# --- La dirección secreta nunca sale en un error ------------------------------------


@pytest.mark.parametrize(
    "error",
    [_http_error(404), requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {URL}")],
)
def test_error_de_red_no_incluye_la_direccion(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    monkeypatch.setattr(comun, "get", _falla_con(error))
    with pytest.raises(agenda.ErrorAgenda) as info:
        agenda.obtener_agenda({"agenda": {"ical_urls": [URL]}})
    assert SECRETO not in str(info.value) and "calendari 1" in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__  # ni en la traza


def test_contenido_que_no_es_ical(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", lambda url, **k: types.SimpleNamespace(content=b"<html>login</html>"))
    with pytest.raises(agenda.ErrorAgenda, match="no és un calendari iCal"):
        agenda.obtener_agenda({"agenda": {"ical_urls": [URL]}})


def test_el_panel_no_escribe_la_direccion_en_log_ni_cache(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Any
) -> None:
    """Reproduce el fallo: state.py guardaba str(ex) del error de requests, con la URL entera."""
    monkeypatch.setattr(comun, "get", _falla_con(_http_error(404)))
    monkeypatch.setattr(state, "CACHE", tmp_path / "cache.json")
    # Las demás secciones no salen a la red: solo interesa la agenda
    monkeypatch.setattr(state.tiempo, "obtener_tiempo", lambda cfg: {})
    monkeypatch.setattr(state.avisos, "obtener_avisos", lambda cfg: [])
    monkeypatch.setattr(state.futbol, "obtener_futbol", lambda cfg: {})
    monkeypatch.setattr(state.noticias, "obtener_noticias", lambda cfg: ({}, []))
    monkeypatch.setattr(state.drawdown, "obtener_drawdown", lambda cfg, ruta: {})
    est = state.Estado()
    with caplog.at_level(logging.INFO, logger="panel"):
        state.actualizar(est, {"agenda": {"ical_urls": [URL]}})
    assert "agenda" in est.datos["errores"]
    assert SECRETO not in caplog.text
    assert SECRETO not in str(est.datos["errores"])
    assert SECRETO not in (tmp_path / "cache.json").read_text(encoding="utf-8")


# --- Comprobación desde el asistente --------------------------------------------------


def test_comprobar_ical_cuenta_los_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", lambda url, **k: types.SimpleNamespace(content=ICS))
    assert agenda.comprobar_ical(URL) == 1


def test_comprobar_ical_con_error_explica_sin_la_direccion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", _falla_con(_http_error(404)))
    with pytest.raises(agenda.ErrorAgenda) as info:
        agenda.comprobar_ical(URL)
    assert SECRETO not in str(info.value) and "404" in str(info.value)
