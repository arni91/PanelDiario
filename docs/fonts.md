# Medios del catálogo: feeds y orientación

El catálogo público de medios ([`outlets.py`](../src/panel_diario/outlets.py)) guarda, de cada medio, sus feeds RSS oficiales por sección y su orientación por defecto. De ahí salen la plantilla `config.example.json` y las opciones del asistente.

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

Feeds que no existen (comprobados el mismo día):

- **El País, Política**: no hay feed solo de política (las rutas `section/politica` y `section/espana/subsection/politica` dan 404 o vienen vacías). En su lugar va la sección España, que es sobre todo política.
- **Ara, tecnología**: no tiene feed de esa sección (`/rss/tecnologia/` y `/rss/ciencia-i-tecnologia/` dan 404).
- **La Directa**: solo publica el feed general; los de sus categorías vienen vacíos.
- **El Salto, internacional**: `/internacional/feed` viene vacío; su sección internacional se llama «Global» (`/global/feed`), por si se quiere añadir.

## Orientación de los medios

### Ejes

Cada titular lleva una etiqueta discreta con el nombre del medio y, si se conoce, su orientación en dos ejes:

| Campo | Valores |
|---|---|
| `ideologia` | `esquerra` · `centreesquerra` · `centre` · `centredreta` · `dreta` |
| `eix_nacional` | `independentista` · `sobiranista` · `no_independentista` · `unionista` |

Los valores por defecto están en el catálogo público ([`outlets.py`](../src/panel_diario/outlets.py)). Cada usuario puede cambiarlos en el asistente (paso «Orientació dels mitjans») o en `config.json` (ver [configuracion.md](configuracion.md)).

### Criterio

- **Una sola fuente verificable para todo el catálogo: [Media Bias/Fact Check](https://mediabiasfactcheck.com/) (MBFC).** Valora el sesgo de cada medio con una metodología publicada y fecha cada ficha. Su escala se traduce así: *Left* → `esquerra`, *Left-Center* → `centreesquerra`, *Least Biased* → `centre`, *Right-Center* → `centredreta`, *Right* → `dreta`.
- **Si un medio no tiene ficha en MBFC, su orientación se deja vacía.** No se completa con otras fuentes ni con impresiones.
- **El eje nacional se deja vacío en todos los medios.** Ninguno de los seis diarios declara su posición en sus páginas («Qui som», «Manifest fundacional», FAQ…). Las fuentes externas se contradicen: eurotopics califica al Ara de *separatista* y Wikipedia habla de «dret a l'autodeterminació».

### Valores del catálogo

Comprobados el 9 de noviembre de 2026.

| Medio | `ideologia` | Fuente | `eix_nacional` |
|---|---|---|---|
| El Salto | — | Sin ficha en MBFC | — |
| eldiario.es | `centreesquerra` | [MBFC: Left-Center](https://mediabiasfactcheck.com/eldiario-es/) (actualizada el 28-01-2025) | — |
| La Directa | — | Sin ficha en MBFC | — |
| Ara | — | Sin ficha en MBFC (la ficha `/ara/` corresponde a otro medio, Ara News) | — |
| La Vanguardia | `centreesquerra` | [MBFC: Left-Center](https://mediabiasfactcheck.com/la-vanguardia/) (actualizada el 09-02-2026) | — |
| El País | `centreesquerra` | [MBFC: Left-Center](https://mediabiasfactcheck.com/el-pais/) (actualizada el 03-01-2025) | — |
| El Crític | — | Sin ficha en MBFC | — |

### Fuentes consultadas y descartadas

- **Reuters Institute, Digital News Report** ([«Polarisation in the News Media», 2017](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/archive/survey/2017/polarisation-in-the-news-media-2017/index.html)): sitúa a la **audiencia** de cada medio según cómo se define políticamente, no la línea editorial. Además, los datos de España solo salen en una imagen y son de 2017.
- **Lo que dice cada medio de sí mismo**: ninguno se coloca en una escala izquierda-derecha. [El Salto](https://elsaltodiario.com/info/que-es-el-salto) y [La Directa](https://directa.cat/qui-som/) hablan de «transformación social», [eldiario.es](https://www.eldiario.es/faq/) de «valores sociales» y el [manifiesto del Ara](https://www.ara.cat/manifest_fundacional.html) no habla ni de ideología ni de soberanía.
- **Wikipedia y eurotopics**: algunas etiquetas no citan ninguna fuente (El Salto, La Vanguardia) y otras se contradicen con MBFC (La Vanguardia figura como «centre-right» en Wikipedia y como *Left-Center* en MBFC).

## Para añadir o corregir un medio

1. Comprueba que sus feeds responden y tienen noticias recientes (`uv run python -m panel_diario.probar_fuentes` con el medio en tu config.json) y añádelos a `feeds`.
2. Busca su ficha en MBFC. Si la tiene, apunta la valoración y la fecha de la ficha; si no, deja el campo vacío.
3. Añádelo a `CATALOG` en `outlets.py`, con sus alias tal como aparecen en Google Noticias.
4. Actualiza las tablas de arriba con el enlace y la fecha.
