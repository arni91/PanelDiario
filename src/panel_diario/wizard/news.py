"""Pasos de noticias del asistente: medios (del catálogo o propios) y secciones del panel.

El paso «Mitjans» elige medios; el paso «Seccions» elige las pestañas (Portades, Política...).
Cada pestaña junta el feed de esa sección de cada medio elegido (catalog/outlets.py). Además:
«Plans a la teva ciutat» y temas propios (búsquedas de Google Noticias) y traducir o no.
"""

from __future__ import annotations

from urllib.parse import quote

from panel_diario.catalog import outlets

# Planes en la ciudad elegida: Google Noticias busca conciertos, exposiciones, festivales...
LOCAL_PLANS_QUERY = "{city} (concert OR exposició OR festival OR teatre)"
LOCAL_PLANS = {"id": "plans", "nombre": "Plans a {city}"}
# Las búsquedas de Google Noticias se hacen en catalán, en la edición de España
GOOGLE_NEWS_LANG, GOOGLE_NEWS_COUNTRY = "ca", "ES"


def google_news_source(query: str, topic: str = "") -> dict:
    """Fuente de Google Noticias que busca `query` en los titulares."""
    url = (
        f"https://news.google.com/rss/search?q={quote(query)}"
        f"&hl={GOOGLE_NEWS_LANG}&gl={GOOGLE_NEWS_COUNTRY}&ceid={GOOGLE_NEWS_COUNTRY}:{GOOGLE_NEWS_LANG}"
    )
    source = {"nombre": "Google Noticias", "url": url, "agregador": True}
    if topic:
        source["tema"] = topic
    return source


# ---------------------------------------------------------------------------
# Opciones que se ofrecen y lo que ya hay configurado
# ---------------------------------------------------------------------------


def outlet_groups() -> list[dict]:
    """Medios del catálogo por grupo (con el bloque de cada grupo), su idioma y las secciones que publican."""
    return [
        {
            "id": group,
            "nombre": g.name,
            "bloc": outlets.BLOCKS[g.block],
            "medios": [
                {"nombre": o.name, "idioma": o.language, "seccions": list(o.feeds)}
                for o in outlets.CATALOG
                if o.group == group
            ],
        }
        for group, g in outlets.GROUPS.items()
    ]


def sections() -> list[dict]:
    return [{"id": k, "nombre": v} for k, v in outlets.SECTIONS.items()]


def current_choices(cfg: dict) -> dict:
    """Lo que ya hay en config.json, para marcarlo en el asistente."""
    catalog_urls = {url: o.name for o in outlets.CATALOG for url in o.feeds.values()}
    chosen: list[str] = []
    own: list[dict] = []
    topics: list[str] = []
    for tab, lista in (cfg.get("fuentes") or {}).items():
        for f in lista:
            name = catalog_urls.get(f.get("url", ""))
            if name and name not in chosen:
                chosen.append(name)
            elif f.get("agregador") and f.get("tema") and tab != LOCAL_PLANS["id"] and f["tema"] not in topics:
                topics.append(f["tema"])
            elif not name and not f.get("agregador") and f not in own:
                own.append({"nombre": f["nombre"], "url": f["url"]})
    tabs = [p["id"] for p in cfg.get("pestanas", [])]
    return {
        # La lista guardada manda: un medio sin feed en las secciones elegidas no sale en "fuentes"
        "medios": cfg.get("medios_triats", chosen),
        "propios": own,
        "seccions": [t for t in tabs if t in outlets.SECTIONS] or ["portades"],
        "plans": LOCAL_PLANS["id"] in tabs,
        "temes": topics,
        "traduir": bool((cfg.get("traduccio") or {}).get("activa", False)),
    }


# ---------------------------------------------------------------------------
# Construir la parte de noticias de config.json
# ---------------------------------------------------------------------------


def _own_source(m: dict) -> dict:
    name, url = (m.get("nombre") or "").strip(), (m.get("url") or "").strip()
    if not name or not url.startswith("https://"):
        raise ValueError("Cada mitjà propi necessita un nom i una adreça RSS que comenci per https://")
    return {"nombre": name, "url": url}


def build(outlets_answer: dict, sections_answer: dict, city: str) -> dict:
    """Pestañas, fuentes y opciones de noticias de config.json a partir de los dos pasos.

    `outlets_answer`: {"medios": [nombres del catálogo], "propios": [{"nombre", "url"}]}.
    `sections_answer`: {"seccions": [ids], "plans": bool, "temes": [palabras], "traduir": bool};
    si se ha saltado, solo Portades. Los medios propios van a Portades.
    """
    names = list(outlets_answer.get("medios", []))
    unknown = [n for n in names if outlets.find(n) is None]
    if unknown:
        raise ValueError(f"«{unknown[0]}» no és al catàleg.")
    own = [_own_source(m) for m in outlets_answer.get("propios", [])]
    chosen_sections = sections_answer.get("seccions") or ["portades"]

    pestanas: list[dict] = []
    fuentes: dict[str, list[dict]] = {}
    for section, label in outlets.SECTIONS.items():
        if section not in chosen_sections:
            continue
        sources = outlets.sources_for(section, names) + (own if section == "portades" else [])
        if sources:
            pestanas.append({"id": section, "nombre": label})
            fuentes[section] = sources

    if sections_answer.get("plans") and city:
        source = google_news_source(LOCAL_PLANS_QUERY.format(city=city), topic=city)
        source["horas_max"] = 720
        pestanas.append(
            {"id": LOCAL_PLANS["id"], "nombre": LOCAL_PLANS["nombre"].format(city=city), "filtro_periodo": True}
        )
        fuentes[LOCAL_PLANS["id"]] = [source]

    for i, text in enumerate(t.strip() for t in sections_answer.get("temes", [])):
        if not text:
            raise ValueError("Escriu les paraules del tema (p. ex. «energia solar») o treu-lo.")
        tab = f"tema{i + 1}"
        pestanas.append({"id": tab, "nombre": text[:1].upper() + text[1:]})
        fuentes[tab] = [google_news_source(text, topic=text)]

    if not pestanas:
        raise ValueError("Cap dels mitjans triats publica les seccions triades: afegeix-ne algun.")
    return {
        "medios_triats": names,
        "pestanas": pestanas,
        "fuentes": fuentes,
        "titulares_por_categoria": {p["id"]: 20 if p["id"] in ("portades", "plans") else 12 for p in pestanas},
        "max_per_font": {p["id"]: 4 for p in pestanas},
        "traduccio": {"activa": bool(sections_answer.get("traduir")), "idioma": "ca", "conservar": ["ca", "es"]},
    }
