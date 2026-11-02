@echo off
rem Instala o actualiza el Panel Diario: entorno con uv, config.json la primera vez,
rem accesos directos (Inicio y Escritorio) y arranque. Si ya estaba abierto, lo reinicia.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PD=%~dp0"

echo.
echo === Panel Diario: instalacion ===
echo.

rem --- uv: instala Python y las dependencias con las versiones fijadas en uv.lock ---
where uv >nul 2>&1 && goto :uv_ok
echo No encuentro uv (el gestor de Python que usa el proyecto).
echo Instalalo abriendo una terminal y escribiendo:
echo     winget install astral-sh.uv
echo Luego cierra esta ventana y vuelve a ejecutar instalar.bat
pause
exit /b 1
:uv_ok

echo Preparando el entorno (la primera vez descarga Python y tarda un minuto)...
rem --no-dev: sin las herramientas de desarrollo. --inexact: si ya estan (quien programa), no las borra.
uv sync --locked --no-dev --inexact --quiet
if errorlevel 1 goto :error

rem --- Primera vez: crear config.json a partir de la plantilla y abrirlo para rellenarlo ---
rem config.json es personal y no va a git; config.example.json es la plantilla publica.
if exist "config.json" goto :config_ok
copy /y "config.example.json" "config.json" >nul
if errorlevel 1 goto :error
echo.
echo Se ha creado config.json. Se abre en el Bloc de notas: pon tu ciudad y coordenadas,
echo y las claves que quieras usar (las instrucciones estan en README.md).
echo Lo que dejes vacio simplemente no se muestra. Guarda y cierra el Bloc de notas para seguir.
notepad "config.json"
:config_ok

rem --- Cerrar una version anterior del panel si esta abierta (panel.py = versiones antiguas) ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and ($_.CommandLine -like '*panel_diario*' -or $_.CommandLine -like '*panel.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
timeout /t 2 /nobreak >nul

rem --- Accesos directos: Inicio (arranca con Windows) y Escritorio (para reabrirlo) ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; foreach($d in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Desktop'))){ $s=$w.CreateShortcut($d+'\Panel Diario.lnk'); $s.TargetPath=$env:PD+'.venv\Scripts\pythonw.exe'; $s.Arguments='-m panel_diario'; $s.WorkingDirectory=$env:PD; $s.Description='Panel Diario'; $s.Save() }"
if errorlevel 1 echo Aviso: no se pudieron crear los accesos directos.

echo.
echo Listo. Arrancando el panel:
echo  - Pildora con el tiempo arriba a la derecha del escritorio: clic para desplegar.
echo  - Arrastrala para moverla donde quieras.
echo  - Tambien: icono junto al reloj, o Ctrl+Alt+N.
start "" "%PD%.venv\Scripts\pythonw.exe" -m panel_diario
echo.
pause
exit /b 0

:error
echo.
echo Algo ha fallado. Copia el texto de arriba y pasaselo a Claude.
pause
exit /b 1
