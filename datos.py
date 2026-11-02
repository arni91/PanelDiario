"""
Panel Diario - obtención de datos.

Cada función devuelve un dict serializable a JSON. Si una fuente falla,
se registra el error y el resto sigue funcionando.
"""

from __future__ import annotations

import calendar
import html
import json
import logging
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import requests

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Madrid")
except Exception:  # sin tzdata
    TZ = None

log = logging.getLogger("panel")

UA = "PanelDiario/1.0 (uso personal; escritorio Windows)"
UA_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT = 15


def ahora_local() -> datetime:
    return datetime.now(TZ) if TZ else datetime.now()


def _get(url, *, headers=None, params=None, timeout=TIMEOUT):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    r = requests.get(url, headers=h, params=params, timeout=timeout)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# TIEMPO (Open-Meteo, sin clave)
# ---------------------------------------------------------------------------

WMO = {   # descripcions en català (codis WMO d'Open-Meteo)
    0: ("☀️", "Serè"), 1: ("🌤️", "Gairebé serè"), 2: ("⛅", "Parcialment ennuvolat"),
    3: ("☁️", "Ennuvolat"), 45: ("🌫️", "Boira"), 48: ("🌫️", "Boira gebradora"),
    51: ("🌦️", "Plugim feble"), 53: ("🌦️", "Plugim"), 55: ("🌧️", "Plugim intens"),
    56: ("🌧️", "Plugim gelat"), 57: ("🌧️", "Plugim gelat"),
    61: ("🌦️", "Pluja feble"), 63: ("🌧️", "Pluja"), 65: ("🌧️", "Pluja forta"),
    66: ("🌧️", "Pluja gelada"), 67: ("🌧️", "Pluja gelada forta"),
    71: ("🌨️", "Neu feble"), 73: ("🌨️", "Neu"), 75: ("❄️", "Neu forta"), 77: ("🌨️", "Calamarsa fina"),
    80: ("🌦️", "Ruixats febles"), 81: ("🌧️", "Ruixats"), 82: ("⛈️", "Ruixats forts"),
    85: ("🌨️", "Ruixats de neu"), 86: ("❄️", "Ruixats de neu forts"),
    95: ("⛈️", "Tempesta"), 96: ("⛈️", "Tempesta amb calamarsa"), 99: ("⛈️", "Tempesta forta amb calamarsa"),
}
NOCHE = {0: "🌙", 1: "🌙"}
DIAS = ["dl", "dt", "dc", "dj", "dv", "ds", "dg"]


def _wmo(code, es_dia=True):
    icono, texto = WMO.get(int(code or 0), ("🌡️", "—"))
    if not es_dia and int(code or 0) in NOCHE:
        icono = NOCHE[int(code)]
    return icono, texto


def obtener_tiempo(cfg: dict) -> dict:
    u = cfg["ubicacion"]
    params = {
        "latitude": u["lat"], "longitude": u["lon"], "timezone": "Europe/Madrid",
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,"
                   "precipitation,relative_humidity_2m,is_day",
        "hourly": "temperature_2m,precipitation_probability,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,sunrise,sunset",
        "forecast_days": 6, "wind_speed_unit": "kmh",
    }
    d = _get("https://api.open-meteo.com/v1/forecast", params=params).json()
    c = d["current"]
    icono, texto = _wmo(c["weather_code"], c.get("is_day", 1) == 1)

    # Próximas 12 horas desde la hora actual
    horas = []
    h = d["hourly"]
    hora_actual = c["time"][:13]  # "YYYY-MM-DDTHH"
    inicio = next((i for i, t in enumerate(h["time"]) if t[:13] >= hora_actual), 0)
    for i in range(inicio, min(inicio + 12, len(h["time"]))):
        ic, _ = _wmo(h["weather_code"][i], h["is_day"][i] == 1)
        horas.append({
            "hora": h["time"][i][11:13] + "h",
            "temp": round(h["temperature_2m"][i]),
            "lluvia": h["precipitation_probability"][i] or 0,
            "icono": ic,
        })

    dias = []
    dd = d["daily"]
    for i, fecha in enumerate(dd["time"]):
        f = datetime.strptime(fecha, "%Y-%m-%d")
        ic, tx = _wmo(dd["weather_code"][i])
        dias.append({
            "dia": "Avui" if i == 0 else DIAS[f.weekday()],
            "icono": ic, "texto": tx,
            "max": round(dd["temperature_2m_max"][i]),
            "min": round(dd["temperature_2m_min"][i]),
            "lluvia": dd["precipitation_probability_max"][i] or 0,
        })

    lluvia_hoy = max((x["lluvia"] for x in horas), default=0)
    return {
        "lugar": u["nombre"],
        "temp": round(c["temperature_2m"]),
        "sensacion": round(c["apparent_temperature"]),
        "viento": round(c["wind_speed_10m"]),
        "humedad": c.get("relative_humidity_2m"),
        "icono": icono, "texto": texto,
        "codigo": int(c.get("weather_code") or 0),   # código WMO: la ficha elige su color con él
        "es_dia": c.get("is_day", 1) == 1,
        "lluvia_12h": lluvia_hoy,
        "salida_sol": dd["sunrise"][0][11:16], "puesta_sol": dd["sunset"][0][11:16],
        "horas": horas, "dias": dias[:6],
    }


