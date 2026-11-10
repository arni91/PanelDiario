"""Tests del precio de la luz (sources/llum.py). Red Eléctrica se simula: no se usa internet."""

import types
from datetime import datetime
from typing import Any

import pytest

from panel_diario.sources import comun, llum

PRECIOS_MWH = [120.0, 100.0, 90.0, 95.0, 150.0, 210.0]  # de las 0 a las 5


def _ree(precios: list[float]) -> dict:
    valores = [{"value": p, "datetime": f"2026-11-10T{h:02d}:00:00.000+01:00"} for h, p in enumerate(precios)]
    otro = {"type": "Precio mercado spot", "attributes": {"values": [{"value": 1, "datetime": "x"}]}}
    return {"included": [otro, {"type": "PVPC", "attributes": {"values": valores}}]}


@pytest.fixture
def ree(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    pedidas: list[dict] = []

    def get(url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        assert url == llum.API
        pedidas.append(params or {})
        return types.SimpleNamespace(json=lambda: _ree(PRECIOS_MWH))

    monkeypatch.setattr(comun, "get", get)
    monkeypatch.setattr(comun, "ahora_local", lambda: datetime(2026, 11, 10, 4, 30, tzinfo=comun.TZ))
    return pedidas


def test_precio_de_ahora_en_euros_por_kwh_y_horas_baratas(ree: list[dict]) -> None:
    r = llum.obtener_llum({"llum": {"activa": True}})
    assert r["ara"] == 0.15  # las 4: 150 €/MWh
    assert r["min"] == {"h": 2, "preu": 0.09} and r["max"] == {"h": 5, "preu": 0.21}
    assert r["barates"] == [1, 2, 3]  # las tres más baratas, por orden de hora
    assert r["mitjana"] == round(sum(PRECIOS_MWH) / 6 / 1000, 4)
    assert len(r["hores"]) == 6
    assert ree == [{"start_date": "2026-11-10T00:00", "end_date": "2026-11-10T23:59", "time_trunc": "hour"}]


def test_sin_activar_no_sale_a_internet() -> None:
    assert llum.obtener_llum({}) == {"sin_configurar": True}
    assert llum.obtener_llum({"llum": {"activa": False}}) == {"sin_configurar": True}


def test_hora_sin_precio() -> None:
    assert llum.summary([{"h": 0, "preu": 0.1}], now_hour=7)["ara"] is None


def test_sin_precios_publicados_se_lanza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(comun, "get", lambda url, **k: types.SimpleNamespace(json=lambda: _ree([])))
    with pytest.raises(RuntimeError, match="Red Eléctrica"):
        llum.obtener_llum({"llum": {"activa": True}})
