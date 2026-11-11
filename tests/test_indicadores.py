"""Indicadores técnicos y reglas de decisión (analisis.py). Solo biblioteca estándar."""
import math

import pytest

import analisis as A


def test_media_movil_simple():
    assert A._sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_media_exponencial_de_serie_constante():
    out = A._ema([10.0] * 30, 12)
    assert out[10] is None
    assert out[11] == pytest.approx(10.0)
    assert out[-1] == pytest.approx(10.0)


def test_rsi_en_los_extremos():
    subiendo = [float(i) for i in range(1, 40)]
    bajando = [float(i) for i in range(40, 1, -1)]
    assert A._rsi(subiendo)[-1] == pytest.approx(100.0)
    assert A._rsi(bajando)[-1] == pytest.approx(0.0, abs=1e-9)


def test_rsi_necesita_mas_datos_que_la_ventana():
    assert all(v is None for v in A._rsi([1.0, 2.0, 3.0], n=14))


def test_bollinger_serie_plana_queda_al_centro():
    mid, up, lo, pb = A._bollinger([5.0] * 25)
    assert mid[-1] == 5.0 and up[-1] == lo[-1] == 5.0
    assert pb[-1] == 0.5


def test_bollinger_bandas_simetricas():
    datos = [100 + (i % 7) for i in range(40)]
    mid, up, lo, _ = A._bollinger(datos)
    assert up[-1] - mid[-1] == pytest.approx(mid[-1] - lo[-1])


def test_regresion_lineal_de_una_recta():
    pendiente, r2 = A._linreg([2.0 * x + 1 for x in range(30)])
    assert pendiente == pytest.approx(2.0)
    assert r2 == pytest.approx(1.0)


def test_regresion_lineal_sin_variacion():
    pendiente, r2 = A._linreg([3.0] * 10)
    assert pendiente == 0.0 and r2 == 0.0


@pytest.mark.parametrize("puntaje, esperado", [
    (100, "COMPRA FUERTE"), (45, "COMPRA FUERTE"), (44.9, "COMPRAR"), (20, "COMPRAR"),
    (19.9, "MANTENER"), (0, "MANTENER"), (-19.9, "MANTENER"), (-20, "VENDER"),
    (-44.9, "VENDER"), (-45, "VENTA FUERTE"), (-100, "VENTA FUERTE"),
])
def test_umbrales_de_decision(puntaje, esperado):
    assert A.veredicto(puntaje) == esperado


def test_toda_decision_tiene_texto_y_accion():
    for clave in ["COMPRA FUERTE", "COMPRAR", "MANTENER", "VENDER", "VENTA FUERTE"]:
        assert A.DECISION[clave] and A.ACCION[clave]


def test_indicadores_devuelven_series_del_mismo_largo():
    cierres = [100 + math.sin(i / 5) * 5 + i * 0.1 for i in range(120)]
    ind = A.indicadores(cierres)
    for nombre, serie in ind.items():
        assert len(serie) == len(cierres), nombre
