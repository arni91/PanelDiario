# Configuración (`config.json`)

Lo normal es configurar el panel con el **asistente** (se abre solo la primera vez; después, icono junto al reloj → **Configura…**). Esta página es la referencia para quien prefiera editar `config.json` a mano: icono junto al reloj → "Obre config.json". Después de cambiarlo, sal del panel y vuelve a abrirlo.

`config.json` vive en la raíz del proyecto y **no se sube a git** (está en `.gitignore`); la plantilla pública es `config.example.json`. Si está mal escrito (una coma de más, unas comillas sin cerrar), el panel no arranca y dice en qué línea está el error. Cada vez que el asistente guarda, deja una copia de la versión anterior en `config.json.bak`.

## Qué funciona sin claves

Tiempo, avisos meteorológicos, noticias, deportes, bolsa, el ETF propio, el precio de la luz, el aire y el polen y los carburantes funcionan sin ninguna clave. La agenda necesita su dirección iCal. Las secciones sin configurar no se muestran, y el pie del panel dice cuáles faltan.

## Ubicación y avisos

- `ubicacion`: `nombre` de tu ciudad, coordenadas (`lat`, `lon`) y `zona_horaria` (formato IANA, p. ej. `Europe/Madrid`).
- `avisos_meteo.zonas`: parte del nombre de tu zona tal como la publica MeteoAlarm (normalmente el de tu provincia). `zonas_excluir` descarta zonas que contengan esos textos. El `feed` termina en el país (`...-spain`, `...-france`…).

## Agenda (Google Calendar, Outlook, iCloud)

El asistente explica dónde está la dirección en cada calendario y la comprueba antes de guardarla. Se acepta `https://` y `webcal://` (iCloud), que se guarda como `https://`. La dirección es secreta: nunca se escribe en el log ni en los avisos del panel.

En Google Calendar, desde el ordenador: abre Google Calendar → ⚙ Configuración → en la izquierda, tu calendario → "Integrar el calendario" → copia la **"Dirección secreta en formato iCal"** (acaba en `.ics`). Pégala en `agenda.ical_urls`; puedes poner varias.

**Es privada**: quien la tenga puede ver tu calendario. No la compartas; si se filtra, regenérala en el mismo sitio.

## El teu dia a dia (`llum`, `aire`, `carburants`)

El asistente las pregunta en un mismo paso, con una casilla para cada una. Las tres vienen apagadas en la plantilla.

- `llum.activa`: el precio de la luz (PVPC, la tarifa regulada) de cada hora de hoy, en €/kWh: el de ahora, la media del día, la hora más barata y la más cara, y las tres más baratas. API pública de Red Eléctrica (apidatos.ree.es), sin clave. Precios de la península.
- `aire.activa`: la calidad del aire (índice europeo, de «Bona» a «Extremadament dolenta») y el polen de hoy en la ubicación del panel. API de calidad del aire de Open-Meteo, sin clave. El polen solo existe en Europa y en temporada; los niveles (baix, moderat, alt: menos de 10, de 10 a 50 y más de 50 granos/m³) son orientativos e iguales para todos los pólenes.
- `carburants`: precio medio de la gasolina 95, la gasolina 98 y el diésel entre las gasolineras de la provincia. `provincia` es el código de provincia del Ministerio (`08` Barcelona, `17` Girona…; lista en [`catalog/fuel.py`](../src/panel_diario/catalog/fuel.py)): el asistente la saca de la ciudad elegida y solo la pregunta si no la reconoce. API pública de precios de carburantes del Ministerio, sin clave, solo España.

## Plans (`plans`)

