# Constitución — Panel Diario

Principios innegociables. Toda spec, plan y tarea debe cumplirlos.

1. **Simplicidad primero**: Python 3.12 + pywebview, interfaz en HTML/CSS/JS sin framework y fuentes públicas sin clave siempre que se pueda. Se instala y arranca con `instalar.bat`; nada de servidores ni servicios en segundo plano aparte de la propia app.
2. **La spec manda**: nada se implementa si no está en la spec activa (`specs/NNN-*/`) o, en un cambio pequeño, en el plan aprobado. Si falta una decisión, se para y se pregunta.
3. **Lógica separada de interfaz**: cada fuente de datos vive en `sources/` y devuelve datos, no HTML; los datos públicos en `catalog/`; la interfaz en `ui/<ventana>/` y lo de Windows en `desktop/`. La red solo pasa por `comun.get` y la hora por `comun.TZ`, para poder sustituirlas en los tests.
4. **Tests como puerta**: `uv run python -m pytest` con red simulada, más ruff, mypy y la revisión de privacidad (pre-commit y CI). Un fallo se reproduce primero con un test. Prohibido avanzar con tests en rojo.
5. **Los datos del usuario son sagrados**: todo lo personal vive solo en `config.json` (y su copia `config.json.bak`), fuera de git. Una clave nueva en `config.json` tiene valor por defecto, para que un `config.json` antiguo siga funcionando. Una fuente caída nunca rompe el panel: se muestra el último dato bueno.
6. **Idioma**: código en inglés (nombres nuevos) y documentación en castellano; textos de la interfaz en catalán; noticias en su idioma.
