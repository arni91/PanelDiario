"""Tests del asistente de configuración (asistente.py): búsquedas, comprobaciones y config.json final.

Las APIs (Open-Meteo, football-data, Yahoo, RSS) se sustituyen por respuestas inventadas: sin internet.
"""

import json
import types
from pathlib import Path
from typing import Any

import pytest

from panel_diario import asistente, config, outlets
from panel_diario.fuentes import agenda, comun, drawdown

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


def test_equipos_de_una_competicion_ordenados(monkeypatch: pytest.MonkeyPatch) -> None:
    equipos = {"teams": [{"id": 2, "shortName": "Zeta"}, {"id": 1, "name": "Alfa FC", "shortName": None}]}
    pedidos = red_falsa(monkeypatch, equipos)
    assert asistente.equipos_de_competicion("clave-falsa", "PD") == [
        {"id": 1, "nombre": "Alfa FC"},
        {"id": 2, "nombre": "Zeta"},
    ]
    assert pedidos[0][0].endswith("/competitions/PD/teams")
    assert pedidos[0][1]["headers"] == {"X-Auth-Token": "clave-falsa"}


def test_equipos_sin_clave_no_llama_a_la_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", lambda *a, **k: pytest.fail("no debe llamar a la API"))
    with pytest.raises(ValueError, match="clau"):
        asistente.equipos_de_competicion(" ", "PD")


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
    base["futbol"] = {"nombre": "Mi equipo", "football_data_api_key": "k", "team_id": 7}
    assert asistente.construir_config(base, {}) == base


def test_no_modifica_la_config_de_partida() -> None:
    base = plantilla()
    original = json.loads(json.dumps(base))
    asistente.construir_config(base, {"ubicacion": LUGAR, "claude": {"api_key": "x"}})
    assert base == original


def test_futbol_drawdown_agenda_y_claude() -> None:
    respuestas = {
        "futbol": {"football_data_api_key": " k ", "team_id": "7", "nombre": "Equip"},
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
        "claude": {"api_key": " clave "},
    }
    cfg = asistente.construir_config(plantilla(), respuestas)
    assert cfg["futbol"] == {"nombre": "Equip", "football_data_api_key": "k", "team_id": 7}
    assert cfg["drawdown"]["ticker"] == "EJEMPLO.DE"
    # Las caídas se guardan siempre negativas y ordenadas de menor a mayor caída
    assert [n["caida"] for n in cfg["drawdown"]["niveles"]] == [-10, -20, -40]
    assert cfg["drawdown"]["actualizar_minutos"] == 30  # lo que el asistente no pregunta se conserva
    assert cfg["agenda"]["ical_urls"] == ["https://calendar.example.com/a.ics"]
    assert cfg["claude"]["api_key"] == "clave"


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


