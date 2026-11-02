"""Tests del módulo de caídas de un ETF (datos.py): cálculo, niveles, caché y fallo de Yahoo.

Se ejecutan con:  uv run pytest
Yahoo se sustituye por respuestas falsas (mock): los tests no usan internet.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import pytest

from panel_diario.fuentes import drawdown

CFG: dict[str, Any] = {
    "drawdown": {
        "ticker": "EJEMPLO.DE",
        "actualizar_minutos": 30,
        "recalcular_dias": 7,
        "niveles": [
            {"caida": -10, "extra_pct": 50},
            {"caida": -20, "extra_pct": 100},
            {"caida": -30, "extra_pct": 200},
            {"caida": -40, "toda_la_reserva": True},
        ],
    }
}


def respuesta_yahoo(cierres: list[float | None], precio_actual: float) -> dict:
    """Imita lo que devuelve Yahoo: un cierre por día y el precio actual en 'meta'."""
    t0 = int(datetime(2019, 7, 24, 12).timestamp())
    return {
        "meta": {
            "regularMarketPrice": precio_actual,
            "regularMarketTime": t0 + 86400 * len(cierres),
            "currency": "EUR",
        },
        "timestamp": [t0 + 86400 * i for i in range(len(cierres))],
        "indicators": {"quote": [{"close": cierres}]},
    }


# --- Cálculo puro ---


def test_caida_en_maximo_es_cero() -> None:
    assert drawdown.calcular_caida(100, 100) == 0


def test_caida_porcentual() -> None:
    assert drawdown.calcular_caida(75, 100) == pytest.approx(-25)


@pytest.mark.parametrize("caida, nivel", [(-5, 0), (-19.99, 0), (-20, 1), (-29.9, 1), (-30, 2), (-40, 3), (-60, 3)])
def test_nivel_alcanzado(caida: float, nivel: int) -> None:
    assert drawdown.nivel_alcanzado(caida, [-20, -30, -40]) == nivel


def test_maximo_ignora_cierres_vacios() -> None:
    maximo, fecha_max, primero = drawdown.maximo_de_cierres(respuesta_yahoo([80, None, 120, 110], 100))
    assert maximo == 120
    assert fecha_max == "26/07/2019"
    assert primero == "24/07/2019"


# --- Flujo completo con caché (Yahoo simulado) ---


def test_primera_vez_descarga_historico_y_calcula_niveles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pedidos: list[str] = []

    def yahoo_falso(ticker: str, rango: str) -> dict:
        pedidos.append(rango)
        return respuesta_yahoo([100, 150, 120], 105)

    monkeypatch.setattr(drawdown, "_yahoo_chart", yahoo_falso)
    d = drawdown.obtener_drawdown(CFG, tmp_path / "dd.json")
    assert pedidos == ["max"]  # sin caché: histórico completo
    assert d["maximo"] == 150 and d["caida"] == -30.0 and d["nivel"] == 3
    assert [n["extra_pct"] for n in d["niveles"]] == [50, 100, 200, None]
    assert [n["toda_la_reserva"] for n in d["niveles"]] == [False, False, False, True]
    assert [n["alcanzado"] for n in d["niveles"]] == [True, True, True, False]


def test_niveles_se_ordenan_aunque_esten_desordenados_en_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = {"drawdown": {**CFG["drawdown"], "niveles": list(reversed(CFG["drawdown"]["niveles"]))}}
    monkeypatch.setattr(drawdown, "_yahoo_chart", lambda t, r: respuesta_yahoo([100], 85))
    d = drawdown.obtener_drawdown(cfg, tmp_path / "dd.json")
    assert [n["umbral"] for n in d["niveles"]] == [-10, -20, -30, -40]
    assert d["nivel"] == 1  # -15 %: solo el nivel de -10 %


def test_con_cache_solo_pide_precio_y_actualiza_maximo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "dd.json"
    monkeypatch.setattr(drawdown, "_yahoo_chart", lambda t, r: respuesta_yahoo([100, 150], 120))
    drawdown.obtener_drawdown(CFG, cache)
    # Forzamos que el precio esté "viejo" pero el histórico reciente
    c = json.loads(cache.read_text())
    c["precio_ts_consulta"] = 0
    cache.write_text(json.dumps(c))
    pedidos: list[str] = []

    def yahoo_falso(ticker: str, rango: str) -> dict:
        pedidos.append(rango)
        return respuesta_yahoo([149, 160], 160)

    monkeypatch.setattr(drawdown, "_yahoo_chart", yahoo_falso)
    d = drawdown.obtener_drawdown(CFG, cache)
    assert pedidos == ["5d"]  # no vuelve a bajar todo el histórico
    assert d["maximo"] == 160 and d["caida"] == 0  # el precio nuevo supera el máximo


def test_si_yahoo_falla_usa_ultimo_dato_y_avisa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "dd.json"
    monkeypatch.setattr(drawdown, "_yahoo_chart", lambda t, r: respuesta_yahoo([100, 200], 150))
    drawdown.obtener_drawdown(CFG, cache)
    c = json.loads(cache.read_text())
    c["precio_ts_consulta"] = 0
    cache.write_text(json.dumps(c))

    def falla(ticker: str, rango: str) -> NoReturn:
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(drawdown, "_yahoo_chart", falla)
    d = drawdown.obtener_drawdown(CFG, cache)
    assert d["desactualizado"] is True
    assert d["precio"] == 150 and d["caida"] == -25.0


def test_sin_ticker_la_seccion_queda_sin_configurar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(drawdown, "_yahoo_chart", lambda t, r: pytest.fail("no debe llamar a Yahoo"))
    assert drawdown.obtener_drawdown({"drawdown": {"ticker": ""}}, tmp_path / "dd.json") == {"sin_configurar": True}


def test_si_yahoo_falla_sin_cache_lanza_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def falla(ticker: str, rango: str) -> NoReturn:
        raise RuntimeError("sin conexión")

    monkeypatch.setattr(drawdown, "_yahoo_chart", falla)
    with pytest.raises(RuntimeError):
        drawdown.obtener_drawdown(CFG, tmp_path / "dd.json")
