"""Tests del catálogo de medios y de la orientación de cada fuente (outlets.py)."""

import logging

import pytest

from panel_diario import outlets

# --- Catálogo ------------------------------------------------------------------


def test_catalogo_con_los_seis_diarios_y_valores_validos() -> None:
    nombres = [o.name for o in outlets.CATALOG]
    assert nombres[:6] == ["El Salto", "eldiario.es", "La Directa", "Ara", "La Vanguardia", "El País"]
    for o in outlets.CATALOG:
        assert o.ideologia in ("", *outlets.IDEOLOGIES)
        assert o.eix_nacional in ("", *outlets.NATIONAL_AXIS)
        assert o.language in ("ca", "es")


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
