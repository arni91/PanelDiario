"""Noticias por pestañas a partir de RSS (medios y búsquedas de Google Noticias).

Lee los feeds de config.json en paralelo, junta la misma noticia publicada por varios medios,
filtra por palabras y antigüedad y traduce lo que haga falta (traduccion.py).
"""

from __future__ import annotations

import calendar
import html
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

import feedparser

from panel_diario.fuentes import comun
from panel_diario.fuentes.traduccion import traduir_noticies

log = logging.getLogger("panel")


STOP = set(
    """
el la los las un una unos unas de del al a ante con contra desde en entre hacia hasta para por segun sin
sobre tras y o u e ni que se su sus lo le les ya mas pero como este esta estos estas ese esa eso es son
ha han fue ser sera hay muy tambien no si sí cuando donde quien cual tras ante tras durante tras
els les uns unes amb per pel pels dels des fins i o que es seu seva seus seves ho hi ja mes pero com
aquest aquesta aquests aquestes ser sera han va van fa no si quan on qui
the of and to in on for with at by from as is are was were be been an it its this that after over new
says said dice dicen afirma asegura segun
""".split()
)


def _tokens(titulo: str) -> set:
    palabras = re.findall(r"[a-z0-9]+", comun.normalizar(titulo))
    return {p for p in palabras if len(p) > 3 and p not in STOP}


def _limpiar_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _leer_feed(fuente: dict, categoria: str, horas_max: int) -> tuple[list, str | None]:
    """Devuelve (noticias, error)."""
    try:
        r = comun.get(
            fuente["url"],
            headers={"User-Agent": comun.UA_NAVEGADOR, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )
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
        items.append(
            {
                "titulo": titulo,
                "enlace": enlace,
                "medio": medio,
                "ts": ts,
                "resumen": resumen[:220],
                "categoria": categoria,
                "portada": bool(fuente.get("portada")),
                "tema": fuente.get("tema", ""),  # en Cultura: de qué búsqueda viene (museus, concerts...)
                "idioma": fuente.get("idioma", ""),  # idioma conocido de la fuente ("ca", "es"...): evita el traductor
            }
        )
    return items, None


def netejar_resum(text: str) -> str:
    """Treu el que afegeix WordPress al final dels resums ("[…]", "L'entrada … va aparèixer primer a …")."""
    text = re.sub(r"\s*(The post|La entrada|L.entrada)\b.*$", "", text, flags=re.S)
    text = re.sub(r"\s*(\[(…|\.\.\.|&#8230;)\]|Continue reading|Llegir més|Leer más).*$", "", text, flags=re.S)
    return text.strip()


def _excluido(medio: str, excluidos: list) -> bool:
    m = comun.normalizar(medio)
    return any(comun.normalizar(x) in m for x in excluidos)


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
        puntos: float = len(medios) * 2 + sum(1 for i in g["items"] if i["portada"])
        puntos *= 1.0 if horas < 12 else (0.7 if horas < 24 else 0.4)
        salida.append(
            {
                "items": g["items"],
                "medios": medios,
                "ts": ts,
                "puntos": puntos,
                "categorias": sorted({i["categoria"] for i in g["items"]}),
            }
        )
    salida.sort(key=lambda g: (-g["puntos"], -(g["ts"] or 0)))
    return salida


def _representante(grupo: dict, prioridad: list) -> dict:
    """Elige el titular a mostrar: el del medio más neutro según el orden de prioridad."""

    def rango(it: dict) -> int:
        m = comun.normalizar(it["medio"])
        for i, p in enumerate(prioridad):
            if comun.normalizar(p) in m:
                return i
        return len(prioridad)

    it = sorted(grupo["items"], key=lambda x: (rango(x), -(x["ts"] or 0)))[0]
    otros = [m for m in grupo["medios"] if m != it["medio"]]
    return {
        "titulo": it["titulo"],
        "enlace": it["enlace"],
        "medio": it["medio"],
        "tema": it.get("tema", ""),
        "idioma": it.get("idioma", ""),
        "ts": grupo["ts"],
        "resumen": it["resumen"],
        "otros_medios": otros,
        "enlaces": [{"medio": x["medio"], "enlace": x["enlace"]} for x in grupo["items"]][:6],
    }


def filtrar_paraules(items: list, requereix: list | None, excloses: list | None) -> list:
    """Filtra titulars per paraules (sense accents ni majúscules) al títol o al resum.

    - requereix: si n'hi ha, el titular ha de contenir-ne almenys una (p. ex. que una revista
      d'àmbit estatal només aporti el que passa a la teva ciutat o comunitat).
    - excloses: si en conté alguna, es descarta (p. ex. tot el que és infantil a Cultura).
    """

    def conte(text: str, paraules: list[str]) -> bool:
        return any(re.search(rf"\b{re.escape(comun.normalizar(p))}", text) for p in paraules)

    sortida = []
    for it in items:
        text = comun.normalizar(f"{it['titulo']} {it.get('resumen', '')}")
        if requereix and not conte(text, requereix):
            continue
        if excloses and conte(text, excloses):
            continue
        sortida.append(it)
    return sortida


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
    resultados: dict[str, list[dict]] = {}
    errores: list[dict] = []
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
        salida[cat] = noticies[: por_cat.get(cat, n)]
    traduir_noticies(salida, cfg)
    return salida, errores
