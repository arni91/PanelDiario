"""Plans: exposiciones, conciertos, charlas, festivales... de los próximos días en una ciudad.

Datos de la Agenda Cultural de Catalunya (dades obertes de la Generalitat, API Socrata, sin
clave; solo Cataluña). Los planes que coinciden con los interesos de config.json
(catalog/interests.py y palabras propias) van en "per_a_tu"; "tot" es la agenda entera, primero
lo que dura pocos días.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from panel_diario.catalog import interests
from panel_diario.sources import comun

API = "https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json"
DEFAULT_DAYS = 7
MAX_FOR_YOU = 15
MAX_ALL = 20
SHORT_DAYS = 7  # lo que dura más (exposiciones largas) va detrás en "tot"
FIELDS = (
    "codi,denominaci,subt_tol,descripcio,tags_categor_es,data_inici,data_fi,permanent,"
    "gratuita,espai,enlla_os,linkbotoentrades,url"
)


def slug(city: str) -> str:
    """Nombre de municipio como lo escribe la Agenda: "L'Hospitalet de Llobregat" -> "l-hospitalet-de-llobregat"."""
    return re.sub(r"[^a-z0-9]+", "-", comun.normalizar(city)).strip("-")


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


def build_plans(events: list[dict], wanted: dict[str, re.Pattern[str]], today: date) -> tuple[list, list]:
    """(per_a_tu, tot) a partir de los planes de la Agenda, sin repetidos ni permanentes."""
    seen: set[str] = set()
    ranked: list[tuple[bool, date, list[str], dict]] = []  # (largo, fecha para ordenar, interesos, plan)
    for e in events:
        start, end = _day(e.get("data_inici")), _day(e.get("data_fi"))
        if not start or not end or e.get("codi") in seen or e.get("permanent") == "Sí":
            continue
        seen.add(e.get("codi", ""))
        long = (end - start).days > SHORT_DAYS
        matched = _matches(e, wanted)
        plan = {
            "titol": (e.get("denominaci") or "").strip(),
            "lloc": (e.get("espai") or "").strip(),
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


def obtener_plans(cfg: dict) -> dict:
    """Sección de planes. Sin activar o sin ciudad, {"sin_configurar": True}."""
    c = cfg.get("plans") or {}
    city = (c.get("ciutat") or "").strip()
    if not c.get("activa") or not slug(city):
        return {"sin_configurar": True}
    today = comun.ahora_local().date()
    days = int(c.get("dies") or DEFAULT_DAYS)
    params = {
        "$select": FIELDS,
        # slug() solo deja letras, números y guiones: no se puede colar nada en la consulta
        "$where": (
            f"municipi like '%/{slug(city)}' AND data_fi >= '{today.isoformat()}'"
            f" AND data_inici <= '{(today + timedelta(days=days)).isoformat()}'"
        ),
        "$order": "data_inici",
        "$limit": 500,
    }
    events = comun.get(API, params=params, timeout=30).json()
    for_you, everything = build_plans(events, _wanted(c), today)
    return {"ciutat": city, "dies": days, "per_a_tu": for_you, "tot": everything}
