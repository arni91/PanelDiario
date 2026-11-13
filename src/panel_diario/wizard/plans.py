"""Paso «Plans» del asistente: la ciudad de los planes y los interesos que van primero.

La ciudad es por defecto la del tiempo, pero puede ser otra (quien vive en un pueblo cercano
suele querer los planes de la ciudad grande). config.json guarda "plans".
"""

from __future__ import annotations

from panel_diario.catalog import interests

DEFAULT_DAYS = 7


def options() -> dict:
    return {"interessos": [{"id": k, "nom": i.name} for k, i in interests.INTERESTS.items()]}


def current_choices(cfg: dict) -> dict:
    c = cfg.get("plans") or {}
    return {
        "activa": bool(c.get("activa")),
        "ciutat": c.get("ciutat", ""),
        "interessos": list(c.get("interessos", [])),
        "paraules": list(c.get("paraules", [])),
    }


def build(answer: dict, weather_city: str) -> dict:
    """La parte "plans" de config.json. `weather_city`: la ciudad si no se ha escrito otra."""
    on = bool(answer.get("activa"))
    city = (answer.get("ciutat") or "").strip() or weather_city
    if on and not city:
        raise ValueError("Escriu la ciutat on vols buscar plans.")
    chosen = list(answer.get("interessos", []))
    unknown = [i for i in chosen if i not in interests.INTERESTS]
    if unknown:
        raise ValueError(f"«{unknown[0]}» no és a la llista d'interessos.")
    words = [w.strip() for w in answer.get("paraules", []) if w.strip()]
    return {"plans": {"activa": on, "ciutat": city, "dies": DEFAULT_DAYS, "interessos": chosen, "paraules": words}}
