"""Tests de la calidad del aire y el polen (sources/aire.py). Open-Meteo se simula."""

import types
from typing import Any

import pytest

from panel_diario.sources import aire, comun

CFG = {"aire": {"activa": True}, "ubicacion": {"lat": 41.98, "lon": 2.82, "zona_horaria": "Europe/Madrid"}}


def _respuesta(aqi: float, horas: dict) -> types.SimpleNamespace:
    datos = {"current": {"european_aqi": aqi}, "hourly": {"time": ["00:00", "01:00"], **horas}}
    return types.SimpleNamespace(json=lambda: datos)


def test_calidad_del_aire_y_polenes_de_hoy(monkeypatch: pytest.MonkeyPatch) -> None:
    pedidas: list[dict] = []

    def get(url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        pedidas.append(params or {})
        horas = {
            "grass_pollen": [12.0, 30.5],
            "olive_pollen": [0.0, 0.4],
            "birch_pollen": [None, None],
            "mugwort_pollen": [2.0, 1.0],
        }
        return _respuesta(21.4, horas)

    monkeypatch.setattr(comun, "get", get)
    r = aire.obtener_aire(CFG)
    assert (r["ica"], r["qualitat"], r["nivell"]) == (21, "Acceptable", 1)
    # El máximo de cada polen; los que no llegan a 1 grano/m³ (olivera) o no tienen datos (bedoll) no salen
    assert r["pollen"] == [
        {"nom": "Gramínies", "valor": 30.5, "nivell": "moderat"},
        {"nom": "Artemísia", "valor": 2.0, "nivell": "baix"},
    ]
    assert pedidas[0]["latitude"] == 41.98 and "grass_pollen" in pedidas[0]["hourly"]


@pytest.mark.parametrize(
    ("aqi", "nombre"),
    [(0, "Bona"), (19.9, "Bona"), (20, "Acceptable"), (85, "Molt dolenta"), (140, "Extremadament dolenta")],
)
def test_tramos_del_indice_europeo(aqi: float, nombre: str) -> None:
    assert aire.level_of(aqi, aire.AQI_LEVELS)[1] == nombre


def test_fuera_de_temporada_sin_polen() -> None:
    assert aire.pollen_today({}) == []


def test_sin_activar_no_sale_a_internet() -> None:
    assert aire.obtener_aire({"ubicacion": CFG["ubicacion"]}) == {"sin_configurar": True}