# ---------------------------------------------------------------------------
# AVISOS METEOROLÓGICOS (MeteoAlarm = avisos oficiales de AEMET)
# ---------------------------------------------------------------------------

SEVERIDAD = {"moderate": ("amarillo", 1), "severe": ("naranja", 2), "extreme": ("rojo", 3)}


def _fecha_aviso(valor):
    """Fecha CAP (ISO 8601 con zona) -> datetime con zona, o None."""
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _fmt_aviso(dt: datetime) -> str:
    local = dt.astimezone(TZ) if TZ else dt
    hoy = ahora_local().date()
    if local.date() == hoy:
        dia = "avui"
    elif local.date() == hoy + timedelta(days=1):
        dia = "demà"
    else:
        dia = DIAS[local.weekday()]
    return f"{dia} {local:%H:%M}"


def obtener_avisos(cfg: dict) -> list:
    a = cfg.get("avisos_meteo") or {}
    if not a.get("activo", True):
        return []
    r = _get(a["feed"])
    feed = feedparser.parse(r.content)
    zonas = [_norm(z) for z in a.get("zonas", [])]
    excluir = [_norm(z) for z in a.get("zonas_excluir", [])]
    ahora = datetime.now(timezone.utc)
    vistos, avisos = set(), []
    for e in feed.entries:
        area = (e.get("cap_areadesc") or "").strip()
        area_n = _norm(area)
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
        try:
            evento = traduir(evento)   # AEMET els publica en castellà
        except Exception:  # noqa: BLE001
            pass
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


# ---------------------------------------------------------------------------
# NOTICIAS (RSS) + agrupación de la misma noticia en varios medios
# ---------------------------------------------------------------------------

STOP = set("""
el la los las un una unos unas de del al a ante con contra desde en entre hacia hasta para por segun sin
sobre tras y o u e ni que se su sus lo le les ya mas pero como este esta estos estas ese esa eso es son
ha han fue ser sera hay muy tambien no si sí cuando donde quien cual tras ante tras durante tras
els les uns unes amb per pel pels dels des fins i o que es seu seva seus seves ho hi ja mes pero com
aquest aquesta aquests aquestes ser sera han va van fa no si quan on qui
the of and to in on for with at by from as is are was were be been an it its this that after over new
says said dice dicen afirma asegura segun
""".split())


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(ch for ch in t if not unicodedata.combining(ch))


def _tokens(titulo: str) -> set:
    palabras = re.findall(r"[a-z0-9]+", _norm(titulo))
    return {p for p in palabras if len(p) > 3 and p not in STOP}


