"""Tests de los pasos de noticias del asistente (wizard/news.py)."""

import pytest

from panel_diario.catalog import outlets
from panel_diario.wizard import news

MEDIOS = {"medios": ["Ara", "El País", "Marca"]}


def _ids(cfg: dict) -> list[str]:
    return [p["id"] for p in cfg["pestanas"]]


# --- Caso normal -------------------------------------------------------------------


def test_una_pestana_por_seccion_con_el_feed_de_cada_medio() -> None:
    cfg = news.build(MEDIOS, {"seccions": ["esports", "portades", "politica"]}, "Girona")
    assert _ids(cfg) == ["portades", "politica", "esports"]  # en el orden de SECTIONS
    assert [f["nombre"] for f in cfg["fuentes"]["esports"]] == ["Ara", "El País", "Marca"]
    assert [f["nombre"] for f in cfg["fuentes"]["portades"]] == ["Ara", "El País"]  # Marca no tiene portada
    assert cfg["pestanas"][0] == {"id": "portades", "nombre": "Portades"}


def test_paso_de_secciones_saltado_solo_portades() -> None:
    assert _ids(news.build(MEDIOS, {}, "")) == ["portades"]


def test_por_defecto_no_se_traduce_y_se_puede_activar() -> None:
    assert news.build(MEDIOS, {}, "")["traduccio"]["activa"] is False
    assert news.build(MEDIOS, {"traduir": True}, "")["traduccio"]["activa"] is True


def test_medios_propios_van_a_portades() -> None:
    propio = {"nombre": "Diari X", "url": "https://diarix.example/feed"}
    cfg = news.build({"medios": [], "propios": [propio]}, {"seccions": ["portades", "cultura"]}, "")
    assert _ids(cfg) == ["portades"] and cfg["fuentes"]["portades"] == [propio]


def test_plans_de_la_ciudad_y_temas_propios_con_google_noticias() -> None:
    cfg = news.build(MEDIOS, {"plans": True, "temes": ["energia solar"]}, "Girona")
    assert _ids(cfg) == ["portades", "plans", "tema1"]
    plans = cfg["pestanas"][1]
    assert plans == {"id": "plans", "nombre": "Plans a Girona", "filtro_periodo": True}
    assert cfg["fuentes"]["plans"][0]["horas_max"] == 720
    assert cfg["fuentes"]["tema1"][0]["url"] == (
        "https://news.google.com/rss/search?q=energia%20solar&hl=ca&gl=ES&ceid=ES:ca"
    )
    assert cfg["pestanas"][2]["nombre"] == "Energia solar"


def test_plans_en_otra_ciudad_que_la_del_tiempo() -> None:
    cfg = news.build(MEDIOS, {"plans": True, "plans_ciutat": " Barcelona "}, "Girona")
    assert cfg["pestanas"][1]["nombre"] == "Plans a Barcelona"
    assert cfg["fuentes"]["plans"][0]["url"].startswith("https://news.google.com/rss/search?q=Barcelona%20")


def test_sin_ciudad_no_hay_plans() -> None:
    assert "plans" not in _ids(news.build(MEDIOS, {"plans": True}, ""))


# --- Errores ------------------------------------------------------------------------


def test_secciones_que_ningun_medio_publica_es_un_error() -> None:
    with pytest.raises(ValueError, match="Cap dels mitjans"):
        news.build({"medios": ["Marca"]}, {"seccions": ["politica"]}, "")


@pytest.mark.parametrize(
    "respuesta",
    [
        {"medios": ["Diari Inventat"]},
        {"medios": [], "propios": [{"nombre": "X", "url": "http://insegura.example/feed"}]},
        {"medios": [], "propios": [{"nombre": "", "url": "https://x.example/feed"}]},
    ],
)
def test_elecciones_no_validas_se_explican(respuesta: dict) -> None:
    with pytest.raises(ValueError):
        news.build(respuesta, {}, "")


def test_tema_vacio_se_explica() -> None:
    with pytest.raises(ValueError, match="paraules"):
        news.build(MEDIOS, {"temes": ["  "]}, "")


# --- Opciones y lo que ya hay configurado ----------------------------------------------


def test_grupos_con_todos_los_medios_del_catalogo() -> None:
    grupos = news.outlet_groups()
    assert [g["id"] for g in grupos] == list(outlets.GROUPS)
    assert sum(len(g["medios"]) for g in grupos) == len(outlets.CATALOG)
    ara = next(m for g in grupos for m in g["medios"] if m["nombre"] == "Ara")
    assert ara["idioma"] == "ca" and "portades" in ara["seccions"]


def test_cada_grupo_lleva_su_bloque_y_los_bloques_no_se_mezclan() -> None:
    bloques = [g["bloc"] for g in news.outlet_groups()]
    assert bloques[0] == "Actualitat" and bloques[-1] == "Per temes"
    # Cada bloque sale seguido (el asistente pone su título una sola vez) y en su orden
    assert [b for i, b in enumerate(bloques) if i == 0 or bloques[i - 1] != b] == list(outlets.BLOCKS.values())


def test_lo_configurado_se_recupera_tal_cual() -> None:
    respuesta = {"medios": ["Ara", "El País"], "propios": [{"nombre": "Diari X", "url": "https://diarix.example/feed"}]}
    secciones = {
        "seccions": ["portades", "cultura"],
        "plans": True,
        "plans_ciutat": "Barcelona",
        "temes": ["energia solar"],
        "traduir": True,
    }
    elegido = news.current_choices(news.build(respuesta, secciones, "Girona"))
    assert elegido == {**respuesta, **secciones}


def test_config_sin_noticias() -> None:
    assert news.current_choices({}) == {
        "medios": [],
        "propios": [],
        "seccions": ["portades"],
        "plans": False,
        "plans_ciutat": "",
        "temes": [],
        "traduir": False,
    }
