"""Catálogo público de borsa: índices, materias primas, divisas y listas de valores del día.

Los símbolos son los de Yahoo Finance. El asistente ofrece estas listas; config.json guarda
los elegidos en "borsa".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Index:
    """Un índice (o activo) que se sigue: símbolo de Yahoo, nombre corto y grupo."""

    symbol: str
    name: str
    group: str


INDICES: tuple[Index, ...] = (
    Index("^IBEX", "IBEX 35", "Europa"),
    Index("^STOXX50E", "Euro Stoxx 50", "Europa"),
    Index("^STOXX", "Stoxx Europe 600", "Europa"),
    Index("^GDAXI", "DAX", "Europa"),
    Index("^FCHI", "CAC 40", "Europa"),
    Index("^FTSE", "FTSE 100", "Europa"),
    Index("^GSPC", "S&P 500", "Estats Units"),
    Index("^IXIC", "Nasdaq", "Estats Units"),
    Index("^DJI", "Dow Jones", "Estats Units"),
    Index("^N225", "Nikkei 225", "Àsia"),
    Index("GC=F", "Or", "Matèries primeres"),
    Index("BZ=F", "Petroli Brent", "Matèries primeres"),
    Index("EURUSD=X", "Euro / dòlar", "Divises"),
    Index("BTC-USD", "Bitcoin", "Criptomonedes"),
)

DEFAULT_INDICES = ("^IBEX", "^STOXX50E", "^GSPC", "^IXIC")

# Listas de valores del día de Yahoo Finance (mercado de EE. UU.): id -> nombre que ve el usuario
MOVERS: dict[str, str] = {
    "day_gainers": "Les que més pugen",
    "day_losers": "Les que més baixen",
    "most_actives": "Les més negociades",
}

DEFAULT_MOVERS = ("day_gainers", "day_losers")


def find_index(symbol: str) -> Index | None:
    return next((i for i in INDICES if i.symbol == symbol), None)
