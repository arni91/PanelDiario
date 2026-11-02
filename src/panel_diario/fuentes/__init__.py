"""Fuentes de datos del panel: un módulo por fuente.

Cada obtener_*() devuelve un dict serializable a JSON. Si la fuente falla, lanza una excepción y
estado.py conserva el último dato bueno. Si a la sección le falta su clave en config.json,
devuelve {"sin_clave"/"sin_url"/"sin_configurar": True} y la interfaz la oculta.
"""
