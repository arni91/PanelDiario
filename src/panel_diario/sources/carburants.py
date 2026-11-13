"""Carburantes: precio medio de la gasolina 95, la 98 y el diésel en la provincia del panel.

Datos de la API pública de precios de carburantes del Ministerio (sin clave, solo España). Una sola
petición trae todas las gasolineras de la provincia con todos sus precios; de cada combustible de
catalog/fuel.py se hace la media de las gasolineras que lo venden.
"""

from __future__ import annotations

from panel_diario.catalog import fuel
from panel_diario.sources import comun

API = (
    "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/"
    "EstacionesTerrestres/FiltroProvincia/{province}"
)


def _number(text: object) -> float | None:
    """ "1,744" -> 1.744; vacío (la gasolinera no vende ese combustible) -> None."""
    try:
        return float(str(text).replace(",", "."))
    except ValueError:
        return None


def averages(stations: list[dict]) -> list[dict]:
    """Media de cada combustible entre las gasolineras que lo venden (None si no lo vende ninguna)."""
    result = []
    for product in fuel.PRODUCTS:
        prices = [p for s in stations if (p := _number(s.get(product.ministry_field, ""))) is not None]
        result.append(
            {
                "nom": product.name,
                "mitjana": round(sum(prices) / len(prices), 3) if prices else None,
                "gasolineres": len(prices),
            }
        )
    return result


def obtener_carburants(cfg: dict) -> dict:
    """Sección de carburantes. Sin activar o sin provincia válida, {"sin_configurar": True}."""
    c = cfg.get("carburants") or {}
    province = c.get("provincia", "")
    if not c.get("activa") or province not in fuel.PROVINCES:
        return {"sin_configurar": True}
    data = comun.get(API.format(province=province), timeout=30).json()
    return {"provincia": fuel.PROVINCES[province][0], "preus": averages(data.get("ListaEESSPrecio", []))}
