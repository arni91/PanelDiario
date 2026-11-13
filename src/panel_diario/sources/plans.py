"""Plans: exposiciones, conciertos, charlas, festivales... de los próximos días cerca de casa.

Datos de la Agenda Cultural de Catalunya (dades obertes de la Generalitat, API Socrata, sin
clave; solo Cataluña). Se piden los planes de un cuadrado alrededor de la ubicación del panel y
se quedan los que están a menos de "radi_km" (quien vive en Sant Cugat ve Barcelona, Sabadell,
Terrassa, Rubí...). Los que coinciden con los interesos de config.json (catalog/interests.py y
palabras propias) van en "per_a_tu"; "tot" es la agenda entera, primero lo que dura pocos días.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta

from panel_diario.catalog import interests
from panel_diario.sources import comun

API = "https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json"
DEFAULT_DAYS = 7
DEFAULT_RADIUS_KM = 20
KM_PER_DEGREE = 111.0  # un grado de latitud
MAX_FOR_YOU = 15
MAX_ALL = 20
SHORT_DAYS = 7  # lo que dura más (exposiciones largas) va detrás en "tot"
FIELDS = (
    "codi,denominaci,subt_tol,descripcio,tags_categor_es,data_inici,data_fi,permanent,"
    "gratuita,espai,latitud,longitud,enlla_os,linkbotoentrades,url"
)


def _day(iso: str | None) -> date | None:
    try:
        return datetime.fromisoformat(iso or "").date()
    except ValueError:
        return None


def _when(start: date, end: date, today: date) -> str:
    """Fechas en corto: "dv 13/11", "fins dg 22/11" o "dv 13/11 – dg 22/11"."""
    if start == end:
        return comun.dia_curt(start)
    if start <= today:
        return "fins " + comun.dia_curt(end)
    return f"{comun.dia_curt(start)} – {comun.dia_curt(end)}"


def _link(e: dict) -> str:
    """El enlace del plan; si no tiene, el de las entradas o la web del espacio."""
    for text in (e.get("enlla_os"), e.get("linkbotoentrades"), e.get("url")):
        found = re.search(r"https?://\S+", text or "")
        if found:
            return found.group(0).rstrip(",")
    return ""


def _categories(e: dict) -> list[str]:
    """ "agenda:categories/festivals-i-mostres" -> "festivals i mostres"."""
    tags = (e.get("tags_categor_es") or "").split(",")
    return [t.rsplit("/", 1)[-1].replace("-", " ") for t in tags if t.strip()]


def _matches(e: dict, wanted: dict[str, re.Pattern[str]]) -> list[str]:
    """Nombres de los interesos que aparecen en el plan."""
    text = comun.normalizar(
        " ".join([e.get("denominaci", ""), e.get("subt_tol", ""), e.get("descripcio", ""), *_categories(e)])
    )
    return [name for name, p in wanted.items() if p.search(text)]


def _wanted(cfg_plans: dict) -> dict[str, re.Pattern[str]]:
    """Interés -> expresión que lo encuentra: los del catálogo elegidos y cada palabra propia."""
    wanted = {
        interests.INTERESTS[i].name: interests.pattern(interests.INTERESTS[i].keywords)
        for i in cfg_plans.get("interessos", [])
        if i in interests.INTERESTS
    }
    for word in cfg_plans.get("paraules", []):
        if word.strip():
            wanted[word.strip()] = interests.pattern([interests.own_word(word)])
    return wanted


def _distance(e: dict, lat: float, lon: float) -> float | None:
    e_lat, e_lon = comun.numero(e.get("latitud", "")), comun.numero(e.get("longitud", ""))
    if e_lat is None or e_lon is None:
        return None
    return comun.distancia_km(lat, lon, e_lat, e_lon)


def build_plans(
    events: list[dict], wanted: dict[str, re.Pattern[str]], today: date, home: tuple[float, float], radius: float
) -> tuple[list, list]:
    """(per_a_tu, tot) a partir de los planes de la Agenda: dentro del radio, sin repetidos ni permanentes."""
    seen: set[str] = set()
    ranked: list[tuple[bool, date, list[str], dict]] = []  # (largo, fecha para ordenar, interesos, plan)
    for e in events:
        start, end = _day(e.get("data_inici")), _day(e.get("data_fi"))
        km = _distance(e, *home)
        if not start or not end or km is None or km > radius:
            continue
        if e.get("codi") in seen or e.get("permanent") == "Sí":
            continue
        seen.add(e.get("codi", ""))
        long = (end - start).days > SHORT_DAYS
        matched = _matches(e, wanted)
        plan = {
            "titol": (e.get("denominaci") or "").strip(),
            "lloc": (e.get("espai") or "").strip(),
            "km": round(km),
            "quan": _when(start, end, today),
            "categoria": (_categories(e) or [""])[0],
            "interessos": matched,
            "gratuit": e.get("gratuita") == "Sí",
            "enllac": _link(e),
        }
        # Lo que dura pocos días por fecha de inicio; lo largo detrás, primero lo que acaba antes
        ranked.append((long, end if long else start, matched, plan))
    ranked.sort(key=lambda r: (r[0], r[1]))
    # Per a tu: primero lo que coincide con más interesos (sorted es estable: a igualdad, el orden de antes)
    for_you = [r[3] for r in sorted((r for r in ranked if r[2]), key=lambda r: -len(r[2]))]
    return for_you[:MAX_FOR_YOU], [r[3] for r in ranked][:MAX_ALL]


def _where(lat: float, lon: float, radius: float, today: date, days: int) -> str:
    """Filtro de la consulta: el cuadrado que contiene el círculo y las fechas. Solo números: nada que escapar."""
    dlat = radius / KM_PER_DEGREE
    dlon = radius / (KM_PER_DEGREE * math.cos(math.radians(lat)))
    return (
        f"latitud::number between {lat - dlat:.4f} and {lat + dlat:.4f}"
        f" AND longitud::number between {lon - dlon:.4f} and {lon + dlon:.4f}"
        f" AND data_fi >= '{today.isoformat()}' AND data_inici <= '{(today + timedelta(days=days)).isoformat()}'"
    )


def obtener_plans(cfg: dict) -> dict:
    """Sección de planes. Sin activar o sin ubicación, {"sin_configurar": True}."""
    c = cfg.get("plans") or {}
    u = cfg.get("ubicacion") or {}
    if not c.get("activa") or "lat" not in u or "lon" not in u:
        return {"sin_configurar": True}
    today = comun.ahora_local().date()
    days = int(c.get("dies") or DEFAULT_DAYS)
    radius = float(c.get("radi_km") or DEFAULT_RADIUS_KM)
    params = {
        "$select": FIELDS,
        "$where": _where(u["lat"], u["lon"], radius, today, days),
        "$order": "data_inici",
        "$limit": 1000,
    }
    events = comun.get(API, params=params, timeout=30).json()
    for_you, everything = build_plans(events, _wanted(c), today, (u["lat"], u["lon"]), radius)
    return {"radi_km": radius, "dies": days, "per_a_tu": for_you, "tot": everything}
