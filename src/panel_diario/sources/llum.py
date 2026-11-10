"""Precio de la luz: el PVPC de cada hora de hoy y las horas más baratas y más caras.

Datos de la API pública de Red Eléctrica (apidatos.ree.es, sin clave). El PVPC es la tarifa
regulada de la península; llega en €/MWh y el panel lo muestra en €/kWh.
"""

from __future__ import annotations

from datetime import datetime

from panel_diario.sources import comun

API = "https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real"
CHEAPEST = 3  # horas más baratas que se destacan


def _pvpc_today() -> list[dict]:
    """[{"h": 0, "preu": 0.1819}, ...]: el precio de cada hora de hoy en €/kWh."""
    today = comun.ahora_local().date()
    params = {"start_date": f"{today}T00:00", "end_date": f"{today}T23:59", "time_trunc": "hour"}
    data = comun.get(API, params=params).json()
    pvpc = next(i for i in data["included"] if i["type"] == "PVPC")["attributes"]["values"]
    # Un día con cambio de hora tiene 23 o 25 horas: la hora sale de la fecha de cada valor
    return [{"h": datetime.fromisoformat(v["datetime"]).hour, "preu": round(v["value"] / 1000, 4)} for v in pvpc]


def summary(hours: list[dict], now_hour: int) -> dict:
    """Precio de ahora, media, la hora más barata y la más cara y las CHEAPEST más baratas (por hora)."""
    prices = [h["preu"] for h in hours]
    now = next((h["preu"] for h in hours if h["h"] == now_hour), None)
    cheapest = sorted(sorted(hours, key=lambda h: h["preu"])[:CHEAPEST], key=lambda h: h["h"])
    return {
        "ara": now,
        "mitjana": round(sum(prices) / len(prices), 4),
        "min": min(hours, key=lambda h: h["preu"]),
        "max": max(hours, key=lambda h: h["preu"]),
        "barates": [h["h"] for h in cheapest],
        "hores": hours,
    }


def obtener_llum(cfg: dict) -> dict:
    """Sección de la luz. Sin "llum.activa" en config.json, {"sin_configurar": True}."""
    if not (cfg.get("llum") or {}).get("activa"):
        return {"sin_configurar": True}
    hours = _pvpc_today()
    if not hours:
        raise RuntimeError("Red Eléctrica no ha publicat els preus d'avui")
    return summary(hours, comun.ahora_local().hour)
