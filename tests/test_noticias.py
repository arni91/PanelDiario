"""Tests de las noticias (datos.py): antigüedad por fuente, límite por pestaña y tema de Cultura.

Los feeds RSS se sustituyen por XML inventado (mock): no se usa internet.
"""

import time
import types
from email.utils import formatdate

from panel_diario import datos


def rss(titulares):
    """Feed RSS mínimo. titulares = [(título, horas desde que se publicó)]."""
    ahora = time.time()
    items = "".join(
        f"<item><title>{t}</title><link>https://x/{i}</link><pubDate>{formatdate(ahora - h * 3600)}</pubDate></item>"
        for i, (t, h) in enumerate(titulares)
    )
    return f"<rss><channel>{items}</channel></rss>".encode()


def preparar(monkeypatch, feeds):
    monkeypatch.setattr(datos, "_get", lambda url, **k: types.SimpleNamespace(content=feeds[url]))


def test_cultura_mira_un_mes_y_las_noticias_36_horas(monkeypatch):
    titulares = [("Concierto techno en la sala", 10 * 24), ("Exposición nueva en el museo", 2)]
    preparar(monkeypatch, {"cult": rss(titulares), "mundo": rss(titulares)})
    cfg = {
        "noticias_horas_max": 36,
        "fuentes": {
            "cultura": [{"nombre": "G", "url": "cult", "horas_max": 720, "tema": "Espais"}],
            "mundo": [{"nombre": "M", "url": "mundo"}],
        },
    }
    noticias, errores = datos.obtener_noticias(cfg)
    assert errores == []
    assert len(noticias["cultura"]) == 2  # la de hace 10 días entra en Cultura
    assert len(noticias["mundo"]) == 1  # pero no en Mundo (más de 36 h)
    assert all(n["tema"] == "Espais" for n in noticias["cultura"])


def test_limite_de_titulares_por_pestana(monkeypatch):
    # Titulares sin palabras en común: si comparten 2 o más, el panel los agrupa como la misma noticia
    titulares = [
        (t, 1)
        for t in [
            "Elecciones anticipadas en Portugal",
            "Terremoto sacude Japón",
            "Aprobada vacuna contra dengue",
            "Lanzan satélite meteorológico europeo",
            "Huelga ferroviaria paraliza Francia",
            "Inflación baja ligeramente en octubre",
            "Incendio forestal arrasa Galicia",
            "Cumbre climática termina sin acuerdo",
            "Museo Picasso amplía horario",
            "Estadio Olímpico reabre puertas",
            "Volcán islandés entra erupción",
            "Puerto Valencia bate récord",
        ]
    ]
    preparar(monkeypatch, {"a": rss(titulares), "b": rss(titulares)})
    cfg = {
        "titulares_por_pestana": 5,
        "titulares_por_categoria": {"cultura": 10},
        "fuentes": {"mundo": [{"nombre": "M", "url": "a"}], "cultura": [{"nombre": "C", "url": "b"}]},
    }
    noticias, _ = datos.obtener_noticias(cfg)
    assert len(noticias["mundo"]) == 5
    assert len(noticias["cultura"]) == 10


def test_filtre_exclou_infantil_i_exigeix_paraules():
    items = [
        {"titulo": "Taller de titelles per a nens al barri", "resumen": ""},
        {"titulo": "Festa major al parc", "resumen": ""},
        {"titulo": "Concierto en Madrid", "resumen": ""},
        {"titulo": "Concierto en Girona", "resumen": ""},
    ]
    # Exclou el que és infantil (sense accents ni majúscules)
    assert [i["titulo"] for i in datos.filtrar_paraules(items, None, ["nens", "titelles"])] == [
        "Festa major al parc",
        "Concierto en Madrid",
        "Concierto en Girona",
    ]
    # Exigeix que parli de Girona
    assert [i["titulo"] for i in datos.filtrar_paraules(items, ["girona"], None)] == ["Concierto en Girona"]


def test_filtre_respecta_inici_de_paraula():
    # "nens" no ha d'eliminar "Llenç" ni "antenes"; sí "nenes"? no: només paraules que comencen per "nens"
    items = [{"titulo": "Exposició de llençols i antenes", "resumen": ""}]
    assert datos.filtrar_paraules(items, None, ["nens"]) == items


def test_maxim_de_noticies_per_font():
    noticies = [{"titulo": f"t{i}", "tema": "", "medio": "Revista A"} for i in range(6)] + [
        {"titulo": "x", "tema": "Museus i expos", "medio": "Diari B"}
    ]
    sortida = datos.limitar_per_font(noticies, 4)
    assert [n["titulo"] for n in sortida] == ["t0", "t1", "t2", "t3", "x"]
    assert datos.limitar_per_font(noticies, None) == noticies


def test_neteja_resums_de_wordpress():
    assert datos.netejar_resum("Una expo al museu sobre la nit. [&#8230;]") == "Una expo al museu sobre la nit."
    assert datos.netejar_resum("Festa al barri [...]") == "Festa al barri"
    text = "Concert a la sala. L'entrada Concert va aparèixer primer a Revista A."
    assert datos.netejar_resum(text) == "Concert a la sala."
    assert datos.netejar_resum("Text normal") == "Text normal"
