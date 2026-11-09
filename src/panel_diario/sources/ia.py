"""Filtro opcional con IA (API de Claude): elige las noticias más relevantes y las resume.

Solo se usa si hay clave en config.json (claude.api_key); app.py lo llama como mucho cada N horas.
"""

from __future__ import annotations

import json
import re

import requests


def filtrar_con_ia(cfg: dict, noticias: dict) -> dict:
    """Pide a Claude las noticias más relevantes de cada pestaña y un resumen; sin clave, no hace nada."""
    ia = cfg.get("claude") or {}
    clave = (ia.get("api_key") or "").strip()
    if not clave:
        return noticias

    catalogo, idx = [], {}
    for cat, lista in noticias.items():
        for i, it in enumerate(lista):
            nid = f"{cat}-{i}"
            idx[nid] = (cat, it)
            catalogo.append(
                {"id": nid, "seccion": cat, "titular": it["titulo"], "medios": [it["medio"]] + it["otros_medios"]}
            )

    prompt = (
        "Eres un editor de noticias neutral. Te paso titulares de hoy agrupados por sección "
        "(incluye cuántos medios los publican). Para cada sección, devuelve los ids de las "
        f"{cfg.get('titulares_por_pestana', 8)} noticias más relevantes e interesantes, ordenadas, "
        "descartando sucesos menores, ruido y contenido de opinión. Para cada id elegido escribe un resumen "
        "factual y neutral de máximo 20 palabras en castellano, sin adjetivos valorativos.\n"
        "Responde SOLO con JSON con esta forma: "
        '{"secciones": {"mundo": ["id", ...], "catalunya": [...], ...}, '
        '"resumenes": {"id": "texto", ...}}\n\n' + json.dumps(catalogo, ensure_ascii=False)
    )
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": clave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": ia.get("modelo", "claude-haiku-5-5"),
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )
    r.raise_for_status()
    texto = "".join(b.get("text", "") for b in r.json().get("content", []))
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError("la IA no ha devuelto JSON")
    datos = json.loads(m.group(0))

    nuevo = {}
    for cat, ids in datos.get("secciones", {}).items():
        lista = []
        for nid in ids:
            if nid in idx:
                it = dict(idx[nid][1])
                it["resumen_ia"] = datos.get("resumenes", {}).get(nid, "")
                lista.append(it)
        if lista:
            nuevo[cat] = lista
    for cat in noticias:  # si la IA omite una sección, se queda la original
        nuevo.setdefault(cat, noticias[cat])
    return nuevo
