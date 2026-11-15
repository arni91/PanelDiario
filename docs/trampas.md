# Trampas conocidas

Lo que es fácil hacer mal y no se deduce leyendo el código. Al encontrar una nueva (sobre todo las que solo se ven con ventanas reales de pywebview), se apunta aquí.

- Win32: usar siempre _user32() (copia propia de user32, en desktop/win32.py). Declarar tipos en ctypes.windll.user32 rompe pywebview.
- pywebview publica en JS los atributos PÚBLICOS del objeto js_api: una ventana (webview.Window) como atributo público bloquea el puente de TODAS las ventanas. Guardarlas siempre como _ventana.
- pywebview impone 200x100 px de mínimo: pasar siempre min_size en create_window.
- pywebview no pone icono a las ventanas en Windows: app.py lo pone con WM_SETICON (win32.poner_icono) al mostrarse, con el hwnd de la propia ventana (hwnd_de: window.native.Handle). Buscarla por título falla si hay dos copias abiertas (--demo y la normal). El logo sale de scripts/generar_logo.py (ui/common/logo.png y logo.ico).
- Con la píldora anclada al escritorio (SetParent), FindWindowW ya no la encuentra: obtener el hwnd ANTES de anclarla (buscar_ventana).
- Al abrir el panel desde la píldora, el foco vuelve un instante a ella: por eso se ignora la pérdida de foco durante 1 s. El panel se oculta al perder el foco: al hacer capturas, no hacer clic en otra ventana antes de capturarlo.
- Un nombre de variable local igual que un módulo de sources/ (noticias, sports...) lo tapa: ruff lo avisa (F823/F821).
- uv: en algunos Windows los hardlinks desde la caché fallan ("operación de nube"); por eso link-mode = "copy" en pyproject.toml.
- Smart App Control (Windows 11) bloquea lo que no está firmado, aunque antes lo dejara pasar ("bloqueado por la directiva de Device Guard" / os error 4551): el Python que descarga uv, los lanzadores que uv crea en .venv\Scripts (mypy.exe, pytest.exe...) y las DLL compiladas de mypy. Por eso: Python oficial de python.org (firmado), que instalar.bat prefiere (UV_PYTHON_PREFERENCE=system) y con el que rehace un .venv antiguo; herramientas siempre con `uv run python -m <herramienta>`; y mypy en Python puro (no-binary-package). El motivo exacto sale en el Visor de eventos: Microsoft-Windows-CodeIntegrity/Operational.
- uv: tras mover o renombrar la carpeta del proyecto, los .exe de .venv\Scripts (mypy, pytest...) fallan con "uv trampoline failed to canonicalize script path": guardan la ruta antigua. Se arregla con `uv sync --reinstall`.
- instalar.bat usa `uv sync --no-dev --inexact`: sin --inexact borraría las herramientas de desarrollo del .venv.
- La revisión de privacidad no busca hexadecimal en uv.lock (huellas públicas de PyPI); sus propios ejemplos se escriben por partes. Busca subcadenas: un término puede saltar dentro de otra palabra; entonces se cambia la frase.
- Los .bat necesitan CRLF (.gitattributes): con LF, cmd.exe puede fallar en los goto. Tras editarlos: git checkout del fichero para recuperar CRLF.
- Las excepciones de requests llevan la URL completa en su texto: en la agenda (dirección iCal secreta) y el traductor se sustituyen por un motivo corto con `raise ... from None` antes de llegar al log, a cache.json o a la interfaz. Nunca loguear `str(ex)` de una petición con secretos en la URL.
- Traductor de Google (no oficial): pedir en lotes por translate_a/t (devuelve el idioma detectado de cada texto), de uno en uno y con memoria. Con muchas peticiones responde 429 con una página "Sorry... automated queries" y puede bloquear el cliente durante horas: por eso la pausa tras un 429 persistente se guarda en disco (hora real, no monotónica) y se dobla con cada bloqueo seguido. Las excepciones de requests llevan la URL con los textos: no loguearlas tal cual.
- astral-sh/setup-uv no publica etiquetas cortas (v10): fijar la versión completa en ci.yml.
- El servidor de carburantes del Ministerio corta a veces la negociación TLS de Python (OpenSSL 3.5) cuando propone ECDHE (SSLEOFError o ConnectionReset); curl sí entra. Por eso carburants.py llama a comun.get con tls_compatible=True: un segundo intento con TLS 1.2 e intercambio RSA, solo para datos públicos.