def _limpiar_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _leer_feed(fuente: dict, categoria: str, horas_max: int) -> tuple[list, str | None]:
    """Devuelve (noticias, error)."""
    try:
        r = _get(fuente["url"], headers={"User-Agent": UA_NAVEGADOR,
                                         "Accept": "application/rss+xml, application/xml, text/xml, */*"})
        feed = feedparser.parse(r.content)
        if not feed.entries:
            return [], "feed vacío o no es RSS"
    except Exception as ex:  # noqa: BLE001
        return [], str(ex)[:120]

    limite = time.time() - fuente.get("horas_max", horas_max) * 3600
    items = []
    for e in feed.entries[:40]:
        titulo = _limpiar_html(e.get("title", ""))
        enlace = e.get("link", "")
        if not titulo or not enlace:
            continue
        medio = fuente["nombre"]
        # Google Noticias: "Titular - Medio"
        if fuente.get("agregador"):
            src = e.get("source", {}).get("title") if isinstance(e.get("source"), dict) else None
            if " - " in titulo:
                titulo, _, sufijo = titulo.rpartition(" - ")
                medio = src or sufijo.strip()
            elif src:
                medio = src
        tp = e.get("published_parsed") or e.get("updated_parsed")
        ts = calendar.timegm(tp) if tp else None
        if ts and ts < limite:
            continue
        resumen = netejar_resum(_limpiar_html(e.get("summary", "")))
        if fuente.get("agregador") or resumen.startswith(titulo[:40]):
            resumen = ""
        items.append({
            "titulo": titulo, "enlace": enlace, "medio": medio, "ts": ts,
            "resumen": resumen[:220], "categoria": categoria,
            "portada": bool(fuente.get("portada")),
            "tema": fuente.get("tema", ""),   # en Cultura: de qué búsqueda viene (museus, concerts...)
            "idioma": fuente.get("idioma", ""),  # idioma conocido de la fuente ("ca", "es"...): evita el traductor
        })
    return items, None


def netejar_resum(text: str) -> str:
    """Treu el que afegeix WordPress al final dels resums ("[…]", "L'entrada … va aparèixer primer a …")."""
    text = re.sub(r"\s*(The post|La entrada|L.entrada)\b.*$", "", text, flags=re.S)
    text = re.sub(r"\s*(\[(…|\.\.\.|&#8230;)\]|Continue reading|Llegir més|Leer más).*$", "", text, flags=re.S)
    return text.strip()


def _excluido(medio: str, excluidos: list) -> bool:
    m = _norm(medio)
    return any(_norm(x) in m for x in excluidos)


def agrupar(items: list) -> list:
    """Agrupa titulares que cuentan la misma noticia. Devuelve grupos ordenados por relevancia."""
    grupos: list[dict] = []
    for it in sorted(items, key=lambda x: -(x["ts"] or 0)):
        tk = _tokens(it["titulo"])
        if not tk:
            continue
        mejor, mejor_sim = None, 0.0
        for g in grupos:
            comunes = len(tk & g["tokens"])
            if comunes < 2:
                continue
            sim = comunes / min(len(tk), len(g["tokens"]))
            jac = comunes / len(tk | g["tokens"])
            puntuacion = max(jac, sim * 0.8)
            if (jac >= 0.34 or (sim >= 0.6 and comunes >= 3)) and puntuacion > mejor_sim:
                mejor, mejor_sim = g, puntuacion
        if mejor:
            mejor["items"].append(it)
            mejor["tokens"] |= tk
        else:
            grupos.append({"items": [it], "tokens": set(tk)})

    ahora = time.time()
    salida = []
    for g in grupos:
        medios = []
        for it in g["items"]:
            if it["medio"] not in medios:
                medios.append(it["medio"])
        ts = max((i["ts"] or 0) for i in g["items"]) or None
        horas = (ahora - ts) / 3600 if ts else 12
        puntos = len(medios) * 2 + sum(1 for i in g["items"] if i["portada"])
        puntos *= 1.0 if horas < 12 else (0.7 if horas < 24 else 0.4)
        salida.append({"items": g["items"], "medios": medios, "ts": ts, "puntos": puntos,
                       "categorias": sorted({i["categoria"] for i in g["items"]})})
    salida.sort(key=lambda g: (-g["puntos"], -(g["ts"] or 0)))
    return salida


def _representante(grupo: dict, prioridad: list) -> dict:
    """Elige el titular a mostrar: el del medio más neutro según el orden de prioridad."""
    def rango(it):
        m = _norm(it["medio"])
        for i, p in enumerate(prioridad):
            if _norm(p) in m:
                return i
        return len(prioridad)
    it = sorted(grupo["items"], key=lambda x: (rango(x), -(x["ts"] or 0)))[0]
    return {
        "titulo": it["titulo"], "enlace": it["enlace"], "medio": it["medio"], "tema": it.get("tema", ""),
        "idioma": it.get("idioma", ""),
        "ts": grupo["ts"], "resumen": it["resumen"],
        "otros_medios": [m for m in grupo["medios"] if m != it["medio"]],
        "enlaces": [{"medio": x["medio"], "enlace": x["enlace"]} for x in grupo["items"]][:6],
    }


