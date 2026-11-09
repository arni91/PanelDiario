"""Traducción de titulares y avisos con el traductor de Google (servicio no oficial).

Los textos se piden en lotes, de uno en uno, con reintentos si Google responde 429 (demasiadas
peticiones), y se guardan en una memoria en disco (configurar_memoria): un texto se traduce una
sola vez aunque el panel se actualice cada 30 minutos o se reinicie. Si algo falla, se muestra
el texto original: el panel no se rompe nunca por la traducción.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Iterable
from pathlib import Path

import requests

from panel_diario.fuentes import comun

log = logging.getLogger("panel")

# Regla: las noticias en los idiomas de "conservar" (por defecto catalán y castellano) se quedan
# tal cual; las demás (inglés, francés...) se traducen a "idioma" (por defecto catalán).
# Si la fuente declara su "idioma" en config.json, ni se consulta el traductor; si no, el
# traductor detecta el idioma de cada texto y, si es uno de los que se conservan, queda el original.

# translate_a/t acepta varios "q" en una petición y devuelve [traducción, idioma detectado] de cada
# uno: un lote puede mezclar idiomas. Por GET, la URL admite holgadamente 3000 caracteres de texto.
URL = "https://translate.googleapis.com/translate_a/t"
MAX_CARACTERES_LOTE = 3000
MAX_TEXTOS_LOTE = 50
REINTENTOS = 3  # tras el primer intento: esperas de 1, 2 y 4 s
ESPERA_BASE = 1.0
# Si Google sigue respondiendo 429 tras los reintentos, no se le vuelve a pedir nada en este rato
PAUSA_TRAS_LIMITE = 300.0
MAX_MEMORIA = 5000

# ---------------------------------------------------------------------------
# Memoria de traducciones (en disco)
# ---------------------------------------------------------------------------


class MemoriaTraduccions:
    """(idioma destino, texto) -> (traducción, idioma detectado). Se guarda en un JSON si hay ruta.

    Se guarda el idioma detectado, no la decisión de conservar o traducir: así la memoria sirve
    aunque cambie la lista "conservar" de config.json.
    """

    def __init__(self, ruta: Path | None = None, maximo: int = MAX_MEMORIA) -> None:
        self.ruta = ruta
        self.maximo = maximo
        self._entradas: dict[tuple[str, str], tuple[str, str]] = {}
        self._cambios = False
        if ruta and ruta.exists():
            self._cargar(ruta)

    def _cargar(self, ruta: Path) -> None:
        try:
            filas = json.loads(ruta.read_text(encoding="utf-8"))
            for desti, text, traduit, idioma in filas:
                self._entradas[(desti, text)] = (traduit, idioma)
        except (OSError, ValueError, TypeError) as ex:
            log.warning("Memoria de traducciones ilegible, se empieza de cero: %s", ex)
            self._entradas.clear()

    def get(self, desti: str, text: str) -> tuple[str, str] | None:
        return self._entradas.get((desti, text))

    def put(self, desti: str, text: str, traduit: str, idioma: str) -> None:
        self._entradas[(desti, text)] = (traduit, idioma)
        while len(self._entradas) > self.maximo:  # se olvidan las más antiguas
            del self._entradas[next(iter(self._entradas))]
        self._cambios = True

    def desar(self) -> None:
        """Escribe el JSON si hay cambios (primero en un temporal: un corte no deja el fichero a medias)."""
        if not self.ruta or not self._cambios:
            return
        filas = [[d, t, tr, i] for (d, t), (tr, i) in self._entradas.items()]
        tmp = self.ruta.with_name(self.ruta.name + ".tmp")
        try:
            tmp.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.ruta)
            self._cambios = False
        except OSError as ex:
            log.warning("No se puede guardar la memoria de traducciones: %s", ex)


_memoria = MemoriaTraduccions()
_lock = threading.Lock()  # noticias y avisos se actualizan en hilos distintos: una petición cada vez
_pausa_hasta = 0.0


def configurar_memoria(ruta: Path) -> None:
    """Usa `ruta` como memoria en disco (la llama app.py al arrancar, con un fichero de DATOS_DIR)."""
    global _memoria
    with _lock:
        _memoria = MemoriaTraduccions(ruta)


# ---------------------------------------------------------------------------
# Peticiones al traductor
# ---------------------------------------------------------------------------


class ErrorTraductor(Exception):
    """El traductor no ha respondido bien (red, HTTP o formato). El mensaje es corto y sin textos."""


class LimiteTraductor(ErrorTraductor):
    """Google sigue respondiendo 429 después de todos los reintentos."""


def lotes(
    textos: list[str], max_caracteres: int = MAX_CARACTERES_LOTE, max_textos: int = MAX_TEXTOS_LOTE
) -> list[list[str]]:
    """Reparte los textos en lotes que no pasan de `max_caracteres` ni de `max_textos`."""
    resultado: list[list[str]] = []
    actual: list[str] = []
    caracteres = 0
    for t in textos:
        if actual and (caracteres + len(t) > max_caracteres or len(actual) >= max_textos):
            resultado.append(actual)
            actual, caracteres = [], 0
        actual.append(t)
        caracteres += len(t)
    if actual:
        resultado.append(actual)
    return resultado


def _estado_http(ex: requests.RequestException) -> int:
    return ex.response.status_code if isinstance(ex, requests.HTTPError) and ex.response is not None else 0


def _describir(ex: requests.RequestException) -> str:
    """Motivo corto para el log. El texto de las excepciones de requests incluye la URL entera,
    con todos los titulares del lote: una línea de log de varios KB que no aporta nada."""
    estado = _estado_http(ex)
    return f"HTTP {estado}" if estado else type(ex).__name__


def _pedir_lote(textos: list[str], desti: str) -> list[tuple[str, str]]:
    """[(traducción, idioma detectado)] de cada texto. Reintenta con espera exponencial si hay 429 o 5xx."""
    for intento in range(REINTENTOS + 1):
        try:
            r = comun.get(
                URL,
                headers={"User-Agent": comun.UA_NAVEGADOR},
                params={"client": "gtx", "sl": "auto", "tl": desti, "q": textos},
            )
            return _leer_respuesta(r.json(), len(textos))
        except requests.RequestException as ex:
            estado = _estado_http(ex)
            if not (estado == 429 or estado >= 500) or intento == REINTENTOS:
                tipo = LimiteTraductor if estado == 429 else ErrorTraductor
                raise tipo(_describir(ex)) from ex
            espera = ESPERA_BASE * 2**intento
            log.info("Traductor: %s; reintento en %.0f s", _describir(ex), espera)
            time.sleep(espera)
    raise AssertionError("inalcanzable")  # el bucle siempre devuelve o lanza


def _leer_respuesta(datos: object, n: int) -> list[tuple[str, str]]:
    """Valida el formato [[traducción, idioma], ...] con un elemento por texto pedido."""
    if not isinstance(datos, list) or len(datos) != n:
        raise ValueError(f"respuesta inesperada del traductor ({type(datos).__name__})")
    resultado = []
    for fila in datos:
        if not (isinstance(fila, list) and len(fila) >= 2 and isinstance(fila[0], str)):
            raise ValueError("respuesta inesperada del traductor (fila sin traducción)")
        resultado.append((fila[0].strip(), str(fila[1])))
    return resultado


def traduir_textos(textos: Iterable[str], desti: str = "ca", conservar: Iterable[str] = ()) -> dict[str, str]:
    """{texto: texto a mostrar}. Nunca lanza excepción: lo que no se puede traducir queda como estaba."""
    global _pausa_hasta
    conservar = set(conservar)
    unicos = list(dict.fromkeys(t for t in textos if t and t.strip()))
    with _lock:
        pendientes = [t for t in unicos if _memoria.get(desti, t) is None]
        if pendientes and time.monotonic() < _pausa_hasta:
            log.info("Traductor en pausa por límite de peticiones: %d textos sin traducir", len(pendientes))
        elif pendientes:
            for lote in lotes(pendientes):
                try:
                    for text, (traduit, idioma) in zip(lote, _pedir_lote(lote, desti), strict=True):
                        _memoria.put(desti, text, traduit or text, idioma)
                except LimiteTraductor as ex:
                    _pausa_hasta = time.monotonic() + PAUSA_TRAS_LIMITE
                    restantes = len(pendientes) - pendientes.index(lote[0])
                    log.warning(
                        "Traducción: %d textos sin traducir; pausa de %.0f s (%s)", restantes, PAUSA_TRAS_LIMITE, ex
                    )
                    break  # no insistir: el resto de lotes también recibiría 429
                except Exception as ex:  # noqa: BLE001  (red, formato...): se sigue con el siguiente lote
                    log.warning("Traducción: lote de %d textos sin traducir (%s)", len(lote), ex)
            _memoria.desar()
        return {t: _mostrar(t, desti, conservar) for t in unicos}


def _mostrar(text: str, desti: str, conservar: set[str]) -> str:
    guardado = _memoria.get(desti, text)
    if guardado is None:
        return text
    traduit, idioma = guardado
    return text if idioma in conservar else traduit


def traduir_noticies(salida: dict, cfg: dict) -> None:
    """Traduce titulares y resúmenes que no están en un idioma que se conserva (modifica `salida`)."""
    t = cfg.get("traduccio") or {}
    if not t.get("activa", True):
        return
    desti = t.get("idioma", "ca")
    conservar = set(t.get("conservar", ["ca", "es"]))
    pendientes = [nt for llista in salida.values() for nt in llista if nt.get("idioma") not in conservar]
    textos = [txt for nt in pendientes for txt in (nt["titulo"], nt.get("resumen", "")) if txt]
    traduccions = traduir_textos(textos, desti, conservar)
    for nt in pendientes:
        nt["titulo"] = traduccions.get(nt["titulo"], nt["titulo"])
        if nt.get("resumen"):
            nt["resumen"] = traduccions.get(nt["resumen"], nt["resumen"])
