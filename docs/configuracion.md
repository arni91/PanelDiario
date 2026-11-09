# Configuración (`config.json`)

Lo normal es configurar el panel con el **asistente** (se abre solo la primera vez; después, icono junto al reloj → **Configura…**). Esta página es la referencia para quien prefiera editar `config.json` a mano: icono junto al reloj → "Obre config.json". Después de cambiarlo, sal del panel y vuelve a abrirlo.

`config.json` vive en la raíz del proyecto y **no se sube a git** (está en `.gitignore`); la plantilla pública es `config.example.json`. Si está mal escrito (una coma de más, unas comillas sin cerrar), el panel no arranca y dice en qué línea está el error. Cada vez que el asistente guarda, deja una copia de la versión anterior en `config.json.bak`.

## Qué funciona sin claves

Tiempo, avisos meteorológicos, noticias y caídas del ETF funcionan sin ninguna clave. Agenda y fútbol necesitan los datos de abajo. Las secciones sin configurar no se muestran, y el pie del panel dice cuáles faltan.

## Ubicación y avisos

- `ubicacion`: `nombre` de tu ciudad, coordenadas (`lat`, `lon`) y `zona_horaria` (formato IANA, p. ej. `Europe/Madrid`).
- `avisos_meteo.zonas`: parte del nombre de tu zona tal como la publica MeteoAlarm (normalmente el de tu provincia). `zonas_excluir` descarta zonas que contengan esos textos. El `feed` termina en el país (`...-spain`, `...-france`…).

## Agenda (Google Calendar)

En el ordenador, abre Google Calendar → ⚙ Configuración → en la izquierda, tu calendario → "Integrar el calendario" → copia la **"Dirección secreta en formato iCal"** (acaba en `.ics`). Pégala en `agenda.ical_urls`; puedes poner varias.

**Es privada**: quien la tenga puede ver tu calendario. No la compartas; si se filtra, regenérala en el mismo sitio.

## Fútbol

1. Clave gratuita en [football-data.org](https://www.football-data.org/client/register) → `futbol.football_data_api_key`.
2. `team_id`: el asistente te deja elegir el equipo de una lista. A mano: con la clave, abre `https://api.football-data.org/v4/competitions/PD/teams` (`PD` LaLiga, `PL` Premier, `SA` Serie A, `BL1` Bundesliga, `FL1` Ligue 1…).
3. `futbol.nombre`: el nombre que quieres ver.

El plan gratuito incluye las ligas principales y la Champions, pero no las copas nacionales.

## Caídas de un ETF (`drawdown`)

- `ticker`: símbolo del ETF en Yahoo Finance (p. ej. `VWCE.DE` para el Vanguard FTSE All-World o `EUNL.DE` para el MSCI World; el asistente ofrece los 10 más negociados). Vacío = sección oculta. `nombre`: cómo quieres que aparezca.
- `niveles`: a partir de qué caída (`caida`, en %) cuánto aportar de más ese mes, en % sobre tu aportación habitual (`extra_pct`; 100 = el doble). El último puede ser `"toda_la_reserva": true`. Por defecto: −10 % → +50 %, −20 % → +100 %, −30 % → +200 %, −40 % → toda la reserva. El widget no guarda importes.
- Caída = (precio actual − máximo histórico) / máximo histórico, con todos los cierres del ETF desde que cotiza. Si Yahoo no responde, se muestra el último dato guardado con un aviso.

## Noticias

- `pestanas`: lista de pestañas con `id`, `nombre` y, para ver noticias de hasta un mes atrás con los botones "Aquesta setmana / Aquest mes", `"filtro_periodo": true`.
- `fuentes`: para cada `id` de pestaña, la lista de medios con `nombre` y `url` del RSS. Opcional: `idioma` (`"ca"`, `"es"`…: evita pasar por el traductor), `ideologia` (`esquerra`, `centreesquerra`, `centre`, `centredreta`, `dreta`) y `eix_nacional` (`independentista`, `sobiranista`, `no_independentista`, `unionista`), que sustituyen a los del catálogo ([fonts.md](fonts.md)) y valen también para las noticias de ese medio que llegan por Google Noticias (`""` quita la del catálogo; un valor no válido se avisa en el log y se ignora), `horas_max` (antigüedad máxima), `tema` (etiqueta), `requereix` (solo titulares con alguna de esas palabras).
- Los feeds verificados de los diarios del catálogo (por pestaña: Món, Catalunya, Espanya, Mobilitzacions, Tecnologia) están en [fonts.md](fonts.md).
- Un tema o un medio sin RSS: Google Noticias como fuente con `"agregador": true`, p. ej. `https://news.google.com/rss/search?q=robotica&hl=es&gl=ES&ceid=ES:es` o `...?q=site:ejemplo.com`.
- La misma noticia publicada por varios medios se muestra una vez, con la versión del primer medio de `prioridad_medios`, y "també a …" con los demás.
- `medios_excluidos`: medios que no quieres ver. `paraules_excloses`: por pestaña, descarta titulares con esas palabras.
- `traduccio`: `activa`, `idioma` al que se traduce (por defecto `"ca"`) y `conservar`, los idiomas que se dejan tal cual (por defecto `["ca", "es"]`). El traductor detecta el idioma de cada titular que no lo tenga declarado en su fuente. Las traducciones se guardan en `%APPDATA%\PanelDiario\traduccions.json`; si el traductor responde 429 (demasiadas peticiones), se reintenta con espera, se hace una pausa de 5 minutos y mientras tanto se muestra el texto original.
- Comprueba tus fuentes con **probar_fuentes.bat**.

## Otros

- `ficha_escritorio.modo`: `"escritorio"` deja la píldora a la altura de los iconos (detrás de las ventanas, visible con Win+D); `"encima"`, siempre por encima. `activa: false` la quita.
- `atajo_teclado`: atajo para abrir el panel. `actualizar_minutos`: cada cuánto se refrescan los datos (mínimo 10).
- **Filtro con IA (opcional)**: con una clave de la API de Anthropic en `claude.api_key`, elige las noticias más relevantes y añade un resumen de una línea. Se ejecuta como mucho cada `cada_horas` horas.
