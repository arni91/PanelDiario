# AGENTS.md — Panel Diario
Widget de escritorio para Windows: una píldora con el tiempo que, al hacer clic, despliega un panel con avisos, agenda (iCal), planes cerca de casa (Cataluña), bolsa, ETF propio, luz, aire y polen, carburantes, deportes, F1/MotoGP y noticias por pestañas. Un asistente escribe config.json.
## Stack y estructura
- Python 3.12 + pywebview (ventanas píldora, panel y asistente) + pystray. Interfaz HTML/CSS/JS sin framework, unida a Python por el puente js_api. uv, ruff, mypy, pytest, pre-commit y GitHub Actions (windows-latest).
- `src/panel_diario/`: app.py (arranque, ventanas, puente y bucle), config.py, state.py (último dato bueno y caché), `sources/` (una fuente por módulo; red solo por `comun.get`), `catalog/` (datos públicos: medios, mercados, deportes, carburantes, interesos), `wizard/` (asistente, un módulo por paso), `desktop/` (Windows: bandeja y win32), `ui/<ventana>/` (.html, .css y .js separados; `common/` compartido), demo.json y probar_fuentes.py.
- `tests/` replica el árbol de `src/`. `docs/`: configuracion.md (referencia de config.json), fonts.md (RSS descartados), trampas.md y capturas/. Fuentes y decisiones de diseño: README.
- `docs/constitution.md` (principios) y `specs/NNN-nombre/` (`spec.md` = qué y por qué; `plan.md` = cómo; `tasks.md` = tareas).
## Comandos (en la raíz)
- Tests: `uv run python -m pytest` (red simulada, sin internet)
- Lint, formato y tipos: `uv run python -m ruff check` · `uv run python -m ruff format` · `uv run python -m mypy`
- Ejecutar: `uv run python -m panel_diario [--consola] [--demo] [--asistente]` · Instalar o reiniciar: `instalar.bat` (`/silencioso` sin pausas)
- Privacidad: `uv run python scripts/revisar_privacidad.py` · Fuentes reales: `uv run python -m panel_diario.probar_fuentes`
## Convenciones
- `main` protegida: rama por cambio (feat/, fix/, docs/…), Pull Request con CI en verde y squash. Conventional Commits en inglés, con el email noreply de GitHub.
- Un módulo por responsabilidad, con cabecera de 1-3 líneas; type hints; comentarios del porqué. Nombres nuevos en inglés; comentarios y docs en castellano.
- Cada cambio visible sube VERSION en `src/panel_diario/__init__.py`. Si cambia config.json o la arquitectura: README y docs/configuracion.md al día.
- Capturas solo con `--demo`, recortando cada ventana y revisándolas antes de guardarlas.
## Reglas de dominio / trampas conocidas
- Una fuente caída nunca rompe el panel: lanza excepción y state.py conserva el último dato bueno (aviso en el pie). Sin su clave, devuelve `{"sin_clave"/"sin_url"/"sin_configurar": True}` y la interfaz la oculta.
- Interfaz en catalán; noticias en su idioma (traducción opcional, `traduccio.activa`). Pestañas, equipos y textos salen de config.json, nunca fijos en el código.
- RSS: comprobar que responde con noticias recientes antes de añadirlo; los descartados, a docs/fonts.md.
- Privacidad (repositorio público): nada personal en git (claves, URLs iCal, ubicación, importes, gustos, nombres, rutas). Lo personal vive en config.json, config.json.bak y `.privado/`. La revisión de privacidad no se salta: se deja el fichero genérico. Ejemplos, demo, tests y capturas con datos inventados.
- **Lee `docs/trampas.md` antes de tocar pywebview, Win32, uv, .bat, el traductor o las peticiones con secretos en la URL.**
## Reglas: Spec-Driven Development (SDD)
- Lee `docs/constitution.md` y la spec activa (`specs/NNN-*/`) antes de tocar código. Si algo no está en la spec, no se implementa: se pregunta.
- Fases, con aprobación entre cada una: spec (requisitos en EARS) → clarificación → plan → tareas → implementación (una tarea cada vez: tests en rojo, código, tests en verde, marcar la tarea y parar) → validación de cada RF. Un cambio pequeño: plan rápido y, aprobado, se hace.
- Plantillas y detalle de cada fase: skill `sdd`. Skills en `.agents/skills/` (estándar) con copia idéntica en `.claude/skills/` (Claude Code); cambia las dos. Atajos para Claude Code: `/sdd-*`, `/feature` y agentes en `.claude/agents/`.
## Forma de trabajar
- Haz solo lo que se pide. "Plan" o "proponme" = solo proponer, sin tocar archivos.
- Cambios pequeños y enfocados; no reescribas lo que ya funciona. Un fallo se reproduce primero con un test; si solo se ve con ventanas reales, se prueba con `--demo` y se apunta en docs/trampas.md.
## Memoria
- Al empezar, lee `.privado/memoria.md` (fuera de git). Al terminar una tarea, actualízalo: estado, decisiones (con su porqué) y errores a evitar. Máximo ~50 líneas. Nunca datos sensibles.
## Límites
- ✅ Siempre: tests, ruff, mypy y revisión de privacidad en verde antes de cada commit; subir VERSION si el cambio se ve.
- ⚠️ Pregunta antes: dependencias nuevas, fuentes de datos nuevas, cambios en el formato de config.json o de cache.json.
- 🚫 Nunca: datos personales en ficheros versionados; saltarse pre-commit; editar `CLAUDE.md` (solo importa `@AGENTS.md`); loguear `str(ex)` de una petición con secretos en la URL.
## Verificación
- `uv run python -m pytest`, `uv run python -m ruff check`, `uv run python -m mypy` en verde y, si cambia la interfaz, arrancar `--demo` y comprobar la ventana afectada.
