"""Carburantes: las gasolineras más baratas cerca de la ubicación del panel, para un combustible.

Datos de la API pública de precios de carburantes del Ministerio (sin clave, solo España). Se pide
la provincia entera de un combustible y se quedan las gasolineras a menos de "radi_km" de la
ubicación, ordenadas por precio.
"""

from __future__ import annotations

import math

from panel_diario.catalog import fuel
from panel_diario.sources import comun

API = (
    "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/"
    "EstacionesTerrestres/FiltroProvinciaProducto/{province}/{product}"
)
DEFAULT_RADIUS_KM = 10
CHEAPEST = 3


def _number(text: str) -> float | None:
    """ "1,744" -> 1.744; vacío (la gasolinera no vende ese combustible) -> None."""
    try:
        return float(text.replace(",", "."))
    except (AttributeError, ValueError):
        return None


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta (fórmula del haversine) en km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def _station(s: dict, lat: float, lon: float) -> dict | None:
    """Una gasolinera del Ministerio con su precio y distancia; None si le falta el precio o la posición."""
    price, s_lat, s_lon = (
        _number(s.get("PrecioProducto", "")),
        _number(s.get("Latitud", "")),
        _number(s.get("Longitud (WGS84)", "")),
    )
    if price is None or s_lat is None or s_lon is None:
        return None
    return {
        "nom": (s.get("Rótulo") or "").strip().title(),
        "adreca": (s.get("Dirección") or "").strip().title(),
        "localitat": (s.get("Localidad") or "").strip().title(),
        "preu": price,
        "km": round(distance_km(lat, lon, s_lat, s_lon), 1),
    }


def obtener_carburants(cfg: dict) -> dict:
    """Sección de carburantes. Sin activar, o sin provincia o combustible válidos, {"sin_configurar": True}."""
    c = cfg.get("carburants") or {}
    product = fuel.PRODUCTS.get(c.get("producte", ""))
    province = c.get("provincia", "")
    if not c.get("activa") or product is None or province not in fuel.PROVINCES:
        return {"sin_configurar": True}
    u = cfg["ubicacion"]
    radius = float(c.get("radi_km") or DEFAULT_RADIUS_KM)
    data = comun.get(API.format(province=province, product=product.ministry_id)).json()
    stations = [st for s in data.get("ListaEESSPrecio", []) if (st := _station(s, u["lat"], u["lon"]))]
    near = sorted((s for s in stations if s["km"] <= radius), key=lambda s: (s["preu"], s["km"]))
    prices = [s["preu"] for s in near]
    return {
        "producte": product.name,
        "radi_km": radius,
        "gasolineres": near[:CHEAPEST],
        "mitjana": round(sum(prices) / len(prices), 3) if prices else None,
        "total": len(near),
    }
