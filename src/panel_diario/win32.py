"""Llamadas a la API de Windows con ctypes: monitores, anclar la píldora al
escritorio, quitar ventanas de la barra de tareas, esquinas redondeadas y mensajes de error.

Trampa conocida: usar siempre _user32() (copia propia de user32). Declarar tipos en
ctypes.windll.user32 rompe pywebview, que comparte ese objeto.
"""

from __future__ import annotations

import ctypes
import logging
import os

import webview

log = logging.getLogger("panel")


def avisar_error(texto: str) -> None:
    """Ventana de error de Windows: el panel corre con pythonw, sin consola donde leer el log."""
    if os.name == "nt":
        MB_ICONERROR = 0x10
        _user32().MessageBoxW(None, texto, "Panel Diario", MB_ICONERROR)


def tamano_pantalla() -> tuple[int, int]:
    """Tamaño del monitor principal."""
    try:
        p = webview.screens[0]
        return int(p.width), int(p.height)
    except Exception:  # noqa: BLE001
        return 1920, 1080


def escritorio_virtual() -> tuple[int, int, int, int]:
    """(x, y, ancho, alto) del escritorio completo, con TODOS los monitores.

    Con dos pantallas, el escritorio de Windows es un único rectángulo que las incluye a las dos;
    un monitor a la izquierda del principal tiene coordenadas x negativas.
    """
    if os.name == "nt":
        try:
            u = _user32()
            # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN
            x, y, w, h = (u.GetSystemMetrics(i) for i in (76, 77, 78, 79))
            if w > 0 and h > 0:
                return x, y, w, h
        except Exception:  # noqa: BLE001
            pass
    sw, sh = tamano_pantalla()
    return 0, 0, sw, sh


