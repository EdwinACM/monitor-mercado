"""Proyecciones, portafolio y duración (proyeccion.py). Solo biblioteca estándar."""
import math

import pytest

import proyeccion as P


def test_volatilidad_ewma_de_rendimientos_cero_es_cero():
    assert all(s == 0 for s in P.sigmas_ewma([0.0] * 40))


def test_volatilidad_ewma_reacciona_a_un_choque():
    rend = [0.001] * 40 + [0.08] + [0.001] * 5
    sig = P.sigmas_ewma(rend)
    assert sig[40] > 3 * sig[39]
    assert sig[-1] < sig[40]


def test_proyeccion_requiere_historia_suficiente():
    assert P.proyectar([100.0] * 59) is None


def test_proyeccion_de_serie_regular_devuelve_resultado():
    cierres = [100 * math.exp(0.001 * i + 0.01 * math.sin(i)) for i in range(400)]
    r = P.proyectar(cierres)
    assert r is not None


def test_simplex_suma_uno_y_no_es_negativo():
    w = P._proy_simplex([0.7, -0.4, 0.5, 0.2])
    assert sum(w) == pytest.approx(1.0)
    assert min(w) >= 0


def test_portafolio_necesita_dos_activos_y_veinte_datos():
    assert P.portafolio({"A": [0.01] * 30}) is None
    assert P.portafolio({"A": [0.01] * 10, "B": [0.02] * 10}) is None


def test_portafolio_de_minima_varianza_no_supera_al_equiponderado():
    azar = [((i * 7919) % 101 - 50) / 5000 for i in range(120)]
    otro = [((i * 104729) % 97 - 48) / 8000 for i in range(120)]
    tercero = [x * 0.5 + y * 0.5 for x, y in zip(azar, otro)]
    r = P.portafolio({"A": azar, "B": otro, "C": tercero})
    assert r["min_varianza"]["vol_anual"] <= r["equiponderado"]["vol_anual"] + 1e-6
    assert sum(r["min_varianza"]["pesos"]) == pytest.approx(100.0, abs=0.1)
    assert r["razon_diversificacion"] >= 1.0


def test_duracion_de_cetes_a_28_dias():
    d = P.duracion("CETES 28 días", 7.0)
    assert d == pytest.approx(28 / 360 / (1 + 0.07 * 28 / 360))


def test_duracion_de_un_bono_largo_es_mayor_que_la_de_cetes():
    assert P.duracion("Bonos M 10 años", 9.0) > 5 * P.duracion("CETES 28 días", 9.0)


def test_duracion_de_tasa_flotante_es_de_28_dias():
    assert P.duracion("Bondes F 2 años", 8.0) == pytest.approx(28 / 360)


def test_duracion_sin_valor():
    assert P.duracion("CETES 28 días", None) is None


def test_proyeccion_de_deuda_sobre_una_recta():
    serie = [8.0 + 0.1 * i for i in range(12)]
    r = P.proyectar_deuda(serie, pasos=(1,))
    p = r["proyecciones"][0]
    assert r["pendiente"] == pytest.approx(0.1, abs=1e-3)
    assert p["centro"] == pytest.approx(9.2, abs=0.01)
    assert p["bajo"] <= p["centro"] <= p["alto"]


def test_proyeccion_de_deuda_con_pocos_datos():
    assert P.proyectar_deuda([8.0, 8.1, 8.2]) is None
