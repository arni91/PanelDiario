---
name: probar
description: Prueba el Panel Diario en este Windows y arregla lo que falle
disable-model-invocation: true
---
1. Si no existe .venv en la raíz del proyecto, ejecuta `cmd //c instalar.bat` primero.
2. Ejecuta `uv run python -m panel_diario.probar_fuentes` y anota qué falla.
3. Para cada fuente RSS caída: busca la URL actual del feed en la web del medio y actualiza config.json. Si el medio ya no tiene RSS, propónme una alternativa antes de cambiarlo.
4. Para fallos de tiempo, caídas del ETF, fútbol o agenda: mira el error, reprodúcelo con un test y corrige el módulo de src/panel_diario/fuentes/.
5. Arranca `uv run python -m panel_diario --consola` unos segundos y revisa que no haya errores en el log.
6. Arregla solo lo roto; no reescribas lo que funciona. ruff, mypy y pytest en verde antes del commit.
7. Resúmeme en pocas líneas qué fallaba y qué has cambiado.
