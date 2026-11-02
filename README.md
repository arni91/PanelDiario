# Panel Diario

Widget de escritorio para Windows. Una **píldora en el escritorio** muestra el tiempo de tu ciudad; al hacer clic se despliega un panel con:

- **Tiempo**: ahora, próximas 12 horas, 6 días y avisos meteorológicos oficiales (MeteoAlarm).
- **Agenda**: tus eventos de hoy y de la semana (Google Calendar).
- **Fútbol**: próximos partidos y último resultado del equipo que elijas.
- **Caídas de un ETF** desde su máximo histórico, con niveles de aportación extra en % (por ejemplo: si cae un 20 %, aporta un 100 % más ese mes).
- **Noticias por pestañas**, con los medios y temas que tú elijas. Cada titular dice de qué medio sale. Las noticias en catalán o castellano se muestran tal cual; las de otros idiomas se traducen al castellano.

Las secciones que no configures (por ejemplo, el fútbol sin clave) simplemente no se muestran.

## Uso

- **Clic en la píldora**: se despliega el panel. Otro clic, Esc o clic fuera: se recoge.
- **Mover la píldora**: mantén pulsado y arrástrala. Recuerda la posición (también con varios monitores).
- Un punto de color en la píldora indica que hay un aviso meteorológico (amarillo, naranja o rojo).
- También se abre con **Ctrl+Alt+N** o desde el icono junto al reloj.
- Para salir: clic derecho en el icono junto al reloj → **Surt**. Para volver a abrirlo: acceso directo "Panel Diario" del escritorio.

## Instalación

Requisitos: Windows 10 u 11 y Python 3.11–3.13 (si no lo tienes, `instalar.bat` te dice cómo instalarlo con una línea).

1. Descarga el proyecto (botón **Code → Download ZIP** en GitHub, o `git clone`).
2. Doble clic en **instalar.bat**.
3. La primera vez crea `config.json` a partir de `config.example.json` y lo abre en el Bloc de notas: rellénalo (ver abajo), guarda y cierra.
4. El panel arranca y, a partir de ahora, se abre solo al encender el PC.

Si cambias algún fichero, vuelve a ejecutar `instalar.bat`: cierra la versión abierta y arranca la nueva.

## Configuración (`config.json`)

Toda tu configuración personal vive en `config.json`, que **no se sube a git** (está en `.gitignore`). Se abre desde el icono junto al reloj → "Obre config.json". Después de cambiarlo, sal del panel y vuelve a abrirlo.

Si `config.json` está mal escrito (una coma de más, unas comillas sin cerrar), el panel no arranca y te dice en qué línea está el error.

### Qué funciona sin claves

Tiempo, avisos meteorológicos, noticias y caídas del ETF funcionan sin ninguna clave. Agenda y fútbol necesitan los datos de abajo.

### Ubicación

`ubicacion`: nombre de tu ciudad y sus coordenadas (`lat`, `lon`). Para saber las coordenadas: en Google Maps, clic derecho sobre tu ciudad → la primera línea son la latitud y la longitud.

`avisos_meteo.zonas`: parte del nombre de tu zona tal como la publica MeteoAlarm (por ejemplo, el nombre de tu provincia). `zonas_excluir` descarta zonas que contengan esos textos. El `feed` de ejemplo es el de España; para otros países, cambia `spain` por el país en la URL.

### Agenda (Google Calendar)

En el ordenador, abre Google Calendar → ⚙ Configuración → en la izquierda, tu calendario → "Integrar el calendario" → copia la **"Dirección secreta en formato iCal"** (acaba en `basic.ics`). Pégala entre comillas en `agenda.ical_urls`; puedes poner varias separadas por comas.

**Es privada**: quien la tenga puede ver tu calendario. No la compartas; si se filtra, regenérala en el mismo sitio.

### Fútbol

