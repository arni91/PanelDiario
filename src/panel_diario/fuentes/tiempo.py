"""Tiempo actual, próximas 12 horas y 6 días (Open-Meteo, sin clave).

Lo usa la píldora del escritorio (temperatura e icono) y la tarjeta de tiempo del panel.
"""

from __future__ import annotations

from datetime import datetime

from panel_diario.fuentes import comun

WMO = {  # descripcions en català (codis WMO d'Open-Meteo)
    0: ("☀️", "Serè"),
    1: ("🌤️", "Gairebé serè"),
    2: ("⛅", "Parcialment ennuvolat"),
    3: ("☁️", "Ennuvolat"),
    45: ("🌫️", "Boira"),
    48: ("🌫️", "Boira gebradora"),
    51: ("🌦️", "Plugim feble"),
    53: ("🌦️", "Plugim"),
    55: ("🌧️", "Plugim intens"),
    56: ("🌧️", "Plugim gelat"),
    57: ("🌧️", "Plugim gelat"),
    61: ("🌦️", "Pluja feble"),
    63: ("🌧️", "Pluja"),
    65: ("🌧️", "Pluja forta"),
    66: ("🌧️", "Pluja gelada"),
    67: ("🌧️", "Pluja gelada forta"),
    71: ("🌨️", "Neu feble"),
    73: ("🌨️", "Neu"),
    75: ("❄️", "Neu forta"),
    77: ("🌨️", "Calamarsa fina"),
    80: ("🌦️", "Ruixats febles"),
    81: ("🌧️", "Ruixats"),
    82: ("⛈️", "Ruixats forts"),
    85: ("🌨️", "Ruixats de neu"),
    86: ("❄️", "Ruixats de neu forts"),
    95: ("⛈️", "Tempesta"),
    96: ("⛈️", "Tempesta amb calamarsa"),
    99: ("⛈️", "Tempesta forta amb calamarsa"),
}
NOCHE = {0: "🌙", 1: "🌙"}


def _wmo(code: int | None, es_dia: bool = True) -> tuple[str, str]:
    codigo = int(code or 0)
    icono, texto = WMO.get(codigo, ("🌡️", "—"))
    if not es_dia and codigo in NOCHE:
        icono = NOCHE[codigo]
    return icono, texto


def obtener_tiempo(cfg: dict) -> dict:
    u = cfg["ubicacion"]
    params = {
        "latitude": u["lat"],
        "longitude": u["lon"],
        "timezone": "auto",  # horas en la zona de la ubicación (la calcula Open-Meteo)
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,"
        "precipitation,relative_humidity_2m,is_day",
        "hourly": "temperature_2m,precipitation_probability,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "forecast_days": 6,
        "wind_speed_unit": "kmh",
    }
    d = comun.get("https://api.open-meteo.com/v1/forecast", params=params).json()
    c = d["current"]
    icono, texto = _wmo(c["weather_code"], c.get("is_day", 1) == 1)

    # Próximas 12 horas desde la hora actual
    horas = []
    h = d["hourly"]
    hora_actual = c["time"][:13]  # "YYYY-MM-DDTHH"
    inicio = next((i for i, t in enumerate(h["time"]) if t[:13] >= hora_actual), 0)
    for i in range(inicio, min(inicio + 12, len(h["time"]))):
        ic, _ = _wmo(h["weather_code"][i], h["is_day"][i] == 1)
        horas.append(
            {
                "hora": h["time"][i][11:13] + "h",
                "temp": round(h["temperature_2m"][i]),
                "lluvia": h["precipitation_probability"][i] or 0,
                "icono": ic,
            }
        )

    dias = []
    dd = d["daily"]
    for i, fecha in enumerate(dd["time"]):
        f = datetime.strptime(fecha, "%Y-%m-%d")
        ic, tx = _wmo(dd["weather_code"][i])
        dias.append(
            {
                "dia": "Avui" if i == 0 else comun.DIAS[f.weekday()],
                "icono": ic,
                "texto": tx,
                "max": round(dd["temperature_2m_max"][i]),
                "min": round(dd["temperature_2m_min"][i]),
                "lluvia": dd["precipitation_probability_max"][i] or 0,
            }
        )

    lluvia_hoy = max((x["lluvia"] for x in horas), default=0)
    return {
        "lugar": u["nombre"],
        "temp": round(c["temperature_2m"]),
        "sensacion": round(c["apparent_temperature"]),
        "viento": round(c["wind_speed_10m"]),
        "humedad": c.get("relative_humidity_2m"),
        "icono": icono,
        "texto": texto,
        "codigo": int(c.get("weather_code") or 0),  # código WMO: la ficha elige su color con él
        "es_dia": c.get("is_day", 1) == 1,
        "lluvia_12h": lluvia_hoy,
        "salida_sol": dd["sunrise"][0][11:16],
        "puesta_sol": dd["sunset"][0][11:16],
        "horas": horas,
        "dias": dias[:6],
    }
