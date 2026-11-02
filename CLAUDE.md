# Panel Diario
Widget de escritorio para Windows. Una píldora en el escritorio muestra el tiempo; al hacer clic despliega un panel con avisos meteorológicos, agenda (Google Calendar por iCal), caídas de un ETF desde su máximo con niveles de compra extra, partidos de un equipo de fútbol y noticias por pestañas.

# Stack
- Python 3.12 + pywebview (2 ventanas: píldora ui/ficha.html y panel ui/index.html) + pystray (icono junto al reloj).
- Interfaz en HTML/CSS/JS sin framework; Python y JS se comunican con el puente js_api de pywebview.
- Datos: Open-Meteo, MeteoAlarm, iCal, Yahoo Finance (no oficial), football-data.org, RSS y Google Noticias. Traducción con el traductor de Google (no oficial).

# Estructura
- src/panel_diario/datos.py: una función por fuente. Si falla, lanza excepción y panel.py conserva el último dato bueno. Si a una sección le falta su clave, devuelve {"sin_clave"/"sin_url"/"sin_configurar": True} y la interfaz la oculta.
- src/panel_diario/panel.py: ventanas, bandeja, atajo, arrastre multimonitor, anclaje al escritorio (Win32 con ctypes), bucle de actualización y caché. Arranque: python -m panel_diario.
- src/panel_diario/ui/: ficha.html (píldora) e index.html (panel). demo.json: datos para --demo, con sus propias pestañas.
- config.json (raíz): TODA la configuración personal. NO va a git. Plantilla pública: config.example.json.
- scripts/revisar_privacidad.py: revisión de privacidad (pre-commit y CI).
- Datos en ejecución: %APPDATA%\PanelDiario (caché, posición, log).

