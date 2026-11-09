"""Catálogo público de medios: feeds RSS verificados por sección.

Cada medio del catálogo trae sus feeds RSS oficiales, cada uno con el tipo de pestaña al que va
(Món, Catalunya, Espanya...): de aquí salen config.example.json y las opciones del asistente.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tipos de pestaña a los que puede ir un feed del catálogo: id -> nombre que ve el usuario
TABS: dict[str, str] = {
    "mon": "Món",
    "catalunya": "Catalunya",
    "espanya": "Espanya",
    "mobilitzacions": "Mobilitzacions",
    "tecnologia": "Tecnologia",
}


@dataclass(frozen=True)
class Feed:
    """Un feed RSS oficial de un medio. `tab`: clave de TABS; `section`: cómo lo llama el medio."""

    tab: str
    section: str
    url: str


@dataclass(frozen=True)
class Outlet:
    """Un medio del catálogo con sus feeds oficiales."""

    name: str
    language: str  # "ca", "es"...: sus titulares no pasan por el traductor
    feeds: tuple[Feed, ...] = ()


_EL_PAIS = "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/"

# Feeds comprobados (responden y tienen noticias del día) el 9-11-2026; los que no existen,
# en docs/fonts.md. Los seis diarios principales van primero: el asistente los ofrece así.
CATALOG: tuple[Outlet, ...] = (
    Outlet(
        "El Salto",
        "es",
        feeds=(
            Feed("mobilitzacions", "Portada", "https://www.elsaltodiario.com/general/feed"),
            Feed("espanya", "Política", "https://www.elsaltodiario.com/politica/feed"),
            Feed("tecnologia", "Tecnología", "https://www.elsaltodiario.com/tecnologia/feed"),
        ),
    ),
    Outlet(
        "eldiario.es",
        "es",
        feeds=(
            Feed("mon", "Internacional", "https://www.eldiario.es/rss/internacional/"),
            Feed("catalunya", "Catalunya", "https://www.eldiario.es/rss/catalunya/"),
            Feed("espanya", "Política", "https://www.eldiario.es/rss/politica/"),
            Feed("tecnologia", "Tecnología", "https://www.eldiario.es/rss/tecnologia/"),
        ),
    ),
    Outlet(
        "La Directa",
        "ca",
        feeds=(
            Feed("catalunya", "Portada", "https://directa.cat/feed/"),
            Feed("mobilitzacions", "Portada", "https://directa.cat/feed/"),
        ),
    ),
    Outlet(
        "Ara",
        "ca",
        feeds=(Feed("catalunya", "Portada", "https://www.ara.cat/rss/"),),
    ),
    Outlet(
        "La Vanguardia",
        "es",
        feeds=(
            Feed("mon", "Internacional", "https://www.lavanguardia.com/rss/internacional.xml"),
            Feed("catalunya", "Catalunya", "https://www.lavanguardia.com/rss/local/catalunya.xml"),
            Feed("tecnologia", "Tecnología", "https://www.lavanguardia.com/rss/tecnologia.xml"),
        ),
    ),
    Outlet(
        "El País",
        "es",
        feeds=(
            Feed("mon", "Internacional", _EL_PAIS + "internacional/portada"),
            # El País no publica un feed solo de política: su sección España es la más cercana
            Feed("espanya", "España", _EL_PAIS + "espana/portada"),
            Feed("tecnologia", "Tecnología", _EL_PAIS + "tecnologia/portada"),
        ),
    ),
    Outlet(
        "El Crític",
        "ca",
        feeds=(Feed("mobilitzacions", "Portada", "https://www.elcritic.cat/feed"),),
    ),
    # Medios generales
    Outlet(
        "Europa Press", "es", feeds=(Feed("mon", "Internacional", "https://www.europapress.es/rss/rss.aspx?ch=69"),)
    ),
    Outlet("BBC Mundo", "es", feeds=(Feed("mon", "Portada", "https://feeds.bbci.co.uk/mundo/rss.xml"),)),
    Outlet("DW", "es", feeds=(Feed("mon", "Portada", "https://rss.dw.com/rdf/rss-sp-all"),)),
    Outlet("France 24", "es", feeds=(Feed("mon", "Portada", "https://www.france24.com/es/rss"),)),
    Outlet("Xataka", "es", feeds=(Feed("tecnologia", "Portada", "https://www.xataka.com/feedburner.xml"),)),
    Outlet(
        "Ars Technica", "en", feeds=(Feed("tecnologia", "Portada", "https://feeds.arstechnica.com/arstechnica/index"),)
    ),
    Outlet(
        "MIT Technology Review", "en", feeds=(Feed("tecnologia", "Portada", "https://www.technologyreview.com/feed/"),)
    ),
)


def sources_for_tab(tab: str) -> list[dict]:
    """Fuentes de config.json para una pestaña: los feeds del catálogo de ese tipo, en su orden."""
    return [{"nombre": o.name, "url": f.url, "idioma": o.language} for o in CATALOG for f in o.feeds if f.tab == tab]
