"""MotoGP: próximo gran premio y ganador del último, para la sección de deportes.

Datos de la API pública de resultados de motogp.com (no oficial, sin clave). ESPN no tiene MotoGP.
Si falla, lanza la excepción y sources/sports.py lo trata como cualquier otro bloque caído.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from panel_diario.sources import comun

API = "https://api.motogp.pulselive.com/motogp/v1/results/"
RACE = "RAC"  # la carrera larga del domingo (SPR es la sprint del sábado)


def _api(path: str, params: dict | None = None) -> Any:
    return comun.get(API + path, headers={"User-Agent": comun.UA_NAVEGADOR}, params=params).json()


def gp_name(raw: str) -> str:
    """ "GRAND PRIX OF PORTUGAL" → "Grand Prix of Portugal"."""
    return raw.strip().title().replace(" Of ", " of ")


def _season_id() -> str:
    return next(s["id"] for s in _api("seasons") if s.get("current"))


def _winner(season_id: str, event_id: str) -> str | None:
    """Ganador de la carrera de MotoGP (no Moto2 ni Moto3) de un gran premio."""
    categories = _api("categories", {"seasonUuid": season_id})
    motogp = next(c for c in categories if c["legacy_id"] == 3)  # 3 = MotoGP, 2 = Moto2, 1 = Moto3
    sessions = _api("sessions", {"eventUuid": event_id, "categoryUuid": motogp["id"]})
    race = next((s for s in sessions if s["type"] == RACE), None)
    if race is None:
        return None
    classification = _api(f"session/{race['id']}/classification", {"test": "false"}).get("classification", [])
    return classification[0]["rider"]["full_name"] if classification else None


def obtener_motogp() -> dict:
    """{"proxim": {nom, data} | None, "ultim": {nom, guanyador} | None}, como la F1."""
    season_id = _season_id()
    events = [e for e in _api("events", {"seasonUuid": season_id}) if not e.get("test")]
    events.sort(key=lambda e: e["date_end"])
    finished = [e for e in events if e["status"] == "FINISHED"]
    upcoming = [e for e in events if e["status"] != "FINISHED"]
    out: dict = {"proxim": None, "ultim": None}
    if upcoming:
        nxt = upcoming[0]
        out["proxim"] = {"nom": gp_name(nxt["name"]), "data": comun.dia_curt(date.fromisoformat(nxt["date_end"]))}
    if finished:
        winner = _winner(season_id, finished[-1]["id"])
        if winner:
            out["ultim"] = {"nom": gp_name(finished[-1]["name"]), "guanyador": winner}
    return out