def filtrar_paraules(items: list, requereix: list | None, excloses: list | None) -> list:
    """Filtra titulars per paraules (sense accents ni majúscules) al títol o al resum.

    - requereix: si n'hi ha, el titular ha de contenir-ne almenys una (p. ex. que una revista
      d'àmbit estatal només aporti el que passa a la teva ciutat o comunitat).
    - excloses: si en conté alguna, es descarta (p. ex. tot el que és infantil a Cultura).
    """
    def conte(text, paraules):
        return any(re.search(rf"\b{re.escape(_norm(p))}", text) for p in paraules)

    sortida = []
    for it in items:
        text = _norm(f"{it['titulo']} {it.get('resumen', '')}")
        if requereix and not conte(text, requereix):
            continue
        if excloses and conte(text, excloses):
            continue
        sortida.append(it)
    return sortida


# ---------------------------------------------------------------------------
# TRADUCCIÓN DE NOTICIAS (traductor de Google, modo gratuito y no oficial)
# ---------------------------------------------------------------------------
# Regla: las noticias en los idiomas de "conservar" (por defecto catalán y castellano) se quedan
# tal cual; las demás (inglés, francés...) se traducen a "idioma" (por defecto castellano).
# Si la fuente declara su "idioma" en config.json, ni se consulta el traductor; si no, el propio
# traductor detecta el idioma y, si es uno de los que se conservan, se deja el original.
# Solo se traducen los titulares (y resúmenes) que se muestran, y se guardan en memoria:
# un titular se traduce una sola vez aunque el panel se actualice cada 30 minutos.
# Si el traductor falla, se muestra el texto original: el panel no se rompe nunca por esto.

_TRADUCCIONS: dict[tuple[str, str], str] = {}   # (idioma destino, texto) -> texto a mostrar


def traduir(text: str, desti: str = "ca", conservar: tuple[str, ...] = ()) -> str:
    if not text or not text.strip():
        return text
    clave = (desti, text)
    if clave in _TRADUCCIONS:
        return _TRADUCCIONS[clave]
    r = _get("https://translate.googleapis.com/translate_a/single", headers={"User-Agent": UA_NAVEGADOR},
             params={"client": "gtx", "sl": "auto", "tl": desti, "dt": "t", "q": text})
    datos = r.json()
    detectado = datos[2] if len(datos) > 2 else None   # el traductor devuelve el idioma de origen aquí
    if detectado in conservar:
        traduit = text
    else:
        traduit = "".join(t[0] for t in (datos[0] or []) if t and t[0]).strip() or text
    if len(_TRADUCCIONS) > 3000:   # que la memoria no crezca sin límite
        _TRADUCCIONS.clear()
    _TRADUCCIONS[clave] = traduit
    return traduit


def traduir_noticies(salida: dict, cfg: dict) -> None:
    """Traduce los titulares y resúmenes que no están en un idioma que se conserva."""
    t = cfg.get("traduccio") or {}
    if not t.get("activa", True):
        return
    desti = t.get("idioma", "es")
    conservar = tuple(t.get("conservar", ["ca", "es"]))
    pendientes = [nt for llista in salida.values() for nt in llista if nt.get("idioma") not in conservar]
    textos = {txt for nt in pendientes for txt in (nt["titulo"], nt.get("resumen", ""))
              if txt and (desti, txt) not in _TRADUCCIONS}
    errors = []

    def una(txt):
        try:
            traduir(txt, desti, conservar)
        except Exception as ex:  # noqa: BLE001
            errors.append(ex)

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(una, textos))
    if errors:
        log.warning("Traducción: %d textos sin traducir (%s)", len(errors), errors[0])
    for nt in pendientes:
        nt["titulo"] = _TRADUCCIONS.get((desti, nt["titulo"]), nt["titulo"])
        if nt.get("resumen"):
            nt["resumen"] = _TRADUCCIONS.get((desti, nt["resumen"]), nt["resumen"])


def limitar_per_font(noticies: list, maxim: int | None) -> list:
    """Com a molt `maxim` notícies de cada tema (o mitjà, si no en té), mantenint l'ordre.
    Així una revista que publica molt no omple tota la pestanya."""
    if not maxim:
        return noticies
    comptador: dict = {}
    sortida = []
    for nt in noticies:
        clau = nt.get("tema") or nt.get("medio")
        comptador[clau] = comptador.get(clau, 0) + 1
        if comptador[clau] <= maxim:
            sortida.append(nt)
    return sortida


