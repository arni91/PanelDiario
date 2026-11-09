"""Paso de borsa del asistente: índices a seguir y listas de valores del día (catalog/markets.py)."""

from __future__ import annotations

from panel_diario.catalog import markets


def options() -> dict:
    """Índices (con su grupo) y listas del día que ofrece el asistente."""
    return {
        "indexs": [{"simbol": i.symbol, "nom": i.name, "grup": i.group} for i in markets.INDICES],
        "moviments": [{"id": k, "nombre": v} for k, v in markets.MOVERS.items()],
    }


def current_choices(cfg: dict) -> dict:
    """Lo que hay en config.json; sin borsa, la selección por defecto."""
    b = cfg.get("borsa")
    if b is None:
        return {"indexs": list(markets.DEFAULT_INDICES), "moviments": list(markets.DEFAULT_MOVERS)}
    return {"indexs": list(b.get("indexs", [])), "moviments": list(b.get("moviments", []))}


def build(answer: dict) -> dict:
    """La parte "borsa" de config.json. Solo símbolos y listas del catálogo."""
    symbols = list(answer.get("indexs", []))
    screens = list(answer.get("moviments", []))
    unknown = [s for s in symbols if markets.find_index(s) is None] + [s for s in screens if s not in markets.MOVERS]
    if unknown:
        raise ValueError(f"«{unknown[0]}» no és a la llista.")
    if not symbols and not screens:
        raise ValueError("Tria almenys un índex o una llista (o salta aquest pas).")
    return {"borsa": {"indexs": symbols, "moviments": screens}}
