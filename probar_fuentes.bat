@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
"%LOCALAPPDATA%\PanelDiario\venv\Scripts\python.exe" probar_fuentes.py
pause
