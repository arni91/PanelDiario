# Panel Diario
Widget de escritorio para Windows. Una píldora en el escritorio muestra el tiempo; al hacer clic despliega un panel con avisos meteorológicos, agenda (Google Calendar por iCal), bolsa (índices y valores del día), precio de la luz por horas, calidad del aire y polen, las gasolineras más baratas cerca, opcionalmente las caídas de un ETF propio con niveles de aportación extra en %, próximos partidos y resultados de varios equipos y deportes, la Fórmula 1 y MotoGP y noticias por pestañas. Un asistente de configuración escribe config.json.

# Stack
- Python 3.12 + pywebview (3 ventanas: píldora ui/pill/, panel ui/panel/ y asistente ui/wizard/) + pystray (icono junto al reloj).
- Interfaz en HTML/CSS/JS sin framework; Python y JS se comunican con el puente js_api de pywebview.
- Datos: Open-Meteo (tiempo y geocodificación), MeteoAlarm, iCal, Yahoo Finance, ESPN y motogp.com (no oficiales, sin clave), Red Eléctrica (luz), Open-Meteo calidad del aire, Ministerio de Industria (carburantes), RSS y Google Noticias. Traducción con el traductor de Google (no oficial).
- uv (uv.lock), ruff, mypy, pytest, pre-commit y GitHub Actions (windows-latest).

# Estructura (src/panel_diario/)
- app.py: arranque (main), ventanas, puente con JS (Api, ApiFicha) y bucle de actualización.
- config.py: rutas (CONFIG, EJEMPLO, DATOS_DIR), leer/guardar config.json, zona horaria.
- state.py: último dato bueno de cada sección y caché; actualizar() pide las fuentes en paralelo.
- sources/ (back): una fuente de datos por módulo. comun.py tiene HTTP (comun.get), zona horaria (comun.TZ) y utilidades. Si una fuente falla, lanza excepción y state.py conserva el último dato bueno. Si a una sección le falta su clave, devuelve {"sin_clave"/"sin_url"/"sin_configurar": True} y la interfaz la oculta.
- catalog/ (datos públicos): markets.py (índices y listas de valores del día de Yahoo), sports.py (deportes del desplegable del asistente: de equipos, con sus competiciones de ESPN, y de motor), fuel.py (combustibles y provincias del Ministerio) y outlets.py, catálogo de medios (nombre, idioma, grupo y feed RSS de cada sección); de ahí salen config.example.json y el asistente. Cada titular muestra solo el nombre del medio.
- wizard/: asistente.py (pasos generales, construir_config y ApiAsistente) y un módulo por paso con lógica propia: news.py (medios y secciones), markets.py (bolsa), sports.py (deportes) y daily.py («El teu dia a dia»: luz, aire y gasolineras).
- desktop/ (Windows): bandeja.py (icono junto al reloj; recibe las acciones como funciones) y win32.py (todo lo que usa ctypes: monitores, anclar al escritorio, barra de tareas, errores).
- ui/ (front): una carpeta por ventana con su .html, .css y .js (panel/, pill/ = píldora, wizard/ = asistente); common/ para lo compartido.
- demo.json: datos para --demo, con sus propias pestañas. probar_fuentes.py: comprueba las fuentes reales de config.json.
- Fuera del paquete: tests/ (replica el árbol de src/: tests/sources/, tests/catalog/, tests/wizard/; test_ui.py comprueba los enlaces de cada página), scripts/revisar_privacidad.py, docs/ (configuracion.md, fonts.md y capturas/).
- config.json (raíz): toda la configuración personal de quien usa el panel. No va a git. Plantilla pública: config.example.json. Copia anterior: config.json.bak.
- Datos en ejecución: %APPDATA%\PanelDiario (caché, posición, log).

# Comandos (en la raíz del proyecto)
- Instalar o reiniciar tras un cambio: instalar.bat (cierra la versión abierta y arranca la nueva). Sin pausas, desde un script o una terminal: instalar.bat /silencioso
- Ejecutar: uv run python -m panel_diario [--consola] [--demo] [--asistente]
- Tests: uv run pytest (red simulada, sin internet)
- Lint, formato y tipos: uv run ruff check · uv run ruff format · uv run mypy
- Revisión de privacidad: uv run python scripts/revisar_privacidad.py (también la lanzan pre-commit y CI)
- Comprobar fuentes reales: uv run python -m panel_diario.probar_fuentes

# Convenciones
- main está protegida: cada cambio va en su rama (feat/…, fix/…, docs/…) y entra por Pull Request con CI en verde, fusionando con squash.
- Commits pequeños (Conventional Commits) con ruff, mypy y tests en verde; pre-commit lo comprueba.
- Un fallo se reproduce primero con un test; un fallo que solo se ve con ventanas reales (pywebview) se prueba arrancando --demo y se anota en "Trampas conocidas".
- Cada cosa en su carpeta: back en sources/, datos públicos en catalog/, front en ui/<ventana>/ (HTML, CSS y JS separados), Windows en desktop/; tests en la misma ruta bajo tests/.
- Un módulo por responsabilidad, con cabecera de 1-3 líneas (qué hace y cómo encaja); comentarios del porqué, separando bloques con títulos. Funciones con type hints.
- Las fuentes externas solo se llaman a través de comun.get, para que los tests las sustituyan en un sitio.
- Cada cambio visible: sube VERSION en src/panel_diario/__init__.py (se ve abajo del panel; pyproject.toml la lee de ahí).
- Capturas para el README: solo con --demo, recortando el rectángulo de cada ventana y revisándolas antes de guardarlas (que no salga nada de detrás).
- README: qué hace, capturas, arquitectura, decisiones y calidad; la referencia de config.json va en docs/configuracion.md. Actualizar los dos si cambia algo.

