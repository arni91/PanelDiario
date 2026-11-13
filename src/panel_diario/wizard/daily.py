"""Paso «El teu dia a dia» del asistente: precio de la luz, aire y polen, y precio de los carburantes.

Tres casillas. Los carburantes necesitan además la provincia, que sale sola de la ciudad elegida
en el paso del tiempo (catalog/fuel.py la reconoce) y solo se pregunta si no se reconoce.
config.json guarda "llum", "aire" y "carburants".
"""

from __future__ import annotations

from panel_diario.catalog import fuel
from panel_diario.sources import comun


def options() -> dict:
    return {
        "provincies": sorted(
            ({"id": k, "nom": v[0]} for k, v in fuel.PROVINCES.items()), key=lambda p: comun.normalizar(p["nom"])
        ),
    }


def current_choices(cfg: dict) -> dict:
    c = cfg.get("carburants") or {}
    return {
        "llum": bool((cfg.get("llum") or {}).get("activa")),
        "aire": bool((cfg.get("aire") or {}).get("activa")),
        "carburants": bool(c.get("activa")),
        "provincia": c.get("provincia", ""),
    }


def build(answer: dict, city_province: str) -> dict:
    """Las partes "llum", "aire" y "carburants" de config.json.

    `city_province`: la provincia de la ciudad del panel, para cuando no se ha elegido otra.
    """
    fuel_on = bool(answer.get("carburants"))
    province = answer.get("provincia") or fuel.find_province(city_province) or ""
    if province and province not in fuel.PROVINCES:
        raise ValueError("Aquesta província no és a la llista.")
    if fuel_on and not province:
        raise ValueError("No sé de quina província és la teva ciutat: tria-la a la llista dels carburants.")
    return {
        "llum": {"activa": bool(answer.get("llum"))},
        "aire": {"activa": bool(answer.get("aire"))},
        "carburants": {"activa": fuel_on, "provincia": province},
    }
