"""Tests del catálogo de medios (catalog/outlets.py)."""

import json
from pathlib import Path

from panel_diario.catalog import outlets

RAIZ = Path(__file__).resolve().parents[2]


def test_cada_medio_tiene_grupo_secciones_e_idioma_validos() -> None:
    for o in outlets.CATALOG:
        assert o.group in outlets.GROUPS, o.name
        assert o.feeds and set(o.feeds) <= set(outlets.SECTIONS), o.name
        assert all(url.startswith("https://") for url in o.feeds.values()), o.name
        assert o.language in ("ca", "es", "en", "fr"), o.name


def test_nombres_y_feeds_sin_repetir() -> None:
    nombres = [o.name for o in outlets.CATALOG]
    assert len(nombres) == len(set(nombres))
    urls = [url for o in outlets.CATALOG for url in o.feeds.values()]
    assert len(urls) == len(set(urls))


def test_variedad_en_cada_grupo_y_cada_seccion() -> None:
    for group in outlets.GROUPS:
        assert sum(o.group == group for o in outlets.CATALOG) >= 4, group
    for section in outlets.SECTIONS:
        assert sum(section in o.feeds for o in outlets.CATALOG) >= 8, section


def test_fuentes_de_una_seccion_en_el_orden_del_catalogo_y_con_idioma() -> None:
    fuentes = outlets.sources_for("esports", ["Marca", "Ara"])
    assert fuentes == [
        {"nombre": "Ara", "url": "https://www.ara.cat/rss/esports/", "idioma": "ca"},
        {"nombre": "Marca", "url": "https://e00-marca.uecdn.es/rss/portada.xml", "idioma": "es"},
    ]


def test_medio_sin_esa_seccion_o_seccion_desconocida() -> None:
    assert outlets.sources_for("esports", ["Politico Europe"]) == []
    assert outlets.sources_for("no-existe", ["Ara"]) == []


def test_buscar_un_medio_por_su_nombre() -> None:
    ara = outlets.find("Ara")
    assert ara is not None and ara.language == "ca"
    assert outlets.find("Arabia") is None


def test_la_plantilla_publica_solo_usa_feeds_del_catalogo() -> None:
    plantilla = json.loads((RAIZ / "config.example.json").read_text(encoding="utf-8"))
    urls = {url for o in outlets.CATALOG for url in o.feeds.values()}
    for tab, fuentes in plantilla["fuentes"].items():
        for fuente in fuentes:
            assert fuente.get("agregador") or fuente["url"] in urls, (tab, fuente["nombre"])
