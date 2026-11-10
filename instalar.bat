@echo off
rem Instala o actualiza el Panel Diario: entorno con uv, accesos directos (Inicio y Escritorio)
rem y arranque. Si ya estaba abierto, lo reinicia. La primera vez se abre el asistente de configuracion.
rem Uso: instalar.bat [/silencioso]   (/silencioso: sin pausas, para lanzarlo desde otro programa)
setlocal
set "PAUSA=pause"
if /i "%~1"=="/silencioso" set "PAUSA=rem"
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
%PAUSA%
exit /b 1
:uv_ok

echo Preparando el entorno (la primera vez descarga Python y tarda un minuto)...
rem --no-dev: sin las herramientas de desarrollo. --inexact: si ya estan (quien programa), no las borra.
uv sync --locked --no-dev --inexact --quiet
if errorlevel 1 goto :error

rem --- La primera vez no hay config.json: el panel abre solo el asistente de configuracion,
rem que pregunta ciudad, agenda, equipo, ETF y noticias y escribe config.json (no va a git).

rem --- Cerrar una version anterior del panel si esta abierta (panel.py = versiones antiguas) y
rem esperar 2 s a que se cierre. Con PowerShell y no con timeout: timeout falla sin teclado.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and ($_.CommandLine -like '*panel_diario*' -or $_.CommandLine -like '*panel.py*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Start-Sleep -Seconds 2" >nul 2>&1

rem --- Accesos directos: Inicio (arranca con Windows) y Escritorio (para reabrirlo) ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; foreach($d in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Desktop'))){ $s=$w.CreateShortcut($d+'\Panel Diario.lnk'); $s.TargetPath=$env:PD+'.venv\Scripts\pythonw.exe'; $s.Arguments='-m panel_diario'; $s.WorkingDirectory=$env:PD; $s.Description='Panel Diario'; $s.IconLocation=$env:PD+'src\panel_diario\ui\common\logo.ico'; $s.Save() }"
if errorlevel 1 echo Aviso: no se pudieron crear los accesos directos.

echo.
echo Listo. Arrancando el panel:
echo  - Pildora con el tiempo arriba a la derecha del escritorio: clic para desplegar.
echo  - Arrastrala para moverla donde quieras.
echo  - Tambien: icono junto al reloj, o Ctrl+Alt+N. Para cambiar la configuracion: icono - Configura...
start "" "%PD%.venv\Scripts\pythonw.exe" -m panel_diario
echo.
%PAUSA%
exit /b 0

:error
echo.
echo Algo ha fallado. Copia el texto de arriba: indica que paso ha fallado y por que.
echo Si no sabes resolverlo, abre una incidencia (issue) en GitHub con ese texto.
%PAUSA%
exit /b 1
