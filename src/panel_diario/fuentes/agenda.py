"""Eventos de hoy y de la semana desde calendarios iCal (dirección secreta de Google Calendar, Outlook...).

La dirección iCal es secreta: quien la tiene lee el calendario. Por eso los errores de esta
fuente (que acaban en el log, en cache.json y en el pie del panel) nunca la incluyen.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import requests

from panel_diario.fuentes import comun

# Por qué iCal y no la API de Google: la dirección secreta solo da lectura y no exige crear
# un proyecto en Google Cloud ni pantallas de permisos (OAuth). Para CREAR eventos sí haría falta.


class ErrorAgenda(Exception):
    """Un calendario no se puede leer. El mensaje dice cuál (por su número) y por qué, sin la dirección."""


def _descargar(url: str, n: int) -> object:
    """Descarga y lee el calendario número `n`. Los errores de requests llevan la URL: se sustituyen."""
    import icalendar  # lee el formato .ics

    try:
        contenido = comun.get(url, timeout=30).content
    except requests.RequestException as ex:
        estado = ex.response.status_code if isinstance(ex, requests.HTTPError) and ex.response is not None else 0
        # "from None": tampoco en la traza encadenada, por si alguien la registra
        raise ErrorAgenda(f"calendari {n}: {f'HTTP {estado}' if estado else type(ex).__name__}") from None
    try:
        return icalendar.Calendar.from_ical(contenido)
    except ValueError:
        raise ErrorAgenda(f"calendari {n}: la resposta no és un calendari iCal") from None


def comprobar_ical(url: str) -> int:
    """Número de eventos del calendario (lo usa el asistente). Lanza ErrorAgenda si no se puede leer."""
    cal = _descargar(url, 1)
    return len(cal.walk("VEVENT"))  # type: ignore[attr-defined]


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

    import recurring_ical_events  # expande los eventos que se repiten (semanales, etc.)

    hoy = comun.ahora_local().date()
    tz = comun.TZ
    inicio = datetime(hoy.year, hoy.month, hoy.day, tzinfo=tz)
    fin = inicio + timedelta(days=int(ag.get("dias", 7)))

    eventos = []
    for n, url in enumerate(urls, start=1):
        cal = _descargar(url, n)
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