# Comandos (Git Bash o terminal, en la raíz)
- Instalar o reiniciar tras un cambio: instalar.bat (en Git Bash: cmd //c instalar.bat). Cierra la versión abierta y arranca la nueva.
- Ejecutar con log en consola: uv run python -m panel_diario --consola
- Interfaz con datos de prueba: uv run python -m panel_diario --demo
- Tests: uv run pytest (red simulada, sin internet)
- Lint, formato y tipos: uv run ruff check · uv run ruff format · uv run mypy
- Revisión de privacidad: uv run python scripts/revisar_privacidad.py (también la lanza pre-commit)
- Comprobar fuentes reales: uv run python -m panel_diario.probar_fuentes

# Reglas del proyecto
- Una fuente caída nunca rompe el panel: se muestra el último dato bueno y un aviso en el pie.
- Textos de la interfaz en catalán. Noticias: las que están en catalán o castellano se dejan tal cual; las de otros idiomas (inglés...) se traducen al castellano. Comentarios y documentación en castellano. Código nuevo con nombres en inglés; no renombrar el código existente.
- Cada cambio visible: sube VERSION en panel.py (se ve abajo del panel).
- Fuentes RSS: verificar que responden antes de añadirlas. Las que están en catalán o castellano llevan "idioma": "ca" o "es" (así no pasan por el traductor).

# Privacidad (REPOSITORIO PÚBLICO) — revisar SIEMPRE
- Nada personal en ningún fichero versionado ni en el historial de git: ni claves, ni URLs privadas, ni ubicación, ni importes, ni gustos, ni nombres, ni rutas de usuario.
- Lo personal vive solo en config.json y en .privado/ (los dos en .gitignore). Nunca escribas en este CLAUDE.md datos personales: es público.
- Lista de términos privados: .privado/terminos.txt. Si no existe, créala tú:
  1. Todos los valores de config.json que sean personales: claves, URLs de calendario, nombre del lugar y coordenadas, importes, ticker, equipo y términos de búsqueda propios.
  2. Mi nombre y usuario: `git config user.name`, `git config user.email` y el usuario de Windows (%USERNAME%).
  3. Enséñame la lista y pregúntame si quiero añadir algo más (nombres de personas, lugares, empresas).
- ANTES DE CADA COMMIT, sin excepción:
  1. Buscar en los ficheros que se van a versionar todos los términos de .privado/terminos.txt (sin distinguir mayúsculas), cualquier cosa con forma de clave o token y las direcciones iCal secretas de Google Calendar.
  2. Comprobar que config.json y .privado/ NO están en `git status` para commit.
  3. Si aparece algo: NO hacer el commit, enseñarme dónde está y proponer cómo dejarlo genérico.
- config.example.json, demo.json, tests, README y capturas: solo valores genéricos de ejemplo (ciudad de ejemplo, importes redondos, eventos y noticias inventados).
- Pestañas de noticias, nombre del equipo y textos de las secciones: deben salir de config.json, no estar fijados en el código.
- Commits con el email "noreply" de GitHub, no con el email personal.
- Si alguna vez una clave llega a subirse a GitHub, avisarme: no basta con borrarla, hay que regenerarla.

# Trampas conocidas
- Win32: usar siempre _user32() (copia propia de user32). Declarar tipos en ctypes.windll.user32 rompe pywebview.
- pywebview impone 200x100 px de mínimo: pasar siempre min_size en create_window.
- Con la píldora anclada al escritorio (SetParent), FindWindowW ya no la encuentra: obtener el hwnd ANTES de anclarla.
- Al abrir el panel desde la píldora, el foco vuelve un instante a ella: por eso se ignora la pérdida de foco durante 1 s.
- uv en este equipo: los hardlinks desde la caché fallan ("operación de nube"); por eso link-mode = "copy" en pyproject.toml.
- mypy: el Control de aplicaciones de Windows bloquea sus DLL compiladas; se instala en Python puro (no-binary-package).
- instalar.bat usa `uv sync --no-dev --inexact`: sin --inexact borraría las herramientas de desarrollo del .venv.
- La revisión de privacidad no busca hexadecimal en uv.lock (huellas públicas de PyPI); sus propios ejemplos se escriben por partes.
- Los .bat necesitan CRLF (.gitattributes): con LF, cmd.exe puede fallar en los goto.
- astral-sh/setup-uv no publica etiquetas cortas (v10): fijar la versión completa en ci.yml.

# Plan de trabajo (borrar esta sección al terminarlo)
Hacerlo por fases y esperar mi OK entre fases. Cada paso: un commit (Conventional Commits) con los tests en verde y la revisión de privacidad hecha.

Fases 0 a 3 — HECHAS: limpieza de lo personal, repositorio público github.com/arni91/panel-diario (MIT, commits como arni91 con el email noreply), uv + src/, ruff, mypy, pre-commit y CI.

Fase 4 — Asistente de primera configuración
Tercera ventana de pywebview (HTML) que pregunta y escribe config.json. Se abre sola si falta config.json y desde la bandeja ("Configura…"). Cada paso se puede saltar; si se salta, esa sección se oculta en el panel.
1. Tiempo: buscar la ciudad (geocodificación de Open-Meteo, sin clave) y elegir entre coincidencias; los avisos de MeteoAlarm salen del país. La zona horaria también debe salir de ahí: hoy está fijada a Europe/Madrid en datos.py (TZ y la llamada a Open-Meteo).
2. Fútbol: clave de football-data → competición → equipo de una lista (nadie escribe un team_id).
3. Inversión (opcional): ETF de una lista de habituales o ticker propio; niveles en % sobre la aportación, editables. Sin importes.
4. Noticias: ámbitos (Món, Estat, comunidad) + temas (cultura, tecnologia, IA/robòtica, ciència, esports…) → una pestaña por elección con búsquedas de Google Noticias; "afegeix els teus mitjans" por RSS, verificando que responden antes de guardarlos. En el código solo un catálogo de medios generales; los gustos de cada uno van a su config.json.
5. Agenda: URL iCal secreta de Google Calendar, con instrucciones de dónde encontrarla.
6. Extras opcionales: clave de Claude para el filtro con IA.
Tests de la lógica (buscar lugar, crear pestañas, niveles en %) con la red simulada. Instalar.bat deja de abrir el Bloc de notas.

Al acabar cada fase: comandos ejecutados, resultado y, al final, el enlace del repositorio.