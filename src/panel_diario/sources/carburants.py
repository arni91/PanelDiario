"""Carburantes: precio medio de la gasolina 95, la 98 y el diésel cerca de la ubicación del panel.

Datos de la API pública de precios de carburantes del Ministerio (sin clave, solo España). Una sola
petición trae todas las gasolineras de la provincia con todos sus precios; de cada combustible de
catalog/fuel.py se hace la media de las gasolineras a menos de RADIUS_KM que lo venden. Si no hay
ninguna tan cerca, la media de toda la provincia.
"""

from __future__ import annotations

from panel_diario.catalog import fuel
from panel_diario.sources import comun

API = (
    "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/"
    "EstacionesTerrestres/FiltroProvincia/{province}"
)
RADIUS_KM = 10


def averages(stations: list[dict]) -> list[dict]:
    """Media de cada combustible entre las gasolineras que lo venden (None si no lo vende ninguna)."""
    result = []
    for product in fuel.PRODUCTS:
        prices = [p for s in stations if (p := comun.numero(s.get(product.ministry_field, ""))) is not None]
        result.append(
            {
                "nom": product.name,
                "mitjana": round(sum(prices) / len(prices), 3) if prices else None,
                "gasolineres": len(prices),
            }
        )
    return result


def _near(stations: list[dict], lat: float, lon: float) -> list[dict]:
    """Las gasolineras a menos de RADIUS_KM (las que no tienen posición no cuentan)."""
    near = []
    for s in stations:
        s_lat, s_lon = comun.numero(s.get("Latitud", "")), comun.numero(s.get("Longitud (WGS84)", ""))
        if s_lat is not None and s_lon is not None and comun.distancia_km(lat, lon, s_lat, s_lon) <= RADIUS_KM:
            near.append(s)
    return near


def obtener_carburants(cfg: dict) -> dict:
    """Sección de carburantes. Sin activar o sin provincia válida, {"sin_configurar": True}."""
    c = cfg.get("carburants") or {}
    province = c.get("provincia", "")
    if not c.get("activa") or province not in fuel.PROVINCES:
        return {"sin_configurar": True}
    stations = comun.get(API.format(province=province), timeout=30).json().get("ListaEESSPrecio", [])
    u = cfg.get("ubicacion") or {}
    near = _near(stations, u["lat"], u["lon"]) if "lat" in u and "lon" in u else []
    if near:
        return {"zona": f"a menys de {RADIUS_KM} km", "preus": averages(near)}
    return {"zona": f"a {fuel.PROVINCES[province][0]}", "preus": averages(stations)}