def obtener_noticias(cfg: dict) -> tuple[dict, list]:
    """Devuelve ({categoria: [noticias]}, [errores de fuentes])."""
    fuentes = cfg["fuentes"]
    horas_max = cfg.get("noticias_horas_max", 36)
    n = cfg.get("titulares_por_pestana", 8)
    excluidos = cfg.get("medios_excluidos", [])
    prioridad = cfg.get("prioridad_medios", [])

    tareas = [(cat, f) for cat, lista in fuentes.items() for f in lista if f.get("activa", True)]
    resultados, errores = {}, []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futuros = {ex.submit(_leer_feed, f, cat, horas_max): (cat, f) for cat, f in tareas}
        for fut, (cat, f) in futuros.items():
            items, err = fut.result()
            if err:
                errores.append({"fuente": f["nombre"], "categoria": cat, "error": err})
                log.warning("Fuente %s (%s) falla: %s", f["nombre"], cat, err)
            items = [i for i in items if not _excluido(i["medio"], excluidos)]
            items = filtrar_paraules(items, f.get("requereix"), cfg.get("paraules_excloses", {}).get(cat))
            resultados.setdefault(cat, []).extend(items)

    salida = {}
    por_cat = cfg.get("titulares_por_categoria", {})
    for cat, items in resultados.items():
        grupos = agrupar(items)
        noticies = [_representante(g, prioridad) for g in grupos]
        noticies = limitar_per_font(noticies, cfg.get("max_per_font", {}).get(cat))
        salida[cat] = noticies[:por_cat.get(cat, n)]
    traduir_noticies(salida, cfg)
    return salida, errores


# ---------------------------------------------------------------------------
# FILTRO OPCIONAL CON IA (API de Claude)
# ---------------------------------------------------------------------------

def filtrar_con_ia(cfg: dict, noticias: dict) -> dict:
    ia = cfg.get("claude") or {}
    clave = (ia.get("api_key") or "").strip()
    if not clave:
        return noticias

    catalogo, idx = [], {}
    for cat, lista in noticias.items():
        for i, it in enumerate(lista):
            nid = f"{cat}-{i}"
            idx[nid] = (cat, it)
            catalogo.append({"id": nid, "seccion": cat, "titular": it["titulo"],
                             "medios": [it["medio"]] + it["otros_medios"]})

    prompt = (
        "Eres un editor de noticias neutral. Te paso titulares de hoy agrupados por sección "
        "(incluye cuántos medios los publican). Para cada sección, devuelve los ids de las "
        f"{cfg.get('titulares_por_pestana', 8)} noticias más relevantes e interesantes, ordenadas, "
        "descartando sucesos menores, ruido y contenido de opinión. Para cada id elegido escribe un resumen "
        "factual y neutral de máximo 20 palabras en castellano, sin adjetivos valorativos.\n"
        "Responde SOLO con JSON con esta forma: "
        '{"secciones": {"mundo": ["id", ...], "catalunya": [...], ...}, '
        '"resumenes": {"id": "texto", ...}}\n\n'
        + json.dumps(catalogo, ensure_ascii=False)
    )
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": clave, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": ia.get("modelo", "claude-haiku-5-5"), "max_tokens": 4000,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    r.raise_for_status()
    texto = "".join(b.get("text", "") for b in r.json().get("content", []))
    m = re.search(r"\{.*\}", texto, re.S)
    datos = json.loads(m.group(0))

    nuevo = {}
    for cat, ids in datos.get("secciones", {}).items():
        lista = []
        for nid in ids:
            if nid in idx:
                it = dict(idx[nid][1])
                it["resumen_ia"] = datos.get("resumenes", {}).get(nid, "")
                lista.append(it)
        if lista:
            nuevo[cat] = lista
    for cat in noticias:  # si la IA omite una sección, se queda la original
        nuevo.setdefault(cat, noticias[cat])
    return nuevo


# ---------------------------------------------------------------------------
# FÚTBOL: partidos del equipo elegido en config.json (football-data.org, clave gratuita)
# ---------------------------------------------------------------------------

def _hora_local(iso_utc: str) -> datetime:
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return dt.astimezone(TZ) if TZ else dt


# Noms de les competicions en català (football-data.org els dona en anglès o castellà)
COMPETICIONS = {"Primera Division": "Lliga", "UEFA Champions League": "Lliga de Campions",
                "Copa del Rey": "Copa del Rei", "Supercopa de España": "Supercopa"}


