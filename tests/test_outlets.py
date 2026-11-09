"""Tests del catálogo de medios y de la orientación de cada fuente (outlets.py)."""

import json
import logging
from pathlib import Path

import pytest

from panel_diario import outlets

RAIZ = Path(__file__).resolve().parent.parent

# --- Catálogo ------------------------------------------------------------------


def test_catalogo_con_los_seis_diarios_y_valores_validos() -> None:
    nombres = [o.name for o in outlets.CATALOG]
    assert nombres[:6] == ["El Salto", "eldiario.es", "La Directa", "Ara", "La Vanguardia", "El País"]
    for o in outlets.CATALOG:
        assert o.ideologia in ("", *outlets.IDEOLOGIES)
        assert o.eix_nacional in ("", *outlets.NATIONAL_AXIS)
        assert o.language in ("ca", "es", "en")


def test_cada_medio_tiene_feeds_validos_y_sin_repetir_pestana() -> None:
    for o in outlets.CATALOG:
        assert o.feeds, o.name
        assert all(f.tab in outlets.TABS and f.url.startswith("https://") for f in o.feeds)
        assert len({f.tab for f in o.feeds}) == len(o.feeds), o.name  # un feed por pestaña y medio


def test_reparto_de_los_diarios_por_pestana() -> None:
    def medios(tab: str) -> list[str]:
        return [f["nombre"] for f in outlets.sources_for_tab(tab)]

    # Los seis diarios principales primero; después, los medios generales
    assert medios("mon") == ["eldiario.es", "La Vanguardia", "El País", "Europa Press", "BBC Mundo", "DW", "France 24"]
    assert medios("catalunya") == ["eldiario.es", "La Directa", "Ara", "La Vanguardia"]
    assert medios("espanya") == ["El Salto", "eldiario.es", "El País"]
    assert medios("mobilitzacions") == ["El Salto", "La Directa", "El Crític"]
    assert medios("tecnologia") == [
        "El Salto",
        "eldiario.es",
        "La Vanguardia",
        "El País",
        "Xataka",
        "Ars Technica",
        "MIT Technology Review",
    ]
    assert outlets.sources_for_tab("no-existe") == []


def test_fuente_del_catalogo_lleva_idioma_para_no_pasar_por_el_traductor() -> None:
    assert outlets.sources_for_tab("mobilitzacions")[1] == {
        "nombre": "La Directa",
        "url": "https://directa.cat/feed/",
        "idioma": "ca",
    }


def test_la_plantilla_publica_usa_los_feeds_del_catalogo() -> None:
    plantilla = json.loads((RAIZ / "config.example.json").read_text(encoding="utf-8"))
    pestana = {"mon": "mundo"}  # en la plantilla, la pestaña Món tiene el id "mundo"
    for tab in outlets.TABS:
        en_plantilla = plantilla["fuentes"][pestana.get(tab, tab)]
        for fuente in outlets.sources_for_tab(tab):
            assert fuente in en_plantilla, (tab, fuente["nombre"])


@pytest.mark.parametrize("nombre", ["El País", "EL PAÍS", "el pais", "elpais.com", "  El   País "])
def test_busca_por_nombre_alias_mayusculas_y_acentos(nombre: str) -> None:
    outlet = outlets.find_outlet(nombre)
    assert outlet is not None and outlet.name == "El País"


@pytest.mark.parametrize("nombre", ["Arabia News", "El País Vasco Hoy", "", "Diario X"])
def test_no_confunde_medios_que_solo_se_parecen(nombre: str) -> None:
    assert outlets.find_outlet(nombre) is None


# --- Validación de config.json -----------------------------------------------------


def test_valores_validos_y_vacios_se_quedan() -> None:
    cfg = {"fuentes": {"mon": [{"nombre": "X", "ideologia": "centre", "eix_nacional": ""}]}}
    outlets.clean_leanings(cfg)
    assert cfg["fuentes"]["mon"][0] == {"nombre": "X", "ideologia": "centre", "eix_nacional": ""}


def test_valor_no_valido_se_avisa_y_se_ignora(caplog: pytest.LogCaptureFixture) -> None:
    cfg = {"fuentes": {"mon": [{"nombre": "X", "ideologia": "liberal", "eix_nacional": "unionista"}]}}
    with caplog.at_level(logging.WARNING, logger="panel"):
        outlets.clean_leanings(cfg)
    assert cfg["fuentes"]["mon"][0] == {"nombre": "X", "eix_nacional": "unionista"}
    assert "liberal" in caplog.text and "mon" in caplog.text and "X" in caplog.text


@pytest.mark.parametrize("valor", [None, 3, ["esquerra"], "Esquerra"])
def test_tipos_o_mayusculas_no_validos_se_ignoran(valor: object) -> None:
    cfg = {"fuentes": {"mon": [{"nombre": "X", "ideologia": valor}]}}
    outlets.clean_leanings(cfg)
    assert "ideologia" not in cfg["fuentes"]["mon"][0]


@pytest.mark.parametrize("cfg", [{}, {"fuentes": None}, {"fuentes": {"mon": None}}, {"fuentes": {"mon": ["texto"]}}])
def test_config_sin_fuentes_o_rara_no_rompe(cfg: dict) -> None:
    outlets.clean_leanings(cfg)  # no lanza excepción


# --- Índice de orientaciones y etiquetas ---------------------------------------------


def test_indice_con_el_catalogo_y_sus_alias() -> None:
    indice = outlets.leaning_index({})
    etiquetas = outlets.labels(["elDiario.es", "Medio desconocido"], indice)
    assert etiquetas == [
        {"medio": "elDiario.es", "ideologia": "centreesquerra", "eix_nacional": ""},
        {"medio": "Medio desconocido", "ideologia": "", "eix_nacional": ""},
    ]


def test_config_cambia_la_orientacion_y_vale_para_sus_alias() -> None:
    cfg = {"fuentes": {"mon": [{"nombre": "El País", "url": "u", "eix_nacional": "no_independentista"}]}}
    indice = outlets.leaning_index(cfg)
    # Lo elegido para la fuente directa vale también para "EL PAÍS" que llega por Google Noticias
    assert outlets.labels(["EL PAÍS"], indice)[0] == {
        "medio": "EL PAÍS",
        "ideologia": "centreesquerra",  # sin tocar: la del catálogo
        "eix_nacional": "no_independentista",
    }


def test_valor_vacio_en_config_quita_la_del_catalogo() -> None:
    cfg = {"fuentes": {"mon": [{"nombre": "La Vanguardia", "url": "u", "ideologia": ""}]}}
    assert outlets.labels(["La Vanguardia"], outlets.leaning_index(cfg))[0]["ideologia"] == ""


def test_fuente_propia_que_no_esta_en_el_catalogo() -> None:
    cfg = {"fuentes": {"local": [{"nombre": "Diari Local", "url": "u", "ideologia": "centre"}]}}
    assert outlets.labels(["diari local"], outlets.leaning_index(cfg))[0]["ideologia"] == "centre"


def test_agregador_no_impone_orientacion() -> None:
    cfg = {"fuentes": {"mon": [{"nombre": "Google Noticias", "url": "u", "agregador": True, "ideologia": "dreta"}]}}
    assert outlets.labels(["Google Noticias"], outlets.leaning_index(cfg))[0]["ideologia"] == ""
