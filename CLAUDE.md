# Panel Diario
Widget de escritorio para Windows. Una píldora en el escritorio muestra el tiempo; al hacer clic despliega un panel con avisos meteorológicos, agenda (Google Calendar por iCal), caídas de un ETF desde su máximo con niveles de aportación extra en %, partidos de un equipo de fútbol y noticias por pestañas. Un asistente de configuración escribe config.json.

# Stack
- Python 3.12 + pywebview (3 ventanas: píldora ui/ficha.html, panel ui/index.html y asistente ui/asistente.html) + pystray (icono junto al reloj).
- Interfaz en HTML/CSS/JS sin framework; Python y JS se comunican con el puente js_api de pywebview.
- Datos: Open-Meteo (tiempo y geocodificación), MeteoAlarm, iCal, Yahoo Finance (no oficial), football-data.org, RSS y Google Noticias. Traducción con el traductor de Google (no oficial).
- uv (uv.lock), ruff, mypy, pytest, pre-commit y GitHub Actions (windows-latest).

# Estructura (src/panel_diario/)
- app.py: ventanas, puente con JS (Api, ApiFicha), bucle de actualización y arranque (main).
- config.py: rutas (CONFIG, EJEMPLO, DATOS_DIR), leer/guardar config.json, zona horaria.
- estado.py: último dato bueno de cada sección y caché; actualizar() pide las fuentes en paralelo.
- asistente.py: lógica del asistente (búsquedas, comprobaciones, construir_config) y ApiAsistente.
- bandeja.py: icono junto al reloj; recibe las acciones como funciones (sin depender de app.py).
- win32.py: todo lo que usa ctypes (monitores, anclar al escritorio, barra de tareas, errores).
- fuentes/: una fuente por módulo. comun.py tiene HTTP (comun.get), zona horaria (comun.TZ) y utilidades. Si una fuente falla, lanza excepción y estado.py conserva el último dato bueno. Si a una sección le falta su clave, devuelve {"sin_clave"/"sin_url"/"sin_configurar": True} y la interfaz la oculta.
- ui/ y demo.json (datos para --demo, con sus propias pestañas).
- Fuera del paquete: tests/ (un fichero por módulo), scripts/revisar_privacidad.py, docs/ (configuracion.md y capturas/).
- config.json (raíz): toda la configuración personal de quien usa el panel. No va a git. Plantilla pública: config.example.json. Copia anterior: config.json.bak.
- Datos en ejecución: %APPDATA%\PanelDiario (caché, posición, log).

# Comandos (en la raíz del proyecto)
- Instalar o reiniciar tras un cambio: instalar.bat (cierra la versión abierta y arranca la nueva).
- Ejecutar: uv run python -m panel_diario [--consola] [--demo] [--asistente]
- Tests: uv run pytest (red simulada, sin internet)
- Lint, formato y tipos: uv run ruff check · uv run ruff format · uv run mypy
- Revisión de privacidad: uv run python scripts/revisar_privacidad.py (también la lanzan pre-commit y CI)
- Comprobar fuentes reales: uv run python -m panel_diario.probar_fuentes

# Convenciones
- Commits pequeños (Conventional Commits) con ruff, mypy y tests en verde; pre-commit lo comprueba.
- Un fallo se reproduce primero con un test; un fallo que solo se ve con ventanas reales (pywebview) se prueba arrancando --demo y se anota en "Trampas conocidas".
- Un módulo por responsabilidad, con cabecera de 1-3 líneas (qué hace y cómo encaja); comentarios del porqué, separando bloques con títulos. Funciones con type hints.
- Las fuentes externas solo se llaman a través de comun.get, para que los tests las sustituyan en un sitio.
- Cada cambio visible: sube VERSION en src/panel_diario/__init__.py (se ve abajo del panel; pyproject.toml la lee de ahí).
- Capturas para el README: solo con --demo, recortando el rectángulo de cada ventana y revisándolas antes de guardarlas (que no salga nada de detrás).
- README: qué hace, capturas, arquitectura, decisiones y calidad; la referencia de config.json va en docs/configuracion.md. Actualizar los dos si cambia algo.

