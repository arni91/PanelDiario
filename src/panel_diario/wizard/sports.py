"""Paso de deportes del asistente: un desplegable de deportes y, debajo, sus equipos o su campeonato.

En un deporte de equipos salen todos los equipos de sus competiciones (catalog/sports.py) en una
sola lista, sin elegir competición: se marca el equipo y ya está. Los de motor (F1, MotoGP) se
siguen enteros. Con «Un altre…» se escribe el nombre de cualquier equipo y se busca en ESPN: solo
salen los que tienen partidos publicados. config.json guarda en "esports" los equipos, "f1" y "motogp".
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor

from panel_diario.catalog import sports
from panel_diario.sources import comun
from panel_diario.sources import sports as espn

log = logging.getLogger("panel")

TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/{path}/teams"
SEARCH_URL = "https://site.web.api.espn.com/apis/search/v2"
MAX_PARALLEL = 6  # peticiones a la vez a ESPN, para no saturarla
MAX_FOUND = 8  # resultados del buscador que se comprueban
MIN_SEARCH = 3  # letras mínimas para buscar
# Competición de ESPN tal como va en la URL ("soccer/sco.1", "rugby/270557"): se valida antes de guardarla
LEAGUE_PATH = re.compile(r"^[a-z-]+/[a-z0-9._-]+$")


def options() -> dict:
    team_sports = [{"id": k, "nombre": v, "tipus": "equips"} for k, v in sports.SPORTS.items()]
    motor = [{"id": k, "nombre": v, "tipus": "motor"} for k, v in sports.MOTOR.items()]
    # Las competiciones solo sirven para mostrar de dónde es cada equipo elegido
    leagues = [{"path": lg.path, "nom": lg.name} for lg in sports.LEAGUES]
    return {"esports": team_sports + motor, "lligues": leagues}


def _league_teams(league: sports.League) -> list[dict] | None:
    """Equipos de una competición; None si ESPN no responde (las demás siguen)."""
    try:
        data = comun.get(TEAMS_URL.format(path=league.path), headers={"User-Agent": comun.UA_NAVEGADOR}).json()
        found = [t["team"] for t in data["sports"][0]["leagues"][0]["teams"]]
    except Exception as ex:  # noqa: BLE001  (una competición caída no deja sin equipos las demás)
        log.warning("Asistente: equips de %s sense resposta (%s)", league.name, type(ex).__name__)
        return None
    return [
        {"id": str(t["id"]), "nom": t["displayName"], "lliga": league.path, "competicio": league.name} for t in found
    ]


def teams(sport: str) -> list[dict]:
    """Todos los equipos de un deporte, por orden alfabético y sin repetir.

    Un equipo que juega varias competiciones (liga, copa, Champions) sale una vez, con la primera
    del catálogo: dos entradas son el mismo equipo si comparten calendario en ESPN.
    """
    leagues = sports.leagues_of(sport)
    if not leagues:
        raise ValueError("Aquest esport no és a la llista.")
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        per_league = list(pool.map(_league_teams, leagues))
    if all(r is None for r in per_league):
        raise RuntimeError("ESPN no respon.")
    unique: dict[str, dict] = {}
    for found in per_league:
        for t in found or []:
            unique.setdefault(sports.schedule_path(t["lliga"], t["id"]), t)
    return sorted(unique.values(), key=lambda t: comun.normalizar(t["nom"]))


# ---------------------------------------------------------------------------
# «Un altre…»: cualquier equipo de ESPN, buscado por su nombre
# ---------------------------------------------------------------------------


def _found_team(result: dict) -> dict | None:
    """Un resultado del buscador como equipo de config.json; None si le falta la competición o el id."""
    team_id = re.search(r"~t:(\d+)$", result.get("uid", ""))
    path = f"{result.get('sport')}/{result.get('defaultLeagueSlug')}"
    if not team_id or not LEAGUE_PATH.match(path) or not result.get("displayName"):
        return None
    return {
        "id": team_id.group(1),
        "nom": result["displayName"],
        "lliga": path,
        "competicio": result.get("subtitle", ""),
    }


def _has_games(team: dict) -> bool:
    """Si ESPN publica partidos del equipo (próximos o el último): si no, el panel no tendría nada que mostrar."""
    try:
        games = espn.team_games(team)
    except Exception:  # noqa: BLE001  (calendario vacío o inexistente: el equipo no se ofrece)
        return False
    return bool(games["proxims"] or games["ultim"])


def search_teams(text: str) -> list[dict]:
    """Equipos de cualquier deporte con ese nombre que tienen partidos publicados en ESPN."""
    text = text.strip()
    if len(text) < MIN_SEARCH:
        raise ValueError(f"Escriu almenys {MIN_SEARCH} lletres del nom de l'equip.")
    params = {"query": text, "limit": MAX_FOUND, "type": "team"}
    data = comun.get(SEARCH_URL, headers={"User-Agent": comun.UA_NAVEGADOR}, params=params).json()
    results = [c for g in data.get("results", []) if g.get("type") == "team" for c in g.get("contents", [])]
    found = [t for t in map(_found_team, results[:MAX_FOUND]) if t]
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        with_games = list(pool.map(_has_games, found))
    return [t for t, ok in zip(found, with_games, strict=True) if ok]


# ---------------------------------------------------------------------------
# Lo que ya hay configurado y lo que se guarda
# ---------------------------------------------------------------------------


def current_choices(cfg: dict) -> dict:
    e = cfg.get("esports") or {}
    return {"equips": list(e.get("equips", [])), "f1": bool(e.get("f1")), "motogp": bool(e.get("motogp"))}


def build(answer: dict) -> dict:
    """La parte "esports" de config.json."""
    chosen = []
    for t in answer.get("equips", []):
        if not LEAGUE_PATH.match(str(t.get("lliga", ""))):
            raise ValueError("Un equip triat no té una competició vàlida.")
        if not str(t.get("id", "")).strip().isdigit() or not str(t.get("nom", "")).strip():
            raise ValueError("Cada equip necessita el seu identificador i el seu nom.")
        team = {"lliga": t["lliga"], "id": str(t["id"]).strip(), "nom": t["nom"].strip()}
        if sports.find_league(t["lliga"]) is None and str(t.get("competicio", "")).strip():
            team["competicio"] = str(t["competicio"]).strip()  # equipo de «Un altre…»: su competición, para mostrarla
        chosen.append(team)
    f1, motogp = bool(answer.get("f1")), bool(answer.get("motogp"))
    if not chosen and not f1 and not motogp:
        raise ValueError("Tria almenys un equip o un campionat de motor (o salta aquest pas).")
    return {"esports": {"equips": chosen, "f1": f1, "motogp": motogp}}
