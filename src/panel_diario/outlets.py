"""Catálogo público de medios y orientación de cada fuente (ideología y eje nacional).

Cada titular lleva una etiqueta con el nombre del medio y su orientación. La orientación sale de
config.json (campos "ideologia" y "eix_nacional" de cada fuente, que el usuario puede cambiar
desde el asistente) o, si no la tiene, de este catálogo. En las fuentes agregadoras (Google
Noticias) se busca el medio de cada noticia por su nombre: si no está, no lleva orientación.
Los valores por defecto salen de una fuente verificable, citada en docs/fonts.md; lo que no se
puede verificar se deja vacío.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from panel_diario.fuentes import comun

log = logging.getLogger("panel")

# Valores válidos de cada campo (en config.json y en el asistente). "" = sin orientación.
IDEOLOGIES = ("esquerra", "centreesquerra", "centre", "centredreta", "dreta")
NATIONAL_AXIS = ("independentista", "sobiranista", "no_independentista", "unionista")
LEANING_FIELDS: dict[str, tuple[str, ...]] = {"ideologia": IDEOLOGIES, "eix_nacional": NATIONAL_AXIS}


@dataclass(frozen=True)
class Outlet:
    """Un medio del catálogo. `aliases`: otros nombres con que aparece (p. ej. en Google Noticias)."""

    name: str
    language: str  # "ca", "es"...: sus titulares no pasan por el traductor
    aliases: tuple[str, ...] = ()
    ideologia: str = ""
    eix_nacional: str = ""


# Orientación por defecto: valoración de Media Bias/Fact Check (ver docs/fonts.md). Los medios
# sin ficha en MBFC y todo el eje nacional (ningún medio declara su posición) quedan vacíos.
CATALOG: tuple[Outlet, ...] = (
    Outlet("El Salto", "es", aliases=("El Salto Diario", "elsaltodiario.com")),
    Outlet("eldiario.es", "es", aliases=("elDiario.es",), ideologia="centreesquerra"),
    Outlet("La Directa", "ca", aliases=("Directa", "directa.cat")),
    Outlet("Ara", "ca", aliases=("Diari Ara", "ara.cat", "Ara.cat")),
    Outlet("La Vanguardia", "es", aliases=("lavanguardia.com",), ideologia="centreesquerra"),
    Outlet("El País", "es", aliases=("elpais.com", "EL PAÍS"), ideologia="centreesquerra"),
)

Leaning = dict[str, str]  # {"ideologia": ..., "eix_nacional": ...}


def outlet_key(name: str) -> str:
    """Nombre comparable: sin mayúsculas, acentos ni espacios de más ("EL PAÍS" = "El País")."""
    return " ".join(comun.normalizar(name).split())


def find_outlet(name: str) -> Outlet | None:
    """El medio del catálogo con ese nombre o alias (comparación exacta: "Ara" no es "Arabia")."""
    k = outlet_key(name)
    for outlet in CATALOG:
        if k in {outlet_key(n) for n in (outlet.name, *outlet.aliases)}:
            return outlet
    return None


# ---------------------------------------------------------------------------
# Validación de config.json (al cargarla)
# ---------------------------------------------------------------------------


def clean_leanings(cfg: dict) -> None:
    """Quita de cada fuente los valores de orientación que no son válidos, con un aviso en el log.

    Un valor mal escrito no impide arrancar el panel: esa fuente se queda sin ese campo y se usa
    el del catálogo, si lo hay.
    """
    fuentes = cfg.get("fuentes")
    if not isinstance(fuentes, dict):
        return
    for tab, lista in fuentes.items():
        for fuente in lista if isinstance(lista, list) else []:
            if not isinstance(fuente, dict):
                continue
            for field, allowed in LEANING_FIELDS.items():
                if field in fuente and fuente[field] not in ("", *allowed):
                    log.warning(
                        "config.json: fuentes → %s → %s: %s «%s» no es válido (opciones: %s); se ignora",
                        tab,
                        fuente.get("nombre", "?"),
                        field,
                        fuente[field],
                        ", ".join(allowed),
                    )
                    del fuente[field]


# ---------------------------------------------------------------------------
# Orientación de cada medio (catálogo + lo que diga config.json)
# ---------------------------------------------------------------------------


def leaning_index(cfg: dict) -> dict[str, Leaning]:
    """{nombre comparable: orientación} de todos los medios conocidos.

    Primero el catálogo (con sus alias); encima, las fuentes de config.json que declaran
    "ideologia" o "eix_nacional" (también "" para quitar la del catálogo). Así, lo que el usuario
    elige para un medio vale también para sus noticias que llegan por Google Noticias.
    """
    index: dict[str, Leaning] = {}
    for outlet in CATALOG:
        leaning = {"ideologia": outlet.ideologia, "eix_nacional": outlet.eix_nacional}
        for name in (outlet.name, *outlet.aliases):
            index[outlet_key(name)] = leaning
    for lista in (cfg.get("fuentes") or {}).values():
        for fuente in lista:
            if fuente.get("agregador") or not any(f in fuente for f in LEANING_FIELDS):
                continue
            known = find_outlet(fuente["nombre"])
            names = (known.name, *known.aliases) if known else (fuente["nombre"],)
            base = dict(index.get(outlet_key(fuente["nombre"]), {"ideologia": "", "eix_nacional": ""}))
            base.update({f: fuente[f] for f in LEANING_FIELDS if f in fuente})
            for name in names:
                index[outlet_key(name)] = base
    return index


def labels(medios: list[str], index: dict[str, Leaning]) -> list[dict[str, str]]:
    """Etiqueta de cada medio de una noticia: {"medio", "ideologia", "eix_nacional"} ("" si no se sabe)."""
    vacio = {"ideologia": "", "eix_nacional": ""}
    return [{"medio": m, **index.get(outlet_key(m), vacio)} for m in medios]
