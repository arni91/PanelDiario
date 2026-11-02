"""Icono junto al reloj (bandeja del sistema): muestra la temperatura y tiene el menú del panel."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from panel_diario.config import CONFIG
from panel_diario.estado import Estado


def _fuente(tam: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for nombre in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default(size=tam)


def icono_temperatura(temp: int | None) -> Image.Image:
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


def refrescar_icono(estado: Estado, icono_ref: dict) -> None:
    icono = icono_ref.get("icono")
    if not icono:
        return
    t = estado.datos["secciones"].get("tiempo")
    if t:
        icono.icon = icono_temperatura(t.get("temp"))
        icono.title = f"{t['lugar']}: {t['temp']}° · {t['texto']}"
    else:
        icono.icon = icono_temperatura(None)


def iniciar_bandeja(
    estado: Estado,
    icono_ref: dict,
    abrir_panel: Callable[[], Any],
    actualizar_ahora: Callable[[], Any],
    abrir_asistente: Callable[[], Any],
) -> None:
    """Crea el icono y su menú. Recibe las acciones como funciones para no depender de app.py.

    El icono se crea y se ejecuta en su propio hilo: en Windows, la ventana de
    mensajes del icono pertenece al hilo que la crea y debe seguir vivo."""
    import pystray

    def hilo() -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Obre el panell", lambda: abrir_panel(), default=True),
            pystray.MenuItem("Actualitza ara", lambda: actualizar_ahora()),
            pystray.MenuItem("Configura…", lambda: abrir_asistente()),
            pystray.MenuItem("Obre config.json", lambda: os.startfile(CONFIG)),
            pystray.MenuItem("Surt", lambda icono: salir(icono)),
        )
        icono = pystray.Icon("PanelDiario", icono_temperatura(None), "Panel Diario", menu)
        icono_ref["icono"] = icono
        refrescar_icono(estado, icono_ref)
        icono.run()

    threading.Thread(target=hilo, daemon=True).start()


def salir(icono: Any) -> None:
    try:
        icono.stop()
    finally:
        os._exit(0)
