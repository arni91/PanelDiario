@echo off
rem Comprueba una a una las fuentes de config.json y dice cuales responden.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
uv run --no-dev python -m panel_diario.probar_fuentes
pause