def test_verificar_ical_que_falla_explica_sin_la_direccion(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(url: str) -> int:
        raise agenda.ErrorAgenda("calendari 1: HTTP 404")

    monkeypatch.setattr(agenda, "comprobar_ical", falla)
    r = asistente.ApiAsistente(plantilla(), lambda cfg: None).verificar_ical("https://cal.example.com/secret-xyz.ics")
    assert r["ok"] is False and "HTTP 404" in r["error"] and "secret-xyz" not in r["error"]


# --- Noticias: catálogo por pestaña, "Un altre…" y Google Noticias ---------------------


def test_catalogo_por_pestana_con_los_seis_diarios_primero_idioma_y_orientacion() -> None:
    catalogo = {t["id"]: t for t in asistente.catalogo_por_pestana({})}
    assert list(catalogo) == ["mon", "catalunya", "espanya", "mobilitzacions", "tecnologia"]
    mon = catalogo["mon"]["medios"]
    assert [m["nombre"] for m in mon[:3]] == ["eldiario.es", "La Vanguardia", "El País"]
    assert mon[2] == {
        "nombre": "El País",
        "seccion": "Internacional",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada",
        "idioma": "es",
        "ideologia": "centreesquerra",
        "eix_nacional": "",
    }


def test_noticias_actuales_marca_lo_que_ya_hay_en_config() -> None:
    cfg = {
        "fuentes": {
            "mundo": [  # id antiguo de la pestaña Món
                {"nombre": "El País", "url": outlets.sources_for_tab("mon")[2]["url"]},
                {"nombre": "Revista", "url": "https://revista.example.com/feed"},
                {"nombre": "Google Noticias", "url": "https://news.google.com/rss", "agregador": True},
            ],
            "cultura": [{"nombre": "Teatre", "url": "https://teatre.example.com/feed"}],  # no es del catálogo
        }
    }
    actuales = asistente.noticias_actuales(cfg)
    assert actuales["catalogo"] == {"mon": [outlets.sources_for_tab("mon")[2]["url"]]}
    assert actuales["propios"] == {"mon": [{"nombre": "Revista", "url": "https://revista.example.com/feed"}]}


def test_noticias_crea_una_pestana_por_eleccion() -> None:
    espanya = [f["url"] for f in outlets.sources_for_tab("espanya")]
    respuestas = {
        "ubicacion": LUGAR,
        "noticias": {
            "idioma": "es",
            "catalogo": {"espanya": espanya[:2], "mon": []},
            "propios": {"tecnologia": [{"nombre": " Revista ", "url": "https://ejemplo.com/feed"}]},
            "ambitos": ["local"],
            "temas": ["cultura", "ia"],
            "temas_propios": ["energia solar"],
        },
    }
    cfg = asistente.construir_config(plantilla(), respuestas)
    ids = [p["id"] for p in cfg["pestanas"]]
    assert ids == ["espanya", "tecnologia", "local", "cultura", "ia", "tema1"]  # Món sin medios: no sale
    assert set(cfg["fuentes"]) == set(ids)  # cada pestaña tiene sus fuentes
    assert [f["url"] for f in cfg["fuentes"]["espanya"]] == espanya[:2]
    assert cfg["fuentes"]["espanya"][0]["idioma"] == "es"  # del catálogo: no pasa por el traductor
    assert cfg["fuentes"]["tecnologia"] == [{"nombre": "Revista", "url": "https://ejemplo.com/feed"}]
    assert next(p for p in cfg["pestanas"] if p["id"] == "local")["nombre"] == "Catalunya"  # la región del lugar
    cultura = cfg["fuentes"]["cultura"][0]
    assert cultura["agregador"] is True and "Girona" in cultura["url"] and "hl=es" in cultura["url"]
    assert next(p for p in cfg["pestanas"] if p["id"] == "cultura")["filtro_periodo"] is True
    tema = cfg["fuentes"]["tema1"][0]
    assert cfg["pestanas"][-1]["nombre"] == "Energia solar" and "energia%20solar" in tema["url"]


def test_noticias_sin_ninguna_eleccion_es_un_error() -> None:
    with pytest.raises(ValueError, match="almenys"):
        asistente.construir_config(plantilla(), {"noticias": {"idioma": "es", "catalogo": {}, "temas": []}})


@pytest.mark.parametrize(
    "noticias",
    [
        {"catalogo": {"mon": ["https://no-es-del-catalogo.example.com/rss"]}},
        {"propios": {"mon": [{"nombre": "", "url": "https://x.example.com/feed"}]}},
        {"propios": {"mon": [{"nombre": "X", "url": "http://x.example.com/feed"}]}},
        {"temas_propios": ["   "]},
    ],
)
def test_noticias_con_elecciones_no_validas_se_explican(noticias: dict) -> None:
    with pytest.raises(ValueError):
        asistente.construir_config(plantilla(), {"noticias": {"idioma": "ca", **noticias}})


def test_inicio_ofrece_listas_con_un_altre_al_final() -> None:
    inicio = asistente.ApiAsistente(plantilla(), lambda cfg: None).inicio()
    assert len(inicio["ciudades"]) >= 10
    assert inicio["calendarios"][-1]["nombre"] == "Un altre…"
    assert all(c["ayuda"] for c in inicio["calendarios"])
    assert inicio["noticias_actuales"]["catalogo"]["espanya"]  # la plantilla ya trae los seis diarios


def test_fuente_google_noticias_codifica_la_busqueda() -> None:
    f = asistente.fuente_google_noticias("robots & IA", "ca", "ES", tema="IA")
    assert f["url"] == "https://news.google.com/rss/search?q=robots%20%26%20IA&hl=ca&gl=ES&ceid=ES:ca"
    assert f["tema"] == "IA"


# --- Orientación de los medios ---


def _cfg_con_fuentes(*fuentes: dict) -> dict:
    return {"fuentes": {"mon": list(fuentes)}}


def test_paso_de_orientacion_lista_catalogo_y_fuentes_propias() -> None:
    cfg = _cfg_con_fuentes(
        {"nombre": "EL PAÍS", "url": "u", "ideologia": "centre"},  # alias del catálogo: no se repite
        {"nombre": "Diari Local", "url": "v"},
        {"nombre": "Google Noticias", "url": "w", "agregador": True},  # agregador: no es un medio
    )
    mitjans = asistente.mitjans_amb_orientacio(cfg)
    nombres = [m["nombre"] for m in mitjans]
    assert nombres[:6] == ["El Salto", "eldiario.es", "La Directa", "Ara", "La Vanguardia", "El País"]
    assert nombres[len(outlets.CATALOG) :] == ["Diari Local"]  # las propias, después del catálogo
    assert next(m for m in mitjans if m["nombre"] == "El País")["ideologia"] == "centre"  # lo de config manda


def test_guardar_orientacion_solo_lo_que_difiere_del_catalogo() -> None:
    base = _cfg_con_fuentes(
        {"nombre": "El País", "url": "u", "ideologia": "centre"},
        {"nombre": "Ara", "url": "a"},
        {"nombre": "Diari Local", "url": "v"},
    )
    elegidas = [
        {"nombre": "El País", "ideologia": "centreesquerra", "eix_nacional": ""},  # vuelve al valor del catálogo
        {"nombre": "Ara", "ideologia": "", "eix_nacional": "sobiranista"},
        {"nombre": "Diari Local", "ideologia": "centre", "eix_nacional": ""},
        {"nombre": "La Directa", "ideologia": "esquerra", "eix_nacional": ""},  # no es fuente: no se guarda
    ]
    fuentes = asistente.construir_config(base, {"orientacions": elegidas})["fuentes"]["mon"]
    assert fuentes == [
        {"nombre": "El País", "url": "u"},
        {"nombre": "Ara", "url": "a", "eix_nacional": "sobiranista"},
        {"nombre": "Diari Local", "url": "v", "ideologia": "centre"},
    ]


def test_orientacion_no_valida_en_el_asistente_se_explica() -> None:
    with pytest.raises(ValueError, match="no és una orientació vàlida"):
        asistente.construir_config(
            _cfg_con_fuentes({"nombre": "Ara", "url": "a"}),
            {"orientacions": [{"nombre": "Ara", "ideologia": "liberal"}]},
        )


def test_inicio_envia_las_opciones_de_orientacion() -> None:
    o = asistente.ApiAsistente(plantilla(), lambda cfg: None).inicio()["orientacions"]
    assert o["ideologia"][0] == "esquerra" and "no_independentista" in o["eix_nacional"]
    assert o["mitjans"][0]["nombre"] == "El Salto"


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
    assert api.guardar({"claude": {"api_key": "k"}}) == {"ok": True, "datos": True}
    assert recibidas[0]["claude"]["api_key"] == "k"


def test_api_explica_los_errores_sin_lanzar_excepciones(monkeypatch: pytest.MonkeyPatch) -> None:
    api = asistente.ApiAsistente(plantilla(), lambda cfg: None)
    assert api.buscar_lugar(" ") == {"ok": False, "error": "Escriu el nom de la teva ciutat."}

    def sin_red(url: str, **kw: Any) -> None:
        raise ConnectionError("sense connexió")

    monkeypatch.setattr(comun, "get", sin_red)
    r = api.buscar_lugar("Girona")
    assert r["ok"] is False and "sense connexió" in r["error"]
