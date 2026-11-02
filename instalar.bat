@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PD=%~dp0"
rem El entorno de Python va fuera de OneDrive para que no sincronice miles de ficheros
set "VENV=%LOCALAPPDATA%\PanelDiario\venv"

echo.
echo === Panel Diario: instalacion ===
echo.

rem --- Buscar Python 3.11 a 3.13 ---
set "PY="
py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12" && goto :py_ok
py -3.13 -c "import sys" >nul 2>&1 && set "PY=py -3.13" && goto :py_ok
py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11" && goto :py_ok
python -c "import sys; sys.exit(0 if (3,11)<=sys.version_info[:2]<(3,14) else 1)" >nul 2>&1 && set "PY=python" && goto :py_ok

echo No encuentro Python 3.11, 3.12 o 3.13.
echo Instalalo abriendo una terminal y escribiendo:
echo     winget install Python.Python.3.12
echo Luego cierra esta ventana y vuelve a ejecutar instalar.bat
pause
exit /b 1

:py_ok
echo Python encontrado: %PY%

rem --- Entorno virtual y dependencias ---
if exist "%VENV%\Scripts\python.exe" goto :venv_ok
echo Creando entorno en %VENV% ...
%PY% -m venv "%VENV%"
if errorlevel 1 goto :error
:venv_ok

echo Instalando dependencias (puede tardar un minuto)...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt --quiet
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

rem --- Cerrar una version anterior del panel si esta abierta ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*panel.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
timeout /t 2 /nobreak >nul

rem --- Accesos directos: Inicio (arranca con Windows) y Escritorio (para reabrirlo) ---
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; foreach($d in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Desktop'))){ $s=$w.CreateShortcut($d+'\Panel Diario.lnk'); $s.TargetPath=$env:VENV+'\Scripts\pythonw.exe'; $s.Arguments=[char]34+$env:PD+'panel.py'+[char]34; $s.WorkingDirectory=$env:PD; $s.Description='Panel Diario'; $s.Save() }"
if errorlevel 1 echo Aviso: no se pudieron crear los accesos directos.

echo.
echo Listo. Arrancando el panel:
echo  - Ficha con la temperatura arriba a la derecha del escritorio: clic para desplegar.
echo  - Arrastrala por la franja de puntos de arriba para moverla donde quieras.
echo  - Tambien: icono junto al reloj, o Ctrl+Alt+N.
start "" "%VENV%\Scripts\pythonw.exe" "%PD%panel.py"
echo.
pause
exit /b 0

:error
echo.
echo Algo ha fallado. Copia el texto de arriba y pasaselo a Claude.
pause
exit /b 1
