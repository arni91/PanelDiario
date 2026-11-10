"""
Comprueba una a una todas las fuentes de config.json y dice cuáles responden.

Uso:  uv run python -m panel_diario.probar_fuentes
"""

import sys
import tempfile
from pathlib import Path

from panel_diario.config import cargar_config
from panel_diario.sources import avisos, drawdown, markets, noticias, sports, tiempo


def linea(ok: bool, nombre: str, detalle: str) -> None:
    marca = "OK   " if ok else "FALLA"
    print(f"  [{marca}] {nombre:<38} {detalle}")


def _si(valor: object) -> str:
    return "sí" if valor else "no"


def main() -> int:
    """Prueba cada RSS y cada API con la config real y resume cuántas fallan (código 1 si alguna)."""
    cfg = cargar_config()
    fallos = 0

    print("\nNOTICIAS (RSS)")
    for cat, lista in cfg["fuentes"].items():
        for f in lista:
            items, err = noticias._leer_feed(f, cat, horas_max=24 * 7)
            ok = err is None and len(items) > 0
            fallos += not ok
            linea(ok, f"{cat} / {f['nombre']}", f"{len(items)} titulares" if ok else (err or "0 titulares recientes"))

    print("\nOTROS DATOS")
    pruebas = [
        ("Tiempo (Open-Meteo)", lambda: tiempo.obtener_tiempo(cfg), lambda r: f"{r['temp']}° {r['texto']}"),
        (
            "Avisos (MeteoAlarm/AEMET)",
            lambda: avisos.obtener_avisos(cfg),
            lambda r: f"{len(r)} avisos activos en tus zonas",
        ),
        (
            "Caídas del ETF (Yahoo Finance)",
            lambda: drawdown.obtener_drawdown(
                cfg, Path(tempfile.mkdtemp()) / "prueba.json"
            ),  # sin caché: descarga todo
            lambda r: (
                "sin ticker en config.json"
                if r.get("sin_configurar")
                else f"{r['precio']} {r['moneda']} · máximo {r['maximo']} ({r['fecha_maximo']}) · "
                f"caída {r['caida']} % · histórico desde {r['primer_dato']}"
            ),
        ),
        (
            "Borsa (Yahoo Finance)",
            lambda: markets.obtener_borsa(cfg),
            lambda r: (
                "sin borsa en config.json"
                if r.get("sin_configurar")
                else f"{len(r['indexs'])} índices · {len(r['moviments'])} listas del día"
            ),
        ),
        (
            "Esports (ESPN y MotoGP)",
            lambda: sports.obtener_esports(cfg),
            lambda r: (
                "sin esports en config.json"
                if r.get("sin_configurar")
                else f"{len(r['equips'])} equipos · F1: {_si(r['f1'])} · MotoGP: {_si(r['motogp'])}"
            ),
        ),
    ]
    for nombre, fn, resumen in pruebas:
        try:
            r = fn()
            linea(True, nombre, resumen(r))
        except Exception as ex:  # noqa: BLE001
            fallos += 1
            linea(False, nombre, str(ex)[:90])

    print(f"\nResultado: {'todo responde' if not fallos else f'{fallos} fallos'}\n")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