def obtener_futbol(cfg: dict) -> dict:
    f = cfg.get("futbol") or {}
    clave = (f.get("football_data_api_key") or "").strip()
    nombre = f.get("nombre") or "Futbol"
    if not clave:
        return {"sin_clave": True, "nombre": nombre}
    equipo_id = f.get("team_id")
    if not equipo_id:
        return {"sin_equipo": True, "nombre": nombre}
    r = _get(f"https://api.football-data.org/v4/teams/{equipo_id}/matches",
             headers={"X-Auth-Token": clave})
    partidos = r.json().get("matches", [])

    def fmt(p):
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
            "competicion": COMPETICIONS.get((p.get("competition") or {}).get("name", ""),
                                            (p.get("competition") or {}).get("name", "")),
            "fecha": f"{DIAS[dt.weekday()]} {dt.day}/{dt.month}",
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


# ---------------------------------------------------------------------------
# AGENDA (Google Calendar mediante su "dirección secreta en formato iCal")
# ---------------------------------------------------------------------------
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


def _etiqueta_dia(d, hoy) -> str:
    if d == hoy:
        return "Avui"
    if d == hoy + timedelta(days=1):
        return "Demà"
    return f"{DIAS[d.weekday()]} {d.day}/{d.month}"


def obtener_agenda(cfg: dict) -> dict:
    ag = cfg.get("agenda") or {}
    urls = [u.strip() for u in ag.get("ical_urls", []) if u and u.strip()]
    if not urls:
        return {"sin_url": True}

    import icalendar               # lee el formato .ics
    import recurring_ical_events   # expande los eventos que se repiten (semanales, etc.)

    hoy = ahora_local().date()
    tz = TZ or timezone.utc
    inicio = datetime(hoy.year, hoy.month, hoy.day, tzinfo=tz)
    fin = inicio + timedelta(days=int(ag.get("dias", 7)))

    eventos = []
    for url in urls:
        cal = icalendar.Calendar.from_ical(_get(url, timeout=30).content)
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
            eventos.append({
                "titulo": str(ev.get("SUMMARY", "(sense títol)")),
                **dict(zip(("lugar", "enlace"), resumir_lugar(str(ev.get("LOCATION", "") or "")))),
                "dia": _etiqueta_dia(dia, hoy), "es_hoy": dia == hoy,
                "hora": hora, "hora_fin": hora_fin, "todo_el_dia": todo_el_dia,
                "_orden": orden.timestamp(),
            })

    eventos.sort(key=lambda e: (e["_orden"], not e["todo_el_dia"]))
    for e in eventos:
        del e["_orden"]
    return {"eventos": eventos}


# ---------------------------------------------------------------------------
# CAÍDAS DE UN ETF DESDE SU MÁXIMO (drawdown) — Yahoo Finance, API no oficial
# ---------------------------------------------------------------------------
# Caída % = (precio actual − máximo histórico) / máximo histórico × 100.
# El máximo es el del propio ETF con TODOS sus cierres desde que cotiza. Como descargar el
# histórico entero es lento, se guarda en caché y en cada refresco solo se pide el precio actual
# (si lo supera, pasa a ser el nuevo máximo). Una vez a la semana se recalcula entero por si Yahoo
# corrige algún dato erróneo que, colado como "máximo", falsearía la caída para siempre.
# Se usa el cierre tal cual: es exacto en un ETF de acumulación; en uno de distribución, cada
# reparto de dividendos baja el precio y la caída sale algo exagerada.

def calcular_caida(precio: float, maximo: float) -> float:
    """Caída en % desde el máximo (0 o negativa)."""
    return (precio - maximo) / maximo * 100


def nivel_alcanzado(caida: float, umbrales: list[float]) -> int:
    """Cuántos umbrales se han alcanzado. Ej.: umbrales [-20, -30, -40] y caída -32 % → 2."""
    return sum(1 for u in sorted(umbrales, reverse=True) if caida <= u)


def _yahoo_chart(ticker: str, rango: str) -> dict:
    """Cierres diarios de Yahoo Finance para `rango` ("5d", "max"...)."""
    ultimo_error = None
    for host in ("query1", "query2"):
        try:
            r = _get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}",
                     headers={"User-Agent": UA_NAVEGADOR},
                     params={"range": rango, "interval": "1d"})
            return r.json()["chart"]["result"][0]
        except Exception as ex:  # noqa: BLE001
            ultimo_error = ex
    raise RuntimeError(f"Yahoo no responde para {ticker}: {ultimo_error}")


