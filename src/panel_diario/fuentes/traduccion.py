"""Traducción de los titulares que no están en un idioma que se conserva (traductor de Google)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from panel_diario.fuentes import comun

log = logging.getLogger("panel")


# Regla: las noticias en los idiomas de "conservar" (por defecto catalán y castellano) se quedan
# tal cual; las demás (inglés, francés...) se traducen a "idioma" (por defecto castellano).
# Si la fuente declara su "idioma" en config.json, ni se consulta el traductor; si no, el propio
# traductor detecta el idioma y, si es uno de los que se conservan, se deja el original.
# Solo se traducen los titulares (y resúmenes) que se muestran, y se guardan en memoria:
# un titular se traduce una sola vez aunque el panel se actualice cada 30 minutos.
# Si el traductor falla, se muestra el texto original: el panel no se rompe nunca por esto.

_TRADUCCIONS: dict[tuple[str, str], str] = {}  # (idioma destino, texto) -> texto a mostrar


def traduir(text: str, desti: str = "ca", conservar: tuple[str, ...] = ()) -> str:
    if not text or not text.strip():
        return text
    clave = (desti, text)
    if clave in _TRADUCCIONS:
        return _TRADUCCIONS[clave]
    r = comun.get(
        "https://translate.googleapis.com/translate_a/single",
        headers={"User-Agent": comun.UA_NAVEGADOR},
        params={"client": "gtx", "sl": "auto", "tl": desti, "dt": "t", "q": text},
    )
    datos = r.json()
    detectado = datos[2] if len(datos) > 2 else None  # el traductor devuelve el idioma de origen aquí
    if detectado in conservar:
        traduit = text
    else:
        traduit = "".join(t[0] for t in (datos[0] or []) if t and t[0]).strip() or text
    if len(_TRADUCCIONS) > 3000:  # que la memoria no crezca sin límite
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
    textos = {
        txt
        for nt in pendientes
        for txt in (nt["titulo"], nt.get("resumen", ""))
        if txt and (desti, txt) not in _TRADUCCIONS
    }
    errors = []

    def una(txt: str) -> None:
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
