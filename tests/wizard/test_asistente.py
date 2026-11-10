"""Tests del asistente de configuración (asistente.py): búsquedas, comprobaciones y config.json final.

Las APIs (Open-Meteo, football-data, Yahoo, RSS) se sustituyen por respuestas inventadas: sin internet.
"""

import json
import types
from pathlib import Path
from typing import Any

import pytest

from panel_diario import config
from panel_diario.sources import agenda, comun, drawdown
from panel_diario.wizard import asistente

GIRONA = {
    "name": "Girona",
    "latitude": 41.98311,
    "longitude": 2.82493,
    "country_code": "ES",
    "country": "Espanya",
    "admin1": "Catalunya",
    "admin2": "Província de Girona",
    "timezone": "Europe/Madrid",
}
LUGAR = {
    "nombre": "Girona",
    "provincia": "Girona",
    "region": "Catalunya",
    "pais": "Espanya",
    "codigo_pais": "ES",
    "lat": 41.9831,
    "lon": 2.8249,
    "zona_horaria": "Europe/Madrid",
}


def red_falsa(monkeypatch: pytest.MonkeyPatch, respuesta: Any) -> list[tuple[str, Any]]:
    """Sustituye comun.get: devuelve siempre `respuesta` y apunta (url, kwargs) de cada petición."""
    pedidos: list[tuple[str, Any]] = []

    def get(url: str, **kw: Any) -> types.SimpleNamespace:
        pedidos.append((url, kw))
        return types.SimpleNamespace(json=lambda: respuesta)

    monkeypatch.setattr(comun, "get", get)
    return pedidos


def plantilla() -> dict:
    return config.cargar_config(config.EJEMPLO)


# --- Búsquedas ---


def test_buscar_lugar_resume_las_coincidencias(monkeypatch: pytest.MonkeyPatch) -> None:
    pedidos = red_falsa(monkeypatch, {"results": [GIRONA]})
    assert asistente.buscar_lugar("  Girona ") == [LUGAR]
    assert pedidos[0][1]["params"]["name"] == "Girona"


def test_buscar_lugar_sin_resultados_o_vacio(monkeypatch: pytest.MonkeyPatch) -> None:
    red_falsa(monkeypatch, {})  # Open-Meteo no incluye "results" si no encuentra nada
    assert asistente.buscar_lugar("Xyzzy") == []
    with pytest.raises(ValueError):
        asistente.buscar_lugar("  ")


def test_validar_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    meta = {"longName": "ETF de ejemplo", "currency": "EUR", "regularMarketPrice": 100.5}
    monkeypatch.setattr(drawdown, "_yahoo_chart", lambda t, r: {"meta": meta})
    assert asistente.validar_ticker(" ejemplo.de ") == {
        "ticker": "EJEMPLO.DE",
        "nombre": "ETF de ejemplo",
        "moneda": "EUR",
        "precio": 100.5,
    }


def test_verificar_rss(monkeypatch: pytest.MonkeyPatch) -> None:
    rss = b"<rss><channel><item><title>Titular de prova</title><link>https://x/1</link></item></channel></rss>"
    monkeypatch.setattr(comun, "get", lambda url, **k: types.SimpleNamespace(content=rss))
    assert asistente.verificar_rss("https://ejemplo.com/feed") == {"titulares": 1, "ejemplo": "Titular de prova"}
    with pytest.raises(ValueError, match="https"):
        asistente.verificar_rss("ftp://ejemplo.com/feed")


def test_rss_vacio_no_se_acepta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", lambda url, **k: types.SimpleNamespace(content=b"<html>no es rss</html>"))
    with pytest.raises(ValueError):
        asistente.verificar_rss("https://ejemplo.com/")


# --- Construir config.json ---


def test_ubicacion_de_espana_activa_meteoalarm_de_su_provincia() -> None:
    cfg = asistente.construir_config(plantilla(), {"ubicacion": LUGAR})
    assert cfg["ubicacion"] == {"nombre": "Girona", "lat": 41.9831, "lon": 2.8249, "zona_horaria": "Europe/Madrid"}
    assert cfg["avisos_meteo"]["activo"] is True
    assert cfg["avisos_meteo"]["feed"].endswith("-spain")
    assert cfg["avisos_meteo"]["zonas"] == ["Girona"]


