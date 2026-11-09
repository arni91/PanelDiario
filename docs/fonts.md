# Catálogo de medios

El catálogo ([`catalog/outlets.py`](../src/panel_diario/catalog/outlets.py)) guarda, de cada medio, su idioma, su grupo y el feed RSS de cada sección que publica. El asistente ofrece los medios por grupo y después las secciones; cada sección del panel junta el feed de esa sección de cada medio elegido. **Portades** es la portada de cada medio: el panel agrupa la misma noticia publicada por varios medios y pone primero las que salen en más.

La selección busca variedad: medios de distintos países, idiomas y líneas editoriales, generalistas, temáticos y revistas. El panel no etiqueta ninguna orientación: cada titular lleva solo el nombre del medio.

## Medios y secciones

Comprobados el 9 de noviembre de 2026: cada feed responde, es RSS válido, sus noticias llevan fecha y la más reciente es de los últimos 3 días (14 en Cultura, Ciència y revistas, que publican menos).

### Catalunya

| Mitjà | Idioma | Seccions |
|---|---|---|
| Ara | català | Portades, Política, Economia, Internacional, Cultura, Esports |
| VilaWeb | català | Portades, Economia, Internacional, Cultura, Esports |
| El Nacional.cat | català | Portades |
| NacióDigital | català | Portades |
| La Vanguardia | castellà | totes |
| El Periódico | castellà | totes |
| Crónica Global | castellà | Portades |
| La Directa | català | Portades |
| El Crític | català | Portades |
| 3Cat Notícies | català | Portades |

### Espanya

| Mitjà | Idioma | Seccions |
|---|---|---|
| El País | castellà | totes |
| El Mundo | castellà | Portades, Política, Economia, Internacional, Cultura, Ciència |
| ABC | castellà | totes |
| La Razón | castellà | totes |
| eldiario.es | castellà | Portades, Política, Economia, Internacional, Cultura, Tecnologia, Ciència |
| El Confidencial | castellà | Portades, Economia, Internacional, Cultura, Tecnologia, Esports |
| El Español | castellà | Portades, Política, Economia |
| 20minutos | castellà | totes |
| Libertad Digital | castellà | Portades |
| El Salto | castellà | Portades, Política, Tecnologia |
| Europa Press | castellà | Portades, Internacional |

### Europa

| Mitjà | Idioma | Seccions |
|---|---|---|
| BBC News | anglès | totes |
| The Guardian | anglès | totes |
| Le Monde | francès | totes |
| Le Figaro | francès | Portades, Internacional |
| Politico Europe | anglès | Portades |
| Euronews | castellà | Portades |
| DW | castellà | Portades |

### Món

| Mitjà | Idioma | Seccions |
|---|---|---|
| The New York Times | anglès | Portades, Política, Economia, Internacional, Cultura, Tecnologia, Ciència |
| The Washington Post | anglès | Portades |
| Fox News | anglès | Portades, Internacional |
| Al Jazeera | anglès | Portades |
| BBC Mundo | castellà | Portades |
| France 24 | castellà | Portades |
| The Economist | anglès | Portades |
| Clarín | castellà | Portades |

### Economia, tecnologia, ciència i esports

| Mitjà | Idioma | Seccions |
|---|---|---|
| Cinco Días | castellà | Economia |
| Xataka | castellà | Tecnologia |
| Genbeta | castellà | Tecnologia |
| The Verge | anglès | Tecnologia |
| Wired | anglès | Tecnologia |
| Ars Technica | anglès | Tecnologia |
| TechCrunch | anglès | Tecnologia |
| Engadget | anglès | Tecnologia |
| MIT Technology Review | anglès | Tecnologia |
| Hacker News | anglès | Tecnologia |
| Nature | anglès | Ciència |
| Muy Interesante | castellà | Ciència |
| Mundo Deportivo | castellà | Esports |
| Marca | castellà | Esports |
| AS | castellà | Esports |

### Revistes

| Mitjà | Idioma | Seccions |
|---|---|---|
| Jot Down | castellà | Cultura |
| Sàpiens | català | Cultura |
| The Atlantic | anglès | Portades |
| The New Yorker | anglès | Cultura |
| Rolling Stone | anglès | Cultura |

## Medios que no están

Comprobados el mismo día; se pueden añadir con «Un altre…» si se encuentra un feed que funcione.

- **Sin RSS que funcione**: Público, Time Out, El Temps, CTXT, Agencia SINC, National Geographic España (403), elEconomista (403), New Scientist (406).
- **De pago o bloqueados**: The Telegraph (402), La Razón respondía 503 a sus antiguas direcciones (se usan las de `?outputType=xml`).
- **Abandonados** (la última noticia tiene meses o años): RTVE, CNN, The Wall Street Journal, Corriere della Sera.
- **Poco actualizados o vacíos**: Der Spiegel International, Expansión, Sport, L'Esportiu, las secciones de ciencia de El Confidencial y Ara, deportes de El Mundo y The New York Times, política de VilaWeb y El Nacional.

## Para añadir o corregir un medio

1. Comprueba que el feed responde y tiene noticias recientes (`uv run python -m panel_diario.probar_fuentes` con el medio en tu config.json).
2. Añádelo a `CATALOG` en `catalog/outlets.py`, con el feed de cada sección que publique.
3. Actualiza este documento con la fecha de la comprobación.
