"""Tests de la carga de config.json (config.cargar_config): el panel falla pronto y con un mensaje claro.

También comprueba que la plantilla pública config.example.json se puede leer.
"""

from pathlib import Path

import pytest

from panel_diario import config
from panel_diario.sources import comun

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
    # Cada pestaña tiene sus fuentes, no hay ninguna clave rellenada ni gustos personales
    assert {p["id"] for p in cfg["pestanas"]} == set(cfg["fuentes"])
    assert cfg["agenda"]["ical_urls"] == []
    assert cfg["esports"] == {"equips": [], "f1": False, "motogp": False}


def test_zona_horaria_de_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "TZ", comun.TZ)  # se restaura al acabar el test
    config.aplicar_zona_horaria({"ubicacion": {"zona_horaria": "America/Mexico_City"}})
    assert str(comun.TZ) == "America/Mexico_City"


def test_sin_zona_horaria_se_queda_la_de_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "TZ", comun.TZ)
    config.aplicar_zona_horaria({"ubicacion": {}})
    assert str(comun.TZ) == "Europe/Madrid"


def test_zona_horaria_desconocida_explica_el_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "TZ", comun.TZ)
    with pytest.raises(config.ConfigError, match="Marte/Olimpo"):
        config.aplicar_zona_horaria({"ubicacion": {"zona_horaria": "Marte/Olimpo"}})