def maximo_de_cierres(res: dict) -> tuple[float, str, str]:
    """(máximo cierre, fecha del máximo, fecha del primer dato) de una respuesta de Yahoo."""
    pares = [(ts, c) for ts, c in zip(res.get("timestamp") or [], res["indicators"]["quote"][0]["close"])
             if c is not None]
    if not pares:
        raise RuntimeError("Yahoo no ha devuelto cierres")
    ts_max, maximo = max(pares, key=lambda p: p[1])
    fecha = lambda ts: datetime.fromtimestamp(ts).strftime("%d/%m/%Y")  # noqa: E731
    return maximo, fecha(ts_max), fecha(pares[0][0])


# Regla de compras extra: a partir de cada caída, cuánto añadir a la aportación habitual, en %
# (+100 % = aportar el doble ese mes). Va en % y no en euros para que el widget no guarde
# importes: cada uno aplica el % a su propia aportación. El último nivel puede ser "toda la reserva".
NIVELES_POR_DEFECTO = [{"caida": -10, "extra_pct": 50}, {"caida": -20, "extra_pct": 100},
                       {"caida": -30, "extra_pct": 200}, {"caida": -40, "toda_la_reserva": True}]


def obtener_drawdown(cfg: dict, cache_path) -> dict:
    dd = cfg.get("drawdown") or {}
    ticker = (dd.get("ticker") or "").strip()
    if not ticker:
        return {"sin_configurar": True}
    niveles = sorted(dd.get("niveles") or NIVELES_POR_DEFECTO, key=lambda n: n["caida"], reverse=True)
    umbrales = [n["caida"] for n in niveles]

    cache = {}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        if cache.get("ticker") != ticker:  # si cambias de ticker, se empieza de cero
            cache = {}
    except Exception:  # noqa: BLE001  (no hay caché todavía o está dañada)
        cache = {}

    ahora = time.time()
    desactualizado, error = False, None
    reciente = ahora - cache.get("precio_ts_consulta", 0) < float(dd.get("actualizar_minutos", 30)) * 60
    if not reciente:
        try:
            completo = ahora - cache.get("historico_ts", 0) > float(dd.get("recalcular_dias", 7)) * 86400
            res = _yahoo_chart(ticker, "max" if completo or "maximo" not in cache else "5d")
            if completo or "maximo" not in cache:
                cache["maximo"], cache["fecha_maximo"], cache["primer_dato"] = maximo_de_cierres(res)
                cache["historico_ts"] = ahora
            meta = res["meta"]
            cierres = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
            precio = meta.get("regularMarketPrice") or cierres[-1]
            t = meta.get("regularMarketTime") or res["timestamp"][-1]
            cache.update(ticker=ticker, precio=float(precio), moneda=meta.get("currency", "EUR"),
                         hora=datetime.fromtimestamp(t).strftime("%d/%m %H:%M"), precio_ts_consulta=ahora)
            if cache["precio"] > cache["maximo"]:  # nuevo máximo histórico
                cache["maximo"] = cache["precio"]
                cache["fecha_maximo"] = datetime.fromtimestamp(t).strftime("%d/%m/%Y")
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            if "precio" not in cache:
                raise  # sin ningún dato guardado no hay nada que mostrar
            desactualizado, error = True, str(ex)[:150]
            log.warning("Caídas: uso el último dato guardado (%s): %s", cache.get("hora"), ex)

    caida = calcular_caida(cache["precio"], cache["maximo"])
    nivel = nivel_alcanzado(caida, umbrales)
    return {
        "nombre": dd.get("nombre", ticker), "ticker": ticker, "moneda": cache.get("moneda", "EUR"),
        "precio": round(cache["precio"], 2), "hora": cache.get("hora", ""),
        "maximo": round(cache["maximo"], 2), "fecha_maximo": cache.get("fecha_maximo", ""),
        "primer_dato": cache.get("primer_dato", ""),
        "caida": round(caida, 2), "nivel": nivel,
        "niveles": [{"umbral": n["caida"], "extra_pct": n.get("extra_pct"),
                     "toda_la_reserva": bool(n.get("toda_la_reserva")), "alcanzado": i < nivel}
                    for i, n in enumerate(niveles)],
        "desactualizado": desactualizado, "error": error,
    }
