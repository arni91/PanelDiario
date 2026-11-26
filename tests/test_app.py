"""Tests del puente con la píldora (app.py): el ancho se ajusta a lo que mide su contenido."""

from typing import Any

import pytest

from panel_diario import app


class _Estado:
    datos: dict = {"secciones": {}}


@pytest.fixture
def llamadas(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """Sustituye las llamadas a Win32 y apunta con qué se han hecho."""
    vistas: list[tuple] = []

    def cambiar_ancho(hwnd: int, ancho: int, alto: int, padre: int | None = None) -> int:
        vistas.append(("ancho", hwnd, ancho, alto, padre))
        return 900

    monkeypatch.setattr(app, "cambiar_ancho", cambiar_ancho)
    monkeypatch.setattr(app, "redondear_esquinas", lambda hwnd, **_: vistas.append(("esquinas", hwnd)))
    return vistas


def _ficha() -> app.ApiFicha:
    panel: Any = None
    estado: Any = _Estado()
    return app.ApiFicha(estado, panel, [1000, 20])


def test_sin_ventana_se_guarda_el_ancho_y_se_aplica_al_mostrarse(llamadas: list[tuple]) -> None:
    ficha = _ficha()
    assert ficha.ajustar_ancho(131.4)
    assert ficha.ancho == 131 and llamadas == []
    ficha._hwnd = 7
    ficha.aplicar_ancho()
    assert llamadas == [("ancho", 7, 131, app.ALTO_FICHA, None), ("esquinas", 7)]
    assert ficha.pos == [900, 20]  # borde derecho fijo: la x cambia, la y no


def test_anclada_al_escritorio_se_coloca_respecto_al_escritorio(llamadas: list[tuple]) -> None:
    ficha = _ficha()
    ficha._hwnd, ficha.anclaje = 7, (7, 99)
    ficha.ajustar_ancho(120)
    assert llamadas[0] == ("ancho", 7, 120, app.ALTO_FICHA, 99)


def test_el_mismo_ancho_no_se_vuelve_a_aplicar(llamadas: list[tuple]) -> None:
    ficha = _ficha()
    ficha._hwnd = 7
    ficha.ajustar_ancho(120)
    ficha.ajustar_ancho(120)
    assert len(llamadas) == 2  # un cambio de ancho y un recorte de esquinas, no dos


@pytest.mark.parametrize(("pedido", "queda"), [(0, app.ANCHO_FICHA_MIN), (5000, app.ANCHO_FICHA_MAX)])
def test_un_ancho_absurdo_se_limita(llamadas: list[tuple], pedido: int, queda: int) -> None:
    ficha = _ficha()
    ficha.ajustar_ancho(pedido)
    assert ficha.ancho == queda


def test_si_windows_falla_no_rompe_y_lo_reintenta(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*_: object) -> int:
        raise OSError("SetWindowPos falló")

    monkeypatch.setattr(app, "cambiar_ancho", falla)
    ficha = _ficha()
    ficha._hwnd = 7
    assert ficha.ajustar_ancho(120) is False
    assert ficha._ancho_aplicado is None  # la siguiente medida lo vuelve a intentar