def test_pais_sin_meteoalarm_desactiva_los_avisos() -> None:
    lejos = {**LUGAR, "codigo_pais": "JP", "provincia": "", "region": "Tokyo"}
    assert asistente.construir_config(plantilla(), {"ubicacion": lejos})["avisos_meteo"]["activo"] is False


def test_pasos_saltados_no_cambian_nada() -> None:
    base = plantilla()
    base["esports"] = {"equips": [{"lliga": "soccer/esp.1", "id": "7", "nom": "Mi equipo"}], "f1": False}
    assert asistente.construir_config(base, {}) == base


def test_no_modifica_la_config_de_partida() -> None:
    base = plantilla()
    original = json.loads(json.dumps(base))
    asistente.construir_config(base, {"ubicacion": LUGAR, "agenda": {"ical_urls": []}})
    assert base == original


def test_esports_drawdown_y_agenda() -> None:
    respuestas = {
        "esports": {"equips": [{"lliga": "soccer/esp.1", "id": 7, "nom": " Equip "}], "f1": True},
        "drawdown": {
            "ticker": "ejemplo.de",
            "nombre": "ETF",
            "niveles": [
                {"caida": 20, "extra_pct": 100},
                {"caida": -10, "extra_pct": 50},
                {"caida": -40, "toda_la_reserva": True},
            ],
        },
        "agenda": {"ical_urls": [" https://calendar.example.com/a.ics ", ""]},
    }
    base = {**plantilla(), "futbol": {"football_data_api_key": "k"}}
    cfg = asistente.construir_config(base, respuestas)
    assert cfg["esports"] == {
        "equips": [{"lliga": "soccer/esp.1", "id": "7", "nom": "Equip"}],
        "f1": True,
        "motogp": False,
    }
    assert "futbol" not in cfg  # el formato anterior desaparece
    assert cfg["drawdown"]["ticker"] == "EJEMPLO.DE"
    # Las caídas se guardan siempre negativas y ordenadas de menor a mayor caída
    assert [n["caida"] for n in cfg["drawdown"]["niveles"]] == [-10, -20, -40]
    assert cfg["drawdown"]["actualizar_minutos"] == 30  # lo que el asistente no pregunta se conserva
    assert cfg["agenda"]["ical_urls"] == ["https://calendar.example.com/a.ics"]


@pytest.mark.parametrize("url", ["http://no-es-segura.com/x.ics", "calendar.example.com/x.ics", "ftp://x/y.ics"])
def test_agenda_rechaza_direcciones_que_no_son_https_ni_webcal(url: str) -> None:
    with pytest.raises(ValueError, match="https:// o webcal://"):
        asistente.construir_config(plantilla(), {"agenda": {"ical_urls": [url]}})


def test_agenda_acepta_webcal_de_icloud_como_https() -> None:
    cfg = asistente.construir_config(plantilla(), {"agenda": {"ical_urls": ["webcal://p01-caldav.example.com/pub/1"]}})
    assert cfg["agenda"]["ical_urls"] == ["https://p01-caldav.example.com/pub/1"]


def test_verificar_ical_cuenta_los_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agenda, "comprobar_ical", lambda url: 3 if url.startswith("https://") else -1)
    assert asistente.verificar_ical("webcal://cal.example.com/x") == {"eventos": 3}


def test_direccion_publica_de_google_explica_que_hace_falta_la_secreta(monkeypatch: pytest.MonkeyPatch) -> None:
    """El caso real: se pega la dirección pública (/public/basic.ics) y Google responde 404."""
    pedidas: list[str] = []

    def comprobar(url: str) -> int:
        pedidas.append(url)
        return 0

    monkeypatch.setattr(agenda, "comprobar_ical", comprobar)
    publica = "https://calendar.google.com/calendar/ical/usuario%40example.com/public/basic.ics"
    r = asistente.ApiAsistente(plantilla(), lambda cfg: None).verificar_ical(publica)
    assert r["ok"] is False and "secreta" in r["error"] and "usuario" not in r["error"]
    assert pedidas == []  # ni se intenta: no funcionaría


