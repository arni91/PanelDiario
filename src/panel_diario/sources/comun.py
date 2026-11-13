"""Utilidades que comparten todas las fuentes de datos: peticiones HTTP, zona horaria y textos.

Las fuentes llaman a estas funciones como comun.get(...), comun.TZ...: así los tests pueden
sustituir comun.get por una respuesta falsa en un solo sitio y ninguna fuente sale a internet.
"""

from __future__ import annotations

import logging
import math
import ssl
import unicodedata
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter

log = logging.getLogger("panel")

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


# ---------------------------------------------------------------------------
# TLS compatible: algunos servidores públicos (el de precios de carburantes del Ministerio) cortan
# la negociación cuando Python (OpenSSL 3.5) propone el intercambio de claves ECDHE, y aceptan
# TLS 1.2 con intercambio RSA, que es lo que acaba usando curl con el TLS de Windows. Solo se usa
# como segundo intento y para datos públicos: el intercambio RSA no tiene secreto hacia delante.
# ---------------------------------------------------------------------------
CIFRADOS_COMPATIBLES = "AES256-GCM-SHA384:AES128-GCM-SHA256"


class _AdaptadorTlsCompatible(HTTPAdapter):
    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        ctx = ssl.create_default_context()  # sigue verificando el certificado y el nombre del servidor
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers(CIFRADOS_COMPATIBLES)
        kwargs["ssl_context"] = ctx
        super().init_poolmanager(*args, **kwargs)


def get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = TIMEOUT,
    tls_compatible: bool = False,
) -> requests.Response:
    """GET con nuestro User-Agent; lanza excepción si la respuesta no es 2xx.

    `tls_compatible`: si la negociación TLS falla, un segundo intento con TLS 1.2 e intercambio RSA.
    """
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    try:
        r = requests.get(url, headers=h, params=params, timeout=timeout)
    except requests.exceptions.SSLError:
        if not tls_compatible:
            raise
        log.info("Negociación TLS cortada; segundo intento con TLS compatible")
        with requests.Session() as s:
            s.mount("https://", _AdaptadorTlsCompatible())
            r = s.get(url, headers=h, params=params, timeout=timeout)
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
