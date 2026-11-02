"""Próximos partidos y último resultado del equipo de config.json (football-data.org, clave gratuita)."""

from __future__ import annotations

from datetime import datetime

from panel_diario.fuentes import comun


def _hora_local(iso_utc: str) -> datetime:
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return dt.astimezone(comun.TZ)


# Noms de les competicions en català (football-data.org els dona en anglès o castellà)
COMPETICIONS = {
    "Primera Division": "Lliga",
    "UEFA Champions League": "Lliga de Campions",
    "Copa del Rey": "Copa del Rei",
    "Supercopa de España": "Supercopa",
}


def obtener_futbol(cfg: dict) -> dict:
    """Próximos 3 partidos y último resultado, desde el punto de vista del equipo configurado."""
    f = cfg.get("futbol") or {}
    clave = (f.get("football_data_api_key") or "").strip()
    nombre = f.get("nombre") or "Futbol"
    if not clave:
        return {"sin_clave": True, "nombre": nombre}
    equipo_id = f.get("team_id")
    if not equipo_id:
        return {"sin_equipo": True, "nombre": nombre}
    r = comun.get(f"https://api.football-data.org/v4/teams/{equipo_id}/matches", headers={"X-Auth-Token": clave})
    partidos = r.json().get("matches", [])

    def fmt(p: dict) -> dict:
        """Un partido en el formato que pinta la interfaz (rival, fecha, hora, goles)."""
        dt = _hora_local(p["utcDate"])
        if p["status"] == "SCHEDULED":  # hora provisional (00:00 UTC): el día bueno es el UTC
            dt = datetime.fromisoformat(p["utcDate"].replace("Z", "+00:00"))
        local = p["homeTeam"]["id"] == equipo_id
        rival = p["awayTeam"] if local else p["homeTeam"]
        ft = (p.get("score") or {}).get("fullTime") or {}
        return {
            "rival": rival.get("shortName") or rival.get("name"),
            "escudo": rival.get("crest", ""),
            "local": local,
            "competicion": COMPETICIONS.get(
                (p.get("competition") or {}).get("name", ""), (p.get("competition") or {}).get("name", "")
            ),
            "fecha": f"{comun.DIAS[dt.weekday()]} {dt.day}/{dt.month}",
            # SCHEDULED = fecha conocida pero hora aún sin confirmar por la liga
            "hora": "hora per confirmar" if p["status"] == "SCHEDULED" else dt.strftime("%H:%M"),
            "goles_equipo": ft.get("home") if local else ft.get("away"),
            "goles_rival": ft.get("away") if local else ft.get("home"),
            "estado": p["status"],
        }

    terminados = [p for p in partidos if p["status"] == "FINISHED"]
    proximos = [p for p in partidos if p["status"] in ("SCHEDULED", "TIMED", "IN_PLAY", "PAUSED")]
    proximos.sort(key=lambda p: p["utcDate"])
    terminados.sort(key=lambda p: p["utcDate"])
    return {
        "nombre": nombre,
        "proximos": [fmt(p) for p in proximos[:3]],
        "ultimo": fmt(terminados[-1]) if terminados else None,
    }
