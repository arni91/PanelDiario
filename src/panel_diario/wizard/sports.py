"""Paso de deportes del asistente: equipos de varias competiciones y la Fórmula 1.

Las competiciones salen de catalog/sports.py; los equipos de cada una, de ESPN (al pulsar
«Carrega els equips»). config.json guarda en "esports" los equipos elegidos y si se sigue la F1.
"""

from __future__ import annotations

from panel_diario.catalog import sports
from panel_diario.sources import comun

TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/{path}/teams"


def options() -> dict:
    return {
        "esports": [{"id": k, "nombre": v} for k, v in sports.SPORTS.items()],
        "lligues": [{"path": lg.path, "nom": lg.name, "esport": lg.sport} for lg in sports.LEAGUES],
    }


def teams(league_path: str) -> list[dict]:
    """Equipos de una competición, por orden alfabético."""
    if sports.find_league(league_path) is None:
        raise ValueError("Aquesta competició no és a la llista.")
    data = comun.get(TEAMS_URL.format(path=league_path), headers={"User-Agent": comun.UA_NAVEGADOR}).json()
    found = [t["team"] for t in data["sports"][0]["leagues"][0]["teams"]]
    return sorted(({"id": str(t["id"]), "nom": t["displayName"]} for t in found), key=lambda t: t["nom"])


def current_choices(cfg: dict) -> dict:
    e = cfg.get("esports") or {}
    return {"equips": list(e.get("equips", [])), "f1": bool(e.get("f1"))}


def build(answer: dict) -> dict:
    """La parte "esports" de config.json."""
    chosen = []
    for t in answer.get("equips", []):
        if sports.find_league(t.get("lliga", "")) is None:
            raise ValueError("Un equip triat és d'una competició que no és a la llista.")
        if not str(t.get("id", "")).strip() or not str(t.get("nom", "")).strip():
            raise ValueError("Cada equip necessita el seu identificador i el seu nom.")
        chosen.append({"lliga": t["lliga"], "id": str(t["id"]), "nom": t["nom"].strip()})
    f1 = bool(answer.get("f1"))
    if not chosen and not f1:
        raise ValueError("Tria almenys un equip o la Fórmula 1 (o salta aquest pas).")
    return {"esports": {"equips": chosen, "f1": f1}}