1. Pide una clave gratuita en [football-data.org](https://www.football-data.org/client/register) y ponla en `futbol.football_data_api_key`.
2. Busca el número de tu equipo (`team_id`): con la clave, abre `https://api.football-data.org/v4/competitions/PD/teams` (cambia `PD` por tu liga: `PL` Premier, `SA` Serie A, `BL1` Bundesliga, `FL1` Ligue 1…) o mira la URL del equipo en la web de football-data.
3. Pon el nombre que quieras ver en `futbol.nombre`.

El plan gratuito incluye las ligas principales y la Champions, pero no las copas nacionales.

### Caídas de un ETF (`drawdown`)

- `ticker`: el símbolo del ETF en Yahoo Finance (por ejemplo, `XXXX.DE` para Xetra en euros). Búscalo en finance.yahoo.com. Vacío = sección oculta.
- `nombre`: cómo quieres que aparezca.
- `niveles`: a partir de qué caída (`caida`, en %) cuánto aportar de más ese mes, en % sobre tu aportación habitual (`extra_pct`; 100 = el doble). El último puede ser `"toda_la_reserva": true`. Por defecto: −10 % → +50 %, −20 % → +100 %, −30 % → +200 %, −40 % → toda la reserva. El widget no guarda importes.
- Caída = (precio actual − máximo histórico) / máximo histórico, con todos los cierres del ETF desde que cotiza. Si Yahoo no responde, se muestra el último dato guardado con un aviso.

### Noticias

- `pestanas`: lista de pestañas con `id`, `nombre` y, si quieres ver noticias de hasta un mes atrás con los botones "Aquesta setmana / Aquest mes", `"filtro_periodo": true`.
- `fuentes`: para cada `id` de pestaña, la lista de medios con `nombre` y `url` del RSS. Opcional: `idioma` (`"ca"`, `"es"`…: evita pasar por el traductor), `horas_max` (antigüedad máxima), `tema` (etiqueta), `requereix` (solo titulares con alguna de esas palabras).
- Para buscar un tema o un medio sin RSS, usa Google Noticias como fuente con `"agregador": true`, por ejemplo `https://news.google.com/rss/search?q=robotica&hl=es&gl=ES&ceid=ES:es` o `...?q=site:ejemplo.com`.
- La misma noticia publicada por varios medios se muestra una vez, con la versión del primer medio de `prioridad_medios`, y "també a …" con los demás.
- `medios_excluidos`: medios que no quieres ver. `paraules_excloses`: por pestaña, descarta titulares con esas palabras.
- `traduccio`: `idioma` al que se traduce y `conservar`, los idiomas que se dejan tal cual.
- Comprueba tus fuentes con **probar_fuentes.bat**.

### Otros

- `ficha_escritorio.modo`: `"escritorio"` deja la píldora a la altura de los iconos (detrás de las ventanas, visible con Win+D); `"encima"`, siempre por encima. `activa: false` la quita.
- `atajo_teclado`: atajo para abrir el panel.
- **Filtro con IA (opcional)**: con una clave de la API de Anthropic en `claude.api_key`, elige las noticias más relevantes y añade un resumen de una línea. Se ejecuta como mucho cada `cada_horas` horas.

## Ejecutar y probar

Con el entorno que crea `instalar.bat` (`%LOCALAPPDATA%\PanelDiario\venv`):

- Con el log en la consola: `python panel.py --consola`
- Con datos de demostración, sin internet ni configuración: `python panel.py --demo`
- Tests (sin internet, la red se simula): `python -m pytest tests`
- Comprobar las fuentes reales: `python probar_fuentes.py`

## Si algo falla

- **probar_fuentes.bat** dice qué fuente responde y cuál no.
- Las fuentes caídas aparecen abajo en el panel (pasa el ratón por encima para ver el detalle).
- Log: `%APPDATA%\PanelDiario\panel.log`.

## Fuentes de datos

Open-Meteo, MeteoAlarm, Google Calendar (iCal), medios por RSS y Google Noticias, football-data.org, Yahoo Finance (no oficial: puede fallar puntualmente) y el traductor de Google (no oficial).

## Licencia

[MIT](LICENSE)
