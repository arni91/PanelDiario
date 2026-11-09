# Medios del catálogo: feeds RSS

El catálogo público de medios ([`catalog/outlets.py`](../src/panel_diario/catalog/outlets.py)) guarda, de cada medio, sus feeds RSS oficiales por sección. De ahí salen la plantilla `config.example.json` y las opciones del asistente.

## Feeds RSS

Comprobados el 9 de noviembre de 2026: cada uno responde, es RSS válido y tenía noticias de las últimas horas.

| Pestaña | Medio | Sección | Feed |
|---|---|---|---|
| Món | El País | Internacional | `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada` |
| Món | eldiario.es | Internacional | `https://www.eldiario.es/rss/internacional/` |
| Món | La Vanguardia | Internacional | `https://www.lavanguardia.com/rss/internacional.xml` |
| Catalunya | Ara | Portada | `https://www.ara.cat/rss/` |
| Catalunya | La Vanguardia | Catalunya | `https://www.lavanguardia.com/rss/local/catalunya.xml` |
| Catalunya | La Directa | Portada | `https://directa.cat/feed/` |
| Catalunya | eldiario.es | Catalunya | `https://www.eldiario.es/rss/catalunya/` |
| Espanya | El País | España | `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada` |
| Espanya | eldiario.es | Política | `https://www.eldiario.es/rss/politica/` |
| Espanya | El Salto | Política | `https://www.elsaltodiario.com/politica/feed` |
| Mobilitzacions | El Salto | Portada | `https://www.elsaltodiario.com/general/feed` |
| Mobilitzacions | La Directa | Portada | `https://directa.cat/feed/` |
| Mobilitzacions | El Crític | Portada | `https://www.elcritic.cat/feed` |
| Tecnologia | El País | Tecnología | `https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada` |
| Tecnologia | eldiario.es | Tecnología | `https://www.eldiario.es/rss/tecnologia/` |
| Tecnologia | La Vanguardia | Tecnología | `https://www.lavanguardia.com/rss/tecnologia.xml` |
| Tecnologia | El Salto | Tecnología | `https://www.elsaltodiario.com/tecnologia/feed` |

Medios generales del catálogo (también comprobados el 9-11-2026), después de los diarios principales:

| Pestaña | Medio | Idioma | Feed |
|---|---|---|---|
| Món | Europa Press | castellano | `https://www.europapress.es/rss/rss.aspx?ch=69` |
| Món | BBC Mundo | castellano | `https://feeds.bbci.co.uk/mundo/rss.xml` |
| Món | DW | castellano | `https://rss.dw.com/rdf/rss-sp-all` |
| Món | France 24 | castellano | `https://www.france24.com/es/rss` |
| Tecnologia | Xataka | castellano | `https://www.xataka.com/feedburner.xml` |
| Tecnologia | Ars Technica | inglés (se traduce) | `https://feeds.arstechnica.com/arstechnica/index` |
| Tecnologia | MIT Technology Review | inglés (se traduce) | `https://www.technologyreview.com/feed/` |
| Món | VilaWeb | catalán | `https://www.vilaweb.cat/categoria/mon/feed/` |
| Món | El Periódico | castellano | `https://www.elperiodico.com/es/rss/internacional/rss.xml` |
| Món | The Guardian | inglés (se traduce) | `https://www.theguardian.com/world/rss` |
| Món | Al Jazeera | inglés (se traduce) | `https://www.aljazeera.com/xml/rss/all.xml` |
| Món | The New York Times | inglés (se traduce) | `https://rss.nytimes.com/services/xml/rss/nyt/World.xml` |
| Tecnologia | VilaWeb | catalán | `https://www.vilaweb.cat/categoria/ciencia-i-tecnologia/feed/` (publica poco: a veces varios días sin noticias) |
| Tecnologia | El Periódico | castellano | `https://www.elperiodico.com/es/rss/tecnologia/rss.xml` |
| Tecnologia | Genbeta | castellano | `https://www.genbeta.com/feedburner.xml` |
| Tecnologia | The Verge | inglés (se traduce) | `https://www.theverge.com/rss/index.xml` |
| Tecnologia | Wired | inglés (se traduce) | `https://www.wired.com/feed/rss` |
| Tecnologia | TechCrunch | inglés (se traduce) | `https://techcrunch.com/feed/` |
| Tecnologia | Engadget | inglés (se traduce) | `https://www.engadget.com/rss.xml` |
| Tecnologia | Hacker News | inglés (se traduce) | `https://hnrss.org/frontpage` |

Feeds que no existen o no sirven (comprobados el mismo día):

- **El Nacional.cat, RTVE y Público**: las direcciones de sus feeds de internacional y ciencia dan 404.
- **Le Monde diplomatique en español**: su feed no pone fecha a las noticias.

- **El País, Política**: no hay feed solo de política (las rutas `section/politica` y `section/espana/subsection/politica` dan 404 o vienen vacías). En su lugar va la sección España, que es sobre todo política.
- **Ara, tecnología**: no tiene feed de esa sección (`/rss/tecnologia/` y `/rss/ciencia-i-tecnologia/` dan 404).
- **La Directa**: solo publica el feed general; los de sus categorías vienen vacíos.
- **El Salto, internacional**: `/internacional/feed` viene vacío; su sección internacional se llama «Global» (`/global/feed`), por si se quiere añadir.

## Para añadir o corregir un medio

1. Comprueba que sus feeds responden y tienen noticias recientes (`uv run python -m panel_diario.probar_fuentes` con el medio en tu config.json) y añádelos a `feeds`.
2. Añádelo a `CATALOG` en `catalog/outlets.py`.
3. Actualiza las tablas de arriba con la fecha de la comprobación.
