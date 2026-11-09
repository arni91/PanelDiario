"""Avisos meteorológicos oficiales (MeteoAlarm: en España son los de AEMET).

Filtra por las zonas de config.json y devuelve como mucho 4, los más graves primero.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import feedparser

from panel_diario.sources import comun
from panel_diario.sources.traduccion import traduir_textos

SEVERIDAD = {"moderate": ("amarillo", 1), "severe": ("naranja", 2), "extreme": ("rojo", 3)}


def _fecha_aviso(valor: object) -> datetime | None:
    """Fecha CAP (ISO 8601 con zona) -> datetime con zona, o None."""
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def _fmt_aviso(dt: datetime) -> str:
    """Fecha corta para el aviso: «avui 21:00», «demà 08:00» o el día de la semana."""
    local = dt.astimezone(comun.TZ)
    hoy = comun.ahora_local().date()
    if local.date() == hoy:
        dia = "avui"
    elif local.date() == hoy + timedelta(days=1):
        dia = "demà"
    else:
        dia = comun.DIAS[local.weekday()]
    return f"{dia} {local:%H:%M}"


def obtener_avisos(cfg: dict) -> list:
    """Avisos vigentes (o que empiezan en menos de 36 h) de las zonas configuradas."""
    a = cfg.get("avisos_meteo") or {}
    if not a.get("activo", True):
        return []
    r = comun.get(a["feed"])
    feed = feedparser.parse(r.content)
    zonas = [comun.normalizar(z) for z in a.get("zonas", [])]
    excluir = [comun.normalizar(z) for z in a.get("zonas_excluir", [])]
    ahora = datetime.now(UTC)
    vistos, avisos = set(), []
    for e in feed.entries:
        area = (e.get("cap_areadesc") or "").strip()
        area_n = comun.normalizar(area)
        if zonas and not any(z in area_n for z in zonas):
            continue
        if any(z in area_n for z in excluir):
            continue
        sev = (e.get("cap_severity") or "").lower()
        if sev not in SEVERIDAD:
            continue
        expira = _fecha_aviso(e.get("cap_expires"))
        inicio = _fecha_aviso(e.get("cap_onset") or e.get("cap_effective"))
        if expira and expira < ahora:
            continue
        if inicio and inicio > ahora + timedelta(hours=36):
            continue
        evento = e.get("cap_event") or e.get("title", "Avís")
        # AEMET los publica en castellano; si el traductor falla, se queda el original
        evento = traduir_textos([evento], "ca", ("ca",)).get(evento, evento)
        clave = (area, evento, sev)
        if clave in vistos:
            continue
        vistos.add(clave)
        nivel, orden = SEVERIDAD[sev]
        cuando = ""
        if inicio and inicio > ahora:
            cuando = "des de " + _fmt_aviso(inicio)
        elif expira:
            cuando = "fins " + _fmt_aviso(expira)
        avisos.append({"nivel": nivel, "orden": orden, "evento": evento, "zona": area, "cuando": cuando})
    avisos.sort(key=lambda x: -x["orden"])
    return avisos[:4]
