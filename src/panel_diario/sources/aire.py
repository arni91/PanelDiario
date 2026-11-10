"""Calidad del aire y polen en la ubicación del panel.

Datos de la API pública de calidad del aire de Open-Meteo (sin clave), la misma fuente que el
tiempo. La calidad del aire es el índice europeo (EAQI); el polen solo existe en Europa y en
temporada: fuera de ella llega vacío y no se muestra.
"""

from __future__ import annotations

import math

from panel_diario.sources import comun

API = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Índice europeo de calidad del aire: límite superior de cada tramo y su nombre (escala de la AEMA)
AQI_LEVELS: tuple[tuple[float, str], ...] = (
    (20, "Bona"),
    (40, "Acceptable"),
    (60, "Moderada"),
    (80, "Dolenta"),
    (100, "Molt dolenta"),
    (math.inf, "Extremadament dolenta"),
)

# Pólenes de Open-Meteo y su nombre en catalán
POLLENS: dict[str, str] = {
    "grass_pollen": "Gramínies",
    "olive_pollen": "Olivera",
    "birch_pollen": "Bedoll",
    "alder_pollen": "Vern",
    "mugwort_pollen": "Artemísia",
    "ragweed_pollen": "Ambròsia",
}
# Granos/m³: por debajo del primero no se muestra. Tramos orientativos, iguales para todos los pólenes
POLLEN_LEVELS: tuple[tuple[float, str], ...] = ((1, ""), (10, "baix"), (50, "moderat"), (math.inf, "alt"))


def level_of(value: float, levels: tuple[tuple[float, str], ...]) -> tuple[int, str]:
    """(número de tramo, nombre) del primer tramo cuyo límite supera el valor."""
    return next((i, name) for i, (limit, name) in enumerate(levels) if value < limit)


def pollen_today(hourly: dict) -> list[dict]:
    """Cada polen presente hoy (su máximo de las horas del día), de más a menos."""
    out = []
    for key, name in POLLENS.items():
        values = [v for v in hourly.get(key) or [] if v is not None]
        peak = max(values, default=0.0)
        tier, label = level_of(peak, POLLEN_LEVELS)
        if tier > 0:
            out.append({"nom": name, "valor": round(peak, 1), "nivell": label})
    return sorted(out, key=lambda p: p["valor"], reverse=True)


def obtener_aire(cfg: dict) -> dict:
    """Sección de aire y polen. Sin "aire.activa" en config.json, {"sin_configurar": True}."""
    if not (cfg.get("aire") or {}).get("activa"):
        return {"sin_configurar": True}
    u = cfg["ubicacion"]
    params = {
        "latitude": u["lat"],
        "longitude": u["lon"],
        "current": "european_aqi",
        "hourly": ",".join(POLLENS),
        "forecast_days": 1,
        "timezone": u.get("zona_horaria", "auto"),
    }
    data = comun.get(API, params=params).json()
    aqi = data["current"]["european_aqi"]
    tier, label = level_of(aqi, AQI_LEVELS)
    return {"ica": round(aqi), "qualitat": label, "nivell": tier, "pollen": pollen_today(data.get("hourly", {}))}
