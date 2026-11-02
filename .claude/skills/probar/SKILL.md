---
name: probar
description: Prueba el Panel Diario en este Windows y arregla lo que falle
disable-model-invocation: true
---
1. Si no existe %LOCALAPPDATA%\PanelDiario\venv, ejecuta instalar.bat primero.
2. Ejecuta probar_fuentes.py con el python del venv y anota qué falla.
3. Para cada fuente RSS caída: busca la URL actual del feed en la web del medio y actualiza config.json. Si el medio ya no tiene RSS, propónme una alternativa antes de cambiarlo.
4. Para fallos de tiempo, caídas del ETF, fútbol o agenda: mira el error, corrige datos.py y vuelve a probar.
5. Arranca panel.py --consola unos segundos y revisa que no haya errores en el log.
6. Arregla solo lo roto; no reescribas lo que funciona.
7. Resúmeme en pocas líneas qué fallaba y qué has cambiado.
