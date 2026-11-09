"""Estado del panel: el último dato bueno de cada sección, guardado en disco (caché).

actualizar() pide todas las fuentes en paralelo; la que falla conserva su dato anterior y su
error queda en estado.datos["errores"] para avisar en el pie del panel.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from panel_diario import VERSION
from panel_diario.config import CACHE, DATOS_DIR
from panel_diario.sources import agenda, avisos, comun, drawdown, ia, markets, noticias, sports, tiempo

log = logging.getLogger("panel")


class Estado:
    """Guarda los últimos datos buenos de cada sección y los persiste en disco."""

    def __init__(self) -> None:
        """Arranca con los datos de la caché, si la hay: así el panel muestra algo antes de actualizar."""
        self.lock = threading.Lock()
        self.datos: dict[str, Any] = {
            "secciones": {},
            "errores": {},
            "fuentes_caidas": [],
            "actualizado": None,
            "leidos": [],
            "ia_ts": 0,
            "ia_activa": False,
        }
        if CACHE.exists():
            try:
                self.datos.update(json.loads(CACHE.read_text(encoding="utf-8")))
            except Exception as ex:  # noqa: BLE001
                log.warning("Caché ilegible, se ignora: %s", ex)
        self.actualizando = False

    def guardar(self) -> None:
        with self.lock:
            CACHE.write_text(json.dumps(self.datos, ensure_ascii=False), encoding="utf-8")

    def instantanea(self) -> dict:
        """Copia de los datos para enviar a JavaScript (sin compartir el dict entre hilos)."""
        with self.lock:
            d = json.loads(json.dumps(self.datos))
        d["actualizando"] = self.actualizando
        d["version"] = VERSION
        return d


def actualizar(estado: Estado, cfg: dict, forzar_ia: bool = False) -> None:
    """Pide todas las fuentes en paralelo y guarda lo que llega; lo que falla conserva su dato anterior."""
    if estado.actualizando:
        return
    estado.actualizando = True
    log.info("Actualizando…")
    try:
        tareas = {
            "tiempo": lambda: tiempo.obtener_tiempo(cfg),
            "avisos": lambda: avisos.obtener_avisos(cfg),
            "noticias": lambda: noticias.obtener_noticias(cfg),
            "esports": lambda: sports.obtener_esports(cfg),
            "borsa": lambda: markets.obtener_borsa(cfg),
            "drawdown": lambda: drawdown.obtener_drawdown(cfg, DATOS_DIR / "drawdown.json"),
            "agenda": lambda: agenda.obtener_agenda(cfg),
        }
        resultados, errores = {}, {}
        hilos = []

        def correr(nombre: str, fn: Callable[[], Any]) -> None:
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
            titulares, caidas = resultados["noticias"]
            # Filtro con IA, como mucho cada N horas (y conservando el último resultado)
            cfg_ia = cfg.get("claude") or {}
            if (cfg_ia.get("api_key") or "").strip():
                toca = forzar_ia or time.time() - estado.datos.get("ia_ts", 0) > cfg_ia.get("cada_horas", 3) * 3600
                if toca:
                    try:
                        titulares = ia.filtrar_con_ia(cfg, titulares)
                        estado.datos["ia_ts"] = time.time()
                        estado.datos["ia_activa"] = True
                    except Exception as ex:  # noqa: BLE001
                        errores["ia"] = str(ex)[:200]
                        log.warning("Filtro IA falla: %s", ex)
                elif estado.datos.get("ia_activa"):
                    # Entre llamadas a la IA se mantiene su selección anterior
                    titulares = estado.datos["secciones"].get("noticias", titulares)
            resultados["noticias"] = titulares

        with estado.lock:
            estado.datos["secciones"].update(resultados)  # lo que falla conserva el dato anterior
            estado.datos["errores"] = errores
            estado.datos["fuentes_caidas"] = caidas
            estado.datos["actualizado"] = comun.ahora_local().strftime("%H:%M")
        estado.guardar()
        log.info("Actualizado. Errores: %s. Fuentes caídas: %d", list(errores), len(caidas))
    finally:
        estado.actualizando = False
