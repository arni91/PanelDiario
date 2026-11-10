"""Dibuja el logo de Panel Diario (logo.png y logo.ico en src/panel_diario/ui/common/).

Un cuadrado redondeado azul con un sol y tres franjas, como titulares de un panel. Se dibuja a
4x y se reduce para que los bordes salgan suaves. Uso: uv run python scripts/generar_logo.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).resolve().parents[1] / "src" / "panel_diario" / "ui" / "common"
LADO = 1024  # se dibuja a 1024 px y se reduce a 256
AZUL_CLARO = (95, 179, 232)  # --accent del panel
AZUL_OSCURO = (31, 92, 150)
BLANCO = (255, 255, 255, 255)
SOL = (255, 214, 102, 255)
TAMANOS_ICO = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _degradado() -> Image.Image:
    """Fondo azul en diagonal, de claro (arriba a la izquierda) a oscuro."""
    fondo = Image.new("RGBA", (LADO, LADO))
    pixeles = fondo.load()
    assert pixeles is not None
    for y in range(LADO):
        for x in range(LADO):
            t = (x + y) / (2 * LADO)
            pixeles[x, y] = tuple(round(c1 + (c2 - c1) * t) for c1, c2 in zip(AZUL_CLARO, AZUL_OSCURO, strict=True)) + (
                255,
            )
    return fondo


def dibujar() -> Image.Image:
    mascara = Image.new("L", (LADO, LADO), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, LADO - 1, LADO - 1), radius=230, fill=255)
    logo = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    logo.paste(_degradado(), (0, 0), mascara)
    d = ImageDraw.Draw(logo)

    # Sol arriba a la izquierda: círculo y ocho rayos
    cx, cy, r = 330, 320, 105
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SOL)
    for i in range(8):
        a = i * math.pi / 4
        x1, y1 = cx + math.cos(a) * (r + 40), cy + math.sin(a) * (r + 40)
        x2, y2 = cx + math.cos(a) * (r + 95), cy + math.sin(a) * (r + 95)
        d.line((x1, y1, x2, y2), fill=SOL, width=42)

    # Tres franjas, como titulares: cada una más corta que la anterior
    for i, ancho in enumerate((640, 520, 380)):
        y = 600 + i * 120
        d.rounded_rectangle((190, y, 190 + ancho, y + 70), radius=35, fill=BLANCO)
    return logo.resize((256, 256), Image.Resampling.LANCZOS)


def main() -> None:
    logo = dibujar()
    logo.save(DESTINO / "logo.png")
    logo.save(DESTINO / "logo.ico", sizes=TAMANOS_ICO)
    print(f"Logo guardado en {DESTINO}")


if __name__ == "__main__":
    main()
