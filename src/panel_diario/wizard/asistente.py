"""Asistente de configuración: la lógica que hay detrás de ui/wizard/asistente.html.

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

import webview

from panel_diario.sources import agenda, comun, drawdown, noticias
from panel_diario.wizard import markets, news

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
    {"ticker": "VWCE.DE", "nombre": "Vanguard FTSE All-World"},
    {"ticker": "EUNL.DE", "nombre": "iShares Core MSCI World"},
    {"ticker": "XDWD.DE", "nombre": "Xtrackers MSCI World"},
    {"ticker": "IUSQ.DE", "nombre": "iShares MSCI ACWI"},
    {"ticker": "SPYI.DE", "nombre": "SPDR MSCI ACWI IMI"},
    {"ticker": "SXR8.DE", "nombre": "iShares Core S&P 500"},
    {"ticker": "VUAA.DE", "nombre": "Vanguard S&P 500"},
    {"ticker": "SXRV.DE", "nombre": "iShares Nasdaq 100"},
    {"ticker": "IS3N.DE", "nombre": "iShares Core MSCI EM IMI (emergents)"},
]

# Ciudades de ejemplo: un clic las busca sin escribir. "Un altre…" abre la búsqueda libre.
CIUDADES = [
    "Barcelona", "Girona", "Lleida", "Tarragona", "València", "Palma", "Andorra la Vella",
    "Madrid", "Bilbao", "Sevilla", "Saragossa", "Perpinyà",
]  # fmt: skip

# Calendarios con dirección iCal: dónde encontrarla en cada uno (el último, cualquier otro)
CALENDARIOS = [
    {
        "id": "google",
        "nombre": "Google Calendar",
        "ayuda": "A l'ordinador: ⚙ Configuració → el teu calendari (a l'esquerra) → «Integra el calendari» → "
        "«Adreça secreta en format iCal».",
    },
    {
        "id": "outlook",
        "nombre": "Outlook / Microsoft 365",
        "ayuda": "Outlook al web: ⚙ Configuració → Calendari → «Calendaris compartits» → «Publica un calendari» → "
        "tria el calendari i «Pot veure tots els detalls» → Publica → copia l'enllaç ICS.",
    },
    {
        "id": "icloud",
        "nombre": "Calendari d'iCloud (Apple)",
        "ayuda": "A iCloud.com o al Mac: al costat del calendari, «Compartir» → marca «Calendari públic» → "
        "copia l'enllaç (comença per webcal://).",
    },
    {
        "id": "altre",
        "nombre": "Un altre…",
        "ayuda": "Qualsevol calendari que doni una adreça iCal (acostuma a acabar en .ics o començar per webcal://).",
    },
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


def _https_ical(url: str) -> str:
    """Dirección iCal limpia: webcal:// (iCloud) es https:// con otro nombre. Solo se acepta https."""
    url = url.strip()
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://") :]
    if not url.startswith("https://"):
        raise ValueError("L'adreça del calendari ha de començar per https:// o webcal://")
    return url


def verificar_ical(url: str) -> dict:
    """Comprueba que la dirección es un calendario iCal que se puede leer. Sin la dirección en ningún mensaje."""
    try:
        return {"eventos": agenda.comprobar_ical(_https_ical(url))}
    except agenda.ErrorAgenda as ex:
        motivo = str(ex).split(": ", 1)[-1]
        raise ValueError(
            f"No puc llegir aquest calendari ({motivo}). Comprova que has copiat l'adreça sencera."
        ) from None


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
    return [_https_ical(u) for u in urls if u and u.strip()]


# Pestañas de config.json que corresponden a una pestaña del catálogo con otro id
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
    if "borsa" in respuestas:
        cfg.update(markets.build(respuestas["borsa"]))
    if "drawdown" in respuestas:
        d = respuestas["drawdown"]
        cfg.setdefault("drawdown", {"actualizar_minutos": 30, "recalcular_dias": 7})
        cfg["drawdown"].update(ticker=d.get("ticker", "").strip().upper(), nombre=d.get("nombre", "").strip())
        if d.get("niveles"):
            cfg["drawdown"]["niveles"] = _niveles(d["niveles"])
    if "noticias" in respuestas or "seccions" in respuestas:
        # Un paso saltado conserva lo que ya había (los medios o las secciones actuales)
        actual = news.current_choices(cfg)
        medios = respuestas.get("noticias") or {k: actual[k] for k in ("medios", "propios")}
        seccions = respuestas.get("seccions") or {k: actual[k] for k in ("seccions", "plans", "temes", "traduir")}
        ciudad = (lugar or cfg.get("ubicacion") or {}).get("nombre", "")
        cfg.update(news.build(medios, seccions, ciudad))
    if "claude" in respuestas:
        cfg.setdefault("claude", {"modelo": "claude-haiku-5-5", "cada_horas": 3})
        cfg["claude"]["api_key"] = respuestas["claude"].get("api_key", "").strip()
    return cfg


# ---------------------------------------------------------------------------
# Puente con el JavaScript de ui/wizard/asistente.html
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
            "ciudades": CIUDADES,
            "calendarios": CALENDARIOS,
            "competiciones": COMPETICIONES,
            "etfs": ETF_HABITUALES,
            "borsa": markets.options(),
            "borsa_actual": markets.current_choices(c),
            "grupos_medios": news.outlet_groups(),
            "seccions": news.sections(),
            "noticias_actuales": news.current_choices(c),
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

    def verificar_ical(self, url: str) -> dict:
        return self._responder(lambda: verificar_ical(url))

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
