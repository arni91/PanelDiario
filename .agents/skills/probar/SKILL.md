---
name: probar
description: Prueba el Panel Diario en este Windows y arregla lo que falle
disable-model-invocation: true
---
1. Si no existe .venv en la raíz del proyecto, ejecuta `cmd //c "instalar.bat /silencioso"` primero.
2. Ejecuta `uv run python -m panel_diario.probar_fuentes` y anota qué falla.
3. Para cada fuente RSS caída: busca la URL actual del feed en la web del medio y actualiza el catálogo de src/panel_diario/catalog/outlets.py (y el config.json de la instalación que se usa a diario, nunca el de la carpeta de desarrollo). Si el medio ya no tiene RSS, propón una alternativa antes de cambiarlo y apunta el descartado en docs/fonts.md.
4. Para fallos del resto de fuentes (tiempo, avisos, agenda, bolsa, deportes, luz, aire, carburantes, planes...): mira el error, reprodúcelo con un test y corrige el módulo de src/panel_diario/sources/.
5. Arranca `uv run python -m panel_diario --consola` unos segundos y revisa que no haya errores en el log.
6. Arregla solo lo roto; no reescribas lo que funciona. ruff, mypy y pytest en verde antes del commit.
7. Resume en pocas líneas qué fallaba y qué has cambiado.
