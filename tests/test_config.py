"""Tests de la carga de config.json (config.cargar_config): el panel falla pronto y con un mensaje claro.

También comprueba que la plantilla pública config.example.json se puede leer.
"""

from pathlib import Path

import pytest

from panel_diario import config

RAIZ = Path(__file__).resolve().parent.parent


def test_config_correcta(tmp_path: Path) -> None:
    ruta = tmp_path / "config.json"
    ruta.write_text('{"ubicacion": {"nombre": "Girona"}}', encoding="utf-8")
    assert config.cargar_config(ruta) == {"ubicacion": {"nombre": "Girona"}}


def test_sin_config_explica_que_hacer(tmp_path: Path) -> None:
    with pytest.raises(config.ConfigError, match="instalar.bat"):
        config.cargar_config(tmp_path / "config.json")


def test_config_mal_escrita_dice_la_linea(tmp_path: Path) -> None:
    ruta = tmp_path / "config.json"
    ruta.write_text('{\n  "a": 1,\n  "b": 2,\n}', encoding="utf-8")  # coma de más al final
    with pytest.raises(config.ConfigError, match="línia 4"):
        config.cargar_config(ruta)


def test_config_que_no_es_un_objeto(tmp_path: Path) -> None:
    ruta = tmp_path / "config.json"
    ruta.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(config.ConfigError, match="objecte"):
        config.cargar_config(ruta)


def test_la_plantilla_publica_se_puede_cargar() -> None:
    cfg = config.cargar_config(RAIZ / "config.example.json")
    # Cada pestaña tiene sus fuentes y no hay ninguna clave rellenada
    assert {p["id"] for p in cfg["pestanas"]} == set(cfg["fuentes"])
    assert cfg["futbol"]["football_data_api_key"] == "" and cfg["claude"]["api_key"] == ""
    assert cfg["agenda"]["ical_urls"] == []
