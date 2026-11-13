"""Paso «Plans» del asistente: activar los planes cerca de casa y los interesos que van primero.

La zona sale sola de la ciudad del paso del tiempo: los planes a menos de 20 km (desde un pueblo
del área metropolitana, también la ciudad grande). config.json guarda "plans".
"""

from __future__ import annotations

from panel_diario.catalog import interests

DEFAULT_DAYS = 7
DEFAULT_RADIUS_KM = 20


def options() -> dict:
    return {"interessos": [{"id": k, "nom": i.name} for k, i in interests.INTERESTS.items()]}


def current_choices(cfg: dict) -> dict:
    c = cfg.get("plans") or {}
    return {
        "activa": bool(c.get("activa")),
        "interessos": list(c.get("interessos", [])),
        "paraules": list(c.get("paraules", [])),
    }


def build(answer: dict) -> dict:
    """La parte "plans" de config.json."""
    chosen = list(answer.get("interessos", []))
    unknown = [i for i in chosen if i not in interests.INTERESTS]
    if unknown:
        raise ValueError(f"«{unknown[0]}» no és a la llista d'interessos.")
    words = [w.strip() for w in answer.get("paraules", []) if w.strip()]
    return {
        "plans": {
            "activa": bool(answer.get("activa")),
            "radi_km": DEFAULT_RADIUS_KM,
            "dies": DEFAULT_DAYS,
            "interessos": chosen,
            "paraules": words,
        }
    }
