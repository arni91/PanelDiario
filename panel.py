"""
Panel Diario — widget de escritorio para Windows.

Una ficha pequeña en el escritorio muestra la temperatura; al hacer clic se
despliega el panel completo. También hay un icono junto al reloj (menú: actualizar,
configuración, salir).

Uso:
    pythonw panel.py          (normal, sin consola)
    python panel.py --demo    (datos de prueba, sin internet)
    python panel.py --consola (muestra el log en consola)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

import webview
from PIL import Image, ImageDraw, ImageFont

import datos

BASE = Path(__file__).resolve().parent
DATOS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PanelDiario"
DATOS_DIR.mkdir(parents=True, exist_ok=True)
CACHE = DATOS_DIR / "cache.json"
POSICION = DATOS_DIR / "posicion_widget.json"

VERSION = "2.9"
ANCHO = 440            # ancho del panel desplegado
ANCHO_FICHA = 176      # ficha en forma de píldora (icono + temperatura + máx/mín + lluvia)
ALTO_FICHA = 34
TITULO_PANEL = "Panel Diario"
TITULO_FICHA = "Panel Diario - ficha"

log = logging.getLogger("panel")


def configurar_log(consola: bool):
    log.setLevel(logging.INFO)
    fh = RotatingFileHandler(DATOS_DIR / "panel.log", maxBytes=500_000, backupCount=1, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)
    if consola:
        log.addHandler(logging.StreamHandler(sys.stdout))


class ConfigError(Exception):
    """config.json falta o no se puede leer: el panel no puede arrancar."""


def cargar_config(ruta: Path = BASE / "config.json") -> dict:
    if not ruta.exists():
        raise ConfigError("No trobo config.json. Executa instalar.bat: el crea a partir de config.example.json.")
    try:
        cfg = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        raise ConfigError(f"config.json està mal escrit (línia {ex.lineno}, columna {ex.colno}): {ex.msg}.\n"
                          "Revisa comes, cometes i claus en aquella línia.") from ex
    if not isinstance(cfg, dict):
        raise ConfigError("config.json ha de ser un objecte JSON ({ ... }).")
    return cfg


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
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                            ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

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


# ---------------------------------------------------------------------------
# Estado y actualización
# ---------------------------------------------------------------------------

class Estado:
    """Guarda los últimos datos buenos de cada sección y los persiste en disco."""

    def __init__(self):
        self.lock = threading.Lock()
        self.datos = {"secciones": {}, "errores": {}, "fuentes_caidas": [],
                      "actualizado": None, "leidos": [], "ia_ts": 0, "ia_activa": False}
        if CACHE.exists():
            try:
                self.datos.update(json.loads(CACHE.read_text(encoding="utf-8")))
            except Exception as ex:  # noqa: BLE001
                log.warning("Caché ilegible, se ignora: %s", ex)
        self.actualizando = False

    def guardar(self):
        with self.lock:
            CACHE.write_text(json.dumps(self.datos, ensure_ascii=False), encoding="utf-8")

    def instantanea(self) -> dict:
        with self.lock:
            d = json.loads(json.dumps(self.datos))
        d["actualizando"] = self.actualizando
        d["version"] = VERSION
        return d


def actualizar(estado: Estado, cfg: dict, forzar_ia: bool = False):
    if estado.actualizando:
        return
    estado.actualizando = True
    log.info("Actualizando…")
    try:
        tareas = {
            "tiempo": lambda: datos.obtener_tiempo(cfg),
            "avisos": lambda: datos.obtener_avisos(cfg),
            "noticias": lambda: datos.obtener_noticias(cfg),
            "futbol": lambda: datos.obtener_futbol(cfg),
            "drawdown": lambda: datos.obtener_drawdown(cfg, DATOS_DIR / "drawdown.json"),
            "agenda": lambda: datos.obtener_agenda(cfg),
        }
        resultados, errores = {}, {}
        hilos = []

        def correr(nombre, fn):
            try:
                resultados[nombre] = fn()
            except Exception as ex:  # noqa: BLE001
                errores[nombre] = str(ex)[:200]
                log.warning("Sección %s falla: %s", nombre, ex)

        for nombre, fn in tareas.items():
            h = threading.Thread(target=correr, args=(nombre, fn), daemon=True)
            h.start()
            hilos.append(h)
        for h in hilos:
            h.join(timeout=90)

        caidas = []
        if "noticias" in resultados:
            noticias, caidas = resultados["noticias"]
            # Filtro con IA, como mucho cada N horas (y conservando el último resultado)
            ia = cfg.get("claude") or {}
            if (ia.get("api_key") or "").strip():
                toca = forzar_ia or time.time() - estado.datos.get("ia_ts", 0) > ia.get("cada_horas", 3) * 3600
                if toca:
                    try:
                        noticias = datos.filtrar_con_ia(cfg, noticias)
                        estado.datos["ia_ts"] = time.time()
                        estado.datos["ia_activa"] = True
                    except Exception as ex:  # noqa: BLE001
                        errores["ia"] = str(ex)[:200]
                        log.warning("Filtro IA falla: %s", ex)
                elif estado.datos.get("ia_activa"):
                    # Entre llamadas a la IA se mantiene su selección anterior
                    noticias = estado.datos["secciones"].get("noticias", noticias)
            resultados["noticias"] = noticias

        with estado.lock:
            estado.datos["secciones"].update(resultados)  # lo que falla conserva el dato anterior
            estado.datos["errores"] = errores
            estado.datos["fuentes_caidas"] = caidas
            estado.datos["actualizado"] = datos.ahora_local().strftime("%H:%M")
        estado.guardar()
        log.info("Actualizado. Errores: %s. Fuentes caídas: %d", list(errores), len(caidas))
    finally:
        estado.actualizando = False


# ---------------------------------------------------------------------------
# Icono de la bandeja con la temperatura
# ---------------------------------------------------------------------------

def _fuente(tam: int):
    for nombre in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default(size=tam)


def icono_temperatura(temp) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 63, 63), radius=14, fill=(28, 74, 110, 255))
    texto = "--" if temp is None else f"{temp}°"
    tam = 34 if len(texto) <= 3 else 28
    f = _fuente(tam)
    caja = d.textbbox((0, 0), texto, font=f)
    w, h = caja[2] - caja[0], caja[3] - caja[1]
    d.text(((64 - w) / 2 - caja[0], (64 - h) / 2 - caja[1]), texto, font=f, fill="white")
    return img


# ---------------------------------------------------------------------------
# API del panel desplegado (JavaScript de ui/index.html)
# ---------------------------------------------------------------------------

class Api:
    def __init__(self, estado: Estado, cfg: dict, icono_ref: dict):
        self._estado = estado
        self._cfg = cfg
        self._icono_ref = icono_ref
        self._ventana = None
        self._ficha = None          # ApiFicha, para colocar el panel junto a ella
        self._alto = 860
        self._pos = [0, 0]          # posición actual del panel (la llevamos nosotros)
        self._visible = False
        self._oculto_en = 0.0
        self._mostrado_en = 0.0
        self._lock = threading.Lock()

    # --- llamadas desde JS ---
    def obtener(self):
        d = self._estado.instantanea()
        d["pestanas"] = self._cfg.get("pestanas", [])   # nombre y orden de las pestañas de noticias
        return d

    def refrescar(self):
        def tarea():
            actualizar(self._estado, self._cfg, True)
            refrescar_icono(self._estado, self._icono_ref)
            self._repintar()
        threading.Thread(target=tarea, daemon=True).start()
        return True

    def abrir(self, url):
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            self.marcar_leido(url)
        return True

    def marcar_leido(self, url):
        with self._estado.lock:
            leidos = self._estado.datos.setdefault("leidos", [])
            if url not in leidos:
                leidos.append(url)
                del leidos[:-600]
        return True

    def ocultar(self):
        # Se oculta siempre, aunque creamos que ya estaba oculto (si no, la ✕ podría no responder)
        if self._ventana:
            if self._visible:
                self._oculto_en = time.time()
            self._visible = False
            try:
                self._ventana.hide()
                log.info("Panel oculto")
            except Exception as ex:  # noqa: BLE001
                log.warning("Error al ocultar el panel: %s", ex)
        return True

    def ocultar_por_foco(self):
        """El panel ha perdido el foco. Se ignora justo después de abrirlo: al abrirse
        desde la ficha, el foco puede volver un instante a la ficha y lo cerraría al momento."""
        if time.time() - self._mostrado_en < 1.0:
            log.info("Pérdida de foco ignorada (panel recién abierto)")
            return False
        return self.ocultar()

    def mover_rel(self, dx, dy):
        """Arrastre: mueve el panel dx, dy desde donde está."""
        nueva = dentro_de_pantalla(self._pos[0] + int(dx), self._pos[1] + int(dy), ANCHO, self._alto)
        try:
            self._ventana.move(nueva[0], nueva[1])
            self._pos = nueva  # solo si el movimiento ha funcionado (si no, la posición se dispararía)
        except Exception as ex:  # noqa: BLE001
            log.warning("Error al mover el panel: %s", ex)
        return True

    # --- llamadas desde Python ---
    def _repintar(self):
        if self._visible and self._ventana:
            try:
                self._ventana.evaluate_js("window.alMostrar && window.alMostrar()")
            except Exception:  # noqa: BLE001
                pass

    def _colocar(self):
        """Sitúa el panel al lado de la ficha (o abajo a la derecha si no hay ficha)."""
        alto = self._alto
        if self._ficha and self._ficha.pos:
            fx, fy = self._ficha.pos
            # Monitor donde está la ficha (con dos pantallas, el panel se abre en la misma)
            mx, my, mw, mh = area_del_monitor(fx + ANCHO_FICHA // 2, fy + ALTO_FICHA // 2)
            # Alineado con el borde derecho de la píldora; debajo si está arriba, encima si está abajo
            x = fx + ANCHO_FICHA - ANCHO
            y = fy + ALTO_FICHA + 8 if fy + ALTO_FICHA / 2 < my + mh / 2 else fy - alto - 8
        else:
            mx, my, mw, mh = area_del_monitor(0, 0)
            x, y = mx + mw - ANCHO - 12, my + mh - alto - 12
        # Que no se salga de ese monitor
        x = min(max(int(x), mx), mx + max(mw - ANCHO, 0))
        y = min(max(int(y), my), my + max(mh - alto, 0))
        self._pos = [x, y]
        try:
            self._ventana.move(x, y)
        except Exception as ex:  # noqa: BLE001
            log.warning("No se pudo colocar el panel: %s", ex)

    def mostrar(self):
        if not self._ventana:
            log.warning("mostrar(): el panel aún no existe")
            return
        self._mostrado_en = time.time()
        self._visible = True
        self._colocar()
        try:
            self._ventana.show()
            log.info("Panel mostrado en %s", self._pos)
        except Exception as ex:  # noqa: BLE001
            log.warning("Error al mostrar el panel: %s", ex)
        self._repintar()

    def alternar(self):
        with self._lock:
            log.info("Abrir/cerrar panel (visible=%s)", self._visible)
            if self._visible:
                self.ocultar()
            elif time.time() - self._oculto_en < 0.4:
                # El mismo clic que ha quitado el foco al panel (y lo ha cerrado): no reabrir
                log.info("Recién cerrado por el mismo clic: no se reabre")
            else:
                self.mostrar()


# ---------------------------------------------------------------------------
# API de la ficha del escritorio (JavaScript de ui/ficha.html)
# ---------------------------------------------------------------------------

class ApiFicha:
    def __init__(self, estado: Estado, panel: Api, pos: list[int]):
        self._estado = estado
        self._panel = panel
        self._ventana = None
        self.pos = pos
        self.anclaje = None         # (hwnd ficha, hwnd escritorio) si está anclada al escritorio
        self._guardar_tm = None

    def mini(self):
        t = self._estado.datos["secciones"].get("tiempo") or {}
        hoy = (t.get("dias") or [{}])[0]
        avisos = self._estado.datos["secciones"].get("avisos") or []
        return {
            "temp": t.get("temp"), "icono": t.get("icono"), "texto": t.get("texto"),
            "codigo": t.get("codigo"), "es_dia": t.get("es_dia", True),
            "max": hoy.get("max"), "min": hoy.get("min"),
            "lluvia": t.get("lluvia_12h"), "lugar": t.get("lugar"),
            "aviso": avisos[0]["nivel"] if avisos else None,
        }

    def clic(self):
        log.info("Clic en la ficha")
        try:
            self._panel.alternar()
        except Exception as ex:  # noqa: BLE001
            log.exception("Error al abrir el panel desde la ficha: %s", ex)
        return True

    def mover_rel(self, dx, dy):
        """Arrastre: mueve la ficha dx, dy desde donde está y guarda la posición."""
        nueva = dentro_de_pantalla(self.pos[0] + int(dx), self.pos[1] + int(dy), ANCHO_FICHA, ALTO_FICHA)
        try:
            if self.anclaje:   # hija del escritorio: la movemos con Win32 directamente
                mover_hija(self.anclaje[0], self.anclaje[1], nueva)
            else:
                self._ventana.move(nueva[0], nueva[1])
            self.pos = nueva   # solo si el movimiento ha funcionado
        except Exception as ex:  # noqa: BLE001
            log.warning("Error al mover la ficha: %s", ex)
            return False
        if self._guardar_tm:
            self._guardar_tm.cancel()
        self._guardar_tm = threading.Timer(1.0, self._guardar_pos)
        self._guardar_tm.daemon = True
        self._guardar_tm.start()
        return True

    def _guardar_pos(self):
        try:
            POSICION.write_text(json.dumps({"x": self.pos[0], "y": self.pos[1]}), encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            log.info("No se pudo guardar la posición de la ficha: %s", ex)


def posicion_inicial_ficha() -> list[int]:
    sw, sh = tamano_pantalla()
    vx, vy, vw, vh = escritorio_virtual()
    try:
        p = json.loads(POSICION.read_text(encoding="utf-8"))
        x, y = int(p["x"]), int(p["y"])
        # Vale en cualquier monitor; si ya no existe (p. ej. desconectas una pantalla), vuelve al principal
        if vx <= x <= vx + vw - 40 and vy <= y <= vy + vh - 20:
            return [x, y]
    except Exception:  # noqa: BLE001
        pass
    return [sw - ANCHO_FICHA - 24, 24]  # arriba a la derecha del monitor principal


_U32 = None


def _user32():
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
        u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_uint]
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


def redondear_esquinas(hwnd, radio_css: int, alto_css: int):
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


def ocultar_de_barra_tareas(titulo: str, reaparecer: bool):
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
            user32.ShowWindow(hwnd, 0)   # SW_HIDE
            user32.ShowWindow(hwnd, 4)   # SW_SHOWNOACTIVATE (para que Windows aplique el cambio)
    except Exception as ex:  # noqa: BLE001
        log.info("No se pudo ocultar %s de la barra de tareas: %s", titulo, ex)


def _ventana_de_iconos_del_escritorio():
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

    def buscar(hwnd, _):
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            encontrada.append(hwnd)
            return False  # parar la búsqueda
        return True

    user32.EnumWindows(WNDENUMPROC(buscar), 0)
    return encontrada[0] if encontrada else user32.FindWindowW("Progman", None)


def mover_hija(hwnd, padre, pos: list[int]):
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


def anclar_al_escritorio(hwnd, pos: list[int]):
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


# ---------------------------------------------------------------------------
# Arranque
# ---------------------------------------------------------------------------

def bucle_actualizacion(estado, cfg, api, icono_ref, ficha):
    minutos = max(10, int(cfg.get("actualizar_minutos", 30)))
    while True:
        actualizar(estado, cfg)
        refrescar_icono(estado, icono_ref)
        api._repintar()
        refrescar_ficha(ficha)
        estado.guardar()
        time.sleep(minutos * 60)


def refrescar_ficha(ficha):
    if ficha and ficha._ventana:
        try:
            ficha._ventana.evaluate_js("window.pintar && window.pintar()")
        except Exception:  # noqa: BLE001
            pass


def refrescar_icono(estado, icono_ref):
    icono = icono_ref.get("icono")
    if not icono:
        return
    t = estado.datos["secciones"].get("tiempo")
    if t:
        icono.icon = icono_temperatura(t.get("temp"))
        icono.title = f"{t['lugar']}: {t['temp']}° · {t['texto']}"
    else:
        icono.icon = icono_temperatura(None)


def iniciar_bandeja(api, estado, cfg, icono_ref):
    """El icono se crea y se ejecuta en su propio hilo: en Windows, la ventana de
    mensajes del icono pertenece al hilo que la crea y debe seguir vivo."""
    import pystray

    def hilo():
        menu = pystray.Menu(
            pystray.MenuItem("Obre el panell", lambda: api.alternar(), default=True),
            pystray.MenuItem("Actualitza ara", lambda: api.refrescar()),
            pystray.MenuItem("Obre config.json", lambda: os.startfile(BASE / "config.json")),
            pystray.MenuItem("Surt", lambda icono: salir(icono)),
        )
        icono = pystray.Icon("PanelDiario", icono_temperatura(None), "Panel Diario", menu)
        icono_ref["icono"] = icono
        refrescar_icono(estado, icono_ref)
        icono.run()

    threading.Thread(target=hilo, daemon=True).start()


def ya_en_marcha() -> bool:
    """Evita dos copias si se arranca el panel otra vez estando ya abierto."""
    if os.name != "nt":
        return False
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, False, "PanelDiario_unica_instancia")
    return kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS


def salir(icono):
    try:
        icono.stop()
    finally:
        os._exit(0)


def registrar_atajo(cfg, api):
    atajo = cfg.get("atajo_teclado")
    if not atajo:
        return
    try:
        import keyboard
        keyboard.add_hotkey(atajo, api.alternar)
        log.info("Atajo %s registrado", atajo)
    except Exception as ex:  # noqa: BLE001
        log.warning("No se pudo registrar el atajo %s: %s", atajo, ex)


def main():
    demo = "--demo" in sys.argv
    configurar_log("--consola" in sys.argv or demo)
    log.info("Arrancando Panel Diario %s (pywebview %s)", VERSION, getattr(webview, "__version__", "?"))
    if not demo and ya_en_marcha():
        log.info("El panel ya está en marcha; se cierra esta segunda copia.")
        return
    try:
        cfg = cargar_config()
    except ConfigError as ex:
        log.error("%s", ex)
        avisar_error(str(ex))
        return
    cfg_ficha = cfg.get("ficha_escritorio") or {}
    estado = Estado()

    if demo:
        datos_demo = json.loads((BASE / "demo.json").read_text(encoding="utf-8"))
        # Las pestañas de la demo sustituyen a las de config.json solo en memoria: así la
        # demostración (y sus capturas) no depende de la configuración personal.
        cfg["pestanas"] = datos_demo.pop("pestanas")
        estado.datos.update(datos_demo)

    icono_ref: dict = {}
    api = Api(estado, cfg, icono_ref)
    sw, sh = tamano_pantalla()
    api._alto = min(860, sh - 90)

    # Panel desplegado (oculto hasta que se pulsa la ficha)
    ventana = webview.create_window(
        TITULO_PANEL, url=str(BASE / "ui" / "index.html"), js_api=api,
        width=ANCHO, height=api._alto, x=sw - ANCHO - 12, y=24, frameless=True, on_top=True,
        resizable=False, hidden=True, background_color="#0f1419", easy_drag=False,
    )
    api._ventana = ventana

    def al_cerrar():
        api.ocultar()
        return False  # nunca se cierra: se oculta (para salir, usa el menú del icono junto al reloj)

    ventana.events.closing += al_cerrar

    # Ficha del escritorio
    ficha = None
    if cfg_ficha.get("activa", True):
        # "escritorio" = a la altura de los iconos (detrás de las ventanas); "encima" = siempre visible
        modo = cfg_ficha.get("modo", "escritorio")
        ficha = ApiFicha(estado, api, posicion_inicial_ficha())
        api._ficha = ficha
        vf = webview.create_window(
            TITULO_FICHA, url=str(BASE / "ui" / "ficha.html"), js_api=ficha,
            width=ANCHO_FICHA, height=ALTO_FICHA, x=ficha.pos[0], y=ficha.pos[1],
            # Sin esto pywebview impone un mínimo de 200x100 px: era el motivo de que la ficha
            # saliera siempre grande (y ovalada al redondearla) hasta la v1.8.
            min_size=(ANCHO_FICHA, ALTO_FICHA),
            frameless=True, on_top=(modo == "encima"), resizable=False,
            background_color="#171e26", easy_drag=False,
        )
        ficha._ventana = vf
        vf.events.closing += lambda: False  # la ficha no se cierra con Alt+F4

        def al_mostrar_ficha():
            ocultar_de_barra_tareas(TITULO_FICHA, reaparecer=True)
            # Buscamos la ventana por su título AHORA: una vez anclada al escritorio deja de ser
            # una ventana "de primer nivel" y FindWindowW ya no la encuentra (fallo de la v1.7).
            hwnd = _user32().FindWindowW(None, TITULO_FICHA) if os.name == "nt" else None
            redondear_esquinas(hwnd, radio_css=ALTO_FICHA // 2, alto_css=ALTO_FICHA)  # extremos redondos
            if modo == "escritorio" and hwnd:
                ficha.anclaje = anclar_al_escritorio(hwnd, ficha.pos)

        vf.events.shown += al_mostrar_ficha

    def arranque():
        iniciar_bandeja(api, estado, cfg, icono_ref)
        registrar_atajo(cfg, api)
        if demo:
            api.mostrar()
        else:
            # Por si Windows lo hubiera mostrado al crearlo: el panel empieza recogido
            time.sleep(1.5)
            if not api._visible:
                api.ocultar()
            threading.Thread(target=bucle_actualizacion, args=(estado, cfg, api, icono_ref, ficha),
                             daemon=True).start()

    webview.start(arranque, private_mode=True)


if __name__ == "__main__":
    main()
