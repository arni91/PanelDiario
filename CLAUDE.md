# Panel Diario
Widget de escritorio para Windows. Una píldora en el escritorio muestra el tiempo; al hacer clic despliega un panel con avisos meteorológicos, agenda (Google Calendar por iCal), caídas de un ETF desde su máximo con niveles de aportación extra en %, partidos de un equipo de fútbol y noticias por pestañas. Un asistente de configuración escribe config.json. Repositorio público: github.com/arni91/panel-diario (portfolio: el README es el escaparate).

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
- config.json (raíz): TODA la configuración personal. NO va a git. Plantilla pública: config.example.json. Copia anterior: config.json.bak.
- Datos en ejecución: %APPDATA%\PanelDiario (caché, posición, log).

# Comandos (Git Bash, en la raíz)
- Instalar o reiniciar tras un cambio: cmd //c instalar.bat (cierra la versión abierta y arranca la nueva).
- Ejecutar: uv run python -m panel_diario [--consola] [--demo] [--asistente]
- Tests: uv run pytest (red simulada, sin internet)
- Lint, formato y tipos: uv run ruff check · uv run ruff format · uv run mypy
- Revisión de privacidad: uv run python scripts/revisar_privacidad.py (también la lanzan pre-commit y CI)
- Comprobar fuentes reales: uv run python -m panel_diario.probar_fuentes

# Forma de trabajar (buenas prácticas del proyecto)
- Antes de algo grande, plan breve y esperar OK; cambios pequeños, directo.
- Cada paso, un commit pequeño (Conventional Commits) con ruff, mypy y tests en verde; pre-commit lo comprueba solo. Push y CI en verde.
- Un fallo se reproduce primero con un test; un fallo que solo se ve con ventanas reales (pywebview) se prueba arrancando --demo y se anota en "Trampas conocidas".
- Un módulo por responsabilidad, con cabecera de 1-3 líneas (qué hace y cómo encaja); comentarios del porqué, separando bloques con títulos. Funciones con type hints.
- Las fuentes externas solo se llaman a través de comun.get, para que los tests las sustituyan en un sitio.
- Cada cambio visible: sube VERSION en src/panel_diario/__init__.py (se ve abajo del panel; pyproject.toml la lee de ahí).
- Capturas para el README: solo con --demo, recortando el rectángulo de cada ventana; revisarlas antes de guardarlas (que no salga nada de detrás).
- README = escaparate (qué hace, capturas, arquitectura, decisiones, calidad); la referencia de config.json va en docs/configuracion.md. Actualizar los dos si cambia algo.

# Reglas del proyecto
- Una fuente caída nunca rompe el panel: se muestra el último dato bueno y un aviso en el pie.
- Textos de la interfaz en catalán. Noticias: las que están en catalán o castellano se dejan tal cual; las de otros idiomas (inglés...) se traducen al castellano. Comentarios y documentación en castellano. Código nuevo con nombres en inglés; no renombrar el código existente sin motivo.
- Fuentes RSS: verificar que responden antes de añadirlas. Las que están en catalán o castellano llevan "idioma": "ca" o "es" (así no pasan por el traductor). El asistente solo ofrece fuentes generales verificadas.

# Privacidad (REPOSITORIO PÚBLICO) — revisar SIEMPRE
- Nada personal en ningún fichero versionado ni en el historial de git: ni claves, ni URLs privadas, ni ubicación, ni importes, ni gustos, ni nombres, ni rutas de usuario.
- Lo personal vive solo en config.json, config.json.bak y .privado/ (en .gitignore). Nunca escribas en este CLAUDE.md datos personales: es público.
- Lista de términos privados: .privado/terminos.txt. Si no existe, créala tú:
  1. Todos los valores de config.json que sean personales: claves, URLs de calendario, nombre del lugar y coordenadas, importes, ticker, equipo y términos de búsqueda propios.
  2. Mi nombre y usuario: `git config user.name`, `git config user.email` y el usuario de Windows (%USERNAME%).
  3. Enséñame la lista y pregúntame si quiero añadir algo más (nombres de personas, lugares, empresas).
- ANTES DE CADA COMMIT, sin excepción (el hook de pre-commit lo hace; si falla, no saltarlo):
  1. Buscar en los ficheros que se van a versionar todos los términos de .privado/terminos.txt (sin distinguir mayúsculas), cualquier cosa con forma de clave o token y las direcciones iCal secretas de Google Calendar.
  2. Comprobar que config.json y .privado/ NO están en `git status` para commit.
  3. Si aparece algo: NO hacer el commit, enseñarme dónde está y proponer cómo dejarlo genérico.
- config.example.json, demo.json, tests, README y capturas: solo valores genéricos de ejemplo (ciudad de ejemplo, importes redondos, eventos y noticias inventados).
- Pestañas de noticias, nombre del equipo y textos de las secciones: deben salir de config.json, no estar fijados en el código.
- Commits como arni91 con el email "noreply" de GitHub, no con el email personal.
- Si alguna vez una clave llega a subirse a GitHub, avisarme: no basta con borrarla, hay que regenerarla.

# Trampas conocidas
- Win32: usar siempre _user32() (copia propia de user32, en win32.py). Declarar tipos en ctypes.windll.user32 rompe pywebview.
- pywebview publica en JS los atributos PÚBLICOS del objeto js_api: una ventana (webview.Window) como atributo público bloquea el puente de TODAS las ventanas. Guardarlas siempre como _ventana.
- pywebview impone 200x100 px de mínimo: pasar siempre min_size en create_window.
- Con la píldora anclada al escritorio (SetParent), FindWindowW ya no la encuentra: obtener el hwnd ANTES de anclarla (buscar_ventana).
- Al abrir el panel desde la píldora, el foco vuelve un instante a ella: por eso se ignora la pérdida de foco durante 1 s. El panel se oculta al perder el foco: al hacer capturas, no hacer clic en otra ventana antes de capturarlo.
- Un nombre de variable local igual que un módulo de fuentes/ (noticias, ia...) lo tapa: ruff lo avisa (F823/F821).
- uv en este equipo: los hardlinks desde la caché fallan ("operación de nube"); por eso link-mode = "copy" en pyproject.toml.
- mypy: el Control de aplicaciones de Windows bloquea sus DLL compiladas; se instala en Python puro (no-binary-package).
- instalar.bat usa `uv sync --no-dev --inexact`: sin --inexact borraría las herramientas de desarrollo del .venv.
- La revisión de privacidad no busca hexadecimal en uv.lock (huellas públicas de PyPI); sus propios ejemplos se escriben por partes. Busca subcadenas: un término puede saltar dentro de otra palabra (p. ej. dentro de un adverbio); entonces se cambia la frase.
- Los .bat necesitan CRLF (.gitattributes): con LF, cmd.exe puede fallar en los goto. Tras editarlos: git checkout del fichero para recuperar CRLF.
- astral-sh/setup-uv no publica etiquetas cortas (v10): fijar la versión completa en ci.yml.
- En Git Bash, los heredoc con barras invertidas se estropean: para scripts con rutas de Windows o regex, escribir el fichero aparte.
