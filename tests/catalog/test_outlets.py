"""Tests del catálogo de medios (outlets.py)."""

import json
from pathlib import Path

from panel_diario.catalog import outlets

RAIZ = Path(__file__).resolve().parents[2]

# --- Catálogo ------------------------------------------------------------------


def test_catalogo_con_los_seis_diarios_primero() -> None:
    nombres = [o.name for o in outlets.CATALOG]
    assert nombres[:6] == ["El Salto", "eldiario.es", "La Directa", "Ara", "La Vanguardia", "El País"]
    for o in outlets.CATALOG:
        assert o.language in ("ca", "es", "en")


def test_cada_medio_tiene_feeds_validos_y_sin_repetir_pestana() -> None:
    for o in outlets.CATALOG:
        assert o.feeds, o.name
        assert all(f.tab in outlets.TABS and f.url.startswith("https://") for f in o.feeds)
        assert len({f.tab for f in o.feeds}) == len(o.feeds), o.name  # un feed por pestaña y medio


def test_reparto_de_los_diarios_por_pestana() -> None:
    def medios(tab: str) -> list[str]:
        return [f["nombre"] for f in outlets.sources_for_tab(tab)]

    # Los seis diarios principales primero; después, los medios generales
    assert medios("mon") == [
        "eldiario.es",
        "La Vanguardia",
        "El País",
        "Europa Press",
        "BBC Mundo",
        "DW",
        "France 24",
        "VilaWeb",
        "El Periódico",
        "The Guardian",
        "Al Jazeera",
        "The New York Times",
    ]
    assert medios("catalunya") == ["eldiario.es", "La Directa", "Ara", "La Vanguardia"]
    assert medios("espanya") == ["El Salto", "eldiario.es", "El País"]
    assert medios("mobilitzacions") == ["El Salto", "La Directa", "El Crític"]
    assert medios("tecnologia") == [
        "El Salto",
        "eldiario.es",
        "La Vanguardia",
        "El País",
        "Xataka",
        "Ars Technica",
        "MIT Technology Review",
        "VilaWeb",
        "El Periódico",
        "Genbeta",
        "The Verge",
        "Wired",
        "TechCrunch",
        "Engadget",
        "Hacker News",
    ]
    assert outlets.sources_for_tab("no-existe") == []


def test_fuente_del_catalogo_lleva_idioma_para_no_pasar_por_el_traductor() -> None:
    assert outlets.sources_for_tab("mobilitzacions")[1] == {
        "nombre": "La Directa",
        "url": "https://directa.cat/feed/",
        "idioma": "ca",
    }


def test_la_plantilla_publica_solo_usa_feeds_del_catalogo() -> None:
    """La plantilla es una selección del catálogo (no todo: cada usuario elige en el asistente)."""
    plantilla = json.loads((RAIZ / "config.example.json").read_text(encoding="utf-8"))
    pestana = {"mon": "mundo"}  # en la plantilla, la pestaña Món tiene el id "mundo"
    for tab in outlets.TABS:
        catalogo = outlets.sources_for_tab(tab)
        for fuente in plantilla["fuentes"][pestana.get(tab, tab)]:
            if not fuente.get("agregador"):
                assert fuente in catalogo, (tab, fuente["nombre"])
