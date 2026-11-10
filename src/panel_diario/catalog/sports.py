"""Catálogo público de deportes: los de equipos (con las competiciones de donde salen sus equipos)
y los de motor (se sigue el campeonato entero).

Los equipos salen de la API pública de ESPN (no oficial, sin clave). `path` es la ruta de ESPN de
cada competición (deporte/liga). Comprobadas el 10-11-2026: la lista de equipos y su calendario
responden. Lo que ESPN no publica (Euroliga, ACB, voleibol, rugbi, balonmano) no está: ver
docs/configuracion.md.
"""

from __future__ import annotations

from dataclasses import dataclass

# Deportes de equipos: el asistente ofrece todos los equipos de sus competiciones en una sola lista
SPORTS: dict[str, str] = {
    "futbol": "Futbol",
    "basquet": "Bàsquet",
    "futbol_america": "Futbol americà",
    "hoquei": "Hoquei sobre gel",
    "beisbol": "Beisbol",
}

# Deportes de motor: se sigue el campeonato (próxima carrera y ganador de la última)
MOTOR: dict[str, str] = {
    "f1": "Fórmula 1",
    "motogp": "MotoGP",
}


@dataclass(frozen=True)
class League:
    path: str
    name: str
    sport: str
    women: bool = False  # liga femenina: sus equipos se llaman igual que los masculinos ("Barcelona")


# El orden importa: un equipo que juega varias competiciones se guarda con la primera de la lista
# (su liga antes que la copa o la Champions). Las copas y torneos europeos están para que salgan
# también los equipos que no son de las ligas de la lista.
LEAGUES: tuple[League, ...] = (
    League("soccer/esp.1", "LaLiga", "futbol"),
    League("soccer/esp.2", "LaLiga Hypermotion", "futbol"),
    League("soccer/esp.w.1", "Liga F", "futbol", women=True),
    League("soccer/eng.1", "Premier League", "futbol"),
    League("soccer/ita.1", "Serie A", "futbol"),
    League("soccer/ger.1", "Bundesliga", "futbol"),
    League("soccer/fra.1", "Ligue 1", "futbol"),
    League("soccer/por.1", "Primeira Liga", "futbol"),
    League("soccer/ned.1", "Eredivisie", "futbol"),
    League("soccer/arg.1", "Liga Profesional Argentina", "futbol"),
    League("soccer/bra.1", "Brasileirão", "futbol"),
    League("soccer/mex.1", "Liga MX", "futbol"),
    League("soccer/usa.1", "MLS", "futbol"),
    League("soccer/uefa.champions", "Champions League", "futbol"),
    League("soccer/esp.copa_del_rey", "Copa del Rei", "futbol"),
    League("basketball/nba", "NBA", "basquet"),
    League("basketball/wnba", "WNBA", "basquet", women=True),
    League("football/nfl", "NFL", "futbol_america"),
    League("hockey/nhl", "NHL", "hoquei"),
    League("baseball/mlb", "MLB", "beisbol"),
)


def find_league(path: str) -> League | None:
    return next((lg for lg in LEAGUES if lg.path == path), None)


def leagues_of(sport: str) -> tuple[League, ...]:
    """Competiciones de un deporte, en el orden del catálogo."""
    return tuple(lg for lg in LEAGUES if lg.sport == sport)


def schedule_path(league_path: str, team_id: str) -> str:
    """Ruta del calendario de un equipo. En fútbol, "soccer/all" junta todas sus competiciones
    (liga, copa, Champions...); en los demás deportes, la de su liga."""
    sport = league_path.split("/")[0]
    base = "soccer/all" if sport == "soccer" else league_path
    return f"{base}/teams/{team_id}/schedule"
