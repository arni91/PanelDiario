"""Asistente de configuración: la lógica que hay detrás de ui/asistente.html.

Pregunta paso a paso (tiempo, agenda, fútbol, inversión, noticias, IA) y construye config.json.
Cada paso se puede saltar: lo saltado se queda como estaba. Las funciones que salen a internet
usan comun.get (los tests la sustituyen). ApiAsistente es el puente con el JavaScript de la ventana.
"""

from __future__ import annotations

import copy
import logging
import webbrowser
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import webview

from panel_diario import outlets
from panel_diario.fuentes import comun, drawdown, noticias

log = logging.getLogger("panel")

# ---------------------------------------------------------------------------
# Catálogos (solo opciones generales: los gustos de cada uno van a su config.json)
# ---------------------------------------------------------------------------

# Países con avisos en MeteoAlarm: código ISO -> nombre en la URL del feed
PAISES_METEOALARM = {
    "ES": "spain",
    "PT": "portugal",
    "FR": "france",
    "IT": "italy",
    "DE": "germany",
    "AT": "austria",
    "BE": "belgium",
    "NL": "netherlands",
    "IE": "ireland",
    "CH": "switzerland",
    "GB": "united-kingdom",
}
FEED_METEOALARM = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-{}"

# Competiciones del plan gratuito de football-data.org
COMPETICIONES = [
    {"codigo": "PD", "nombre": "LaLiga"},
    {"codigo": "PL", "nombre": "Premier League"},
    {"codigo": "SA", "nombre": "Serie A"},
    {"codigo": "BL1", "nombre": "Bundesliga"},
    {"codigo": "FL1", "nombre": "Ligue 1"},
    {"codigo": "DED", "nombre": "Eredivisie"},
    {"codigo": "PPL", "nombre": "Primeira Liga"},
    {"codigo": "CL", "nombre": "Lliga de Campions"},
]

# ETF UCITS indexados más negociados, con su ticker de Xetra en Yahoo Finance (verificados).
# El primero sale elegido por defecto en el asistente.
ETF_HABITUALES = [
    {"ticker": "VWCE.DE", "nombre": "Vanguard FTSE All-World (acumulació)"},
    {"ticker": "VGWL.DE", "nombre": "Vanguard FTSE All-World (distribució)"},
    {"ticker": "EUNL.DE", "nombre": "iShares Core MSCI World"},
    {"ticker": "XDWD.DE", "nombre": "Xtrackers MSCI World"},
    {"ticker": "IUSQ.DE", "nombre": "iShares MSCI ACWI"},
    {"ticker": "SPYI.DE", "nombre": "SPDR MSCI ACWI IMI"},
    {"ticker": "SXR8.DE", "nombre": "iShares Core S&P 500"},
    {"ticker": "VUAA.DE", "nombre": "Vanguard S&P 500 (acumulació)"},
    {"ticker": "SXRV.DE", "nombre": "iShares Nasdaq 100"},
    {"ticker": "IS3N.DE", "nombre": "iShares Core MSCI EM IMI (emergents)"},
]

# Ámbitos geográficos. "mon" usa medios internacionales en castellano (RSS verificados);
# "estat" y "local" salen de Google Noticias según el país y la región del lugar elegido.
FUENTES_MON = [
    {"nombre": "BBC Mundo", "url": "https://feeds.bbci.co.uk/mundo/rss.xml", "idioma": "es"},
    {"nombre": "DW", "url": "https://rss.dw.com/rdf/rss-sp-all", "idioma": "es"},
    {"nombre": "France 24", "url": "https://www.france24.com/es/rss", "idioma": "es"},
    {"nombre": "Europa Press", "url": "https://www.europapress.es/rss/rss.aspx?ch=69", "idioma": "es"},
]
AMBITOS = [
    {"id": "mon", "nombre": "Món"},
    {"id": "estat", "nombre": "El teu país"},
    {"id": "local", "nombre": "La teva comunitat"},
]

