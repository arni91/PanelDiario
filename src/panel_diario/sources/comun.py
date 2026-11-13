"""Utilidades que comparten todas las fuentes de datos: peticiones HTTP, zona horaria y textos.

Las fuentes llaman a estas funciones como comun.get(...), comun.TZ...: así los tests pueden
sustituir comun.get por una respuesta falsa en un solo sitio y ninguna fuente sale a internet.
"""

from __future__ import annotations

import math
import unicodedata
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

# Zona horaria de las fechas que se muestran (la fija config.py al arrancar, desde config.json).
# En Windows, zoneinfo necesita el paquete tzdata: es una dependencia fijada en pyproject.toml.
TZ = ZoneInfo("Europe/Madrid")

UA = "PanelDiario/1.0 (widget de escritorio)"
UA_NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
TIMEOUT = 15

# Días de la semana abreviados en catalán (datetime.weekday(): 0 = lunes)
DIAS = ["dl", "dt", "dc", "dj", "dv", "ds", "dg"]


def ahora_local() -> datetime:
    return datetime.now(TZ)


def dia_curt(d: date) -> str:
    """Día corto en catalán: "dg 22/11"."""
    return f"{DIAS[d.weekday()]} {d.day}/{d.month}"


def get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = TIMEOUT,
) -> requests.Response:
    """GET con nuestro User-Agent; lanza excepción si la respuesta no es 2xx."""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    r = requests.get(url, headers=h, params=params, timeout=timeout)
    r.raise_for_status()
    return r


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta (fórmula del haversine) en km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def numero(texto: object) -> float | None:
    """ "1,744" o "41.47" -> número; vacío o no numérico -> None (las APIs públicas usan coma o punto)."""
    try:
        return float(str(texto).replace(",", "."))
    except ValueError:
        return None


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos: para comparar textos ("Catalunya" = "catalunya", "Gràcia" = "gracia")."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))
