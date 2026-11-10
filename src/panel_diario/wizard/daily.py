"""Paso «El teu dia a dia» del asistente: precio de la luz, aire y polen, y gasolineras baratas.

Tres casillas. Las gasolineras necesitan además el combustible, la distancia y la provincia; la
provincia sale sola de la ciudad elegida en el paso del tiempo (catalog/fuel.py la reconoce) y
solo se pregunta si no se reconoce. config.json guarda "llum", "aire" y "carburants".
"""

from __future__ import annotations

from panel_diario.catalog import fuel
from panel_diario.sources import comun

RADIUS_KM = (5, 10, 20, 30)  # distancias que ofrece el asistente; la segunda es la de por defecto


def options() -> dict:
    return {
        "carburants": [{"id": k, "nom": p.name} for k, p in fuel.PRODUCTS.items()],
        "provincies": sorted(
            ({"id": k, "nom": v[0]} for k, v in fuel.PROVINCES.items()), key=lambda p: comun.normalizar(p["nom"])
        ),
        "radis": list(RADIUS_KM),
    }


def current_choices(cfg: dict) -> dict:
    c = cfg.get("carburants") or {}
    return {
        "llum": bool((cfg.get("llum") or {}).get("activa")),
        "aire": bool((cfg.get("aire") or {}).get("activa")),
        "carburants": bool(c.get("activa")),
        "producte": c.get("producte") or next(iter(fuel.PRODUCTS)),
        "provincia": c.get("provincia", ""),
        "radi_km": c.get("radi_km") or RADIUS_KM[1],
    }


def build(answer: dict, city_province: str) -> dict:
    """Las partes "llum", "aire" y "carburants" de config.json.

    `city_province`: la provincia de la ciudad del panel, para cuando no se ha elegido otra.
    """
    fuel_on = bool(answer.get("carburants"))
    product = answer.get("producte") or next(iter(fuel.PRODUCTS))
    if product not in fuel.PRODUCTS:
        raise ValueError("Aquest carburant no és a la llista.")
    radius = int(answer.get("radi_km") or RADIUS_KM[1])
    if radius not in RADIUS_KM:
        raise ValueError("Tria una distància de la llista.")
    province = answer.get("provincia") or fuel.find_province(city_province) or ""
    if province and province not in fuel.PROVINCES:
        raise ValueError("Aquesta província no és a la llista.")
    if fuel_on and not province:
        raise ValueError("No sé de quina província és la teva ciutat: tria-la a la llista de les gasolineres.")
    return {
        "llum": {"activa": bool(answer.get("llum"))},
        "aire": {"activa": bool(answer.get("aire"))},
        "carburants": {"activa": fuel_on, "provincia": province, "producte": product, "radi_km": radius},
    }