def area_del_monitor(x: int, y: int) -> tuple[int, int, int, int]:
    """(x, y, ancho, alto) útil (sin barra de tareas) del monitor que contiene el punto x, y."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                """Estructura de Win32 que devuelve GetMonitorInfoW (rcWork = área sin barra de tareas)."""

                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                ]

            u = _user32()
            MONITOR_DEFAULTTONEAREST = 2
            monitor = u.MonitorFromPoint(wintypes.POINT(int(x), int(y)), MONITOR_DEFAULTTONEAREST)
            info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
            if monitor and u.GetMonitorInfoW(monitor, ctypes.byref(info)):
                r = info.rcWork
                return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:  # noqa: BLE001
            pass
    sw, sh = tamano_pantalla()
    return 0, 0, sw, sh - 40


_U32 = None


def _user32() -> ctypes.WinDLL:
    """Copia PROPIA de la librería user32 de Windows.

    Importante: no usar ctypes.windll.user32 para declarar tipos, porque es un objeto
    compartido con pywebview; cambiarle los tipos rompió su función de mover ventanas (v1.5).
    """
    global _U32
    if _U32 is None:
        import ctypes
        from ctypes import wintypes

        u = ctypes.WinDLL("user32", use_last_error=True)
        u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        u.FindWindowW.restype = wintypes.HWND
        u.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        u.FindWindowExW.restype = wintypes.HWND
        u.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
        u.SetParent.restype = wintypes.HWND
        u.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        u.SetWindowPos.restype = wintypes.BOOL
        u.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HANDLE, wintypes.BOOL]
        u.GetSystemMetrics.argtypes = [ctypes.c_int]
        u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        u.MonitorFromPoint.restype = wintypes.HANDLE
        u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_uint]
        _U32 = u
    return _U32


def redondear_esquinas(hwnd: int | None, radio_css: int, alto_css: int) -> None:
    """Recorta la ventana con esquinas redondeadas (las ventanas de Windows son rectangulares).

    La región se mide en píxeles reales, que con escalado (125 %, 150 %...) no coinciden
    con los de la página: por eso el radio se calcula en proporción al tamaño real.
    """
    if os.name != "nt" or not hwnd:
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = _user32()
        gdi32 = ctypes.WinDLL("gdi32")
        gdi32.CreateRoundRectRgn.argtypes = [ctypes.c_int] * 6
        gdi32.CreateRoundRectRgn.restype = wintypes.HANDLE
        r = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        ancho, alto = r.right - r.left, r.bottom - r.top
        diametro = max(2, round(2 * radio_css * alto / alto_css))
        region = gdi32.CreateRoundRectRgn(0, 0, ancho + 1, alto + 1, diametro, diametro)
        ok = user32.SetWindowRgn(hwnd, region, True)  # Windows se queda la región: no hay que liberarla
        log.info("Esquinas redondeadas: ventana %dx%d px reales, diámetro %d, ok=%s", ancho, alto, diametro, ok)
    except Exception as ex:  # noqa: BLE001
        log.warning("No se pudieron redondear las esquinas: %s", ex)


def dentro_de_pantalla(x: int, y: int, ancho: int, alto: int) -> list[int]:
    """Limita una posición para que la ventana no se salga del escritorio (todos los monitores)."""
    vx, vy, vw, vh = escritorio_virtual()
    return [min(max(x, vx), vx + max(vw - ancho, 0)), min(max(y, vy), vy + max(vh - min(alto, 120), 0))]


_YA_SIN_BARRA: set[str] = set()


def ocultar_de_barra_tareas(titulo: str, reaparecer: bool) -> None:
    """Quita la ventana de la barra de tareas y de Alt+Tab (es un widget, no una app).

    Solo se hace una vez por ventana. `reaparecer` = la ventana debe quedar visible
    (la ficha). El panel NUNCA se muestra desde aquí: eso lo decide la app.
    """
    if os.name != "nt" or titulo in _YA_SIN_BARRA:
        return
    _YA_SIN_BARRA.add(titulo)
    try:
        user32 = _user32()
        hwnd = user32.FindWindowW(None, titulo)
        if not hwnd:
            return
        GWL_EXSTYLE, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW = -20, 0x80, 0x40000
        estilo = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (estilo | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
        if reaparecer and user32.IsWindowVisible(hwnd):
            user32.ShowWindow(hwnd, 0)  # SW_HIDE
            user32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE (para que Windows aplique el cambio)
    except Exception as ex:  # noqa: BLE001
        log.info("No se pudo ocultar %s de la barra de tareas: %s", titulo, ex)


def _ventana_de_iconos_del_escritorio() -> int | None:
    """Devuelve la ventana de Windows que contiene los iconos del escritorio.

    Los iconos viven en una ventana "SHELLDLL_DefView" cuyo padre es "Progman" o un
    "WorkerW" (depende de la versión de Windows). Si la ficha se hace hija de ese padre,
    se comporta como un icono más: queda por debajo de todas las ventanas y sigue
    visible con Win+D ("mostrar escritorio").
    """
    import ctypes
    from ctypes import wintypes

    user32 = _user32()
    encontrada = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def buscar(hwnd: int, _: int) -> bool:
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            encontrada.append(hwnd)
            return False  # parar la búsqueda
        return True

    user32.EnumWindows(WNDENUMPROC(buscar), 0)
    return encontrada[0] if encontrada else user32.FindWindowW("Progman", None)


def mover_hija(hwnd: int, padre: int, pos: list[int]) -> None:
    """Coloca una ventana hija del escritorio en `pos` (coordenadas de pantalla)."""
    import ctypes
    from ctypes import wintypes

    user32 = _user32()
    # Las coordenadas de una ventana hija son relativas a su padre: convertimos desde pantalla
    punto = wintypes.POINT(pos[0], pos[1])
    user32.ScreenToClient(padre, ctypes.byref(punto))
    SWP_NOSIZE, SWP_NOZORDER, SWP_NOACTIVATE = 0x1, 0x4, 0x10
    if not user32.SetWindowPos(hwnd, None, punto.x, punto.y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE):
        raise OSError(f"SetWindowPos falló (error {ctypes.get_last_error()})")


def anclar_al_escritorio(hwnd: int, pos: list[int]) -> tuple[int, int] | None:
    """Convierte la ficha en parte del escritorio (a la altura de los iconos).
    Devuelve (hwnd ficha, hwnd escritorio) o None si no se ha podido."""
    if os.name != "nt":
        return None
    try:
        user32 = _user32()
        padre = _ventana_de_iconos_del_escritorio()
        if not hwnd or not padre:
            log.warning("Escritorio: no se encontró la ficha (%s) o el escritorio (%s)", hwnd, padre)
            return None
        user32.SetParent(hwnd, padre)
        mover_hija(hwnd, padre, pos)
        SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE, SWP_SHOWWINDOW = 0x2, 0x1, 0x10, 0x40
        # HWND_TOP (0): por encima de los iconos dentro del escritorio, no por encima de las ventanas
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        log.info("Ficha anclada al escritorio (padre %s)", padre)
        return (hwnd, padre)
    except Exception as ex:  # noqa: BLE001
        log.warning("No se pudo anclar la ficha al escritorio: %s", ex)
        return None


def buscar_ventana(titulo: str) -> int | None:
    """hwnd de la ventana de primer nivel con ese título (None si no existe o no es Windows)."""
    if os.name != "nt":
        return None
    return _user32().FindWindowW(None, titulo) or None


def ya_en_marcha() -> bool:
    """Evita dos copias si se arranca el panel otra vez estando ya abierto."""
    if os.name != "nt":
        return False
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, False, "PanelDiario_unica_instancia")
    return kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
