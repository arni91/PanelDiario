"""
Panel Diario — arranque y ventanas.

Crea las tres ventanas de pywebview (la píldora del escritorio, el panel desplegado y el asistente
de configuración), el puente con su JavaScript (Api, ApiFicha; ApiAsistente está en asistente.py),
el icono de la bandeja y el bucle que actualiza los datos cada N minutos.

Uso (desde la raíz del proyecto, con el entorno de uv):
    uv run pythonw -m panel_diario          (normal, sin consola)
    uv run python -m panel_diario --demo    (datos de prueba, sin internet)
    uv run python -m panel_diario --consola (muestra el log en consola)
    uv run python -m panel_diario --asistente (abre el asistente de configuración al arrancar)
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
import webbrowser
from logging.handlers import RotatingFileHandler

import webview

from panel_diario import VERSION
from panel_diario.config import (
    CONFIG,
    DATOS_DIR,
    EJEMPLO,
    PAQUETE,
    POSICION,
    ConfigError,
    aplicar_zona_horaria,
    cargar_config,
    guardar_config,
)
from panel_diario.desktop.bandeja import iniciar_bandeja, refrescar_icono
from panel_diario.desktop.win32 import (
    anclar_al_escritorio,
    area_del_monitor,
    avisar_error,
    buscar_ventana,
    dentro_de_pantalla,
    escritorio_virtual,
    mover_hija,
    ocultar_de_barra_tareas,
    redondear_esquinas,
    tamano_pantalla,
    ya_en_marcha,
)
from panel_diario.sources import traduccion
from panel_diario.state import Estado, actualizar
from panel_diario.wizard.asistente import ApiAsistente

ANCHO = 440  # ancho del panel desplegado
ANCHO_FICHA = 176  # ficha en forma de píldora (icono + temperatura + máx/mín + lluvia)
ALTO_FICHA = 34
TITULO_PANEL = "Panel Diario"
TITULO_FICHA = "Panel Diario - ficha"
TITULO_ASISTENTE = "Panel Diario · Configuració"

log = logging.getLogger("panel")


def configurar_log(consola: bool) -> None:
    """Log en %APPDATA%\\PanelDiario\\panel.log (rota a los 500 KB) y, si se pide, también en consola."""
    log.setLevel(logging.INFO)
    fh = RotatingFileHandler(DATOS_DIR / "panel.log", maxBytes=500_000, backupCount=1, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)
    if consola:
        log.addHandler(logging.StreamHandler(sys.stdout))


# ---------------------------------------------------------------------------
# Puente con el JavaScript del panel (ui/panel/index.html)
# ---------------------------------------------------------------------------


class Api:
    """Puente con el JavaScript del panel desplegado (ui/panel/index.html): datos, abrir enlaces, mostrar y ocultar."""

    def __init__(self, estado: Estado, cfg: dict, icono_ref: dict) -> None:
        """La ventana y la píldora se asignan después, en main(), cuando ya existen."""
        self._estado = estado
        self._cfg = cfg
        self._icono_ref = icono_ref
        self._ventana: webview.Window | None = None
        self._ficha: ApiFicha | None = None  # para colocar el panel junto a ella
        self._alto = 860
        self._pos = [0, 0]  # posición actual del panel (la llevamos nosotros)
        self._visible = False
        self._oculto_en = 0.0
        self._mostrado_en = 0.0
        self._lock = threading.Lock()

    # --- llamadas desde JS ---
    def obtener(self) -> dict:
        d = self._estado.instantanea()
        d["pestanas"] = self._cfg.get("pestanas", [])  # nombre y orden de las pestañas de noticias
        return d

    def refrescar(self) -> bool:
        def tarea() -> None:
            actualizar(self._estado, self._cfg, True)
            refrescar_icono(self._estado, self._icono_ref)
            self._repintar()

        threading.Thread(target=tarea, daemon=True).start()
        return True

    def abrir(self, url: str) -> bool:
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            self.marcar_leido(url)
        return True

    def marcar_leido(self, url: str) -> bool:
        with self._estado.lock:
            leidos = self._estado.datos.setdefault("leidos", [])
            if url not in leidos:
                leidos.append(url)
                del leidos[:-600]
        return True

    def ocultar(self) -> bool:
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

    def ocultar_por_foco(self) -> bool:
        """El panel ha perdido el foco. Se ignora justo después de abrirlo: al abrirse
        desde la ficha, el foco puede volver un instante a la ficha y lo cerraría al momento."""
        if time.time() - self._mostrado_en < 1.0:
            log.info("Pérdida de foco ignorada (panel recién abierto)")
            return False
        return self.ocultar()

    def mover_rel(self, dx: float, dy: float) -> bool:
        """Arrastre: mueve el panel dx, dy desde donde está."""
        if not self._ventana:
            return False
        nueva = dentro_de_pantalla(self._pos[0] + int(dx), self._pos[1] + int(dy), ANCHO, self._alto)
        try:
            self._ventana.move(nueva[0], nueva[1])
            self._pos = nueva  # solo si el movimiento ha funcionado (si no, la posición se dispararía)
        except Exception as ex:  # noqa: BLE001
            log.warning("Error al mover el panel: %s", ex)
        return True

    # --- llamadas desde Python ---
    def _repintar(self) -> None:
        if self._visible and self._ventana:
            try:
                self._ventana.evaluate_js("window.alMostrar && window.alMostrar()")
            except Exception:  # noqa: BLE001
                pass

    def _colocar(self) -> None:
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
        if not self._ventana:
            return
        try:
            self._ventana.move(x, y)
        except Exception as ex:  # noqa: BLE001
            log.warning("No se pudo colocar el panel: %s", ex)

    def mostrar(self) -> None:
        """Coloca el panel junto a la píldora, lo enseña y repinta con los datos actuales."""
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

    def alternar(self) -> None:
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
# Puente con el JavaScript de la píldora (ui/pill/ficha.html)
# ---------------------------------------------------------------------------


class ApiFicha:
    """Puente con el JavaScript de la píldora (ui/pill/ficha.html): datos mínimos, clic y arrastre."""

    def __init__(self, estado: Estado, panel: Api, pos: list[int]) -> None:
        """`pos` es la posición inicial en pantalla (la guardada o la de por defecto)."""
        self._estado = estado
        self._panel = panel
        self._ventana: webview.Window | None = None
        self.pos = pos
        self.anclaje: tuple[int, int] | None = None  # (hwnd ficha, hwnd escritorio) si está anclada al escritorio
        self._guardar_tm: threading.Timer | None = None

    def mini(self) -> dict:
        """Lo poco que pinta la píldora: temperatura, icono, máx/mín, lluvia y si hay aviso."""
        t = self._estado.datos["secciones"].get("tiempo") or {}
        hoy = (t.get("dias") or [{}])[0]
        lista_avisos = self._estado.datos["secciones"].get("avisos") or []
        return {
            "temp": t.get("temp"),
            "icono": t.get("icono"),
            "texto": t.get("texto"),
            "codigo": t.get("codigo"),
            "es_dia": t.get("es_dia", True),
            "max": hoy.get("max"),
            "min": hoy.get("min"),
            "lluvia": t.get("lluvia_12h"),
            "lugar": t.get("lugar"),
            "aviso": lista_avisos[0]["nivel"] if lista_avisos else None,
        }

    def clic(self) -> bool:
        log.info("Clic en la ficha")
        try:
            self._panel.alternar()
        except Exception as ex:  # noqa: BLE001
            log.exception("Error al abrir el panel desde la ficha: %s", ex)
        return True

    def mover_rel(self, dx: float, dy: float) -> bool:
        """Arrastre: mueve la ficha dx, dy desde donde está y guarda la posición."""
        nueva = dentro_de_pantalla(self.pos[0] + int(dx), self.pos[1] + int(dy), ANCHO_FICHA, ALTO_FICHA)
        try:
            if self.anclaje:  # hija del escritorio: la movemos con Win32 directamente
                mover_hija(self.anclaje[0], self.anclaje[1], nueva)
            elif self._ventana:
                self._ventana.move(nueva[0], nueva[1])
            self.pos = nueva  # solo si el movimiento ha funcionado
        except Exception as ex:  # noqa: BLE001
            log.warning("Error al mover la ficha: %s", ex)
            return False
        if self._guardar_tm:
            self._guardar_tm.cancel()
        self._guardar_tm = threading.Timer(1.0, self._guardar_pos)
        self._guardar_tm.daemon = True
        self._guardar_tm.start()
        return True

    def _guardar_pos(self) -> None:
        try:
            POSICION.write_text(json.dumps({"x": self.pos[0], "y": self.pos[1]}), encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            log.info("No se pudo guardar la posición de la ficha: %s", ex)


def posicion_inicial_ficha() -> list[int]:
    """Posición guardada de la píldora si sigue dentro de algún monitor; si no, arriba a la derecha."""
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


# ---------------------------------------------------------------------------
# Bucle de actualización y arranque
# ---------------------------------------------------------------------------


def bucle_actualizacion(estado: Estado, cfg: dict, api: Api, icono_ref: dict, ficha: ApiFicha | None) -> None:
    minutos = max(10, int(cfg.get("actualizar_minutos", 30)))
    while True:
        actualizar(estado, cfg)
        refrescar_icono(estado, icono_ref)
        api._repintar()
        refrescar_ficha(ficha)
        estado.guardar()
        time.sleep(minutos * 60)


def refrescar_ficha(ficha: ApiFicha | None) -> None:
    if ficha and ficha._ventana:
        try:
            ficha._ventana.evaluate_js("window.pintar && window.pintar()")
        except Exception:  # noqa: BLE001
            pass


def registrar_atajo(cfg: dict, api: Api) -> None:
    atajo = cfg.get("atajo_teclado")
    if not atajo:
        return
    try:
        import keyboard

        keyboard.add_hotkey(atajo, api.alternar)
        log.info("Atajo %s registrado", atajo)
    except Exception as ex:  # noqa: BLE001
        log.warning("No se pudo registrar el atajo %s: %s", atajo, ex)


def main() -> None:
    """Arranca el panel: config, estado, las tres ventanas, la bandeja, el atajo y el bucle de actualización."""
    demo = "--demo" in sys.argv
    configurar_log("--consola" in sys.argv or demo)
    log.info("Arrancando Panel Diario %s (pywebview %s)", VERSION, getattr(webview, "__version__", "?"))
    if not demo and ya_en_marcha():
        log.info("El panel ya está en marcha; se cierra esta segunda copia.")
        return
    # La primera vez (sin config.json) se arranca con la plantilla y se abre el asistente
    primera_vez = not CONFIG.exists()
    try:
        cfg = cargar_config(EJEMPLO if primera_vez else CONFIG)
        aplicar_zona_horaria(cfg)
    except ConfigError as ex:
        log.error("%s", ex)
        avisar_error(str(ex))
        return
    cfg_ficha = cfg.get("ficha_escritorio") or {}
    estado = Estado()
    traduccion.configurar_memoria(DATOS_DIR / "traduccions.json")
    traduccion.configurar_pausa(DATOS_DIR / "traductor_pausa.json")

    if demo:
        datos_demo = json.loads((PAQUETE / "demo.json").read_text(encoding="utf-8"))
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
        TITULO_PANEL,
        url=str(PAQUETE / "ui" / "panel" / "index.html"),
        js_api=api,
        width=ANCHO,
        height=api._alto,
        x=sw - ANCHO - 12,
        y=24,
        frameless=True,
        on_top=True,
        resizable=False,
        hidden=True,
        background_color="#0f1419",
        easy_drag=False,
    )
    if ventana is None:
        raise RuntimeError("pywebview no ha podido crear la ventana del panel")
    api._ventana = ventana

    def al_cerrar() -> bool:
        api.ocultar()
        return False  # nunca se cierra: se oculta (para salir, usa el menú del icono junto al reloj)

    ventana.events.closing += al_cerrar

    # Asistente de configuración (oculto salvo la primera vez o con --asistente)
    def al_guardar(nueva: dict) -> None:
        """El asistente ha terminado: se guarda config.json y se aplica sin reiniciar."""
        if demo:
            log.info("Modo demo: la configuración del asistente no se guarda")
            return
        aplicar_zona_horaria(nueva)  # antes de guardar: si la zona no existe, no se escribe nada
        guardar_config(nueva)
        cfg.clear()
        cfg.update(nueva)  # es el mismo dict que usan el panel y el bucle: ven la config nueva
        api.refrescar()

    # En demo, el asistente parte de la plantilla pública: así sus capturas nunca enseñan claves personales
    api_asistente = ApiAsistente(cargar_config(EJEMPLO) if demo else cfg, al_guardar)
    ventana_asistente = webview.create_window(
        TITULO_ASISTENTE,
        url=str(PAQUETE / "ui" / "wizard" / "asistente.html"),
        js_api=api_asistente,
        width=640,
        height=760,
        min_size=(520, 560),
        hidden=not (primera_vez or "--asistente" in sys.argv),
        background_color="#0f1419",
    )
    if ventana_asistente is None:
        raise RuntimeError("pywebview no ha podido crear la ventana del asistente")
    api_asistente._ventana = ventana_asistente

    def al_cerrar_asistente() -> bool:
        ventana_asistente.hide()
        return False  # se oculta para poder reabrirlo desde la bandeja

    ventana_asistente.events.closing += al_cerrar_asistente

    # Ficha del escritorio
    ficha: ApiFicha | None = None
    if cfg_ficha.get("activa", True):
        # "escritorio" = a la altura de los iconos (detrás de las ventanas); "encima" = siempre visible
        modo = cfg_ficha.get("modo", "escritorio")
        nueva_ficha = ApiFicha(estado, api, posicion_inicial_ficha())
        ficha = api._ficha = nueva_ficha
        vf = webview.create_window(
            TITULO_FICHA,
            url=str(PAQUETE / "ui" / "pill" / "ficha.html"),
            js_api=ficha,
            width=ANCHO_FICHA,
            height=ALTO_FICHA,
            x=ficha.pos[0],
            y=ficha.pos[1],
            # Sin esto pywebview impone un mínimo de 200x100 px: era el motivo de que la ficha
            # saliera siempre grande (y ovalada al redondearla) hasta la v1.8.
            min_size=(ANCHO_FICHA, ALTO_FICHA),
            frameless=True,
            on_top=(modo == "encima"),
            resizable=False,
            background_color="#171e26",
            easy_drag=False,
        )
        if vf is None:
            raise RuntimeError("pywebview no ha podido crear la ventana de la ficha")
        nueva_ficha._ventana = vf
        vf.events.closing += lambda: False  # la ficha no se cierra con Alt+F4

        def al_mostrar_ficha() -> None:
            """Al aparecer la píldora: fuera de la barra de tareas, esquinas redondas y anclada al escritorio."""
            ocultar_de_barra_tareas(TITULO_FICHA, reaparecer=True)
            # Buscamos la ventana por su título AHORA: una vez anclada al escritorio deja de ser
            # una ventana "de primer nivel" y FindWindowW ya no la encuentra (fallo de la v1.7).
            hwnd = buscar_ventana(TITULO_FICHA)
            redondear_esquinas(hwnd, radio_css=ALTO_FICHA // 2, alto_css=ALTO_FICHA)  # extremos redondos
            if modo == "escritorio" and hwnd:
                nueva_ficha.anclaje = anclar_al_escritorio(hwnd, nueva_ficha.pos)

        vf.events.shown += al_mostrar_ficha

    def arranque() -> None:
        iniciar_bandeja(
            estado,
            icono_ref,
            abrir_panel=api.alternar,
            actualizar_ahora=api.refrescar,
            abrir_asistente=ventana_asistente.show,
        )
        registrar_atajo(cfg, api)
        if demo:
            api.mostrar()
        else:
            # Por si Windows lo hubiera mostrado al crearlo: el panel empieza recogido
            time.sleep(1.5)
            if not api._visible:
                api.ocultar()
            threading.Thread(target=bucle_actualizacion, args=(estado, cfg, api, icono_ref, ficha), daemon=True).start()

    webview.start(arranque, private_mode=True)
