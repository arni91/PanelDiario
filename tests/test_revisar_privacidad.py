"""Tests de la revisión de privacidad (scripts/revisar_privacidad.py): términos, formas de claves y lista."""

from pathlib import Path

import revisar_privacidad as rp  # scripts/ está en el pythonpath de pytest (pyproject.toml)


def test_encuentra_terminos_sin_distinguir_mayusculas():
    texto = "linea limpia\nVivo en CIUDADFALSA desde hace años"
    assert rp.revisar_texto(texto, ["ciudadfalsa"]) == [(2, "término privado «ciudadfalsa»")]


def test_encuentra_formas_de_claves_sin_lista():
    # Los ejemplos se montan por partes para que este fichero no dé positivo en la revisión real
    clave = "0123456789abcdef" * 2
    url = "https://x/calendar/ical/a%40b/" + "priv" + "ate-zz/basic.ics"
    texto = f'clave = "{clave}"\nurl = "{url}"'
    assert rp.revisar_texto(texto, []) == [(1, "clave hexadecimal larga"), (2, "dirección iCal secreta")]


def test_en_uv_lock_no_busca_hexadecimal_pero_si_terminos():
    linea = 'url = "https://x/' + "cd" * 30 + '/p.whl", hash = "sha256:' + "ab" * 32 + '" ciudadfalsa'
    uv_lock = rp.patrones_para(Path("uv.lock"))
    assert rp.revisar_texto(linea, ["ciudadfalsa"], uv_lock) == [(1, "término privado «ciudadfalsa»")]
    assert rp.revisar_texto(linea, [], rp.patrones_para(Path("otro.py"))) == [(1, "clave hexadecimal larga")]


def test_texto_limpio():
    assert rp.revisar_texto("Ciudad de ejemplo: Girona", ["ciudadfalsa"]) == []


def test_lista_ignora_comentarios_y_lineas_vacias(tmp_path):
    ruta = tmp_path / "terminos.txt"
    ruta.write_text("# comentario\n\nuno\n  dos  \n", encoding="utf-8")
    assert rp.leer_terminos(ruta) == ["uno", "dos"]
    assert rp.leer_terminos(tmp_path / "no_existe.txt") == []
