"""Catálogo público de deportes: competiciones de las que se pueden seguir equipos.

Los datos salen de la API pública de ESPN (no oficial, sin clave). `path` es la ruta de ESPN de
cada competición (deporte/liga). Comprobadas el 9-11-2026: la lista de equipos y su calendario
responden. Euroliga y ACB no están: ESPN no publica sus partidos (ver docs/configuracion.md).
"""

from __future__ import annotations

from dataclasses import dataclass

SPORTS: dict[str, str] = {
    "futbol": "Futbol",
    "basquet": "Bàsquet",
    "futbol_america": "Futbol americà",
    "hoquei": "Hoquei sobre gel",
}


@dataclass(frozen=True)
class League:
    path: str
    name: str
    sport: str


LEAGUES: tuple[League, ...] = (
    League("soccer/esp.1", "LaLiga", "futbol"),
    League("soccer/esp.2", "LaLiga Hypermotion", "futbol"),
    League("soccer/esp.w.1", "Liga F", "futbol"),
    League("soccer/eng.1", "Premier League", "futbol"),
    League("soccer/ita.1", "Serie A", "futbol"),
    League("soccer/ger.1", "Bundesliga", "futbol"),
    League("soccer/fra.1", "Ligue 1", "futbol"),
    League("soccer/por.1", "Primeira Liga", "futbol"),
    League("soccer/ned.1", "Eredivisie", "futbol"),
    League("soccer/arg.1", "Liga Profesional Argentina", "futbol"),
    League("soccer/usa.1", "MLS", "futbol"),
    League("basketball/nba", "NBA", "basquet"),
    League("basketball/wnba", "WNBA", "basquet"),
    League("football/nfl", "NFL", "futbol_america"),
    League("hockey/nhl", "NHL", "hoquei"),
)


def find_league(path: str) -> League | None:
    return next((lg for lg in LEAGUES if lg.path == path), None)


def schedule_path(league_path: str, team_id: str) -> str:
    """Ruta del calendario de un equipo. En fútbol, "soccer/all" junta todas sus competiciones
    (liga, copa, Champions...); en los demás deportes, la de su liga."""
    sport = league_path.split("/")[0]
    base = "soccer/all" if sport == "soccer" else league_path
    return f"{base}/teams/{team_id}/schedule"