def test_verificar_ical_que_falla_explica_sin_la_direccion(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(url: str) -> int:
        raise agenda.ErrorAgenda("calendari 1: HTTP 404")

    monkeypatch.setattr(agenda, "comprobar_ical", falla)
    r = asistente.ApiAsistente(plantilla(), lambda cfg: None).verificar_ical("https://cal.example.com/secret-xyz.ics")
    assert r["ok"] is False and "HTTP 404" in r["error"] and "secret-xyz" not in r["error"]


# --- Noticias (detalle en test_news.py) ---------------------------------------------


def test_noticias_con_sus_dos_pasos_y_la_ciudad_ya_configurada() -> None:
    respuestas = {"noticias": {"medios": ["Ara"]}, "seccions": {"seccions": ["portades"], "plans": True}}
    cfg = asistente.construir_config({"ubicacion": {"nombre": "Girona"}}, respuestas)
    assert [p["nombre"] for p in cfg["pestanas"]] == ["Portades", "Plans a Girona"]


def test_saltar_el_paso_de_medios_conserva_los_que_habia() -> None:
    base = asistente.construir_config({}, {"noticias": {"medios": ["Ara", "Marca"]}})
    cfg = asistente.construir_config(base, {"seccions": {"seccions": ["portades", "esports"]}})
    assert [f["nombre"] for f in cfg["fuentes"]["esports"]] == ["Ara", "Marca"]


def test_saltar_el_paso_de_secciones_conserva_las_que_habia() -> None:
    base = asistente.construir_config({}, {"noticias": {"medios": ["Ara"]}, "seccions": {"seccions": ["cultura"]}})
    cfg = asistente.construir_config(base, {"noticias": {"medios": ["El País"]}})
    assert [p["id"] for p in cfg["pestanas"]] == ["cultura"]
    assert cfg["fuentes"]["cultura"][0]["nombre"] == "El País"


def test_inicio_ofrece_listas_con_un_altre_al_final() -> None:
    inicio = asistente.ApiAsistente(plantilla(), lambda cfg: None).inicio()
    assert len(inicio["ciudades"]) >= 10
    assert inicio["calendarios"][-1]["nombre"] == "Un altre…"
    assert all(c["ayuda"] for c in inicio["calendarios"])
    assert inicio["grupos_medios"] and inicio["seccions"][0]["id"] == "portades"
    assert inicio["noticias_actuales"]["medios"]  # la plantilla ya trae medios del catálogo


# --- Guardar ---


def test_guardar_config_hace_copia_de_la_anterior(tmp_path: Path) -> None:
    ruta = tmp_path / "config.json"
    ruta.write_text('{"viejo": true}', encoding="utf-8")
    config.guardar_config({"nuevo": "sí"}, ruta)
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"nuevo": "sí"}
    assert json.loads((tmp_path / "config.json.bak").read_text(encoding="utf-8")) == {"viejo": True}


# --- Puente con JavaScript ---


def test_api_guardar_construye_y_entrega_la_config_nueva() -> None:
    recibidas: list[dict] = []
    api = asistente.ApiAsistente(plantilla(), recibidas.append)
    assert api.guardar({"esports": {"equips": [], "f1": True}}) == {"ok": True, "datos": True}
    assert recibidas[0]["esports"]["f1"] is True


def test_api_explica_los_errores_sin_lanzar_excepciones(monkeypatch: pytest.MonkeyPatch) -> None:
    api = asistente.ApiAsistente(plantilla(), lambda cfg: None)
    assert api.buscar_lugar(" ") == {"ok": False, "error": "Escriu el nom de la teva ciutat."}

    def sin_red(url: str, **kw: Any) -> None:
        raise ConnectionError("sense connexió")

    monkeypatch.setattr(comun, "get", sin_red)
    r = api.buscar_lugar("Girona")
    assert r["ok"] is False and "sense connexió" in r["error"]
