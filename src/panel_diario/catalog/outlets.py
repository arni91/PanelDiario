"""Catálogo público de medios: grupos, secciones y feeds RSS verificados.

El asistente ofrece los medios en dos bloques: Actualitat (generalistas, por zona: Catalunya,
Espanya, Europa, Món) y Per temes (Economia, Tecnologia, Ciència, Esports, Cultura); después, las
secciones (Portades, Política, Economia...). Cada sección del panel junta el feed de esa sección de cada
medio elegido; "portades" es la portada de cada medio. Feeds comprobados el 9 y el 10-11-2026 (responden,
tienen fecha y noticias recientes); los descartados están en docs/fonts.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# Bloques del asistente: los diarios generalistas por zona y los medios especializados por tema
BLOCKS: dict[str, str] = {
    "actualitat": "Actualitat",
    "temes": "Per temes",
}


@dataclass(frozen=True)
class Group:
    name: str
    block: str


# Grupos en que el asistente ofrece los medios, en este orden
GROUPS: dict[str, Group] = {
    "catalunya": Group("Catalunya", "actualitat"),
    "espanya": Group("Espanya", "actualitat"),
    "europa": Group("Europa", "actualitat"),
    "mon": Group("Món", "actualitat"),
    "economia": Group("Economia", "temes"),
    "tecnologia": Group("Tecnologia", "temes"),
    "ciencia": Group("Ciència", "temes"),
    "esports": Group("Esports", "temes"),
    "cultura": Group("Cultura i revistes", "temes"),
}

# Secciones del panel, en el orden en que salen las pestañas
SECTIONS: dict[str, str] = {
    "portades": "Portades",
    "politica": "Política",
    "economia": "Economia",
    "internacional": "Internacional",
    "cultura": "Cultura",
    "tecnologia": "Tecnologia",
    "ciencia": "Ciència",
    "esports": "Esports",
}


@dataclass(frozen=True)
class Outlet:
    """Un medio: idioma de sus titulares, grupo y feed RSS de cada sección que publica.

    `google_news`: el medio no publica RSS y sus feeds son búsquedas de Google Noticias
    (site:dominio); el panel las lee como agregador y saca el nombre del medio de cada titular.
    """

    name: str
    language: str
    group: str
    feeds: dict[str, str]
    google_news: bool = False


CATALOG: tuple[Outlet, ...] = (
    # --- Catalunya ---
    Outlet(
        "Ara",
        "ca",
        "catalunya",
        {
            "portades": "https://www.ara.cat/rss/",
            "politica": "https://www.ara.cat/rss/politica/",
            "economia": "https://www.ara.cat/rss/economia/",
            "internacional": "https://www.ara.cat/rss/internacional/",
            "cultura": "https://www.ara.cat/rss/cultura/",
            "esports": "https://www.ara.cat/rss/esports/",
        },
    ),
    Outlet(
        "VilaWeb",
        "ca",
        "catalunya",
        {
            "portades": "https://www.vilaweb.cat/feed/",
            "economia": "https://www.vilaweb.cat/categoria/economia/feed/",
            "internacional": "https://www.vilaweb.cat/categoria/mon/feed/",
            "cultura": "https://www.vilaweb.cat/categoria/cultura/feed/",
            "esports": "https://www.vilaweb.cat/categoria/esports/feed/",
        },
    ),
    Outlet("El Nacional.cat", "ca", "catalunya", {"portades": "https://www.elnacional.cat/ca/feed"}),
    Outlet("NacióDigital", "ca", "catalunya", {"portades": "https://www.naciodigital.cat/rss"}),
    Outlet(
        "La Vanguardia",
        "es",
        "catalunya",
        {
            "portades": "https://www.lavanguardia.com/rss/home.xml",
            "politica": "https://www.lavanguardia.com/rss/politica.xml",
            "economia": "https://www.lavanguardia.com/rss/economia.xml",
            "internacional": "https://www.lavanguardia.com/rss/internacional.xml",
            "cultura": "https://www.lavanguardia.com/rss/cultura.xml",
            "tecnologia": "https://www.lavanguardia.com/rss/tecnologia.xml",
            "ciencia": "https://www.lavanguardia.com/rss/ciencia.xml",
            "esports": "https://www.lavanguardia.com/rss/deportes.xml",
        },
    ),
    Outlet(
        "El Periódico",
        "es",
        "catalunya",
        {
            "portades": "https://www.elperiodico.com/ca/rss/rss_portada.xml",
            "politica": "https://www.elperiodico.com/es/rss/politica/rss.xml",
            "economia": "https://www.elperiodico.com/es/rss/economia/rss.xml",
            "internacional": "https://www.elperiodico.com/es/rss/internacional/rss.xml",
            "cultura": "https://www.elperiodico.com/es/rss/cultura/rss.xml",
            "tecnologia": "https://www.elperiodico.com/es/rss/tecnologia/rss.xml",
            "ciencia": "https://www.elperiodico.com/es/rss/ciencia/rss.xml",
            "esports": "https://www.elperiodico.com/es/rss/deportes/rss.xml",
        },
    ),
    Outlet("Crónica Global", "es", "catalunya", {"portades": "https://cronicaglobal.elespanol.com/rss"}),
    Outlet("La Directa", "ca", "catalunya", {"portades": "https://directa.cat/feed/"}),
    Outlet("El Crític", "ca", "catalunya", {"portades": "https://www.elcritic.cat/feed"}),
    Outlet("3Cat Notícies", "ca", "catalunya", {"portades": "https://api.3cat.cat/noticies?_format=rss"}),
    # --- Espanya ---
    Outlet(
        "El País",
        "es",
        "espanya",
        {
            "portades": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
            "politica": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada",
            "economia": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada",
            "internacional": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada",
            "cultura": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/cultura/portada",
            "tecnologia": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",
            "ciencia": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada",
            "esports": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada",
        },
    ),
    Outlet(
        "El Mundo",
        "es",
        "espanya",
        {
            "portades": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
            "politica": "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
            "economia": "https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml",
            "internacional": "https://e00-elmundo.uecdn.es/elmundo/rss/internacional.xml",
            "cultura": "https://e00-elmundo.uecdn.es/elmundo/rss/cultura.xml",
            "ciencia": "https://e00-elmundo.uecdn.es/elmundo/rss/ciencia.xml",
        },
    ),
    Outlet(
        "ABC",
        "es",
        "espanya",
        {
            "portades": "https://www.abc.es/rss/2.0/portada/",
            "politica": "https://www.abc.es/rss/2.0/espana/",
            "economia": "https://www.abc.es/rss/2.0/economia/",
            "internacional": "https://www.abc.es/rss/2.0/internacional/",
            "cultura": "https://www.abc.es/rss/2.0/cultura/",
            "tecnologia": "https://www.abc.es/rss/2.0/tecnologia/",
            "ciencia": "https://www.abc.es/rss/2.0/ciencia/",
            "esports": "https://www.abc.es/rss/2.0/deportes/",
        },
    ),
    Outlet(
        "La Razón",
        "es",
        "espanya",
        {
            "portades": "https://www.larazon.es/?outputType=xml",
            "politica": "https://www.larazon.es/espana/?outputType=xml",
            "economia": "https://www.larazon.es/economia/?outputType=xml",
            "internacional": "https://www.larazon.es/internacional/?outputType=xml",
            "cultura": "https://www.larazon.es/cultura/?outputType=xml",
            "tecnologia": "https://www.larazon.es/tecnologia/?outputType=xml",
            "ciencia": "https://www.larazon.es/ciencia/?outputType=xml",
            "esports": "https://www.larazon.es/deportes/?outputType=xml",
        },
    ),
    Outlet(
        "eldiario.es",
        "es",
        "espanya",
        {
            "portades": "https://www.eldiario.es/rss/",
            "politica": "https://www.eldiario.es/rss/politica/",
            "economia": "https://www.eldiario.es/rss/economia/",
            "internacional": "https://www.eldiario.es/rss/internacional/",
            "cultura": "https://www.eldiario.es/rss/cultura/",
            "tecnologia": "https://www.eldiario.es/rss/tecnologia/",
            "ciencia": "https://www.eldiario.es/rss/ciencia/",
        },
    ),
    Outlet(
        "El Confidencial",
        "es",
        "espanya",
        {
            "portades": "https://rss.elconfidencial.com/espana/",
            "economia": "https://rss.elconfidencial.com/economia/",
            "internacional": "https://rss.elconfidencial.com/mundo/",
            "cultura": "https://rss.elconfidencial.com/cultura/",
            "tecnologia": "https://rss.elconfidencial.com/tecnologia/",
            "esports": "https://rss.elconfidencial.com/deportes/",
        },
    ),
    Outlet(
        "El Español",
        "es",
        "espanya",
        {
            "portades": "https://www.elespanol.com/rss/",
            "politica": "https://www.elespanol.com/rss/espana/",
            "economia": "https://www.elespanol.com/rss/invertia/",
        },
    ),
    Outlet(
        "20minutos",
        "es",
        "espanya",
        {
            "portades": "https://www.20minutos.es/rss/",
            "politica": "https://www.20minutos.es/rss/nacional/",
            "economia": "https://www.20minutos.es/rss/economia/",
            "internacional": "https://www.20minutos.es/rss/internacional/",
            "cultura": "https://www.20minutos.es/rss/cultura/",
            "tecnologia": "https://www.20minutos.es/rss/tecnologia/",
            "ciencia": "https://www.20minutos.es/rss/ciencia/",
            "esports": "https://www.20minutos.es/rss/deportes/",
        },
    ),
    Outlet("Libertad Digital", "es", "espanya", {"portades": "https://feeds2.feedburner.com/libertaddigital/portada"}),
    Outlet(
        "El Salto",
        "es",
        "espanya",
        {
            "portades": "https://www.elsaltodiario.com/general/feed",
            "politica": "https://www.elsaltodiario.com/politica/feed",
            "tecnologia": "https://www.elsaltodiario.com/tecnologia/feed",
        },
    ),
    Outlet(
        "Europa Press",
        "es",
        "espanya",
        {
            "portades": "https://www.europapress.es/rss/rss.aspx",
            "internacional": "https://www.europapress.es/rss/rss.aspx?ch=69",
        },
    ),
    # --- Europa ---
    Outlet(
        "BBC News",
        "en",
        "europa",
        {
            "portades": "https://feeds.bbci.co.uk/news/rss.xml",
            "politica": "https://feeds.bbci.co.uk/news/politics/rss.xml",
            "economia": "https://feeds.bbci.co.uk/news/business/rss.xml",
            "internacional": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "cultura": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
            "tecnologia": "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "ciencia": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "esports": "https://feeds.bbci.co.uk/sport/rss.xml",
        },
    ),
    Outlet(
        "The Guardian",
        "en",
        "europa",
        {
            "portades": "https://www.theguardian.com/international/rss",
            "politica": "https://www.theguardian.com/politics/rss",
            "economia": "https://www.theguardian.com/business/rss",
            "internacional": "https://www.theguardian.com/world/rss",
            "cultura": "https://www.theguardian.com/culture/rss",
            "tecnologia": "https://www.theguardian.com/technology/rss",
            "ciencia": "https://www.theguardian.com/science/rss",
            "esports": "https://www.theguardian.com/sport/rss",
        },
    ),
    Outlet(
        "Le Monde",
        "fr",
        "europa",
        {
            "portades": "https://www.lemonde.fr/rss/une.xml",
            "politica": "https://www.lemonde.fr/politique/rss_full.xml",
            "economia": "https://www.lemonde.fr/economie/rss_full.xml",
            "internacional": "https://www.lemonde.fr/international/rss_full.xml",
            "cultura": "https://www.lemonde.fr/culture/rss_full.xml",
            "tecnologia": "https://www.lemonde.fr/pixels/rss_full.xml",
            "ciencia": "https://www.lemonde.fr/sciences/rss_full.xml",
            "esports": "https://www.lemonde.fr/sport/rss_full.xml",
        },
    ),
    Outlet(
        "Le Figaro",
        "fr",
        "europa",
        {
            "portades": "https://www.lefigaro.fr/rss/figaro_actualites.xml",
            "internacional": "https://www.lefigaro.fr/rss/figaro_international.xml",
        },
    ),
    Outlet("Politico Europe", "en", "europa", {"portades": "https://www.politico.eu/feed/"}),
    Outlet("Euronews", "es", "europa", {"portades": "https://es.euronews.com/rss"}),
    Outlet("DW", "es", "europa", {"portades": "https://rss.dw.com/rdf/rss-sp-all"}),
    # --- Món ---
    Outlet(
        "The New York Times",
        "en",
        "mon",
        {
            "portades": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "politica": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
            "economia": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
            "internacional": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "cultura": "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
            "tecnologia": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
            "ciencia": "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        },
    ),
    Outlet("The Washington Post", "en", "mon", {"portades": "https://feeds.washingtonpost.com/rss/world"}),
    Outlet(
        "Fox News",
        "en",
        "mon",
        {
            "portades": "https://moxie.foxnews.com/google-publisher/latest.xml",
            "internacional": "https://moxie.foxnews.com/google-publisher/world.xml",
        },
    ),
    Outlet("Al Jazeera", "en", "mon", {"portades": "https://www.aljazeera.com/xml/rss/all.xml"}),
    Outlet("BBC Mundo", "es", "mon", {"portades": "https://feeds.bbci.co.uk/mundo/rss.xml"}),
    Outlet("France 24", "es", "mon", {"portades": "https://www.france24.com/es/rss"}),
    Outlet("The Economist", "en", "mon", {"portades": "https://www.economist.com/the-world-this-week/rss.xml"}),
    Outlet("Clarín", "es", "mon", {"portades": "https://www.clarin.com/rss/lo-ultimo/"}),
    # --- Economia ---
    Outlet(
        "Cinco Días",
        "es",
        "economia",
        {"economia": "https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/portada"},
    ),
    Outlet("Economía Digital", "es", "economia", {"economia": "https://www.economiadigital.es/feed/"}),
    Outlet("Investing.com", "es", "economia", {"economia": "https://es.investing.com/rss/news.rss"}),
    Outlet("Financial Times", "en", "economia", {"economia": "https://www.ft.com/rss/home"}),
    Outlet("Bloomberg", "en", "economia", {"economia": "https://feeds.bloomberg.com/markets/news.rss"}),
    Outlet(
        "The Wall Street Journal",
        "en",
        "economia",
        {"economia": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"},
    ),
    # --- Tecnologia ---
    Outlet("Xataka", "es", "tecnologia", {"tecnologia": "https://www.xataka.com/feedburner.xml"}),
    Outlet("Genbeta", "es", "tecnologia", {"tecnologia": "https://www.genbeta.com/feedburner.xml"}),
    Outlet("The Verge", "en", "tecnologia", {"tecnologia": "https://www.theverge.com/rss/index.xml"}),
    Outlet("Wired", "en", "tecnologia", {"tecnologia": "https://www.wired.com/feed/rss"}),
    Outlet("Ars Technica", "en", "tecnologia", {"tecnologia": "https://feeds.arstechnica.com/arstechnica/index"}),
    Outlet("TechCrunch", "en", "tecnologia", {"tecnologia": "https://techcrunch.com/feed/"}),
    Outlet("Engadget", "en", "tecnologia", {"tecnologia": "https://www.engadget.com/rss.xml"}),
    Outlet("MIT Technology Review", "en", "tecnologia", {"tecnologia": "https://www.technologyreview.com/feed/"}),
    Outlet("Hacker News", "en", "tecnologia", {"tecnologia": "https://hnrss.org/frontpage"}),
    # --- Ciència ---
    Outlet("Nature", "en", "ciencia", {"ciencia": "https://www.nature.com/nature.rss"}),
    Outlet("Muy Interesante", "es", "ciencia", {"ciencia": "https://www.muyinteresante.com/feed/"}),
    Outlet("ScienceDaily", "en", "ciencia", {"ciencia": "https://www.sciencedaily.com/rss/all.xml"}),
    Outlet(
        "Scientific American",
        "en",
        "ciencia",
        {"ciencia": "https://www.scientificamerican.com/platform/syndication/rss/"},
    ),
    Outlet("Quanta Magazine", "en", "ciencia", {"ciencia": "https://www.quantamagazine.org/feed/"}),
    # --- Esports ---
    Outlet("Mundo Deportivo", "es", "esports", {"esports": "https://www.mundodeportivo.com/rss/home.xml"}),
    Outlet("Marca", "es", "esports", {"esports": "https://e00-marca.uecdn.es/rss/portada.xml"}),
    Outlet("AS", "es", "esports", {"esports": "https://feeds.as.com/mrss-s/pages/as/site/as.com/portada/"}),
    Outlet("Motorsport.com", "en", "esports", {"esports": "https://www.motorsport.com/rss/all/news/"}),
    # --- Cultura i revistes ---
    Outlet(
        "Time Out Barcelona",
        "ca",
        "cultura",
        {"cultura": "https://news.google.com/rss/search?q=site%3Atimeout.cat&hl=ca&gl=ES&ceid=ES:ca"},
        google_news=True,
    ),
    Outlet("Jot Down", "es", "cultura", {"cultura": "https://www.jotdown.es/feed/"}),
    Outlet("Sàpiens", "ca", "cultura", {"cultura": "https://www.sapiens.cat/uploads/feeds/feed_sapiens_ca.xml"}),
    Outlet("The Atlantic", "en", "cultura", {"portades": "https://www.theatlantic.com/feed/all/"}),
    Outlet("The New Yorker", "en", "cultura", {"cultura": "https://www.newyorker.com/feed/everything"}),
    Outlet("Rolling Stone", "en", "cultura", {"cultura": "https://www.rollingstone.com/feed/"}),
)


def find(name: str) -> Outlet | None:
    """El medio del catálogo con ese nombre exacto."""
    return next((o for o in CATALOG if o.name == name), None)


def sources_for(section: str, names: Iterable[str]) -> list[dict]:
    """Fuentes de config.json para una sección: el feed de esa sección de cada medio elegido."""
    elegidos = set(names)
    return [
        {"nombre": o.name, "url": o.feeds[section], "idioma": o.language}
        | ({"agregador": True} if o.google_news else {})
        for o in CATALOG
        if o.name in elegidos and section in o.feeds
    ]
