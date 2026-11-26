"""Tests de win32.py: el ancho que pide la página se pasa a píxeles reales con cualquier escala."""

import pytest

from panel_diario.desktop import win32


@pytest.mark.parametrize(
    ("pedido", "vista", "real_actual", "esperado"),
    [
        (134, 134, 134, 134),  # sin escala: igual
        (134, 160, 200, 168),  # escalado del 125 %: la página ve 160 px donde hay 200 reales
        (134, 107.2, 134, 168),  # zoom del 125 % sin escalado de Windows (lo que cortaba el «0%»)
    ],
)
def test_el_ancho_pedido_se_pasa_a_pixeles_reales_con_la_vista(
    pedido: int, vista: float, real_actual: int, esperado: int
) -> None:
    assert win32.ancho_en_pixeles_reales(pedido, real_actual, 34, 34, vista) == esperado


def test_sin_vista_usa_la_proporcion_del_alto() -> None:
    # Compatibilidad: si la página no dice cuánto ve, se usa alto real / alto de la página
    assert win32.ancho_en_pixeles_reales(100, 300, 51, 34, None) == 150
