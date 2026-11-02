"""Eventos de hoy y de la semana desde Google Calendar (dirección secreta en formato iCal)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from panel_diario.fuentes import comun

# Por qué iCal y no la API de Google: la dirección secreta solo da lectura y no exige crear
# un proyecto en Google Cloud ni pantallas de permisos (OAuth). Para CREAR eventos sí haría falta.


def resumir_lugar(lugar: str) -> tuple[str, str]:
    """Si el "lugar" del evento es un enlace (p. ej. una videollamada), lo acorta al nombre
    de la web y devuelve también el enlace completo para poder abrirlo. -> (texto, enlace)"""
    lugar = (lugar or "").strip()
    m = re.match(r"https?://(?:www\.)?([^/\s?#]+)", lugar)
    if m:
        return f"🔗 {m.group(1)}", lugar.split()[0]
    return lugar, ""


def _etiqueta_dia(d: date, hoy: date) -> str:
    if d == hoy:
        return "Avui"
    if d == hoy + timedelta(days=1):
        return "Demà"
    return f"{comun.DIAS[d.weekday()]} {d.day}/{d.month}"


def obtener_agenda(cfg: dict) -> dict:
    """Eventos de hoy a N días de todos los calendarios iCal, ordenados por hora."""
    ag = cfg.get("agenda") or {}
    urls = [u.strip() for u in ag.get("ical_urls", []) if u and u.strip()]
    if not urls:
        return {"sin_url": True}

    import icalendar  # lee el formato .ics
    import recurring_ical_events  # expande los eventos que se repiten (semanales, etc.)

    hoy = comun.ahora_local().date()
    tz = comun.TZ
    inicio = datetime(hoy.year, hoy.month, hoy.day, tzinfo=tz)
    fin = inicio + timedelta(days=int(ag.get("dias", 7)))

    eventos = []
    for url in urls:
        cal = icalendar.Calendar.from_ical(comun.get(url, timeout=30).content)
        for ev in recurring_ical_events.of(cal).between(inicio, fin):
            ini = ev.get("DTSTART").dt
            fin_ev = ev.get("DTEND").dt if ev.get("DTEND") else None
            todo_el_dia = not isinstance(ini, datetime)  # los eventos de día completo son "date"
            if todo_el_dia:
                dia, hora, hora_fin = max(ini, hoy), "", ""
                orden = datetime(dia.year, dia.month, dia.day, tzinfo=tz)
            else:
                ini = ini.astimezone(tz) if ini.tzinfo else ini.replace(tzinfo=tz)
                dia, hora = ini.date(), ini.strftime("%H:%M")
                hora_fin = ""
                if isinstance(fin_ev, datetime):
                    fin_ev = fin_ev.astimezone(tz) if fin_ev.tzinfo else fin_ev.replace(tzinfo=tz)
                    hora_fin = fin_ev.strftime("%H:%M")
                orden = ini
            eventos.append(
                {
                    "titulo": str(ev.get("SUMMARY", "(sense títol)")),
                    **dict(zip(("lugar", "enlace"), resumir_lugar(str(ev.get("LOCATION", "") or "")), strict=True)),
                    "dia": _etiqueta_dia(dia, hoy),
                    "es_hoy": dia == hoy,
                    "hora": hora,
                    "hora_fin": hora_fin,
                    "todo_el_dia": todo_el_dia,
                    "_orden": orden.timestamp(),
                }
            )

    eventos.sort(key=lambda e: (e["_orden"], not e["todo_el_dia"]))
    for e in eventos:
        del e["_orden"]
    return {"eventos": eventos}