# Temas: búsqueda de Google Noticias en cada idioma. "{ciudad}" se cambia por la del lugar.
TEMAS: list[dict[str, Any]] = [
    {
        "id": "cultura",
        "nombre": "Cultura",
        "local": True,  # planes en tu ciudad: mira un mes atrás, con botones semana / mes
        "consulta": {
            "ca": "{ciudad} (concert OR exposició OR festival OR teatre)",
            "es": "{ciudad} (concierto OR exposición OR festival OR teatro)",
        },
    },
    {
        "id": "tecnologia",
        "nombre": "Tecnologia",
        "consulta": {"ca": "tecnologia OR programari OR startups", "es": "tecnología OR software OR startups"},
    },
    {
        "id": "ia",
        "nombre": "IA i robòtica",
        "consulta": {"ca": '"intel·ligència artificial" OR robòtica', "es": '"inteligencia artificial" OR robótica'},
    },
    {
        "id": "ciencia",
        "nombre": "Ciència",
        "consulta": {"ca": "ciència OR investigació científica", "es": "ciencia OR investigación científica"},
    },
    {"id": "esports", "nombre": "Esports", "consulta": {"ca": "esports", "es": "deportes"}},
    {"id": "economia", "nombre": "Economia", "consulta": {"ca": "economia OR mercats", "es": "economía OR mercados"}},
]

# ---------------------------------------------------------------------------
# Búsquedas y comprobaciones (cada una la pide un botón del asistente)
# ---------------------------------------------------------------------------


def _sin_prefijo_provincia(nombre: str) -> str:
    """ "Província de Girona" -> "Girona": así coincide con las zonas de MeteoAlarm ("Litoral de Girona")."""
    for prefijo in ("Província de ", "Provincia de ", "Província d'", "Provincia d'"):
        if nombre.startswith(prefijo):
            return nombre[len(prefijo) :]
    return nombre


def buscar_lugar(texto: str) -> list[dict]:
    """Ciudades que coinciden con `texto` (geocodificación de Open-Meteo, sin clave)."""
    texto = texto.strip()
    if not texto:
        raise ValueError("Escriu el nom de la teva ciutat.")
    r = comun.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": texto, "count": 6, "language": "ca"},
    )
    return [
        {
            "nombre": x["name"],
            "provincia": _sin_prefijo_provincia(x.get("admin2", "")),
            "region": x.get("admin1", ""),
            "pais": x.get("country", ""),
            "codigo_pais": x.get("country_code", ""),
            "lat": round(x["latitude"], 4),
            "lon": round(x["longitude"], 4),
            "zona_horaria": x.get("timezone", "Europe/Madrid"),
        }
        for x in r.json().get("results", [])
    ]


def equipos_de_competicion(clave: str, codigo: str) -> list[dict]:
    """Equipos de una competición, ordenados por nombre (así nadie tiene que buscar su team_id)."""
    clave = clave.strip()
    if not clave:
        raise ValueError("Primer posa la clau de football-data.org.")
    r = comun.get(
        f"https://api.football-data.org/v4/competitions/{codigo}/teams",
        headers={"X-Auth-Token": clave},
    )
    equipos = [{"id": e["id"], "nombre": e.get("shortName") or e.get("name")} for e in r.json().get("teams", [])]
    return sorted(equipos, key=lambda e: e["nombre"])