Exposiciones, conciertos, charlas, festivales y espectáculos de los próximos días en una ciudad de Cataluña, de la [Agenda Cultural de Catalunya](https://analisi.transparenciacatalunya.cat/d/rhpv-yr4f) (dades obertes de la Generalitat, sin clave). El panel tiene dos vistas: «Per a tu», con los planes que coinciden con los interesos, y «Tot», la agenda entera (primero lo que dura pocos días; las exposiciones largas, detrás).

- `activa`: mostrar la sección.
- `ciutat`: el municipio, como se escribe normalmente (`Barcelona`, `L'Hospitalet de Llobregat`…). El asistente pone la del tiempo si no se escribe otra: quien vive en un pueblo cercano suele querer los planes de la ciudad grande.
- `dies`: cuántos días hacia delante (7 por defecto).
- `interessos`: ids de [`catalog/interests.py`](../src/panel_diario/catalog/interests.py) (`lgtbi`, `electronica`, `performance`, `drag`, `feminisme`, `reivindicatiu`, `underground`, `art_contemporani`). Cada uno es una lista de palabras que se buscan en el título, el subtítulo, la descripción y las categorías del plan.
- `paraules`: palabras propias que también cuentan como interés (`["jazz", "cinema japonès"]`).

La Agenda la alimentan los equipamientos y los ayuntamientos: museos, centros de arte, teatros, salas de conciertos, ateneos… La escena de clubes casi no está.

## Esports (`esports`)

- `equips`: lista de equipos con `lliga` (ruta de ESPN de su competición, p. ej. `soccer/esp.1`), `id` (identificador de ESPN) y `nom`. En el asistente se elige el deporte en un desplegable y debajo salen **todos sus equipos** en una lista con buscador, sin elegir competición: se marca el equipo y ya está. La lista junta los equipos de todas las competiciones del deporte de [`catalog/sports.py`](../src/panel_diario/catalog/sports.py): fútbol (LaLiga, Hypermotion, Liga F, Premier, Serie A, Bundesliga, Ligue 1, Portugal, Países Bajos, Argentina, Brasil, México, MLS, Champions y Copa del Rey), baloncesto (NBA, WNBA), fútbol americano (NFL), hockey sobre hielo (NHL) y béisbol (MLB). Un equipo que juega varias competiciones sale una vez y se guarda con la primera de la lista (su liga).
- **Un altre…** (última opción del desplegable): se escribe el nombre de cualquier equipo, de cualquier deporte, y se busca en ESPN. Solo se ofrecen los que tienen partidos publicados; se guardan con su competición de ESPN (`lliga`, p. ej. `soccer/sco.1`) y su nombre (`competicio`).
- En fútbol se muestran todas las competiciones del equipo (liga, copa, Champions…); en los demás deportes, las de su liga. Próximos 3 partidos y el último resultado. Fuera de temporada (béisbol en invierno, por ejemplo) no hay partidos publicados.
- `f1` y `motogp`: `true` para seguir el campeonato: el próximo gran premio y el ganador del último.
- Equipos y F1: API pública de ESPN. MotoGP: API pública de resultados de motogp.com (ESPN no la tiene). Las dos son sin clave y no oficiales: si no responden, se muestra el último dato bueno.
- Descartados (comprobado el 10-11-2026): Euroliga y ACB (ESPN no publica sus partidos), voleibol (solo la liga universitaria de EE. UU.), rugbi (da los equipos, pero el calendario sale vacío), balonmano y tenis (no hay datos; el tenis, además, es de jugadores).

## Borsa (`borsa`)

- `indexs`: símbolos de Yahoo Finance de los índices o activos a seguir (IBEX 35 `^IBEX`, Euro Stoxx 50 `^STOXX50E`, S&P 500 `^GSPC`, Nasdaq `^IXIC`, oro, Brent, euro/dólar, bitcoin…; la lista del asistente está en [`catalog/markets.py`](../src/panel_diario/catalog/markets.py)). Cada uno muestra el precio y la variación respecto al cierre de la sesión anterior.
- `moviments`: listas de valores del día del mercado de EE. UU.: `day_gainers` (los que más suben), `day_losers` (los que más bajan), `most_actives` (los más negociados). Cinco valores por lista.
- Sin `borsa` (o con las dos listas vacías), la sección no se muestra. Yahoo Finance no es un servicio oficial: si un índice no responde se omite; si no responde ninguno, se muestra el último dato bueno.

## El teu ETF o acció, opcional (`drawdown`)

- `ticker`: símbolo del ETF o la acción en Yahoo Finance (p. ej. `VWCE.DE` para el Vanguard FTSE All-World o `EUNL.DE` para el MSCI World; el asistente ofrece los 10 más negociados). Vacío = sección oculta. `nombre`: cómo quieres que aparezca.
- `niveles`: a partir de qué caída (`caida`, en %) cuánto aportar de más ese mes, en % sobre tu aportación habitual (`extra_pct`; 100 = el doble). El último puede ser `"toda_la_reserva": true`. Por defecto: −10 % → +50 %, −20 % → +100 %, −30 % → +200 %, −40 % → toda la reserva. El widget no guarda importes.
- Caída = (precio actual − máximo histórico) / máximo histórico, con todos los cierres del ETF desde que cotiza. Si Yahoo no responde, se muestra el último dato guardado con un aviso.

## Noticias

El asistente lo escribe todo a partir de dos pasos: los medios (`medios_triats`) y las secciones. Cada sección (`portades`, `politica`, `economia`, `internacional`, `cultura`, `tecnologia`, `ciencia`, `esports`) es una pestaña con el feed de esa sección de cada medio elegido; el catálogo está en [fonts.md](fonts.md).

- `medios_triats`: los medios del catálogo elegidos en el asistente (aunque no publiquen ninguna de las secciones elegidas).
- `pestanas`: lista de pestañas con `id`, `nombre` y, para ver noticias de hasta un mes atrás con los botones "Aquesta setmana / Aquest mes", `"filtro_periodo": true`.
- `fuentes`: para cada `id` de pestaña, la lista de medios con `nombre` y `url` del RSS. Opcional: `idioma` (`"ca"`, `"es"`…: evita pasar por el traductor), `horas_max` (antigüedad máxima), `tema` (etiqueta), `requereix` (solo titulares con alguna de esas palabras).
- `tema1`, `tema2`…: temas propios, de Google Noticias.
- Un tema o un medio sin RSS: Google Noticias como fuente con `"agregador": true`, p. ej. `https://news.google.com/rss/search?q=robotica&hl=es&gl=ES&ceid=ES:es` o `...?q=site:ejemplo.com`.
- La misma noticia publicada por varios medios se muestra una vez, con la versión del primer medio de `prioridad_medios`, y "també a …" con los demás.
- `medios_excluidos`: medios que no quieres ver. `paraules_excloses`: por pestaña, descarta titulares con esas palabras.
- `traduccio`: `activa` (por defecto `false`: cada noticia sale en su idioma), `idioma` al que se traduce (por defecto `"ca"`) y `conservar`, los idiomas que se dejan tal cual (por defecto `["ca", "es"]`). El traductor detecta el idioma de cada titular que no lo tenga declarado en su fuente. Las traducciones se guardan en `%APPDATA%\PanelDiario\traduccions.json`; si el traductor responde 429 (demasiadas peticiones), se reintenta con espera y se hace una pausa (5 minutos, que se dobla con cada bloqueo seguido hasta 6 horas y vuelve a 5 minutos tras una traducción buena). La pausa se guarda en `traductor_pausa.json`, así que reiniciar el panel no la salta. Mientras tanto se muestra el texto original.
- Comprueba tus fuentes con **probar_fuentes.bat**.

## Otros

- `ficha_escritorio.modo`: `"escritorio"` deja la píldora a la altura de los iconos (detrás de las ventanas, visible con Win+D); `"encima"`, siempre por encima. `activa: false` la quita.
- `atajo_teclado`: atajo para abrir el panel. `actualizar_minutos`: cada cuánto se refrescan los datos (mínimo 10).
