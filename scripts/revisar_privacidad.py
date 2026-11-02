"""Revisión de privacidad: bloquea el commit si un fichero versionado contiene algo personal.

Busca, sin distinguir mayúsculas, los términos de .privado/terminos.txt (lista personal, fuera de git)
y cualquier cosa con forma de clave, token o dirección iCal secreta. Se ejecuta desde pre-commit
y también a mano:  python scripts/revisar_privacidad.py [ficheros...]
Sin ficheros, revisa todos los que git versionaría (los ignorados por .gitignore no cuentan).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TERMINOS = RAIZ / ".privado" / "terminos.txt"

# Formas típicas de secretos. Se buscan aunque no estén en la lista de términos.
PATRONES = {
    "clave hexadecimal larga": re.compile(r"\b[0-9a-f]{32,}\b", re.I),
    "clave de Anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    "token de GitHub": re.compile(r"\b(ghp_|gho_|github_pat_)[A-Za-z0-9_]{20,}"),
    "clave de Google": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    # Se escribe por partes para que este mismo fichero no dé positivo en la revisión
    "dirección iCal secreta": re.compile(r"calendar/ical/[^\s\"']+/priv" + "ate-", re.I),
}


def leer_terminos(ruta: Path) -> list[str]:
    """Un término por línea; se ignoran las vacías y las que empiezan por #."""
    if not ruta.exists():
        return []
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return [t.strip() for t in lineas if t.strip() and not t.lstrip().startswith("#")]


def ficheros_versionados() -> list[Path]:
    """Ficheros que git versiona o versionaría (incluye los nuevos sin añadir, no los ignorados)."""
    salida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    return [RAIZ / f for f in salida.splitlines() if (RAIZ / f).is_file()]


def revisar_texto(texto: str, terminos: list[str]) -> list[tuple[int, str]]:
    """Devuelve (número de línea, motivo) de cada hallazgo. El motivo nunca incluye el secreto."""
    hallazgos = []
    for n, linea in enumerate(texto.splitlines(), start=1):
        minus = linea.lower()
        for t in terminos:
            if t.lower() in minus:
                hallazgos.append((n, f"término privado «{t}»"))
        for motivo, patron in PATRONES.items():
            if patron.search(linea):
                hallazgos.append((n, motivo))
    return hallazgos


def main(argv: list[str]) -> int:
    terminos = leer_terminos(TERMINOS)
    if not terminos:
        print(f"Aviso: no hay términos en {TERMINOS.relative_to(RAIZ)}; solo se buscan formas de claves.")
    rutas = [Path(a).resolve() for a in argv] if argv else ficheros_versionados()
    total = 0
    for ruta in rutas:
        if ruta == TERMINOS.resolve():
            continue
        try:
            texto = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue   # binarios (imágenes...) y ficheros borrados: no hay texto que revisar
        for n, motivo in revisar_texto(texto, terminos):
            print(f"{ruta.relative_to(RAIZ)}:{n}: {motivo}")
            total += 1
    if total:
        print(f"\nRevisión de privacidad: {total} hallazgos. No hagas el commit hasta dejarlos genéricos.")
        return 1
    print(f"Revisión de privacidad: limpio ({len(rutas)} ficheros).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