def validar_ticker(ticker: str) -> dict:
    """Comprueba en Yahoo Finance que el ticker existe y devuelve su nombre y precio."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Escriu el ticker de l'ETF (p. ex. EUNL.DE).")
    meta = drawdown._yahoo_chart(ticker, "5d")["meta"]  # misma consulta que usa la sección de caídas
    return {
        "ticker": ticker,
        "nombre": meta.get("longName") or meta.get("shortName") or ticker,
        "moneda": meta.get("currency", ""),
        "precio": meta.get("regularMarketPrice"),
    }


def verificar_rss(url: str) -> dict:
    """Comprueba que la URL es un RSS que responde y tiene titulares (regla del proyecto)."""
    url = url.strip()
    if not url.startswith("https://"):
        raise ValueError("L'adreça del RSS ha de començar per https://")
    items, error = noticias._leer_feed({"nombre": "prova", "url": url}, "prova", horas_max=24 * 30)
    if error or not items:
        raise ValueError(f"Aquest RSS no respon o no té notícies ({error or 'cap titular recent'}).")
    return {"titulares": len(items), "ejemplo": items[0]["titulo"]}


def fuente_google_noticias(consulta: str, idioma: str, pais: str, tema: str = "") -> dict:
    """Fuente RSS de una búsqueda de Google Noticias (sirve para temas y medios sin RSS propio)."""
    url = f"https://news.google.com/rss/search?q={quote(consulta)}&hl={idioma}&gl={pais}&ceid={pais}:{idioma}"
    fuente = {"nombre": "Google Noticias", "url": url, "agregador": True}
    if tema:
        fuente["tema"] = tema
    return fuente


# ---------------------------------------------------------------------------
# Construir config.json a partir de las respuestas
# ---------------------------------------------------------------------------


def _ubicacion(lugar: dict) -> tuple[dict, dict]:
    """(ubicacion, avisos_meteo) del lugar elegido. Sin MeteoAlarm en ese país, avisos desactivados."""
    ubicacion = {
        "nombre": lugar["nombre"],
        "lat": lugar["lat"],
        "lon": lugar["lon"],
        "zona_horaria": lugar["zona_horaria"],
    }
    pais = PAISES_METEOALARM.get(lugar.get("codigo_pais", ""))
    zona = lugar.get("provincia") or lugar.get("region") or ""
    avisos = {
        "activo": bool(pais),
        "feed": FEED_METEOALARM.format(pais or "spain"),
        "zonas": [zona] if zona else [],
        "zonas_excluir": [],
    }
    return ubicacion, avisos


def _niveles(niveles: list[dict]) -> list[dict]:
    """Niveles de caída limpios: caídas negativas, % enteros y ordenados de menor a mayor caída."""
    limpios = []
    for n in niveles:
        caida = -abs(float(n["caida"]))
        if n.get("toda_la_reserva"):
            limpios.append({"caida": caida, "toda_la_reserva": True})
        else:
            limpios.append({"caida": caida, "extra_pct": max(0, int(n["extra_pct"]))})
    for n in limpios:
        if n["caida"].is_integer():
            n["caida"] = int(n["caida"])  # -10 en vez de -10.0 en config.json
    return sorted(limpios, key=lambda n: n["caida"], reverse=True)


def _ical(urls: list[str]) -> list[str]:
    limpias = [u.strip() for u in urls if u and u.strip()]
    for u in limpias:
        if not u.startswith("https://") or ".ics" not in u:
            raise ValueError("Una adreça del calendari no és iCal: ha de començar per https:// i acabar en .ics")
    return limpias


def _noticias(resp: dict, lugar: dict | None) -> dict:
    """Pestañas y fuentes de noticias según los ámbitos, temas y medios elegidos."""
    idioma = resp.get("idioma", "es")
    pais = (lugar or {}).get("codigo_pais") or "ES"
    ciudad = (lugar or {}).get("nombre") or ""
    region = (lugar or {}).get("region") or ""
    pestanas: list[dict] = []
    fuentes: dict[str, list[dict]] = {}

    for ambito in resp.get("ambitos", []):
        if ambito == "mon":
            pestanas.append({"id": "mon", "nombre": "Món"})
            fuentes["mon"] = copy.deepcopy(FUENTES_MON)
        elif ambito == "estat":
            # Portada de Google Noticias del país: las noticias generales más destacadas
            pestanas.append({"id": "estat", "nombre": (lugar or {}).get("pais") or "El teu país"})
            url = f"https://news.google.com/rss?hl={idioma}&gl={pais}&ceid={pais}:{idioma}"
            fuentes["estat"] = [{"nombre": "Google Noticias", "url": url, "agregador": True}]
        elif ambito == "local" and region:
            pestanas.append({"id": "local", "nombre": region})
            fuentes["local"] = [fuente_google_noticias(f'"{region}" when:1d', idioma, pais)]

    for tema in TEMAS:
        if tema["id"] not in resp.get("temas", []):
            continue
        consulta = tema["consulta"].get(idioma, tema["consulta"]["es"])
        if tema.get("local"):
            if not ciudad:
                continue  # sin ciudad no hay planes locales que buscar
            consulta = consulta.format(ciudad=ciudad)
        fuente = fuente_google_noticias(consulta, idioma, pais, tema=tema["nombre"])
        pestana = {"id": tema["id"], "nombre": tema["nombre"]}
        if tema.get("local"):
            pestana["filtro_periodo"] = True
            fuente["horas_max"] = 720
        pestanas.append(pestana)
        fuentes[tema["id"]] = [fuente]

    mitjans = [{"nombre": m["nombre"].strip(), "url": m["url"].strip()} for m in resp.get("mitjans", [])]
    if mitjans:
        pestanas.append({"id": "mitjans", "nombre": "Els meus mitjans"})
        fuentes["mitjans"] = mitjans

    if not pestanas:
        raise ValueError("Tria almenys un àmbit, un tema o un mitjà (o salta aquest pas).")
    return {
        "pestanas": pestanas,
        "fuentes": fuentes,
        "titulares_por_categoria": {p["id"]: 20 if p.get("filtro_periodo") else 12 for p in pestanas},
        "max_per_font": {p["id"]: 6 for p in pestanas},
    }


def _fuentes_directas(cfg: dict) -> list[dict]:
    """Las fuentes de config.json que son un medio concreto (no un agregador como Google Noticias)."""
    return [f for lista in (cfg.get("fuentes") or {}).values() for f in lista if not f.get("agregador")]


def mitjans_amb_orientacio(cfg: dict) -> list[dict]:
    """Medios para el paso de orientación: los del catálogo y las fuentes propias, con la orientación actual."""
    indice = outlets.leaning_index(cfg)
    nombres = [o.name for o in outlets.CATALOG]
    for f in _fuentes_directas(cfg):
        outlet = outlets.find_outlet(f["nombre"])
        nombre = outlet.name if outlet else f["nombre"]
        if outlets.outlet_key(nombre) not in {outlets.outlet_key(n) for n in nombres}:
            nombres.append(nombre)
    vacio = {"ideologia": "", "eix_nacional": ""}
    return [{"nombre": n, **indice.get(outlets.outlet_key(n), vacio)} for n in nombres]


def _orientacions(cfg: dict, elegidas: list[dict]) -> None:
    """Guarda en cada fuente la orientación elegida en el asistente.

    Solo se escribe lo que difiere del catálogo: si el catálogo se corrige, las fuentes que no
    se han tocado reciben el valor nuevo. Se aplica a los medios que son fuente en config.json.
    """
    por_medio: dict[str, dict] = {}
    for e in elegidas:
        for campo, validos in outlets.LEANING_FIELDS.items():
            if e.get(campo, "") not in ("", *validos):
                raise ValueError(f"«{e.get(campo)}» no és una orientació vàlida per a {e.get('nombre', '?')}.")
        outlet = outlets.find_outlet(e["nombre"])
        por_medio[outlets.outlet_key(outlet.name if outlet else e["nombre"])] = e
    for f in _fuentes_directas(cfg):
        outlet = outlets.find_outlet(f["nombre"])
        elegida = por_medio.get(outlets.outlet_key(outlet.name if outlet else f["nombre"]))
        if elegida is None:
            continue
        for campo in outlets.LEANING_FIELDS:
            defecto = getattr(outlet, campo) if outlet else ""
            if elegida.get(campo, "") == defecto:
                f.pop(campo, None)
            else:
                f[campo] = elegida.get(campo, "")


def construir_config(base: dict, respuestas: dict) -> dict:
    """config.json nuevo: `base` (la config actual) con los pasos que el usuario ha completado.

    Un paso que no está en `respuestas` (saltado) se queda como estaba. `base` no se modifica.
    """
    cfg = copy.deepcopy(base)
    lugar = respuestas.get("ubicacion")
    if lugar:
        cfg["ubicacion"], cfg["avisos_meteo"] = _ubicacion(lugar)
    if "agenda" in respuestas:
        cfg.setdefault("agenda", {"dias": 7})["ical_urls"] = _ical(respuestas["agenda"].get("ical_urls", []))
    if "futbol" in respuestas:
        f = respuestas["futbol"]
        cfg["futbol"] = {
            "nombre": f.get("nombre", "").strip(),
            "football_data_api_key": f.get("football_data_api_key", "").strip(),
            "team_id": int(f["team_id"]) if f.get("team_id") else None,
        }
    if "drawdown" in respuestas:
        d = respuestas["drawdown"]
        cfg.setdefault("drawdown", {"actualizar_minutos": 30, "recalcular_dias": 7})
        cfg["drawdown"].update(ticker=d.get("ticker", "").strip().upper(), nombre=d.get("nombre", "").strip())
        if d.get("niveles"):
            cfg["drawdown"]["niveles"] = _niveles(d["niveles"])
    if "noticias" in respuestas:
        cfg.update(_noticias(respuestas["noticias"], lugar))
    if "orientacions" in respuestas:  # después de noticias: se aplica a las fuentes que quedan
        _orientacions(cfg, respuestas["orientacions"])
    if "claude" in respuestas:
        cfg.setdefault("claude", {"modelo": "claude-haiku-5-5", "cada_horas": 3})
        cfg["claude"]["api_key"] = respuestas["claude"].get("api_key", "").strip()
    return cfg


# ---------------------------------------------------------------------------
# Puente con el JavaScript de ui/asistente.html
# ---------------------------------------------------------------------------


class ApiAsistente:
    """Métodos que llama el JavaScript del asistente. Devuelven {"ok": True, "datos": ...} o
    {"ok": False, "error": "..."}: el error se enseña tal cual en la ventana, en catalán."""

    def __init__(self, cfg: dict, al_guardar: Callable[[dict], None]) -> None:
        self._cfg = cfg  # config actual (la de la plantilla si es la primera vez)
        self._al_guardar = al_guardar  # app.py aplica la config nueva sin reiniciar
        self._ventana: webview.Window | None = None  # privada: pywebview publica en JS los atributos públicos

    @staticmethod
    def _responder(fn: Callable[[], Any]) -> dict:
        try:
            return {"ok": True, "datos": fn()}
        except ValueError as ex:  # error de lo que ha escrito el usuario: se le explica
            return {"ok": False, "error": str(ex)}
        except Exception as ex:  # noqa: BLE001  (red caída, API que no responde...: se avisa en la ventana)
            log.warning("Asistente: %s", ex)
            return {"ok": False, "error": f"No s'ha pogut comprovar: {str(ex)[:160]}"}

    def inicio(self) -> dict:
        """Opciones de cada paso y lo que ya hay configurado (para rellenar los campos)."""
        c = self._cfg
        return {
            "competiciones": COMPETICIONES,
            "etfs": ETF_HABITUALES,
            "ambitos": AMBITOS,
            "temas": [{"id": t["id"], "nombre": t["nombre"]} for t in TEMAS],
            "orientacions": {
                "ideologia": outlets.IDEOLOGIES,
                "eix_nacional": outlets.NATIONAL_AXIS,
                "mitjans": mitjans_amb_orientacio(c),
            },
            "actual": {
                "lugar": (c.get("ubicacion") or {}).get("nombre", ""),
                "ical_urls": (c.get("agenda") or {}).get("ical_urls", []),
                "futbol": c.get("futbol") or {},
                "drawdown": c.get("drawdown") or {},
                "claude_api_key": (c.get("claude") or {}).get("api_key", ""),
                "pestanas": [p["nombre"] for p in c.get("pestanas", [])],
            },
        }

    def buscar_lugar(self, texto: str) -> dict:
        return self._responder(lambda: buscar_lugar(texto))

    def equipos(self, clave: str, codigo: str) -> dict:
        return self._responder(lambda: equipos_de_competicion(clave, codigo))

    def validar_ticker(self, ticker: str) -> dict:
        return self._responder(lambda: validar_ticker(ticker))

    def verificar_rss(self, url: str) -> dict:
        return self._responder(lambda: verificar_rss(url))

    def guardar(self, respuestas: dict) -> dict:
        def tarea() -> bool:
            """Construye la config nueva, la entrega a app.py (que la guarda y aplica) y la recuerda."""
            nueva = construir_config(self._cfg, respuestas)
            self._al_guardar(nueva)
            self._cfg = nueva
            return True

        return self._responder(tarea)

    def abrir(self, url: str) -> bool:
        """Abre un enlace (p. ej. dónde pedir la clave) en el navegador, no dentro del asistente."""
        if url.startswith("https://"):
            webbrowser.open(url)
        return True

    def cerrar(self) -> bool:
        if self._ventana:
            self._ventana.hide()
        return True
