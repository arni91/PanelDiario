"""Tests del catálogo de deportes (catalog/sports.py)."""

from panel_diario.catalog import sports


def test_cada_deporte_de_equipos_tiene_competiciones() -> None:
    assert all(sports.leagues_of(s) for s in sports.SPORTS)


def test_cada_competicion_es_de_un_deporte_del_desplegable_y_sin_repetir() -> None:
    assert {lg.sport for lg in sports.LEAGUES} == set(sports.SPORTS)
    assert len({lg.path for lg in sports.LEAGUES}) == len(sports.LEAGUES)


def test_motor_y_equipos_no_comparten_identificador() -> None:
    assert not set(sports.SPORTS) & set(sports.MOTOR)


def test_la_liga_va_antes_que_las_copas() -> None:
    """Un equipo que juega varias competiciones se guarda con la primera: su liga."""
    futbol = [lg.path for lg in sports.leagues_of("futbol")]
    assert futbol.index("soccer/esp.1") < futbol.index("soccer/uefa.champions")
    assert futbol.index("soccer/esp.1") < futbol.index("soccer/esp.copa_del_rey")


def test_calendario_del_futbol_junta_competiciones() -> None:
    assert sports.schedule_path("soccer/esp.1", "83") == "soccer/all/teams/83/schedule"
    assert sports.schedule_path("baseball/mlb", "10") == "baseball/mlb/teams/10/schedule"
