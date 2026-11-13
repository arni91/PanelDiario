"""Tests de los planes (sources/plans.py). La Agenda Cultural de Catalunya se simula."""

import types
from datetime import date, datetime
from typing import Any

import pytest

from panel_diario.sources import comun, plans

HOY = date(2026, 11, 13)  # viernes
CFG = {"plans": {"activa": True, "ciutat": "Barcelona", "interessos": ["electronica"], "paraules": ["jazz"]}}


def _plan(codi: str, titol: str, inicio: str, fin: str, **extra: str) -> dict:
    return {
        "codi": codi,
        "denominaci": titol,
        "data_inici": f"{inicio}T00:00:00.000",
        "data_fi": f"{fin}T00:00:00.000",
        "espai": "Sala d'exemple",
        "tags_categor_es": "agenda:categories/concerts",
        "gratuita": "No",
        "permanent": "No",
        **extra,
    }


AGENDA = [
    _plan("1", "Exposició llarga", "2026-10-01", "2027-01-17", tags_categor_es="agenda:categories/exposicions"),
    _plan("2", "Concert de jazz", "2026-11-15", "2026-11-15", url="https://sala.example/"),
    _plan("3", "Nit de techno", "2026-11-14", "2026-11-14", linkbotoentrades="https://entrades.example/3"),
    _plan("3", "Nit de techno", "2026-11-14", "2026-11-14", espai="Una altra sala"),  # repetido en otro espacio
    _plan("4", "Col·lecció permanent", "2020-01-01", "2030-01-01", permanent="Sí"),
    _plan("5", "Xerrada", "2026-11-13", "2026-11-16", gratuita="Sí"),
]


@pytest.fixture
def agenda_cultural(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    peticiones: list[dict] = []

    def get(url: str, params: dict | None = None, **k: Any) -> types.SimpleNamespace:
        peticiones.append(params or {})
        return types.SimpleNamespace(json=lambda: AGENDA)

    monkeypatch.setattr(comun, "get", get)
    monkeypatch.setattr(comun, "ahora_local", lambda: datetime(2026, 11, 13, 9, 0, tzinfo=comun.TZ))
    return peticiones


def test_primero_lo_de_tus_interesos_y_despues_toda_la_agenda(agenda_cultural: list[dict]) -> None:
    r = plans.obtener_plans(CFG)
    assert "municipi like '%/barcelona'" in agenda_cultural[0]["$where"]
    assert "data_inici <= '2026-11-20'" in agenda_cultural[0]["$where"]  # los próximos 7 días
    assert [p["titol"] for p in r["per_a_tu"]] == ["Nit de techno", "Concert de jazz"]
    assert r["per_a_tu"][1]["interessos"] == ["jazz"]  # palabra propia
    # Lo corto por fecha de inicio y lo largo detrás; sin repetidos ni permanentes
    assert [p["titol"] for p in r["tot"]] == ["Xerrada", "Nit de techno", "Concert de jazz", "Exposició llarga"]
    assert r["ciutat"] == "Barcelona" and r["dies"] == 7


def test_cada_plan_con_lo_que_pinta_el_panel(agenda_cultural: list[dict]) -> None:
    techno, jazz = plans.obtener_plans(CFG)["per_a_tu"]
    assert techno == {
        "titol": "Nit de techno",
        "lloc": "Sala d'exemple",
        "quan": "ds 14/11",
        "categoria": "concerts",
        "interessos": ["Música electrònica"],
        "gratuit": False,
        "enllac": "https://entrades.example/3",  # sin enlace propio, el de las entradas
    }
    assert jazz["enllac"] == "https://sala.example/"  # ni enlace ni entradas: la web del espacio


@pytest.mark.parametrize(
    ("inicio", "fin", "texto"),
    [
        (date(2026, 11, 14), date(2026, 11, 14), "ds 14/11"),
        (date(2026, 10, 1), date(2026, 11, 22), "fins dg 22/11"),  # ya empezado
        (date(2026, 11, 14), date(2026, 11, 15), "ds 14/11 – dg 15/11"),
    ],
)
def test_fechas_en_corto(inicio: date, fin: date, texto: str) -> None:
    assert plans._when(inicio, fin, HOY) == texto


@pytest.mark.parametrize(
    ("ciudad", "slug"),
    [
        ("Barcelona", "barcelona"),
        ("L'Hospitalet de Llobregat", "l-hospitalet-de-llobregat"),
        ("Sant Adrià de Besòs", "sant-adria-de-besos"),
        ("La Seu d'Urgell", "la-seu-d-urgell"),
    ],
)
def test_nombre_del_municipio_como_en_la_agenda(ciudad: str, slug: str) -> None:
    assert plans.slug(ciudad) == slug


@pytest.mark.parametrize("cfg_plans", [{}, {"activa": False, "ciutat": "Barcelona"}, {"activa": True, "ciutat": " "}])
def test_sin_configurar_no_sale_a_internet(cfg_plans: dict) -> None:
    assert plans.obtener_plans({"plans": cfg_plans}) == {"sin_configurar": True}
