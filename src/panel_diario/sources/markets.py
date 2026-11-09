"""Borsa: cotización y variación del día de los índices elegidos y listas de valores del día.

Datos de Yahoo Finance (no oficial). Un índice que falla se omite con un aviso en el log; si
fallan todos, se lanza la excepción y state.py conserva el último dato bueno.
"""

from __future__ import annotations

import logging
from datetime import datetime

from panel_diario.catalog import markets
from panel_diario.sources import comun

log = logging.getLogger("panel")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
MOVERS_COUNT = 5


def _yahoo(url: str, params: dict) -> dict:
    return comun.get(url, headers={"User-Agent": comun.UA_NAVEGADOR}, params=params).json()


def change_pct(price: float, previous: float) -> float:
    """Variación en % respecto al cierre anterior."""
    return (price - previous) / previous * 100 if previous else 0.0


def quote(symbol: str) -> dict:
    """Precio actual y variación del día respecto al cierre de la sesión anterior."""
    # Con range=1d, chartPreviousClose es el cierre de la sesión anterior (con 5d sería el de hace 5 días)
    meta = _yahoo(CHART_URL.format(symbol=symbol), {"range": "1d", "interval": "1d"})["chart"]["result"][0]["meta"]
    price, previous = float(meta["regularMarketPrice"]), float(meta["chartPreviousClose"])
    index = markets.find_index(symbol)
    return {
        "simbol": symbol,
        "nom": index.name if index else meta.get("shortName", symbol),
        "preu": price,
        "canvi_pct": round(change_pct(price, previous), 2),
        "moneda": meta.get("currency", ""),
        "hora": datetime.fromtimestamp(meta["regularMarketTime"], comun.TZ).strftime("%d/%m %H:%M"),
    }


def movers(screen: str, count: int = MOVERS_COUNT) -> list[dict]:
    """Los valores de una lista del día (los que más suben, bajan...)."""
    data = _yahoo(SCREENER_URL, {"scrIds": screen, "count": count})
    return [
        {
            "simbol": q["symbol"],
            "nom": (q.get("shortName") or q["symbol"]).strip(),
            "preu": q.get("regularMarketPrice"),
            "canvi_pct": round(float(q.get("regularMarketChangePercent", 0.0)), 2),
        }
        for q in data["finance"]["result"][0]["quotes"][:count]
    ]


def obtener_borsa(cfg: dict) -> dict:
    """Sección de borsa del panel. Sin "borsa" en config.json, {"sin_configurar": True}."""
    b = cfg.get("borsa") or {}
    symbols, screens = b.get("indexs", []), b.get("moviments", [])
    if not symbols and not screens:
        return {"sin_configurar": True}
    indexs, errors = [], []
    for symbol in symbols:
        try:
            indexs.append(quote(symbol))
        except Exception as ex:  # noqa: BLE001  (un índice caído no tapa los demás)
            log.warning("Borsa: %s sin datos (%s)", symbol, type(ex).__name__)
            errors.append(ex)
    if symbols and not indexs:
        raise RuntimeError("Yahoo Finance no respon") from errors[-1]
    moviments = [
        {"id": s, "nombre": markets.MOVERS.get(s, s), "valors": movers(s)} for s in screens if s in markets.MOVERS
    ]
    return {"indexs": indexs, "moviments": moviments}
