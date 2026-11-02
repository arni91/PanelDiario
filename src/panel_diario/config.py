"""Rutas del proyecto y lectura de config.json (la configuración personal, fuera de git).

Si config.json falta o está mal escrito, cargar_config() lanza ConfigError con un mensaje
claro en catalán (lo ve el usuario) y el panel no arranca.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PAQUETE = Path(__file__).resolve().parent  # carpeta del paquete: ui/ y demo.json
# config.json vive en la raíz del proyecto (src/panel_diario -> src -> raíz), donde lo edita cada uno.
# Funciona porque uv instala el proyecto en modo editable: el código se ejecuta desde esta carpeta.
CONFIG = PAQUETE.parents[1] / "config.json"
# Datos que genera el panel al funcionar (caché, posición de la píldora, log)
DATOS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PanelDiario"
DATOS_DIR.mkdir(parents=True, exist_ok=True)
CACHE = DATOS_DIR / "cache.json"
POSICION = DATOS_DIR / "posicion_widget.json"


class ConfigError(Exception):
    """config.json falta o no se puede leer: el panel no puede arrancar."""


def cargar_config(ruta: Path = CONFIG) -> dict:
    if not ruta.exists():
        raise ConfigError("No trobo config.json. Executa instalar.bat: el crea a partir de config.example.json.")
    try:
        cfg = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        raise ConfigError(
            f"config.json està mal escrit (línia {ex.lineno}, columna {ex.colno}): {ex.msg}.\n"
            "Revisa comes, cometes i claus en aquella línia."
        ) from ex
    if not isinstance(cfg, dict):
        raise ConfigError("config.json ha de ser un objecte JSON ({ ... }).")
    return cfg
