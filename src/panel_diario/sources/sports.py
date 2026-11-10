"""Deportes: próximos partidos y último resultado de los equipos elegidos, la Fórmula 1 y MotoGP.

Datos de la API pública de ESPN (no oficial, sin clave); MotoGP sale de sources/motogp.py. Un bloque
que falla se omite con un aviso en el log; si falla todo, se lanza la excepción y state.py conserva
el último dato bueno.
"""

from __future__ import annotations

import logging
from datetime import datetime

from panel_diario.catalog import sports
from panel_diario.sources import comun, motogp

log = logging.getLogger("panel")

ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
NEXT_GAMES = 3
# ESPN pone el país delante del nombre de la liga ("Spanish LALIGA"): se quita
NATIONALITIES = ("Spanish ", "English ", "Italian ", "German ", "French ", "Portuguese ", "Dutch ", "Argentine ")


def competition_name(event: dict, default: str) -> str:
    name = (event.get("league") or {}).get("name") or default
    for prefix in NATIONALITIES:
        name = name.removeprefix(prefix)
    return name


def _espn(path: str, params: dict | None = None) -> dict:
    return comun.get(ESPN + path, headers={"User-Agent": comun.UA_NAVEGADOR}, params=params).json()


def _local_time(iso: str) -> datetime:
    """Fecha de ESPN ("2026-11-22T13:00Z", en UTC) en la zona horaria del panel."""
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(comun.TZ)


def _score(competitor: dict) -> int | None:
    s = competitor.get("score")
    value = s.get("displayValue") if isinstance(s, dict) else s
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _game(event: dict, team_id: str, league_name: str) -> dict:
    """Un partido visto desde el equipo: rival, si juega en casa, competición, fecha y marcador."""
    comp = event["competitions"][0]
    ours = next(c for c in comp["competitors"] if str(c["team"]["id"]) == team_id)
    rival = next(c for c in comp["competitors"] if c is not ours)
    dt = _local_time(event["date"])
    return {
        "rival": rival["team"].get("shortDisplayName") or rival["team"]["displayName"],
        "local": ours.get("homeAway") == "home",
        "competicio": competition_name(event, league_name),
        "data": comun.dia_curt(dt),
        "hora": dt.strftime("%H:%M"),
        "ts": dt.timestamp(),
        "gols_equip": _score(ours),
        "gols_rival": _score(rival),
    }


def result(game: dict) -> str:
    """ "v" (victoria), "d" (derrota) o "e" (empate) del último partido."""
    a, b = game["gols_equip"], game["gols_rival"]
    if a is None or b is None:
        return ""
    return "v" if a > b else "d" if a < b else "e"


def team_games(team: dict) -> dict:
    """Próximos partidos y último resultado de un equipo de config.json."""
    path = sports.schedule_path(team["lliga"], str(team["id"]))
    events = _espn(path).get("events", [])
    if path.startswith("soccer/"):
        # En fútbol, el calendario sin parámetros trae lo jugado; con fixture=true, lo que falta
        events += _espn(path, {"fixture": "true"}).get("events", [])
    league = sports.find_league(team["lliga"])
    league_name = league.name if league else ""
    played: list[dict] = []
    upcoming: list[dict] = []
    seen: set[str] = set()
    for e in events:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        game = _game(e, str(team["id"]), league_name)
        (played if e["competitions"][0]["status"]["type"]["completed"] else upcoming).append(game)
    last = max(played, key=lambda g: g["ts"]) if played else None
    if last:
        last["resultat"] = result(last)
    return {
        "nom": team["nom"],
        "esport": league.sport if league else "",
        "proxims": sorted(upcoming, key=lambda g: g["ts"])[:NEXT_GAMES],
        "ultim": last,
    }


def formula1() -> dict:
    """Próximo gran premio y ganador del último, del calendario de ESPN."""
    data = _espn("racing/f1/scoreboard")
    now = datetime.now(comun.TZ)
    calendar = data["leagues"][0].get("calendar", [])
    upcoming = [c for c in calendar if _local_time(c["endDate"]) >= now]
    out: dict = {"proxim": None, "ultim": None}
    if upcoming:
        dt = _local_time(upcoming[0]["endDate"])
        out["proxim"] = {"nom": upcoming[0]["label"], "data": comun.dia_curt(dt)}
    for e in data.get("events", []):
        race = e["competitions"][-1]  # la última sesión del fin de semana es la carrera
        if race.get("status", {}).get("type", {}).get("completed"):
            winner = next((c for c in race.get("competitors", []) if c.get("winner")), None)
            if winner:
                out["ultim"] = {"nom": e["name"], "guanyador": winner["athlete"]["displayName"]}
    return out


def obtener_esports(cfg: dict) -> dict:
    """Sección de deportes del panel. Sin equipos ni motor en config.json, {"sin_configurar": True}."""
    e = cfg.get("esports") or {}
    teams, f1, moto = e.get("equips", []), bool(e.get("f1")), bool(e.get("motogp"))
    if not teams and not f1 and not moto:
        return {"sin_configurar": True}
    out: dict = {"equips": [], "f1": None, "motogp": None}
    errors: list[Exception] = []
    for team in teams:
        try:
            out["equips"].append(team_games(team))
        except Exception as ex:  # noqa: BLE001  (un equipo caído no tapa los demás)
            log.warning("Esports: %s sin datos (%s)", team.get("nom"), type(ex).__name__)
            errors.append(ex)
    if f1:
        try:
            out["f1"] = formula1()
        except Exception as ex:  # noqa: BLE001
            log.warning("Esports: F1 sin datos (%s)", type(ex).__name__)
            errors.append(ex)
    if moto:
        try:
            out["motogp"] = motogp.obtener_motogp()
        except Exception as ex:  # noqa: BLE001
            log.warning("Esports: MotoGP sin datos (%s)", type(ex).__name__)
            errors.append(ex)
    if errors and not out["equips"] and not out["f1"] and not out["motogp"]:
        raise RuntimeError("Les fonts d'esports no responen") from errors[-1]
    return out
