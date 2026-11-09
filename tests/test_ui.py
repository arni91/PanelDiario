"""Tests de la interfaz (ui/): cada página enlaza ficheros que existen."""

import re
from pathlib import Path

import pytest

UI = Path(__file__).resolve().parents[1] / "src" / "panel_diario" / "ui"
PAGINAS = sorted(UI.glob("*/*.html"))


def test_hay_una_pagina_por_ventana() -> None:
    assert [p.relative_to(UI).as_posix() for p in PAGINAS] == [
        "panel/index.html",
        "pill/ficha.html",
        "wizard/asistente.html",
    ]


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.parent.name)
def test_los_css_y_js_enlazados_existen(pagina: Path) -> None:
    html = pagina.read_text(encoding="utf-8")
    enlaces = re.findall(r'<(?:link[^>]*href|script[^>]*src)="([^"]+)"', html)
    assert enlaces, "la página no enlaza su CSS ni su JS"
    for enlace in enlaces:
        assert (pagina.parent / enlace).is_file(), enlace