# Reglas del proyecto
- Una fuente caída nunca rompe el panel: se muestra el último dato bueno y un aviso en el pie.
- Textos de la interfaz en catalán. Noticias: cada una en su idioma; traducir al catalán es opcional (traduccio.activa, por defecto false).
- Fuentes RSS: verificar que responden, con fecha y noticias recientes, antes de añadirlas (docs/fonts.md lista las descartadas). El asistente ofrece el catálogo de catalog/outlets.py en dos pasos: medios (por grupo) y secciones; cada lista termina en «Un altre…» (entrada manual que se comprueba antes de guardar).
- Pestañas de noticias, equipos y textos de las secciones salen de config.json, no se fijan en el código.

# Privacidad (repositorio público)
- Nada personal en ningún fichero versionado ni en el historial de git: ni claves, ni URLs privadas, ni ubicación, ni importes, ni gustos, ni nombres, ni rutas de usuario. Este CLAUDE.md también es público.
- Lo personal vive solo en config.json, config.json.bak y .privado/ (en .gitignore).
- .privado/terminos.txt: lista local, un término por línea, de lo que nunca debe publicarse (los valores personales de config.json, tu nombre, tu usuario de git y de Windows...). scripts/revisar_privacidad.py la lee en cada commit (pre-commit) y bloquea el commit si encuentra algún término, algo con forma de clave o token o una dirección iCal secreta. En CI, sin esa lista, solo busca formas de claves.
- Si la revisión falla, no se salta: se deja el fichero genérico.
- config.example.json, demo.json, tests, README y capturas: solo valores genéricos de ejemplo (ciudad de ejemplo, eventos y noticias inventados).
- Commits con el email "noreply" de GitHub. Una clave que llegue a subirse hay que regenerarla: borrarla no basta.

# Trampas conocidas
- Win32: usar siempre _user32() (copia propia de user32, en desktop/win32.py). Declarar tipos en ctypes.windll.user32 rompe pywebview.
- pywebview publica en JS los atributos PÚBLICOS del objeto js_api: una ventana (webview.Window) como atributo público bloquea el puente de TODAS las ventanas. Guardarlas siempre como _ventana.
- pywebview impone 200x100 px de mínimo: pasar siempre min_size en create_window.
- pywebview no pone icono a las ventanas en Windows: app.py lo pone con WM_SETICON (win32.poner_icono) al mostrarse, con el hwnd de la propia ventana (hwnd_de: window.native.Handle). Buscarla por título falla si hay dos copias abiertas (--demo y la normal). El logo sale de scripts/generar_logo.py (ui/common/logo.png y logo.ico).
- Con la píldora anclada al escritorio (SetParent), FindWindowW ya no la encuentra: obtener el hwnd ANTES de anclarla (buscar_ventana).
- Al abrir el panel desde la píldora, el foco vuelve un instante a ella: por eso se ignora la pérdida de foco durante 1 s. El panel se oculta al perder el foco: al hacer capturas, no hacer clic en otra ventana antes de capturarlo.
- Un nombre de variable local igual que un módulo de sources/ (noticias, sports...) lo tapa: ruff lo avisa (F823/F821).
- uv: en algunos Windows los hardlinks desde la caché fallan ("operación de nube"); por eso link-mode = "copy" en pyproject.toml.
- mypy: el Control de aplicaciones de Windows (Smart App Control) puede bloquear sus DLL compiladas; por eso se instala en Python puro (no-binary-package).
- uv: tras mover o renombrar la carpeta del proyecto, los .exe de .venv\Scripts (mypy, pytest...) fallan con "uv trampoline failed to canonicalize script path": guardan la ruta antigua. Se arregla con `uv sync --reinstall`.
- instalar.bat usa `uv sync --no-dev --inexact`: sin --inexact borraría las herramientas de desarrollo del .venv.
- La revisión de privacidad no busca hexadecimal en uv.lock (huellas públicas de PyPI); sus propios ejemplos se escriben por partes. Busca subcadenas: un término puede saltar dentro de otra palabra; entonces se cambia la frase.
- Los .bat necesitan CRLF (.gitattributes): con LF, cmd.exe puede fallar en los goto. Tras editarlos: git checkout del fichero para recuperar CRLF.
- Las excepciones de requests llevan la URL completa en su texto: en la agenda (dirección iCal secreta) y el traductor se sustituyen por un motivo corto con `raise ... from None` antes de llegar al log, a cache.json o a la interfaz. Nunca loguear `str(ex)` de una petición con secretos en la URL.
- Traductor de Google (no oficial): pedir en lotes por translate_a/t (devuelve el idioma detectado de cada texto), de uno en uno y con memoria. Con muchas peticiones responde 429 con una página "Sorry... automated queries" y puede bloquear el cliente durante horas: por eso la pausa tras un 429 persistente se guarda en disco (hora real, no monotónica) y se dobla con cada bloqueo seguido. Las excepciones de requests llevan la URL con los textos: no loguearlas tal cual.
- astral-sh/setup-uv no publica etiquetas cortas (v10): fijar la versión completa en ci.yml.
