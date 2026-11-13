"""Paso «El teu dia a dia» del asistente: precio de la luz, aire y polen, y precio de los carburantes.

Tres casillas y nada más que elegir. Los carburantes necesitan la provincia, que sale sola de la
ciudad elegida en el paso del tiempo (catalog/fuel.py la reconoce). config.json guarda "llum",
"aire" y "carburants".
"""

from __future__ import annotations

from panel_diario.catalog import fuel


def current_choices(cfg: dict) -> dict:
    return {
        "llum": bool((cfg.get("llum") or {}).get("activa")),
        "aire": bool((cfg.get("aire") or {}).get("activa")),
        "carburants": bool((cfg.get("carburants") or {}).get("activa")),
    }


def build(answer: dict, city_province: str) -> dict:
    """Las partes "llum", "aire" y "carburants" de config.json.

    `city_province`: la provincia de la ciudad del panel, de la que salen los precios de los carburantes.
    """
    fuel_on = bool(answer.get("carburants"))
    province = fuel.find_province(city_province) or ""
    if fuel_on and not province:
        raise ValueError("Els preus dels carburants només hi són per a Espanya i no reconec la teva província.")
    return {
        "llum": {"activa": bool(answer.get("llum"))},
        "aire": {"activa": bool(answer.get("aire"))},
        "carburants": {"activa": fuel_on, "provincia": province},
    }
