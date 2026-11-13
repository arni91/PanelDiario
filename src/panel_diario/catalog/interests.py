"""Catálogo público de interesos para los planes: qué palabras delatan cada tipo de plan.

Los planes (sources/plans.py) que contienen alguna de estas palabras en el título, el subtítulo,
la descripción o las categorías salen primero, marcados con el interés. Las palabras se comparan
en minúsculas y sin acentos, al principio de una palabra del texto: "feminis" encuentra
"feminisme" y "feministes"; con \\b al final solo vale la palabra entera ("trans" no es "transport").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from panel_diario.sources import comun


@dataclass(frozen=True)
class Interest:
    name: str
    keywords: tuple[str, ...]  # fragmentos de expresión regular, sin acentos y en minúsculas


# En el orden del asistente
INTERESTS: dict[str, Interest] = {
    "lgtbi": Interest(
        "LGTBIQ+",
        (
            "lgtb",
            "lgbt",
            "queer",
            r"pride\b",
            r"trans\b",
            "transgener",
            "lesbi",
            r"gai\b",
            r"gais\b",
            r"gay\b",
            "bisexual",
            "no binari",
            "dissidencies sexuals",
        ),
    ),
    "electronica": Interest(
        "Música electrònica",
        (
            "electronica",
            "electronic music",
            "techno",
            r"tecno\b",
            r"house\b",
            r"djs?\b",
            r"dj set",
            r"rave\b",
            "clubbing",
            "sintetitzador",
        ),
    ),
    "performance": Interest(
        "Performance",
        ("performance", "performatiu", "performativa", "art d.accio", "happening", r"live art\b"),
    ),
    "drag": Interest("Drag i cabaret", (r"drag\b", r"drags\b", "cabaret", "burlesc", "vogue")),
    "feminisme": Interest("Feminisme", ("feminis", r"8m\b", r"25n\b", "masclis", "patriarca", "sororitat")),
    "reivindicatiu": Interest(
        "Reivindicatiu",
        (
            "activis",
            "reivindicativ",
            "antirracis",
            "decolonial",
            "anticolonial",
            "memoria democratica",
            "drets humans",
            "protesta",
            "palestin",
            "migrant",
        ),
    ),
    "underground": Interest(
        "Underground i experimental",
        (
            "underground",
            "experimental",
            "alternatiu",
            "alternativa",
            "autogesti",
            "contracultur",
            "fanzine",
            r"punk\b",
            r"noise\b",
        ),
    ),
    "art_contemporani": Interest(
        "Art contemporani",
        ("art contemporani", "creacio contemporania", "videoart", "videocreaci", r"macba\b", r"cccb\b"),
    ),
}


def pattern(keywords: list[str] | tuple[str, ...]) -> re.Pattern[str]:
    """Expresión que encuentra cualquiera de las palabras al principio de una palabra."""
    return re.compile(r"\b(?:" + "|".join(keywords) + ")")


def own_word(word: str) -> str:
    """Una palabra propia del usuario, lista para pattern(): sin acentos y sin caracteres especiales."""
    return re.escape(comun.normalizar(word.strip()))
