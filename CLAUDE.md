# Panel Diario
Widget de escritorio para Windows. Una píldora en el escritorio muestra el tiempo; al hacer clic despliega un panel con avisos meteorológicos, agenda (Google Calendar por iCal), caídas de un ETF desde su máximo con niveles de compra extra, partidos de un equipo de fútbol y noticias por pestañas.

# Stack
- Python 3.12 + pywebview (2 ventanas: píldora ui/ficha.html y panel ui/index.html) + pystray (icono junto al reloj).
- Interfaz en HTML/CSS/JS sin framework; Python y JS se comunican con el puente js_api de pywebview.
- Datos: Open-Meteo, MeteoAlarm, iCal, Yahoo Finance (no oficial), football-data.org, RSS y Google Noticias. Traducción con el traductor de Google (no oficial).

# Estructura
- datos.py: una función por fuente. Si falla, lanza excepción y panel.py conserva el último dato bueno.
- panel.py: ventanas, bandeja, atajo, arrastre multimonitor, anclaje al escritorio (Win32 con ctypes), bucle de actualización y caché.
- config.json: TODA la configuración personal. NO va a git. Plantilla pública: config.example.json.
- Datos en ejecución: %APPDATA%\PanelDiario (caché, posición, log).

# Comandos
- Instalar o reiniciar tras un cambio: instalar.bat (cierra la versión abierta y arranca la nueva).
- Ejecutar con log en consola: python panel.py --consola
- Interfaz con datos de prueba: python panel.py --demo
- Tests: python -m pytest tests (red simulada, sin internet)
- Comprobar fuentes reales: python probar_fuentes.py

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

# Plan de trabajo (borrar esta sección al terminarlo)
Hacerlo por fases y esperar mi OK entre fases. Cada paso: un commit (Conventional Commits) con los tests en verde y la revisión de privacidad hecha.

Fase 0 — Comprobaciones: HECHA. Pendiente: configurar en el repositorio, justo tras git init, user.name "arni91" y el email noreply (sale de `gh api user`: <id>+<login>@users.noreply.github.com).

Fase 1 — Limpiar lo personal (todavía SIN git)
1. Mover skill_probar/SKILL.md a .claude/skills/probar/SKILL.md.
2. .gitignore: config.json, .privado/, .env, .venv, __pycache__, *.log, .pytest_cache, .ruff_cache, .mypy_cache.
3. Sacar a config.json lo que hoy está fijado en el código: lista de pestañas con su nombre, nombre del equipo y valores por defecto del drawdown (los de datos.py son personales: cambiarlos por ejemplos). Formato nuevo, el mismo que escribirá el asistente de la Fase 4: la sección "barca" pasa a "futbol" y los niveles del drawdown se expresan en % extra sobre la aportación habitual, sin euros (p. ej. -10 % → +50 %, -20 % → +100 %, -30 % → +200 %, -40 % → toda la reserva).
4. Crear config.example.json genérico, con las claves vacías. Si falta config.json, el panel falla pronto con un mensaje claro e instalar.bat lo crea copiando la plantilla.
5. Hacer genéricos demo.json, los tests y la documentación. Ciudad de ejemplo que no sea la mía (ninguna de .privado/terminos.txt).
6. Credenciales para quien descargue el widget: si falta una clave, se oculta solo esa sección y el pie dice qué falta (el panel solo falla si config.json está mal escrito). instalar.bat abre config.json en el Bloc de notas la primera vez. Instrucciones por credencial en la documentación (iCal secreto, football-data y team_id, coordenadas) y qué funciona sin claves.
7. Hacer la revisión de privacidad de todos los ficheros. Enseñarme el resultado: tiene que salir limpio.

Fase 2 — Repositorio
1. git init (rama main), revisión de privacidad y primer commit "chore: estado inicial del Panel Diario".
2. Preguntarme la licencia (recomendada: MIT) y añadirla.
3. gh repo create panel-diario --public --source . --push

Fase 3 — Estándar
1. pyproject.toml con uv y dependencias fijadas (uv.lock), entorno en .venv. pytest, ruff, mypy y pre-commit como dependencias de desarrollo. Adaptar instalar.bat a uv.
2. Estructura src/panel_diario/ y tests/ (sin sys.path.insert).
3. ruff sin errores. Type hints y mypy sin errores (módulo a módulo).
4. pre-commit con ruff, mypy y un script que haga la revisión de privacidad (que lea .privado/terminos.txt y bloquee el commit si encuentra algo), para que se compruebe solo en cada commit.
5. GitHub Actions: lint, tipos y tests en cada push, en windows-latest (panel.py usa la API de Windows).
6. Actualizar README.md (ya existe; LEEME.md ya está borrado) con la instalación con uv. Capturas solo con --demo. Actualizar este CLAUDE.md.

Fase 4 — Asistente de primera configuración
Tercera ventana de pywebview (HTML) que pregunta y escribe config.json. Se abre sola si falta config.json y desde la bandeja ("Configura…"). Cada paso se puede saltar; si se salta, esa sección se oculta en el panel.
1. Tiempo: buscar la ciudad (geocodificación de Open-Meteo, sin clave) y elegir entre coincidencias; los avisos de MeteoAlarm salen del país.
2. Fútbol: clave de football-data → competición → equipo de una lista (nadie escribe un team_id).
3. Inversión (opcional): ETF de una lista de habituales o ticker propio; niveles en % sobre la aportación, editables. Sin importes.
4. Noticias: ámbitos (Món, Estat, comunidad) + temas (cultura, tecnologia, IA/robòtica, ciència, esports…) → una pestaña por elección con búsquedas de Google Noticias; "afegeix els teus mitjans" por RSS, verificando que responden antes de guardarlos. En el código solo un catálogo de medios generales; los gustos de cada uno van a su config.json.
5. Agenda: URL iCal secreta de Google Calendar, con instrucciones de dónde encontrarla.
6. Extras opcionales: clave de Claude para el filtro con IA.
Tests de la lógica (buscar lugar, crear pestañas, niveles en %) con la red simulada. Instalar.bat deja de abrir el Bloc de notas.

Al acabar cada fase: comandos ejecutados, resultado y, al final, el enlace del repositorio.