# Reglas del proyecto
- Una fuente caída nunca rompe el panel: se muestra el último dato bueno y un aviso en el pie.
- Textos de la interfaz en catalán. Noticias: las que están en catalán o castellano se dejan tal cual; las de otros idiomas (inglés...) se traducen al castellano. Comentarios y documentación en castellano. Código nuevo con nombres en inglés; no renombrar el código existente sin motivo.
- Fuentes RSS: verificar que responden antes de añadirlas. Las que están en catalán o castellano llevan "idioma": "ca" o "es" (así no pasan por el traductor). El asistente solo ofrece fuentes generales verificadas.
- Pestañas de noticias, nombre del equipo y textos de las secciones salen de config.json, no se fijan en el código.

# Privacidad (repositorio público)
- Nada personal en ningún fichero versionado ni en el historial de git: ni claves, ni URLs privadas, ni ubicación, ni importes, ni gustos, ni nombres, ni rutas de usuario. Este CLAUDE.md también es público.
- Lo personal vive solo en config.json, config.json.bak y .privado/ (en .gitignore).
- .privado/terminos.txt: lista local, un término por línea, de lo que nunca debe publicarse (los valores personales de config.json, tu nombre, tu usuario de git y de Windows...). scripts/revisar_privacidad.py la lee en cada commit (pre-commit) y bloquea el commit si encuentra algún término, algo con forma de clave o token o una dirección iCal secreta. En CI, sin esa lista, solo busca formas de claves.
- Si la revisión falla, no se salta: se deja el fichero genérico.
- config.example.json, demo.json, tests, README y capturas: solo valores genéricos de ejemplo (ciudad de ejemplo, eventos y noticias inventados).
- Commits con el email "noreply" de GitHub. Una clave que llegue a subirse hay que regenerarla: borrarla no basta.

# Trampas conocidas
- Win32: usar siempre _user32() (copia propia de user32, en win32.py). Declarar tipos en ctypes.windll.user32 rompe pywebview.
- pywebview publica en JS los atributos PÚBLICOS del objeto js_api: una ventana (webview.Window) como atributo público bloquea el puente de TODAS las ventanas. Guardarlas siempre como _ventana.
- pywebview impone 200x100 px de mínimo: pasar siempre min_size en create_window.
- Con la píldora anclada al escritorio (SetParent), FindWindowW ya no la encuentra: obtener el hwnd ANTES de anclarla (buscar_ventana).
- Al abrir el panel desde la píldora, el foco vuelve un instante a ella: por eso se ignora la pérdida de foco durante 1 s. El panel se oculta al perder el foco: al hacer capturas, no hacer clic en otra ventana antes de capturarlo.
- Un nombre de variable local igual que un módulo de fuentes/ (noticias, ia...) lo tapa: ruff lo avisa (F823/F821).
- uv: en algunos Windows los hardlinks desde la caché fallan ("operación de nube"); por eso link-mode = "copy" en pyproject.toml.
- mypy: el Control de aplicaciones de Windows (Smart App Control) puede bloquear sus DLL compiladas; por eso se instala en Python puro (no-binary-package).
- instalar.bat usa `uv sync --no-dev --inexact`: sin --inexact borraría las herramientas de desarrollo del .venv.
- La revisión de privacidad no busca hexadecimal en uv.lock (huellas públicas de PyPI); sus propios ejemplos se escriben por partes. Busca subcadenas: un término puede saltar dentro de otra palabra; entonces se cambia la frase.
- Los .bat necesitan CRLF (.gitattributes): con LF, cmd.exe puede fallar en los goto. Tras editarlos: git checkout del fichero para recuperar CRLF.
- astral-sh/setup-uv no publica etiquetas cortas (v10): fijar la versión completa en ci.yml.
