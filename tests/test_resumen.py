"""Texto del resumen del mercado (analisis.resumen_mercado)."""
import analisis as A


def _item(nombre, var, veredicto, score, ret=1.0):
    return {"nombre": nombre, "ticker": nombre[:4], "var_pct": var, "veredicto": veredicto,
            "score": score, "ret_periodo": ret}


def test_resumen_sin_datos():
    assert A.resumen_mercado([])["texto"] == "Sin datos."


def test_una_sola_decision_de_comprar_va_en_singular():
    items = [_item("Uno", 1.0, "COMPRAR", 30), _item("Dos", -1.0, "MANTENER", 0),
             _item("Tres", -2.0, "VENDER", -30)]
    texto = A.resumen_mercado(items)["texto_periodo"]
    assert "1 decisión de comprar" in texto
    assert "1 decisiones" not in texto


def test_varias_o_ninguna_decision_de_comprar_va_en_plural():
    items = [_item("Uno", 1.0, "COMPRAR", 30), _item("Dos", 2.0, "COMPRA FUERTE", 60)]
    assert "2 decisiones de comprar" in A.resumen_mercado(items)["texto_periodo"]
    sin_compras = [_item("Uno", 1.0, "MANTENER", 0), _item("Dos", -1.0, "VENDER", -30)]
    assert "0 decisiones de comprar" in A.resumen_mercado(sin_compras)["texto_periodo"]


def test_cuenta_las_senales_fuertes_con_su_lado():
    items = [_item("Uno", 1.0, "COMPRA FUERTE", 60), _item("Dos", -1.0, "VENTA FUERTE", -60)]
    r = A.resumen_mercado(items)
    assert r["senales"] == {"COMPRAR": 1, "VENDER": 1}
    assert r["suben"] == 1 and r["bajan"] == 1


def test_el_sesgo_sigue_al_puntaje_promedio():
    positivo = [_item("A", 1.0, "COMPRAR", 40), _item("B", 1.0, "COMPRAR", 30)]
    negativo = [_item("A", -1.0, "VENDER", -40), _item("B", -1.0, "VENDER", -30)]
    assert A.resumen_mercado(positivo)["sesgo"] == "positivo"
    assert A.resumen_mercado(negativo)["sesgo"] == "negativo"
