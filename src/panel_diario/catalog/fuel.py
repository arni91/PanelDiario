"""Catálogo público de carburantes: los combustibles con precio medio y las provincias de España.

Los campos de precio y los códigos de provincia son los de la API pública de precios de
carburantes del Ministerio (ServiciosRESTCarburantes: EstacionesTerrestres/FiltroProvincia y
Listados/Provincias, comprobados el 13-11-2026). Cada provincia lleva su nombre en catalán y los
nombres con que la puede dar la geocodificación (castellano, euskera, gallego...), para reconocer
la de la ciudad del panel.
"""

from __future__ import annotations

from dataclasses import dataclass

from panel_diario.sources import comun


@dataclass(frozen=True)
class Product:
    name: str
    ministry_field: str  # campo con su precio en cada gasolinera de la API


# Combustibles de los que el panel da el precio medio, en el orden en que salen
PRODUCTS: tuple[Product, ...] = (
    Product("Gasolina 95", "Precio Gasolina 95 E5"),
    Product("Gasolina 98", "Precio Gasolina 98 E5"),
    Product("Dièsel", "Precio Gasoleo A"),
)

# Código de provincia -> (nombre en catalán, otros nombres con que puede llegar)
PROVINCES: dict[str, tuple[str, ...]] = {
    "01": ("Àlaba", "Araba", "Álava"),
    "02": ("Albacete",),
    "03": ("Alacant", "Alicante"),
    "04": ("Almeria", "Almería"),
    "05": ("Àvila", "Ávila"),
    "06": ("Badajoz",),
    "07": ("Illes Balears", "Islas Baleares", "Baleares", "Balears"),
    "08": ("Barcelona",),
    "09": ("Burgos",),
    "10": ("Càceres", "Cáceres"),
    "11": ("Cadis", "Cádiz"),
    "12": ("Castelló", "Castellón"),
    "13": ("Ciudad Real",),
    "14": ("Còrdova", "Córdoba"),
    "15": ("la Corunya", "A Coruña", "La Coruña"),
    "16": ("Conca", "Cuenca"),
    "17": ("Girona", "Gerona"),
    "18": ("Granada",),
    "19": ("Guadalajara",),
    "20": ("Guipúscoa", "Gipuzkoa", "Guipúzcoa"),
    "21": ("Huelva",),
    "22": ("Osca", "Huesca"),
    "23": ("Jaén",),
    "24": ("Lleó", "León"),
    "25": ("Lleida", "Lérida"),
    "26": ("la Rioja", "La Rioja"),
    "27": ("Lugo",),
    "28": ("Madrid",),
    "29": ("Màlaga", "Málaga"),
    "30": ("Múrcia", "Murcia"),
    "31": ("Navarra", "Nafarroa"),
    "32": ("Ourense", "Orense"),
    "33": ("Astúries", "Asturias"),
    "34": ("Palència", "Palencia"),
    "35": ("Las Palmas",),
    "36": ("Pontevedra",),
    "37": ("Salamanca",),
    "38": ("Santa Cruz de Tenerife",),
    "39": ("Cantàbria", "Cantabria"),
    "40": ("Segòvia", "Segovia"),
    "41": ("Sevilla",),
    "42": ("Sòria", "Soria"),
    "43": ("Tarragona",),
    "44": ("Terol", "Teruel"),
    "45": ("Toledo",),
    "46": ("València", "Valencia"),
    "47": ("Valladolid",),
    "48": ("Biscaia", "Bizkaia", "Vizcaya"),
    "49": ("Zamora",),
    "50": ("Saragossa", "Zaragoza"),
    "51": ("Ceuta",),
    "52": ("Melilla",),
}


def find_province(name: str) -> str | None:
    """Código de la provincia con ese nombre en cualquiera de sus idiomas, sin mirar acentos ni mayúsculas."""
    wanted = comun.normalizar(name.strip())
    return next((pid for pid, names in PROVINCES.items() if wanted in {comun.normalizar(n) for n in names}), None)
