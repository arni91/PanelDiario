# Orientación de los medios

Cada titular lleva una etiqueta discreta con el nombre del medio y, si se conoce, su orientación en dos ejes:

| Campo | Valores |
|---|---|
| `ideologia` | `esquerra` · `centreesquerra` · `centre` · `centredreta` · `dreta` |
| `eix_nacional` | `independentista` · `sobiranista` · `no_independentista` · `unionista` |

Los valores por defecto están en el catálogo público ([`outlets.py`](../src/panel_diario/outlets.py)). Cada usuario puede cambiarlos en el asistente (paso «Orientació dels mitjans») o en `config.json` (ver [configuracion.md](configuracion.md)).

## Criterio

- **Una sola fuente verificable para todo el catálogo: [Media Bias/Fact Check](https://mediabiasfactcheck.com/) (MBFC).** Valora el sesgo de cada medio con una metodología publicada y fecha cada ficha. Su escala se traduce así: *Left* → `esquerra`, *Left-Center* → `centreesquerra`, *Least Biased* → `centre`, *Right-Center* → `centredreta`, *Right* → `dreta`.
- **Si un medio no tiene ficha en MBFC, su orientación se deja vacía.** No se completa con otras fuentes ni con impresiones.
- **El eje nacional se deja vacío en todos los medios.** Ninguno de los seis diarios declara su posición en sus páginas («Qui som», «Manifest fundacional», FAQ…). Las fuentes externas se contradicen: eurotopics califica al Ara de *separatista* y Wikipedia habla de «dret a l'autodeterminació».

## Valores del catálogo

Comprobados el 9 de noviembre de 2026.

| Medio | `ideologia` | Fuente | `eix_nacional` |
|---|---|---|---|
| El Salto | — | Sin ficha en MBFC | — |
| eldiario.es | `centreesquerra` | [MBFC: Left-Center](https://mediabiasfactcheck.com/eldiario-es/) (actualizada el 28-01-2025) | — |
| La Directa | — | Sin ficha en MBFC | — |
| Ara | — | Sin ficha en MBFC (la ficha `/ara/` corresponde a otro medio, Ara News) | — |
| La Vanguardia | `centreesquerra` | [MBFC: Left-Center](https://mediabiasfactcheck.com/la-vanguardia/) (actualizada el 09-02-2026) | — |
| El País | `centreesquerra` | [MBFC: Left-Center](https://mediabiasfactcheck.com/el-pais/) (actualizada el 03-01-2025) | — |

## Fuentes consultadas y descartadas

- **Reuters Institute, Digital News Report** ([«Polarisation in the News Media», 2017](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/archive/survey/2017/polarisation-in-the-news-media-2017/index.html)): sitúa a la **audiencia** de cada medio según cómo se define políticamente, no la línea editorial. Además, los datos de España solo salen en una imagen y son de 2017.
- **Lo que dice cada medio de sí mismo**: ninguno se coloca en una escala izquierda-derecha. [El Salto](https://elsaltodiario.com/info/que-es-el-salto) y [La Directa](https://directa.cat/qui-som/) hablan de «transformación social», [eldiario.es](https://www.eldiario.es/faq/) de «valores sociales» y el [manifiesto del Ara](https://www.ara.cat/manifest_fundacional.html) no habla ni de ideología ni de soberanía.
- **Wikipedia y eurotopics**: algunas etiquetas no citan ninguna fuente (El Salto, La Vanguardia) y otras se contradicen con MBFC (La Vanguardia figura como «centre-right» en Wikipedia y como *Left-Center* en MBFC).

## Para añadir o corregir un medio

1. Busca su ficha en MBFC. Si la tiene, apunta la valoración y la fecha de la ficha; si no, deja el campo vacío.
2. Añádelo a `CATALOG` en `outlets.py`, con sus alias tal como aparecen en Google Noticias.
3. Actualiza la tabla de arriba con el enlace y la fecha.
