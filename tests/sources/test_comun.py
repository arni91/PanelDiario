"""Tests de las utilidades comunes de las fuentes (sources/comun.py)."""

from datetime import date, datetime

import pytest
import requests

from panel_diario.sources import comun


@pytest.mark.parametrize(
    ("dia", "texto"),
    [(date(2026, 11, 22), "dg 22/11"), (datetime(2026, 1, 5, 21, 0), "dl 5/1")],
)
def test_dia_curt(dia: date, texto: str) -> None:
    assert comun.dia_curt(dia) == texto


def test_normalizar_sin_acentos_ni_mayusculas() -> None:
    assert comun.normalizar("Gràcia") == "gracia"


def test_distancia() -> None:
    assert round(comun.distancia_km(41.3874, 2.1686, 41.9794, 2.8214)) == 85  # Barcelona-Girona en línea recta


@pytest.mark.parametrize(("texto", "valor"), [("1,744", 1.744), ("41.47", 41.47), ("", None), (None, None)])
def test_numero_con_coma_o_punto(texto: object, valor: float | None) -> None:
    assert comun.numero(texto) == valor


# --- Segundo intento TLS (servidores que cortan la negociación con ECDHE) ---------------


class _Respuesta:
    status_code = 200

    def raise_for_status(self) -> None:
        pass


def test_si_la_negociacion_tls_falla_reintenta_con_tls_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*a: object, **k: object) -> None:
        raise requests.exceptions.SSLError("EOF occurred in violation of protocol")

    montados: list[object] = []

    class Sesion:
        def __enter__(self) -> "Sesion":
            return self

        def __exit__(self, *a: object) -> None:
            pass

        def mount(self, prefijo: str, adaptador: object) -> None:
            montados.append(adaptador)

        def get(self, *a: object, **k: object) -> _Respuesta:
            return _Respuesta()

    monkeypatch.setattr(requests, "get", falla)
    monkeypatch.setattr(requests, "Session", Sesion)
    assert comun.get("https://ministerio.example/", tls_compatible=True).status_code == 200
    assert len(montados) == 1 and isinstance(montados[0], comun._AdaptadorTlsCompatible)


def test_sin_tls_compatible_el_error_tls_se_lanza(monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(*a: object, **k: object) -> None:
        raise requests.exceptions.SSLError("EOF occurred in violation of protocol")

    monkeypatch.setattr(requests, "get", falla)
    with pytest.raises(requests.exceptions.SSLError):
        comun.get("https://otra.example/")
