"""Caída de un ETF desde su máximo histórico y nivel de aportación extra (Yahoo Finance, no oficial)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

from panel_diario.fuentes import comun

log = logging.getLogger("panel")


# Caída % = (precio actual − máximo histórico) / máximo histórico × 100.
# El máximo es el del propio ETF con TODOS sus cierres desde que cotiza. Como descargar el
# histórico entero es lento, se guarda en caché y en cada refresco solo se pide el precio actual
# (si lo supera, pasa a ser el nuevo máximo). Una vez a la semana se recalcula entero por si Yahoo
# corrige algún dato erróneo que, colado como "máximo", falsearía la caída para siempre.
# Se usa el cierre tal cual: es exacto en un ETF de acumulación; en uno de distribución, cada
# reparto de dividendos baja el precio y la caída sale algo exagerada.


def calcular_caida(precio: float, maximo: float) -> float:
    """Caída en % desde el máximo (0 o negativa)."""
    return (precio - maximo) / maximo * 100


def nivel_alcanzado(caida: float, umbrales: list[float]) -> int:
    """Cuántos umbrales se han alcanzado. Ej.: umbrales [-20, -30, -40] y caída -32 % → 2."""
    return sum(1 for u in sorted(umbrales, reverse=True) if caida <= u)


def _yahoo_chart(ticker: str, rango: str) -> dict:
    """Cierres diarios de Yahoo Finance para `rango` ("5d", "max"...)."""
    ultimo_error = None
    for host in ("query1", "query2"):
        try:
            r = comun.get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}",
                headers={"User-Agent": comun.UA_NAVEGADOR},
                params={"range": rango, "interval": "1d"},
            )
            return r.json()["chart"]["result"][0]
        except Exception as ex:  # noqa: BLE001
            ultimo_error = ex
    raise RuntimeError(f"Yahoo no responde para {ticker}: {ultimo_error}")


def maximo_de_cierres(res: dict) -> tuple[float, str, str]:
    """(máximo cierre, fecha del máximo, fecha del primer dato) de una respuesta de Yahoo."""
    pares = [
        # strict=False: si Yahoo devolviera listas de distinta longitud, se usan los pares completos
        (ts, c)
        for ts, c in zip(res.get("timestamp") or [], res["indicators"]["quote"][0]["close"], strict=False)
        if c is not None
    ]
    if not pares:
        raise RuntimeError("Yahoo no ha devuelto cierres")
    ts_max, maximo = max(pares, key=lambda p: p[1])
    fecha = lambda ts: datetime.fromtimestamp(ts).strftime("%d/%m/%Y")  # noqa: E731
    return maximo, fecha(ts_max), fecha(pares[0][0])


# Regla de compras extra: a partir de cada caída, cuánto añadir a la aportación habitual, en %
# (+100 % = aportar el doble ese mes). Va en % y no en euros para que el widget no guarde
# importes: cada uno aplica el % a su propia aportación. El último nivel puede ser "toda la reserva".
NIVELES_POR_DEFECTO = [
    {"caida": -10, "extra_pct": 50},
    {"caida": -20, "extra_pct": 100},
    {"caida": -30, "extra_pct": 200},
    {"caida": -40, "toda_la_reserva": True},
]


def obtener_drawdown(cfg: dict, cache_path: Path) -> dict:
    dd = cfg.get("drawdown") or {}
    ticker = (dd.get("ticker") or "").strip()
    if not ticker:
        return {"sin_configurar": True}
    niveles = sorted(dd.get("niveles") or NIVELES_POR_DEFECTO, key=lambda n: n["caida"], reverse=True)
    umbrales = [n["caida"] for n in niveles]

    cache = {}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        if cache.get("ticker") != ticker:  # si cambias de ticker, se empieza de cero
            cache = {}
    except Exception:  # noqa: BLE001  (no hay caché todavía o está dañada)
        cache = {}

    ahora = time.time()
    desactualizado, error = False, None
    reciente = ahora - cache.get("precio_ts_consulta", 0) < float(dd.get("actualizar_minutos", 30)) * 60
    if not reciente:
        try:
            completo = ahora - cache.get("historico_ts", 0) > float(dd.get("recalcular_dias", 7)) * 86400
            res = _yahoo_chart(ticker, "max" if completo or "maximo" not in cache else "5d")
            if completo or "maximo" not in cache:
                cache["maximo"], cache["fecha_maximo"], cache["primer_dato"] = maximo_de_cierres(res)
                cache["historico_ts"] = ahora
            meta = res["meta"]
            cierres = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
            precio = meta.get("regularMarketPrice") or cierres[-1]
            t = meta.get("regularMarketTime") or res["timestamp"][-1]
            cache.update(
                ticker=ticker,
                precio=float(precio),
                moneda=meta.get("currency", "EUR"),
                hora=datetime.fromtimestamp(t).strftime("%d/%m %H:%M"),
                precio_ts_consulta=ahora,
            )
            if cache["precio"] > cache["maximo"]:  # nuevo máximo histórico
                cache["maximo"] = cache["precio"]
                cache["fecha_maximo"] = datetime.fromtimestamp(t).strftime("%d/%m/%Y")
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            if "precio" not in cache:
                raise  # sin ningún dato guardado no hay nada que mostrar
            desactualizado, error = True, str(ex)[:150]
            log.warning("Caídas: uso el último dato guardado (%s): %s", cache.get("hora"), ex)

    caida = calcular_caida(cache["precio"], cache["maximo"])
    nivel = nivel_alcanzado(caida, umbrales)
    return {
        "nombre": dd.get("nombre", ticker),
        "ticker": ticker,
        "moneda": cache.get("moneda", "EUR"),
        "precio": round(cache["precio"], 2),
        "hora": cache.get("hora", ""),
        "maximo": round(cache["maximo"], 2),
        "fecha_maximo": cache.get("fecha_maximo", ""),
        "primer_dato": cache.get("primer_dato", ""),
        "caida": round(caida, 2),
        "nivel": nivel,
        "niveles": [
            {
                "umbral": n["caida"],
                "extra_pct": n.get("extra_pct"),
                "toda_la_reserva": bool(n.get("toda_la_reserva")),
                "alcanzado": i < nivel,
            }
            for i, n in enumerate(niveles)
        ],
        "desactualizado": desactualizado,
        "error": error,
    }
