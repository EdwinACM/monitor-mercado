"""Ejercicio de rendimientos: 5 acciones de EE. UU., el IPC, el S&P 500 y 5 instrumentos de deuda.

Entrega un Excel con las fórmulas de la clase y una presentación ejecutiva de 8 páginas en PDF.

    Ra (variación diaria)          = ((precio de hoy / precio del día anterior) - 1) x 100
    Rendimiento efectivo           = ((precio final / precio inicial) - 1) x 100
    Rendimiento promedio (Rprom)   = promedio de los Ra
    Diferencia de rendimiento      = Ra - Rprom (y su cuadrado)
    Beta                           = Cov(índice, acción) / Var(índice)

El periodo empieza el 1 de marzo de 2026 y termina el 25 de noviembre de 2026 (o en el último cierre disponible si esa fecha aún no llega).
"""
import math
from datetime import date, datetime, timedelta
from statistics import mean, median, stdev, variance

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

import excel as X
import fichas
import glosario
import reportes as R
import server

FIN_ANALISIS = date(2026, 11, 25)
G, GOSC, GSUAVE, GRIS_S, GTXT = "750946", "4F0630", "F7ECF1", "E8E9EA", "636569"
AZUL, NARANJA = "1D63C1", "C8480F"
COLORES = [(29, 99, 193), (200, 72, 15), (10, 127, 88), (168, 109, 0), (194, 59, 120)]
NEGRO, GRIS, BLANCO, GUINDA = (35, 31, 32), (99, 101, 105), (255, 255, 255), (117, 9, 70)
GUINDA_SUAVE, GRIS_SUAVE = (247, 236, 241), (232, 233, 234)
SUBE, BAJA = (0, 100, 63), (179, 38, 30)
TZ = server.TZ
FUENTE = "Calibri"

TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "KO"]
IDX = {"IPC": ("IPC", "S&P/BMV IPC", "ipc"), "SP500": ("S&P 500", "S&P 500", "sp500")}
SECTOR = {"AAPL": "Tecnología", "MSFT": "Tecnología y software", "NVDA": "Semiconductores e inteligencia artificial", "TSLA": "Automóviles eléctricos", "KO": "Consumo (bebidas)"}
SIC_ES = {"Electronic Computers": "Computadoras electrónicas", "Services-Prepackaged Software": "Servicios de software empaquetado", "Semiconductors & Related Devices": "Semiconductores y dispositivos relacionados",
          "Motor Vehicles & Passenger Car Bodies": "Vehículos de motor y carrocerías", "Beverages": "Bebidas"}
PAR = {"AAPL": 0.00001, "MSFT": 0.00000625, "NVDA": 0.001, "TSLA": 0.001, "KO": 0.25}  # valor par por acción, de la portada y el balance de cada 10-K
CONSTITUCION = {"AAPL": "3 de enero de 1977 (California)", "MSFT": "1981 (Washington); sociedad desde 1975", "NVDA": "Abril de 1993 (California); Delaware desde abril de 1998",
                "TSLA": "1 de julio de 2003 (Delaware); Texas desde el 13 de junio de 2024", "KO": "Septiembre de 1919 (Delaware)"}
DEUDA_EQ = {
    "CETES 28 días": ("CETES", "Muy bajo", "Financiar al Gobierno Federal."),
    "BONOS M 10 años": ("BONOS", "Bajo", "Obtener financiamiento de largo plazo para el gobierno."),
    "UDIBONOS 10 años": ("UDIBONOS", "Bajo", "Mantener el poder adquisitivo de la inversión."),
    "PAPEL COMERCIAL": ("PAPEL COMERCIAL", "Medio: depende de la empresa emisora", "Obtener recursos rápidamente."),
    "CERTIFICADOS BURSÁTILES": ("CERTIFICADOS BURSÁTILES", "Variable según la solvencia del emisor", "Financiar proyectos, expansión o capital de trabajo."),
}


# ----------------------------------------------------------------------------- datos
def _stats(ra):
    n = len(ra)
    m, s = mean(ra), stdev(ra)
    cuenta = {}
    for v in ra:
        cuenta[round(v, 10)] = cuenta.get(round(v, 10), 0) + 1
    mx = max(cuenta.values())
    mo = next(v for v in ra if cuenta[round(v, 10)] == mx) if mx > 1 else None
    asim = n / ((n - 1) * (n - 2)) * sum(((v - m) / s) ** 3 for v in ra) if n > 2 and s else None
    curt = (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3)) * sum(((v - m) / s) ** 4 for v in ra) - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))) if n > 3 and s else None
    return {"n": n, "media": m, "error": s / math.sqrt(n), "mediana": median(ra), "moda": mo, "desv": s, "var": variance(ra), "curtosis": curt, "asimetria": asim,
            "rango": max(ra) - min(ra), "min": min(ra), "max": max(ra), "suma": sum(ra)}


def _instrumento(clave, nombre, moneda, ticker, serie, indice=False, volumen=None):
    p = [v for _, v in serie]
    ra = [(p[i] / p[i - 1] - 1) * 100 for i in range(1, len(p))]
    st = _stats(ra)
    return {"clave": clave, "nombre": nombre, "moneda": moneda, "ticker": ticker, "serie": serie, "ra": ra, "stats": st, "efectivo": (p[-1] / p[0] - 1) * 100, "indice": indice,
            "pi": p[0], "pf": p[-1], "fi": serie[0][0], "ff": serie[-1][0], "pmax": max(p), "pmin": min(p), "volumen": volumen or {},
            "sumdif2": sum((r - st["media"]) ** 2 for r in ra)}


def preparar(fin=None):
    """Series de cierre del periodo: 5 acciones de EE. UU., el IPC, el S&P 500, y las tasas de 5 instrumentos de deuda."""
    import contexto
    hoy = datetime.now(TZ).date()
    fin = min(fin or FIN_ANALISIS, FIN_ANALISIS, hoy)
    ini = server.INICIO
    hist = server._historiales()
    res, _ = contexto.series(fin)
    items = []
    for t in TICKERS:
        todos = [(r["fecha"], r["cierre"], r.get("volumen") or 0) for r in hist.get(t, [])]
        rows = [(f, c) for f, c, _ in todos if ini.isoformat() <= f <= fin.isoformat()]
        if len(rows) < 3:
            continue
        it = _instrumento(t, server.ACCIONES[t], server.META[t]["moneda"], t, rows, volumen={f: v for f, _, v in todos if ini.isoformat() <= f <= fin.isoformat()})
        hace = (date.fromisoformat(rows[-1][0]) - timedelta(days=365)).isoformat()
        ant = [c for f, c, _ in todos if f <= hace]
        ult = [c for f, c, _ in todos if f > hace]
        it["cambio_12m"] = (rows[-1][1] / ant[-1] - 1) * 100 if ant else None
        it["max52"], it["min52"] = max(ult), min(ult)
        items.append(it)
    for clave, (corto, nombre, key) in IDX.items():
        serie = [(f, v) for f, v in res.get(key, []) if ini.isoformat() <= f <= fin.isoformat()]
        if len(serie) >= 3:
            items.append(_instrumento(corto, nombre, "puntos", corto, serie, indice=True))
    if not items:
        raise ValueError("No hay precios en el periodo.")
    fechas = sorted({f for it in items for f, _ in it["serie"]})
    deuda = []
    for sd in server.deuda(date.today() - timedelta(days=300)):
        if sd["nombre"] not in DEUDA_EQ:
            continue
        datos = [x for x in sd["datos"] if ini.isoformat() <= x["fecha"] <= fin.isoformat()]
        if len(datos) < 2:
            continue
        es_monto = sd["tipo"] == "monto"
        vals = [x["valor"] / 1000 if es_monto else x["valor"] for x in datos]
        var = [None] + [((vals[i] - vals[i - 1]) if es_monto else (vals[i] - vals[i - 1]) * 100) for i in range(1, len(vals))]
        deuda.append({"nombre": sd["nombre"], "corto": DEUDA_EQ[sd["nombre"]][0], "riesgo": DEUDA_EQ[sd["nombre"]][1], "objetivo": DEUDA_EQ[sd["nombre"]][2], "unidad": sd["unidad"],
                      "serie": [(x["fecha"], v) for x, v in zip(datos, vals)], "var": var, "es_monto": es_monto, "media": mean(vals), "min": min(vals), "max": max(vals),
                      "ult": vals[-1], "fult": datos[-1]["fecha"]})
    return {"inicio": ini.isoformat(), "fin": fin.isoformat(), "ultimo": max(f for it in items for f, _ in it["serie"]), "items": items, "fechas": fechas, "deuda": deuda,
            "completo": fin >= FIN_ANALISIS, "generado": datetime.now(TZ)}


def _acciones(d):
    return [x for x in d["items"] if not x["indice"]]


def _indices(d):
    return [x for x in d["items"] if x["indice"]]


def _por_fecha(it):
    return dict(it["serie"])


def _acumulado(d, it):
    """Rendimiento acumulado (%) en cada fecha del periodo, arrastrando el último cierre en los días sin operación."""
    m, ult, out = _por_fecha(it), None, []
    for f in d["fechas"]:
        if f in m:
            ult = m[f]
        out.append((ult / it["pi"] - 1) * 100 if ult is not None else None)
    return out


def _beta(d, it, idx):
    a, b = _por_fecha(it), _por_fecha(idx)
    com = [f for f in d["fechas"] if f in a and f in b]
    if len(com) < 10:
        return None
    ra = [(a[com[i]] / a[com[i - 1]] - 1) * 100 for i in range(1, len(com))]
    rb = [(b[com[i]] / b[com[i - 1]] - 1) * 100 for i in range(1, len(com))]
    mb, ma = mean(rb), mean(ra)
    n = len(ra)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (n - 1)
    vb, va = variance(rb), variance(ra)
    return {"beta": cov / vb if vb else None, "corr": cov / math.sqrt(va * vb) if va and vb else None, "n": n, "cov": cov * (n - 1) / n, "var": vb * (n - 1) / n}


def _bursatilidad(d):
    """Indicador propio con el volumen de Yahoo Finance: importe operado y rotación diarios, y posición entre las acciones."""
    out = {}
    for it in _acciones(d):
        vol = it["volumen"]
        precios = _por_fecha(it)
        dias = [f for f in precios if vol.get(f)]
        if not dias:
            continue
        F = fichas.datos(it["ticker"]) or {}
        circ = F.get("acciones")
        out[it["clave"]] = {"importe": mean(vol[f] * precios[f] for f in dias) / 1e6, "volumen": mean(vol[f] for f in dias) / 1e6,
                            "rotacion": mean(vol[f] for f in dias) / circ * 100 if circ else None, "dias": len(dias) / len(precios) * 100}
    for i, k in enumerate(sorted(out, key=lambda k: -out[k]["importe"]), 1):
        out[k]["posicion"] = i
    return out


def _ficha(d, it, burs):
    """Todo lo que se sabe de la acción, con cifras reales."""
    F = fichas.datos(it["ticker"]) or {}
    e = fichas._vivo()["empresas"].get(it["ticker"], {})
    a = e.get("acciones", {})
    fin = F.get("financieros")
    cif = {et: (x, y) for et, x, y, _ in fin["filas"]} if fin else {}
    g = next((x for x in glosario.guia({it["ticker"]: it["nombre"]}, server.META, {})["acciones"] if x["ticker"] == it["ticker"]), {})
    emitidas = (a.get("emitidas") or {}).get("valor")
    par = PAR.get(it["ticker"]) or (a.get("valor_par") or {}).get("valor")
    vol = it["stats"]["desv"] * math.sqrt(252)
    crec = lambda k: ((cif[k][0] / cif[k][1] - 1) * 100) if k in cif and cif[k][1] else None
    return {"F": F, "sic": e.get("sic"), "autorizadas": (a.get("autorizadas") or {}).get("valor"), "emitidas": emitidas, "par": par,
            "capital_social": emitidas * par / 1e6 if emitidas and par else None, "cif": cif, "fin": fin, "g": g, "vol": vol,
            "nivel": "baja" if vol < 20 else "media" if vol < 35 else "alta", "betas": {x["clave"]: _beta(d, it, x) for x in _indices(d)},
            "burs": burs.get(it["clave"]), "crec_ing": crec("Ingresos"), "crec_util": crec("Utilidad neta")}


def _razon(it, f):
    partes = []
    if f["fin"] and f["crec_ing"] is not None:
        t = f"En su último ejercicio ({f['fin']['periodos'][0]}) los ingresos cambiaron {f['crec_ing']:+.2f} %"
        partes.append(t + (f" y la utilidad neta {f['crec_util']:+.2f} %." if f["crec_util"] is not None else "."))
    partes.append(f["g"].get("que_la_mueve", ""))
    return " ".join(p for p in partes if p)


def _conclusion(it, f, sp):
    b = f["betas"].get("S&P 500")
    t = f"{it['nombre']} {'subió' if it['efectivo'] > 0 else 'bajó'} {abs(it['efectivo']):.2f} % en el periodo"
    if sp:
        t += f" ({'más' if it['efectivo'] > sp['efectivo'] else 'menos'} que el S&P 500, que rindió {sp['efectivo']:+.2f} %)"
    t += f", con volatilidad anual {f['nivel']} ({f['vol']:.2f} %)"
    return t + (f" y beta de {b['beta']:.2f} frente al S&P 500." if b else ".")


# ------------------------------------------------------------------------------ Excel
AMARILLO = PatternFill("solid", fgColor="FFFF00")
FILA = Side(style="thin", color=GRIS_S)
F_RET = "[Color10]+0.00;[Red]-0.00;0.00"  # verde si sube, rojo si baja
F_PX = "#,##0.00"


def _fnt(**kw):
    return Font(name=FUENTE, size=kw.pop("size", 10), **kw)


def _tit(ws, titulo, sub=None):
    ws.sheet_view.showGridLines = False
    ws.row_dimensions[1].height = 30
    ws.cell(1, 1, titulo).font = _fnt(bold=True, size=18, color=G)
    if sub:
        ws.cell(2, 1, sub).font = _fnt(italic=True, color=GTXT)
    ws.sheet_properties.tabColor = G


def _enc(ws, fila, col, texto, ancho=None, alto=None):
    c = ws.cell(fila, col, texto)
    c.fill, c.font = PatternFill("solid", fgColor=G), _fnt(bold=True, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if ancho:
        ws.column_dimensions[get_column_letter(col)].width = ancho
    if alto:
        ws.row_dimensions[fila].height = alto
    return c


def _seccion(ws, fila, texto, c1, c2):
    for j in range(c1, c2 + 1):
        ws.cell(fila, j).fill = PatternFill("solid", fgColor=GSUAVE)
        ws.cell(fila, j).border = Border(bottom=Side(style="medium", color=G))
    ws.cell(fila, c1, texto).font = _fnt(bold=True, size=11, color=G)


def _borde(ws, r, c1, c2, par=False):
    for j in range(c1, c2 + 1):
        ws.cell(r, j).border = Border(bottom=FILA)
        if par:
            ws.cell(r, j).fill = PatternFill("solid", fgColor="FAF5F8")


def _f(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def libro(d):
    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True
    items, acc, idx = d["items"], _acciones(d), _indices(d)
    burs = _bursatilidad(d)
    fichas_ = {x["clave"]: _ficha(d, x, burs) for x in acc}
    hojas = {}
    _hoja_inicio(wb, d)
    _hoja_acciones(wb, d, acc, fichas_)
    _hoja_ancha(wb, d)
    for it in items:
        hojas[it["clave"]] = _hoja_instrumento(wb, d, it, idx)
    _hoja_comparacion(wb, d, hojas)
    _hoja_graficas(wb, d)
    _hoja_estadistica(wb, d)
    _hoja_deuda(wb, d)
    _hoja_conclusiones(wb, d, fichas_)
    orden = ["Inicio", "Acciones", "Comparación", "Gráficas", "Precios y variaciones", "Estadística"] + [it["clave"] for it in items] + ["Deuda tasas", "Instrumentos de deuda", "Conclusiones"]
    wb._sheets = [wb[n] for n in orden]
    for w in wb.worksheets:
        w.page_setup.orientation, w.page_setup.fitToWidth, w.page_setup.fitToHeight = "landscape", 1, 0
        w.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return X._guardar(wb)


def _hoja_inicio(wb, d):
    ws = wb.active
    ws.title = "Inicio"
    _tit(ws, "Rendimiento de 5 acciones, el IPC y la deuda", f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 96
    _seccion(ws, 4, "Qué hay en este archivo", 1, 2)
    indice = [("Acciones", "Acciones", "Ficha de cada empresa: tipo de acción, serie, clasificación, capital social, bursatilidad, cifras financieras y comportamiento."),
              ("Comparación", "Comparación", "Precio inicial y final, rendimiento efectivo y promedio, y diferencia contra el S&P 500 y el IPC."),
              ("Gráficas", "Gráficas", "Rendimiento acumulado de cada acción frente a su índice."),
              ("Precios y variaciones", "Precios y variaciones", "Fecha, precio de cierre y variación de cada instrumento y de los índices."),
              ("Estadística", "Estadística", "Media, desviación, curtosis y demás medidas, y beta contra cada índice."),
              ("AAPL, MSFT, NVDA, TSLA, KO", "AAPL", "Una hoja por acción con las fórmulas de la clase; también para el IPC y el S&P 500."),
              ("Deuda tasas", "Deuda tasas", "Tasa semanal y variación de CETES, Bonos, Udibonos, papel comercial y certificados bursátiles."),
              ("Instrumentos de deuda", "Instrumentos de deuda", "Emisor, plazo, intereses, riesgo y objetivo de cada instrumento."),
              ("Conclusiones", "Conclusiones", "Resultado de cada acción y de la deuda.")]
    for i, (a, dest, b) in enumerate(indice, 5):
        c = ws.cell(i, 1, a)
        c.hyperlink = f"#'{dest}'!A1"
        c.font = _fnt(bold=True, color=G, underline="single")
        ws.cell(i, 2, b).font = _fnt()
        ws.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
        _borde(ws, i, 1, 2)
    r = 5 + len(indice) + 1
    _seccion(ws, r, "Cómo se calcula", 1, 2)
    calc = [("Variación diaria Ra", "((precio de hoy / precio del día anterior) - 1) x 100"), ("Rendimiento efectivo", "((precio final / precio inicial) - 1) x 100, de todo el periodo"),
            ("Rendimiento promedio Rprom", "Promedio de las variaciones diarias"), ("Diferencia de rendimiento", "Ra - Rprom de cada día, y ese valor al cuadrado"), ("Beta", "Cov(índice, acción) / Var(índice)")]
    for i, (a, b) in enumerate(calc, r + 1):
        ws.cell(i, 1, a).font = _fnt(bold=True)
        ws.cell(i, 2, b).font = _fnt()
        _borde(ws, i, 1, 2)
    r = r + len(calc) + 2
    _seccion(ws, r, "Antes de comparar", 1, 2)
    notas = [("Monedas", "Las acciones cotizan en dólares y el IPC en pesos. El índice que corresponde a estas acciones es el S&P 500; el IPC se muestra como referencia mexicana."),
             ("Días sin operación", "Si una bolsa no abrió un día, ese instrumento queda en blanco y su variación se calcula contra su cierre anterior."),
             ("Periodo", "Empieza el 1 de marzo de 2026 y termina el 25 de noviembre de 2026" + ("." if d["completo"] else "; este archivo llega al último cierre disponible y se completa al volver a generarlo después de esa fecha.")),
             ("Fuentes", "Precios: Yahoo Finance (referencia). Empresas: SEC EDGAR. Deuda: Banco de México."), ("Aviso", R.AVISO)]
    for i, (a, b) in enumerate(notas, r + 1):
        ws.cell(i, 1, a).font = _fnt(bold=True)
        ws.cell(i, 1).alignment = Alignment(vertical="top")
        c = ws.cell(i, 2, b)
        c.font = _fnt()
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = max(16, 14 * (len(b) // 92 + 1))
        _borde(ws, i, 1, 2)


def _hoja_acciones(wb, d, acc, fichas_):
    ws = wb.create_sheet("Acciones")
    _tit(ws, "Las 5 acciones: ficha completa", "Cifras reales de la SEC (EDGAR) y de Yahoo Finance. Cada columna es una acción.")
    ws.column_dimensions["A"].width = 40
    _enc(ws, 4, 1, "Concepto", alto=34)
    for j, it in enumerate(acc, 2):
        _enc(ws, 4, j, f"{it['clave']}\n{it['nombre']}", 30)
    sp = next((x for x in _indices(d) if x["clave"] == "S&P 500"), None)
    num = lambda v, fmt: (v, fmt)
    bloques = [
        ("Identificación", [
            ("Empresa", lambda it, f: f["F"].get("denominacion")), ("Bolsa y clave", lambda it, f: f["F"].get("clave")), ("Sector", lambda it, f: SECTOR[it["ticker"]]),
            ("Clasificación (SEC)", lambda it, f: f"{SIC_ES.get(f['sic'], f['sic'])} ({f['sic']})" if f["sic"] else "No consta"),
            ("Tipo de acción", lambda it, f: f["F"].get("tipo")), ("Serie", lambda it, f: "Una sola clase: no se emiten series"),
            ("Constitución", lambda it, f: f["F"].get("constitucion")), ("Domicilio", lambda it, f: f["F"].get("domicilio"))]),
        ("Capital y acciones", [
            ("Acciones autorizadas", lambda it, f: num(f["autorizadas"], "#,##0")), ("Acciones emitidas", lambda it, f: num(f["emitidas"], "#,##0")),
            ("Acciones en circulación", lambda it, f: num(f["F"].get("acciones"), "#,##0")), ("Fecha del dato de circulación", lambda it, f: f["F"].get("acciones_fecha")),
            ("Valor par (nominal) por acción, USD", lambda it, f: num(f["par"], "0.00000000")),
            ("Capital social (emitidas x valor par), millones de USD", lambda it, f: num(f["capital_social"], "#,##0.00")),
            ("Capital contable del último ejercicio, millones de USD", lambda it, f: num(f["cif"].get("Capital contable", (None,))[0], "#,##0.00")), ("Derechos", lambda it, f: f["F"].get("derechos"))]),
        ("Mercado y bursatilidad", [
            ("Precio final, USD", lambda it, f: num(it["pf"], F_PX)), ("Valor de mercado, millones de USD", lambda it, f: num(it["pf"] * f["F"]["acciones"] / 1e6 if f["F"].get("acciones") else None, "#,##0.00")),
            ("Cambio en 12 meses (%)", lambda it, f: num(it.get("cambio_12m"), F_RET)), ("Máximo de 12 meses, USD", lambda it, f: num(it.get("max52"), F_PX)),
            ("Mínimo de 12 meses, USD", lambda it, f: num(it.get("min52"), F_PX)),
            ("Importe operado promedio diario, millones de USD", lambda it, f: num(f["burs"]["importe"] if f["burs"] else None, "#,##0.00")),
            ("Volumen promedio diario, millones de acciones", lambda it, f: num(f["burs"]["volumen"] if f["burs"] else None, "#,##0.00")),
            ("Rotación diaria (% de las acciones en circulación)", lambda it, f: num(f["burs"]["rotacion"] if f["burs"] else None, "0.000")),
            ("Posición de bursatilidad entre las 5 (1 = la más operada)", lambda it, f: num(f["burs"]["posicion"] if f["burs"] else None, "0"))]),
        ("Finanzas del último ejercicio (millones de USD)", [
            ("Ejercicio fiscal al", lambda it, f: f["fin"]["periodos"][0] if f["fin"] else "No consta"), ("Ingresos", lambda it, f: num(f["cif"].get("Ingresos", (None,))[0], "#,##0.00")),
            ("Variación de ingresos (%)", lambda it, f: num(f["crec_ing"], F_RET)), ("Utilidad neta", lambda it, f: num(f["cif"].get("Utilidad neta", (None,))[0], "#,##0.00")),
            ("Variación de utilidad neta (%)", lambda it, f: num(f["crec_util"], F_RET)), ("Activos totales", lambda it, f: num(f["cif"].get("Activos totales", (None,))[0], "#,##0.00")),
            ("Pasivos totales", lambda it, f: num(f["cif"].get("Pasivos totales", (None,))[0], "#,##0.00")), ("Utilidad por acción, USD", lambda it, f: num(f["cif"].get("Utilidad por acción", (None,))[0], "0.00")),
            ("Dividendo por acción, USD", lambda it, f: num(f["cif"].get("Dividendo por acción", (None,))[0], "0.00"))]),
        ("Desempeño en el periodo", [
            ("Rendimiento efectivo (%)", lambda it, f: num(it["efectivo"], F_RET)), ("Rendimiento promedio diario Rprom (%)", lambda it, f: num(it["stats"]["media"], F_RET)),
            ("Desviación estándar diaria (%)", lambda it, f: num(it["stats"]["desv"], "0.00")), ("Volatilidad anual (%)", lambda it, f: num(f["vol"], "0.00")),
            ("Beta frente al S&P 500", lambda it, f: num((f["betas"].get("S&P 500") or {}).get("beta"), "0.00")), ("Beta frente al IPC", lambda it, f: num((f["betas"].get("IPC") or {}).get("beta"), "0.00"))]),
        ("Lectura", [("Qué mueve su precio", lambda it, f: _razon(it, f)), ("Conclusión", lambda it, f: _conclusion(it, f, sp))]),
    ]
    r = 5
    for titulo, filas in bloques:
        _seccion(ws, r, titulo, 1, 1 + len(acc))
        r += 1
        for etq, fn in filas:
            ws.cell(r, 1, etq).font = _fnt(bold=True)
            ws.cell(r, 1).alignment = Alignment(wrap_text=True, vertical="top")
            largo = 0
            for j, it in enumerate(acc, 2):
                val = fn(it, fichas_[it["clave"]])
                fmt = None
                if isinstance(val, tuple):
                    val, fmt = val
                if val is None:
                    val = "No consta"
                c = ws.cell(r, j, val)
                c.font = _fnt()
                c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(val, (int, float)) else "left")
                if fmt and isinstance(val, (int, float)):
                    c.number_format = fmt
                if isinstance(val, str):
                    largo = max(largo, len(val))
            ws.row_dimensions[r].height = max(16, 14 * (largo // 30 + 1))
            _borde(ws, r, 1, 1 + len(acc), (r % 2) == 0)
            r += 1
    ws.freeze_panes = "B5"
    ws.cell(r + 1, 1, "Bursatilidad: indicador propio con el volumen de Yahoo Finance. El índice oficial de la BMV (alta, media, baja, mínima) no se publica para estas emisoras.").font = _fnt(italic=True, color=GTXT)


def _hoja_ancha(wb, d):
    ws = wb.create_sheet("Precios y variaciones")
    items = d["items"]
    _tit(ws, "Precios de cierre y variación diaria", "Fecha | precio de cierre | variación de cada acción, y al final los índices. Variación = ((cierre de hoy / cierre anterior) - 1) x 100.")
    _enc(ws, 4, 1, "Fecha", 12)
    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    mapas = [_por_fecha(it) for it in items]
    prev = [None] * len(items)
    for k, it in enumerate(items):
        c0 = 2 + 2 * k
        _enc(ws, 4, c0, it["clave"])
        _enc(ws, 4, c0 + 1, it["clave"])
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
        if it["indice"]:
            ws.cell(4, c0).fill = ws.cell(4, c0 + 1).fill = PatternFill("solid", fgColor=GOSC)
        _enc(ws, 5, c0, "Precio de cierre" + (" (puntos)" if it["indice"] else " (USD)"), 14)
        _enc(ws, 5, c0 + 1, "Variación (%)", 12)
    ws.row_dimensions[5].height = 32
    for i, f in enumerate(d["fechas"]):
        r = 6 + i
        ws.cell(r, 1, _f(f)).number_format = "dd/mm/yyyy"
        ws.cell(r, 1).font = _fnt()
        for k, (it, m) in enumerate(zip(items, mapas)):
            if f in m:
                c0 = 2 + 2 * k
                c = ws.cell(r, c0, round(m[f], 4))
                c.number_format, c.font = F_PX, _fnt()
                if prev[k] is not None:
                    c = ws.cell(r, c0 + 1, (m[f] / prev[k] - 1) * 100)
                    c.number_format, c.font = F_RET, _fnt()
                prev[k] = m[f]
        _borde(ws, r, 1, 1 + 2 * len(items), i % 2 == 1)
    ws.freeze_panes = "B6"


def _bloque_indice(ws, d, it, idx, col, r0):
    """Date | Cierre índice | Rendimiento índice | Cierre acción | Rendimiento acción, con Cov, Var y Beta (como en la clase)."""
    a, b = _por_fecha(it), _por_fecha(idx)
    com = [f for f in d["fechas"] if f in a and f in b]
    u = r0 + len(com) - 1
    nc = idx["clave"]
    for j, (t, w) in enumerate(zip(["Date", f"Cierre {nc}", f"Rendimiento {nc}", f"Cierre {it['clave']}", f"Rendimiento {it['clave']}"], [12, 13, 15, 13, 15])):
        _enc(ws, 4, col + j, t, w)
    L = lambda k: get_column_letter(col + k)
    for i, f in enumerate(com):
        r = r0 + i
        ws.cell(r, col, _f(f)).number_format = "dd/mm/yyyy"
        ws.cell(r, col + 1, round(b[f], 4)).number_format = F_PX
        ws.cell(r, col + 3, round(a[f], 4)).number_format = F_PX
        if i:
            ws.cell(r, col + 2, f"=(({L(1)}{r}/{L(1)}{r - 1})-1)*100").number_format = "0.0000"
            ws.cell(r, col + 4, f"=(({L(3)}{r}/{L(3)}{r - 1})-1)*100").number_format = "0.0000"
        for j in range(5):
            ws.cell(r, col + j).font = _fnt()
        _borde(ws, r, col, col + 4, i % 2 == 1)
    ri, re_ = f"${L(2)}${r0 + 1}:${L(2)}${u}", f"${L(4)}${r0 + 1}:${L(4)}${u}"
    ws.column_dimensions[get_column_letter(col + 5)].width = 3
    ws.column_dimensions[get_column_letter(col + 6)].width = 24
    ws.column_dimensions[get_column_letter(col + 7)].width = 14
    c1, c2 = col + 6, col + 7
    cv = get_column_letter(c2)
    for k, (et, f) in enumerate([(f"Cov({nc}, {it['clave']})", f"=COVAR({ri},{re_})"), (f"Var({nc})", f"=VARP({ri})"), ("Beta", f"={cv}5/{cv}6"), ("Correlación", f"=CORREL({ri},{re_})")]):
        r = 5 + k
        ws.cell(r, c1, et).font = _fnt(bold=True)
        ws.cell(r, c2, f).number_format = "0.0000"
        ws.cell(r, c1).fill = ws.cell(r, c2).fill = AMARILLO
    ws.cell(10, c1, f"Beta = Cov({nc}, acción) / Var({nc}).").font = _fnt(italic=True, color=GTXT)
    ws.cell(11, c1, f"Fechas en que operaron los dos: {len(com)}.").font = _fnt(italic=True, color=GTXT)
    return {"beta": f"{cv}7", "corr": f"{cv}8"}


def _hoja_instrumento(wb, d, it, idx):
    """Formato de la clase: datos en amarillo, tabla de rendimientos, estadística, rendimientos ordenados y bloques contra cada índice."""
    ws = wb.create_sheet(it["clave"])
    n = len(it["serie"])
    r0, ult = 5, 5 + n - 1
    unidad = "puntos" if it["indice"] else "USD"
    _tit(ws, f"Rendimiento de precio de cierre: {it['nombre']}", "Ra = ((precio final - precio inicial) / precio inicial) x 100, con el cierre del día anterior como precio inicial de cada día.")
    _enc(ws, 4, 1, "Date", 12, 48)
    _enc(ws, 4, 2, f"Precios Cierre {it['clave']}", 16)
    ws.column_dimensions["C"].width = 3
    for i, (f, p) in enumerate(it["serie"]):
        r = r0 + i
        ws.cell(r, 1, _f(f)).number_format = "dd/mm/yyyy"
        ws.cell(r, 2, round(p, 4)).number_format = F_PX
        ws.cell(r, 1).fill = ws.cell(r, 2).fill = AMARILLO
        ws.cell(r, 1).font = ws.cell(r, 2).font = _fnt()
    enc = ["N", "Date", f"Precios Cierre {it['clave']} ({unidad})", "Ra = ((Pf - Pi) / Pi) x 100\nRendimiento del activo", "Rendimiento prom.\nRprom", "Diferencia de rendimiento\nRa - Rprom", "Diferencia del rendimiento al cuadrado"]
    for j, (t, a) in enumerate(zip(enc, [6, 12, 18, 21, 16, 20, 20]), 4):
        _enc(ws, 4, j, t, a)
    rng = f"$G${r0 + 1}:$G${ult}"
    for i in range(n):
        r = r0 + i
        ws.cell(r, 4, i + 1)
        ws.cell(r, 5, f"=A{r}").number_format = "dd/mm/yyyy"
        ws.cell(r, 6, f"=B{r}").number_format = F_PX
        if i:
            ws.cell(r, 7, f"=((F{r}/F{r - 1})-1)*100").number_format = "0.0000"
            ws.cell(r, 8, f"=AVERAGE({rng})").number_format = "0.0000"
            ws.cell(r, 9, f"=G{r}-H{r}").number_format = "0.0000"
            ws.cell(r, 10, f"=I{r}^2").number_format = "0.0000"
        for j in range(4, 11):
            ws.cell(r, j).font = _fnt()
        _borde(ws, r, 4, 10, i % 2 == 1)
    for j, w in zip((12, 13, 14), (28, 16, 70)):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.column_dimensions["K"].width = 3
    _enc(ws, 4, 12, "Estadística de Ra")
    _enc(ws, 4, 13, "Valor")
    _enc(ws, 4, 14, "Cómo se calcula")
    est = [("Media", f"=AVERAGE({rng})", "Suma de los rendimientos entre el número de días."), ("Error típico", f"=STDEV({rng})/SQRT(COUNT({rng}))", "Desviación estándar entre la raíz del número de datos."),
           ("Mediana", f"=MEDIAN({rng})", "Valor central de los rendimientos ordenados."), ("Moda", f'=IFERROR(MODE({rng}),"No se repite")', "Valor que más se repite."),
           ("Desviación estándar", f"=STDEV({rng})", "Qué tanto se alejan los rendimientos de la media (muestra)."), ("Varianza de la muestra", f"=VAR({rng})", "Desviación estándar al cuadrado."),
           ("Curtosis", f"=KURT({rng})", "Mayor que 0: colas más pesadas que una distribución normal."), ("Coeficiente de asimetría", f"=SKEW({rng})", "Positivo: más extremos al alza."),
           ("Rango", f"=MAX({rng})-MIN({rng})", "Diferencia entre el rendimiento mayor y el menor."), ("Mínimo", f"=MIN({rng})", "Peor rendimiento diario."), ("Máximo", f"=MAX({rng})", "Mejor rendimiento diario."),
           ("Suma", f"=SUM({rng})", "Suma de los rendimientos diarios."), ("DIAS TRABAJADOS", f"=COUNT({rng})", "Número de variaciones diarias.")]
    for k, (a, f, e) in enumerate(est):
        r = 5 + k
        ws.cell(r, 12, a).font = _fnt(bold=True)
        c = ws.cell(r, 13, f)
        c.number_format, c.font = ("0" if a == "DIAS TRABAJADOS" else "0.0000"), _fnt()
        ws.cell(r, 14, e).font = _fnt(size=9, color=GTXT)
        _borde(ws, r, 12, 14)
    base = 5 + len(est) + 1
    _enc(ws, base, 12, "Rendimiento del periodo")
    _enc(ws, base, 13, "Valor")
    _enc(ws, base, 14, "Cómo se calcula")
    res = [("Precio inicial", f"=B{r0}", "Cierre del primer día.", F_PX), ("Precio final", f"=B{ult}", "Cierre del último día.", F_PX), ("Rendimiento efectivo (%)", f"=((B{ult}/B{r0})-1)*100", "((precio final / precio inicial) - 1) x 100.", "0.0000"),
           ("Rendimiento promedio Rprom (%)", f"=AVERAGE({rng})", "Promedio de los Ra diarios.", "0.0000"), ("Suma de diferencias al cuadrado", f"=SUM($J${r0 + 1}:$J${ult})", "Entre los días menos uno da la varianza.", "0.0000")]
    for k, (a, f, e, nf) in enumerate(res):
        r = base + 1 + k
        ws.cell(r, 12, a).font = _fnt(bold=True)
        c = ws.cell(r, 13, f)
        c.number_format, c.font = nf, _fnt()
        ws.cell(r, 14, e).font = _fnt(size=9, color=GTXT)
        _borde(ws, r, 12, 14)
    ws.column_dimensions["O"].width = 3
    _enc(ws, 4, 16, "N", 6)
    _enc(ws, 4, 17, "Ra ordenados (menor a mayor)", 20)
    for k in range(1, n):
        r = r0 + k - 1
        ws.cell(r, 16, k).font = _fnt()
        c = ws.cell(r, 17, f"=SMALL({rng},P{r})")
        c.number_format, c.font = "0.0000", _fnt()
        _borde(ws, r, 16, 17, k % 2 == 0)
    ws.column_dimensions["R"].width = 3
    celdas = {"hoja": it["clave"], "pi": f"M{base + 1}", "pf": f"M{base + 2}", "efectivo": f"M{base + 3}", "promedio": f"M{base + 4}", "desv": "M9", "n": "M17", "betas": {}}
    col = 19
    if not it["indice"]:
        for x in idx:
            celdas["betas"][x["clave"]] = _bloque_indice(ws, d, it, x, col, r0)
            col += 9
        _enc(ws, 4, col, "Date", 12)
        _enc(ws, 4, col + 1, f"{it['clave']} (%)", 11)
        for k, x in enumerate(idx):
            _enc(ws, 4, col + 2 + k, f"{x['clave']} (%)", 11)
        acu = [_acumulado(d, it)] + [_acumulado(d, x) for x in idx]
        for i, f in enumerate(d["fechas"]):
            r = 5 + i
            ws.cell(r, col, _f(f)).number_format = "dd/mm/yyyy"
            for k, serie in enumerate(acu):
                if serie[i] is not None:
                    ws.cell(r, col + 1 + k, round(serie[i], 4)).number_format = "0.00"
        ult2 = 4 + len(d["fechas"])
        ch = LineChart()
        ch.title, ch.height, ch.width = f"{it['clave']} frente a sus índices: rendimiento acumulado (%)", 9.5, 22
        ch.y_axis.number_format, ch.x_axis.number_format = "0.00", "dd/mm"
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.tickLblSkip = max(1, len(d["fechas"]) // 8)
        for k, color in enumerate([G, AZUL, NARANJA][:1 + len(idx)]):
            ch.add_data(Reference(ws, min_col=col + 1 + k, min_row=4, max_row=ult2), titles_from_data=True)
            s = ch.series[-1]
            s.graphicalProperties.line.solidFill = color
            s.graphicalProperties.line.width = 28000 if k == 0 else 17000
            s.marker.symbol, s.smooth = "none", False
        ch.set_categories(Reference(ws, min_col=col, min_row=5, max_row=ult2))
        ws.add_chart(ch, "L" + str(base + 8))
    ws.freeze_panes = "A5"
    ws.sheet_properties.tabColor = GOSC if it["indice"] else G
    return celdas


def _hoja_comparacion(wb, d, hojas):
    ws = wb.create_sheet("Comparación")
    items, idx = d["items"], _indices(d)
    _tit(ws, "Comparación: precio, rendimiento efectivo y promedio", f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}. Las cifras se leen de la hoja de cada instrumento.")
    cols = ["Instrumento", "Precio inicial", "Precio final", "Máximo", "Mínimo", "Rendimiento efectivo (%)", "Rendimiento promedio diario Rprom (%)", "Desviación estándar diaria (%)", "Días trabajados"] + \
          [f"Beta frente al {x['clave']}" for x in idx] + [f"Diferencia contra el {x['clave']} (puntos)" for x in idx]
    anchos = [30, 13, 13, 13, 13, 16, 18, 16, 11] + [13] * len(idx) + [17] * len(idx)
    for j, (t, a) in enumerate(zip(cols, anchos), 1):
        _enc(ws, 4, j, t, a)
    ws.row_dimensions[4].height = 58
    pos = {x["clave"]: 5 + i for i, x in enumerate(items)}
    for i, it in enumerate(items):
        r = 5 + i
        h = hojas[it["clave"]]
        q = f"'{h['hoja']}'!"
        ws.cell(r, 1, f"{it['clave']} · {it['nombre']}" if not it["indice"] else it["nombre"])
        for j, ref in ((2, h["pi"]), (3, h["pf"]), (6, h["efectivo"]), (7, h["promedio"]), (8, h["desv"]), (9, h["n"])):
            ws.cell(r, j, f"={q}{ref}")
        ws.cell(r, 4, round(it["pmax"], 4))
        ws.cell(r, 5, round(it["pmin"], 4))
        for k, x in enumerate(idx):
            if not it["indice"]:
                ws.cell(r, 10 + k, f"={q}{h['betas'][x['clave']]['beta']}").number_format = "0.00"
                ws.cell(r, 10 + len(idx) + k, f"=F{r}-$F${pos[x['clave']]}").number_format = F_RET
        for j in (2, 3, 4, 5):
            ws.cell(r, j).number_format = F_PX
        for j in (6, 7):
            ws.cell(r, j).number_format = F_RET
        ws.cell(r, 8).number_format = "0.00"
        ws.cell(r, 9).number_format = "0"
        ws.cell(r, 1).hyperlink = f"#'{h['hoja']}'!A1"
        for j in range(1, len(cols) + 1):
            ws.cell(r, j).font = _fnt(bold=(j == 1), color=G if j == 1 else None, underline="single" if j == 1 else None)
        _borde(ws, r, 1, len(cols), i % 2 == 1)
        if it["indice"]:
            for j in range(1, len(cols) + 1):
                ws.cell(r, j).fill = PatternFill("solid", fgColor="EFEFEF")
    ws.cell(6 + len(items), 1, "Diferencia: rendimiento efectivo de la acción menos el del índice, en puntos porcentuales. Verde sube, rojo baja.").font = _fnt(italic=True, color=GTXT)
    ws.freeze_panes = "B5"


def _hoja_graficas(wb, d):
    ws = wb.create_sheet("Gráficas")
    items, acc, idx = d["items"], _acciones(d), _indices(d)
    _tit(ws, "Rendimientos para comparar", "Rendimiento acumulado (%) = ((precio de hoy / precio inicial) - 1) x 100. Cada acción se compara con el S&P 500 y el IPC.")
    c0 = 40
    _enc(ws, 4, c0, "Fecha", 12)
    for k, it in enumerate(items):
        _enc(ws, 4, c0 + 1 + k, it["clave"], 11)
    acum = [_acumulado(d, it) for it in items]
    for i, f in enumerate(d["fechas"]):
        r = 5 + i
        ws.cell(r, c0, _f(f)).number_format = "dd/mm/yyyy"
        for k in range(len(items)):
            if acum[k][i] is not None:
                ws.cell(r, c0 + 1 + k, round(acum[k][i], 4)).number_format = "0.00"
    ult = 4 + len(d["fechas"])
    col = {it["clave"]: c0 + 1 + k for k, it in enumerate(items)}
    palette = [AZUL, NARANJA, "0A7F58", "A86D00", "C23B78"]

    def linea(titulo, claves, ancla, colores):
        ch = LineChart()
        ch.title, ch.height, ch.width = titulo, 9.5, 24
        ch.y_axis.number_format, ch.x_axis.number_format = "0.00", "dd/mm"
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.tickLblSkip = max(1, len(d["fechas"]) // 8)
        for k, cl in enumerate(claves):
            ch.add_data(Reference(ws, min_col=col[cl], min_row=4, max_row=ult), titles_from_data=True)
            s = ch.series[-1]
            s.graphicalProperties.line.solidFill = colores[k]
            s.graphicalProperties.line.width = 28000 if k == 0 else 17000
            s.marker.symbol, s.smooth = "none", False
        ch.set_categories(Reference(ws, min_col=c0, min_row=5, max_row=ult))
        ws.add_chart(ch, ancla)

    lugar = lambda n: f"{'A' if n % 2 == 0 else 'M'}{4 + (n // 2) * 21}"
    for n, it in enumerate(acc):
        linea(f"{it['clave']} frente al S&P 500 y al IPC (%)", [it["clave"]] + [x["clave"] for x in idx], lugar(n), [G, AZUL, NARANJA])
    sp = [x["clave"] for x in idx if x["clave"] == "S&P 500"]
    linea("Las 5 acciones y el S&P 500 (%)", [x["clave"] for x in acc] + sp, lugar(len(acc)), palette + ["231F20"])
    ws.cell(4, c0 + 10, "Instrumento")
    ws.cell(4, c0 + 11, "Rendimiento efectivo (%)")
    for k, it in enumerate(items):
        ws.cell(5 + k, c0 + 10, it["clave"])
        ws.cell(5 + k, c0 + 11, round(it["efectivo"], 4)).number_format = "0.00"
    b = BarChart()
    b.type, b.title, b.height, b.width, b.legend = "col", "Rendimiento efectivo del periodo (%)", 9.5, 24, None
    b.y_axis.number_format = "0.00"
    b.x_axis.delete = b.y_axis.delete = False
    b.add_data(Reference(ws, min_col=c0 + 11, min_row=4, max_row=4 + len(items)), titles_from_data=True)
    b.set_categories(Reference(ws, min_col=c0 + 10, min_row=5, max_row=4 + len(items)))
    b.series[0].graphicalProperties.solidFill = G
    ws.add_chart(b, lugar(len(acc) + 1))


def _hoja_estadistica(wb, d):
    ws = wb.create_sheet("Estadística")
    items, acc, idx = d["items"], _acciones(d), _indices(d)
    _tit(ws, "Estadística descriptiva de los rendimientos diarios (Ra, en %)", "Las mismas medidas de la hoja de cada instrumento, una columna por instrumento.")
    _enc(ws, 4, 1, "Medida", 26)
    for k, it in enumerate(items):
        _enc(ws, 4, 2 + k, it["clave"], 12)
        if it["indice"]:
            ws.cell(4, 2 + k).fill = PatternFill("solid", fgColor=GOSC)
    medidas = [("Media", "media"), ("Error típico", "error"), ("Mediana", "mediana"), ("Moda", "moda"), ("Desviación estándar", "desv"), ("Varianza de la muestra", "var"), ("Curtosis", "curtosis"),
               ("Coeficiente de asimetría", "asimetria"), ("Rango", "rango"), ("Mínimo", "min"), ("Máximo", "max"), ("Suma", "suma"), ("Días trabajados", "n")]
    for i, (et, k) in enumerate(medidas):
        r = 5 + i
        ws.cell(r, 1, et).font = _fnt(bold=True)
        for j, it in enumerate(items):
            v = it["stats"][k]
            c = ws.cell(r, 2 + j, "No se repite" if v is None and k == "moda" else v)
            c.number_format, c.font, c.alignment = ("0" if k == "n" else "0.00"), _fnt(), Alignment(horizontal="right")
        _borde(ws, r, 1, 1 + len(items), i % 2 == 1)
    r0 = 5 + len(medidas) + 2
    ws.cell(r0, 1, "Relación con los índices (rendimientos diarios en las fechas en que operaron los dos)").font = _fnt(bold=True, size=12, color=G)
    enc = ["Acción"]
    for x in idx:
        enc += [f"Cov({x['clave']}, acción)", f"Var({x['clave']})", f"Beta {x['clave']}", f"Correlación {x['clave']}"]
    for j, t in enumerate(enc, 1):
        _enc(ws, r0 + 1, j, t)
    ws.row_dimensions[r0 + 1].height = 34
    for i, it in enumerate(acc):
        r = r0 + 2 + i
        ws.cell(r, 1, it["clave"]).font = _fnt(bold=True)
        for k, x in enumerate(idx):
            b = _beta(d, it, x)
            if b:
                for j, v in enumerate([b["cov"], b["var"], b["beta"], b["corr"]]):
                    c = ws.cell(r, 2 + 4 * k + j, v)
                    c.number_format, c.font = "0.0000", _fnt()
        _borde(ws, r, 1, len(enc), i % 2 == 1)
    ws.cell(r0 + 8, 1, "Beta: cuánto se mueve la acción por cada 1 % que se mueve el índice (covarianza entre varianza). La correlación va de -1 a +1.").font = _fnt(italic=True, color=GTXT)
    ws.freeze_panes = "B5"


def _hoja_deuda(wb, d):
    ws = wb.create_sheet("Deuda tasas")
    deu = d["deuda"]
    _tit(ws, "Deuda: tasas semanales y variaciones", "La deuda no tiene precio diario: se muestra la tasa de cada subasta o colocación (Banco de México). Variación en puntos base (pb).")
    _enc(ws, 4, 1, "Fecha", 12)
    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    for k, x in enumerate(deu):
        c0 = 2 + 2 * k
        _enc(ws, 4, c0, x["corto"])
        _enc(ws, 4, c0 + 1, x["corto"])
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
        _enc(ws, 5, c0, "Monto colocado (millones de pesos)" if x["es_monto"] else ("Tasa real (%)" if "real" in x["unidad"] else "Tasa (%)"), 16)
        _enc(ws, 5, c0 + 1, "Variación del monto (mdp)" if x["es_monto"] else "Variación (pb)", 14)
    ws.row_dimensions[5].height = 44
    fechas = sorted({f for x in deu for f, _ in x["serie"]})
    mapas = [{f: (v, vr) for (f, v), vr in zip(x["serie"], x["var"])} for x in deu]
    for i, f in enumerate(fechas):
        r = 6 + i
        ws.cell(r, 1, _f(f)).number_format = "dd/mm/yyyy"
        ws.cell(r, 1).font = _fnt()
        for k, m in enumerate(mapas):
            if f in m:
                v, vr = m[f]
                c = ws.cell(r, 2 + 2 * k, round(v, 4))
                c.number_format, c.font = "0.00", _fnt()
                if vr is not None:
                    c = ws.cell(r, 3 + 2 * k, vr)
                    c.number_format, c.font = F_RET, _fnt()
        _borde(ws, r, 1, 1 + 2 * len(deu), i % 2 == 1)
    ult = 5 + len(fechas)
    r0 = ult + 2
    _seccion(ws, r0, "Estadística", 1, 1 + 2 * len(deu))
    for i, (et, f) in enumerate([("Media", "AVERAGE({})"), ("Desviación estándar", "STDEV({})"), ("Mínimo", "MIN({})"), ("Máximo", "MAX({})"), ("Datos", "COUNT({})")]):
        r = r0 + 1 + i
        ws.cell(r, 1, et).font = _fnt(bold=True)
        for k in range(len(deu)):
            for col in (2 + 2 * k, 3 + 2 * k):
                L = get_column_letter(col)
                c = ws.cell(r, col, "=" + f.format(f"{L}6:{L}{ult}"))
                c.number_format, c.font = ("0" if et == "Datos" else "0.00"), _fnt()
        _borde(ws, r, 1, 1 + 2 * len(deu), i % 2 == 1)
    ws.cell(r0 + 7, 1, "Papel comercial: no hubo colocaciones en el periodo, por eso su monto es 0.00. Los certificados bursátiles son los de corto plazo.").font = _fnt(italic=True, color=GTXT)
    tasas = [(k, x) for k, x in enumerate(deu) if not x["es_monto"]]
    ch = LineChart()
    ch.title, ch.height, ch.width = "Tasas de las subastas y colocaciones (%)", 9.5, 24
    ch.y_axis.number_format, ch.x_axis.number_format = "0.00", "dd/mm"
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.x_axis.tickLblSkip = max(1, len(fechas) // 8)
    palette = [AZUL, NARANJA, "0A7F58", "C23B78"]
    for n, (k, x) in enumerate(tasas):
        ch.add_data(Reference(ws, min_col=2 + 2 * k, min_row=5, max_row=ult), titles_from_data=True)
        s = ch.series[-1]
        s.graphicalProperties.line.solidFill = palette[n % 4]
        s.graphicalProperties.line.width = 19000
        s.marker.symbol, s.smooth = "none", False
    ch.set_categories(Reference(ws, min_col=1, min_row=6, max_row=ult))
    ws.add_chart(ch, f"A{r0 + 10}")
    ws.freeze_panes = "B6"
    w2 = wb.create_sheet("Instrumentos de deuda")
    _tit(w2, "Instrumentos de deuda: ficha", "Riesgo y objetivo: material del equipo. Características: Banco de México. Cifras: subastas del periodo.")
    w2.column_dimensions["A"].width = 30
    _enc(w2, 4, 1, "Concepto", alto=30)
    for j, x in enumerate(deu, 2):
        _enc(w2, 4, j, x["corto"], 34)
    filas = [("Emisor", lambda x, F: F.get("emisor")), ("Plazo", lambda x, F: F.get("plazo")), ("Pago de intereses", lambda x, F: F.get("intereses")), ("Valor nominal", lambda x, F: F.get("nominal")),
             ("Tasa", lambda x, F: F.get("tasa")), ("Primera emisión", lambda x, F: F.get("primera")), ("Respaldo", lambda x, F: F.get("garantia")), ("Riesgo (equipo)", lambda x, F: x["riesgo"]),
             ("Objetivo (equipo)", lambda x, F: x["objetivo"]), ("Última cifra", lambda x, F: (x["ult"], "0.00")), ("Fecha de la última cifra", lambda x, F: R.fecha_corta(x["fult"])),
             ("Mínimo del periodo", lambda x, F: (x["min"], "0.00")), ("Máximo del periodo", lambda x, F: (x["max"], "0.00")), ("Promedio del periodo", lambda x, F: (x["media"], "0.00"))]
    for i, (et, fn) in enumerate(filas, 5):
        w2.cell(i, 1, et).font = _fnt(bold=True)
        w2.cell(i, 1).alignment = Alignment(vertical="top")
        largo = 0
        for j, x in enumerate(deu, 2):
            v = fn(x, fichas.DEUDA.get(x["nombre"], {}))
            fmt = None
            if isinstance(v, tuple):
                v, fmt = v
            c = w2.cell(i, j, v)
            c.font = _fnt()
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(v, (int, float)) else "left")
            if fmt:
                c.number_format = fmt
            if isinstance(v, str):
                largo = max(largo, len(v))
        w2.row_dimensions[i].height = max(16, 14 * (largo // 34 + 1))
        _borde(w2, i, 1, 1 + len(deu), i % 2 == 0)
    w2.cell(5 + len(filas) + 1, 1, "Cifras en % anual (Udibonos, % real); en papel comercial, millones de pesos colocados por semana.").font = _fnt(italic=True, color=GTXT)
    w2.freeze_panes = "B5"


def _hoja_conclusiones(wb, d, fichas_):
    ws = wb.create_sheet("Conclusiones")
    _tit(ws, "Conclusiones")
    ws.column_dimensions["A"].width = 130
    acc, idx = _acciones(d), _indices(d)
    sp = next((x for x in idx if x["clave"] == "S&P 500"), None)
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    sup = [x["clave"] for x in acc if sp and x["efectivo"] > sp["efectivo"]]
    lineas = [("Acciones", True)]
    lineas += [("• " + _conclusion(it, fichas_[it["clave"]], sp), False) for it in acc]
    lineas.append((f"En conjunto, {mejor['clave']} fue la de mayor rendimiento ({mejor['efectivo']:+.2f} %) y {peor['clave']} la de menor ({peor['efectivo']:+.2f} %)."
                   + (f" El S&P 500 rindió {sp['efectivo']:+.2f} % y lo superaron {', '.join(sup) if sup else 'ninguna'}." if sp else ""), False))
    lineas.append(("", False))
    lineas.append(("Deuda", True))
    for x in d["deuda"]:
        if x["es_monto"]:
            lineas.append((f"• {x['corto']}: {x['ult']:,.2f} millones de pesos colocados en la última semana; en el periodo se colocaron {sum(v for _, v in x['serie']):,.2f} millones. Riesgo: {x['riesgo'].lower()}.", False))
        else:
            lineas.append((f"• {x['corto']}: última tasa {x['ult']:.2f} % ({R.fecha_corta(x['fult'])}), entre {x['min']:.2f} % y {x['max']:.2f} %, promedio {x['media']:.2f} %. Riesgo: {x['riesgo'].lower()}.", False))
    lineas.append(("CETES, Bonos y Udibonos son deuda del Gobierno Federal y tienen el menor riesgo. El papel comercial y los certificados bursátiles los emiten empresas, y su riesgo depende de la solvencia del emisor.", False))
    for i, (t, h) in enumerate(lineas, 3):
        c = ws.cell(i, 1, t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = _fnt(bold=True, size=12, color=G) if h else _fnt(size=11)
        if not h:
            ws.row_dimensions[i].height = max(18, 15 * (len(t) // 120 + 1))


# ------------------------------------------------------------------------------- PDF
class _PDF(FPDF):
    total = 8

    def header(self):
        pass

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-9)
        self.set_font("Barlow", "", 7.5)
        self.set_text_color(*GRIS)
        self.set_x(14)
        self.cell(230, 4, "Instituto Politécnico Nacional · Escuela Superior de Economía · Seminario de Titulación 2026 · Herramienta educativa, no es asesoría financiera")
        self.cell(40, 4, f"{self.page_no()} de {self.total}", align="R")


def _nuevo():
    pdf = _PDF(orientation="L", format="A4")
    for est, arch in (("", "Barlow-Regular"), ("B", "Barlow-Bold"), ("I", "Barlow-Italic")):
        pdf.add_font("Barlow", est, str(R.FUENTES_TTF / f"{arch}.ttf"))
    pdf.add_font("BarlowC", "B", str(R.FUENTES_TTF / "BarlowSemiCondensed-Bold.ttf"))
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(False)
    return pdf


def _pagina(pdf, titulo, mensaje=None):
    """Banda guinda con el título; debajo, una sola frase con lo que debe entender quien lee la página."""
    pdf.add_page()
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, 297, 17, "F")
    pdf.image(str(R.MARCA / "ipn-escudo-blanco.png"), x=14, y=2.5, h=12)
    pdf.set_xy(30, 3.4)
    pdf.set_font("BarlowC", "B", 17)
    pdf.set_text_color(*BLANCO)
    pdf.cell(230, 10, titulo)
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(276, 2.5, 12, 12, "F")
    pdf.image(str(R.MARCA / "ese-escudo.png"), x=277, y=3.5, w=10, h=10)
    pdf.set_y(22)
    if mensaje:
        pdf.set_x(14)
        pdf.set_font("Barlow", "B", 12.5)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(269, 6, mensaje, new_x="LMARGIN", new_y="NEXT")


def _tabla(pdf, cols, filas, anchos, aligns=None, estilos=None, size=8.6, alto=5.6, y=None, x=14, tope=268.0):
    aligns = aligns or ["LEFT"] + ["RIGHT"] * (len(cols) - 1)
    k = min(1.0, tope / sum(anchos))
    anchos = tuple(a * k for a in anchos)
    if y:
        pdf.set_y(y)
    pdf.set_left_margin(x)
    pdf.set_x(x)
    pdf.set_fill_color(*BLANCO)
    pdf.set_text_color(*NEGRO)
    pdf.set_font("Barlow", "", size)
    with pdf.table(col_widths=anchos, text_align=aligns, line_height=alto, borders_layout="HORIZONTAL_LINES", headings_style=R.FontFace(emphasis="BOLD", color=BLANCO, fill_color=GUINDA),
                   cell_fill_color=GUINDA_SUAVE, cell_fill_mode="ROWS", padding=(1.0, 1.6, 1.0, 1.6), width=sum(anchos), align="LEFT") as t:
        r = t.row()
        for c in cols:
            r.cell(c)
        for i, f in enumerate(filas):
            r = t.row()
            for j, v in enumerate(f):
                col = (estilos or {}).get((i, j))
                r.cell(str(v), style=R.FontFace(color=col) if col else None)
    pdf.set_left_margin(14)
    pdf.set_x(14)
    return pdf.get_y()


def _n(x, signo=False):
    return "s/d" if x is None else (f"{x:+,.2f}" if signo else f"{x:,.2f}")


def _color(x):
    return SUBE if x > 0 else BAJA if x < 0 else NEGRO


def _ticks(lo, hi, n=5):
    raw = (hi - lo) / n or 1
    mag = 10 ** math.floor(math.log10(raw))
    paso = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    a, b = math.floor(lo / paso) * paso, math.ceil(hi / paso) * paso
    out, v = [], a
    while v <= b + paso / 2:
        out.append(round(v, 10))
        v += paso
    return out


def _lineas(pdf, x0, y0, w, h, series, fechas, titulo=None, signo=True, leyenda=True):
    """series: [(nombre, valores, color, grosor, punteada)]; la leyenda trae el último valor de cada línea."""
    if titulo:
        pdf.set_xy(x0, y0)
        pdf.set_font("Barlow", "B", 9.5)
        pdf.set_text_color(*NEGRO)
        pdf.cell(w, 5, titulo)
        y0 += 6
    vals = [v for s in series for v in s[1] if v is not None]
    marcas = _ticks(min(vals), max(vals), 4)
    lo, hi = marcas[0], marcas[-1]
    px0, pw = x0 + 11, w - 14
    ph = h - (14 if leyenda else 8)
    py = lambda v: y0 + ph - (v - lo) / (hi - lo) * ph
    n = len(fechas)
    pdf.set_font("Barlow", "", 7)
    pdf.set_line_width(0.12)
    for v in marcas:
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.line(px0, py(v), px0 + pw, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(x0, py(v) - 1.7)
        pdf.cell(10, 3.4, f"{v:g}", align="R")
    if lo < 0 < hi:
        pdf.set_draw_color(*GRIS)
        pdf.set_line_width(0.25)
        pdf.line(px0, py(0), px0 + pw, py(0))
    for nombre, vs, col, gr, punt in series[::-1]:
        pdf.set_draw_color(*col)
        pdf.set_line_width(gr)
        prev = None
        for i, v in enumerate(vs):
            if v is None:
                prev = None
                continue
            xx = px0 + i / max(1, n - 1) * pw
            if prev is not None and not (punt and i % 3 == 0):
                pdf.line(prev[0], prev[1], xx, py(v))
            prev = (xx, py(v))
    pdf.set_line_width(0.2)
    pdf.set_text_color(*GRIS)
    pdf.set_font("Barlow", "", 7)
    for i in (0, n // 2, n - 1):
        pdf.set_xy(min(max(px0 + i / max(1, n - 1) * pw - 10, x0), x0 + w - 20), y0 + ph + 1)
        pdf.cell(20, 3.4, R.fecha_corta(fechas[i]), align="C")
    if leyenda:
        yl, xl = y0 + ph + 6, px0
        pdf.set_font("Barlow", "", 7.8)
        for nombre, vs, col, gr, punt in series:
            ult = next((v for v in reversed(vs) if v is not None), 0)
            txt = f"{nombre} {ult:+.2f} %" if signo else f"{nombre} {ult:.2f} %"
            ancho = pdf.get_string_width(txt) + 11
            if xl + ancho > x0 + w:
                xl, yl = px0, yl + 4.2
            pdf.set_fill_color(*col)
            pdf.rect(xl, yl + 1.2, 5, 1.6, "F")
            pdf.set_xy(xl + 6.2, yl)
            pdf.set_text_color(*NEGRO)
            pdf.cell(ancho - 6.2, 4.2, txt)
            xl += ancho


def _barras(pdf, x0, y0, w, h, nombres, valores, titulo, colores=None):
    pdf.set_xy(x0, y0)
    pdf.set_font("Barlow", "B", 9.5)
    pdf.set_text_color(*NEGRO)
    pdf.cell(w, 5, titulo)
    y0 += 8
    marcas = _ticks(min(0, min(valores)), max(0, max(valores)), 4)
    lo, hi = marcas[0], marcas[-1]
    ph = h - 18
    py = lambda v: y0 + (hi - v) / (hi - lo) * ph
    px0, pw = x0 + 11, w - 14
    pdf.set_line_width(0.12)
    pdf.set_font("Barlow", "", 7)
    for v in marcas:
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.line(px0, py(v), px0 + pw, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(x0, py(v) - 1.7)
        pdf.cell(10, 3.4, f"{v:g}", align="R")
    bw = pw / len(valores)
    for i, v in enumerate(valores):
        pdf.set_fill_color(*((colores or {}).get(i, GUINDA)))
        top, bot = (py(v), py(0)) if v >= 0 else (py(0), py(v))
        pdf.rect(px0 + i * bw + bw * 0.2, top, bw * 0.6, max(0.3, bot - top), "F")
        pdf.set_text_color(*GRIS)
        pdf.set_xy(px0 + i * bw - 2, py(lo) + 1)
        pdf.cell(bw + 4, 3.4, nombres[i], align="C")
        pdf.set_text_color(*NEGRO)
        pdf.set_xy(px0 + i * bw - 2, (top - 3.6) if v >= 0 else (bot + 0.3))
        pdf.cell(bw + 4, 3.4, f"{v:.2f}", align="C")
    pdf.set_line_width(0.2)


def presentacion(d):
    pdf = _nuevo()
    items, acc, idx, deu = d["items"], _acciones(d), _indices(d), d["deuda"]
    sp = next((x for x in idx if x["clave"] == "S&P 500"), None)
    ipc = next((x for x in idx if x["clave"] == "IPC"), None)
    burs = _bursatilidad(d)
    fichas_ = {x["clave"]: _ficha(d, x, burs) for x in acc}
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    ganan = [x["clave"] for x in acc if sp and x["efectivo"] > sp["efectivo"]]
    periodo = f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}"
    fechas = d["fechas"]
    ac = {x["clave"]: _acumulado(d, x) for x in items}
    col_acc = {x["clave"]: COLORES[i % 5] for i, x in enumerate(acc)}

    # 1 portada
    pdf.add_page()
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.image(str(R.MARCA / "ipn-escudo-blanco.png"), x=20, y=22, h=62)
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(238, 24, 40, 40, "F")
    pdf.image(str(R.MARCA / "ese-escudo.png"), x=241, y=27, w=34, h=34)
    pdf.set_text_color(*BLANCO)
    for y, txt, fnt, sz in ((30, "INSTITUTO POLITÉCNICO NACIONAL", "B", 18), (38, "ESCUELA SUPERIOR DE ECONOMÍA", "B", 14), (45, "Seminario de Titulación 2026", "", 12)):
        pdf.set_xy(80, y)
        pdf.set_font("Barlow", fnt, sz)
        pdf.cell(150, 7, txt)
    pdf.set_xy(20, 112)
    pdf.set_font("BarlowC", "B", 38)
    pdf.cell(250, 16, "Cinco acciones frente a su índice", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font("Barlow", "", 15)
    pdf.cell(250, 9, "Apple, Microsoft, NVIDIA, Tesla y Coca-Cola, el S&P 500, el IPC y la deuda", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font("Barlow", "", 13)
    pdf.cell(250, 8, periodo)
    pdf.set_xy(20, 190)
    pdf.set_font("Barlow", "", 9.5)
    pdf.cell(250, 5, f"Elaborado el {R.fecha_corta(d['generado'].date().isoformat())}. " + ("Cubre hasta el 25 de noviembre de 2026." if d["completo"] else "El análisis termina el 25 de noviembre de 2026; este corte llega al último cierre disponible."))

    # 2 lo esencial: una gráfica grande y el ranking
    msg = (f"{mejor['nombre']} rindió más ({mejor['efectivo']:+.2f} %) y {peor['nombre']} menos ({peor['efectivo']:+.2f} %). "
           f"{len(ganan)} de {len(acc)} acciones superaron al S&P 500, que rindió {sp['efectivo']:+.2f} %.") if sp else ""
    _pagina(pdf, "Lo esencial", msg)
    series = [(x["clave"], ac[x["clave"]], col_acc[x["clave"]], 0.55, False) for x in acc]
    if sp:
        series.append(("S&P 500", ac["S&P 500"], NEGRO, 0.8, True))
    if ipc:
        series.append(("IPC", ac["IPC"], GRIS, 0.8, True))
    _lineas(pdf, 14, 38, 190, 150, series, fechas, "Rendimiento acumulado desde el inicio del periodo (%)")
    orden = sorted(items, key=lambda x: -x["efectivo"])
    pdf.set_xy(212, 38)
    pdf.set_font("Barlow", "B", 9.5)
    pdf.set_text_color(*NEGRO)
    pdf.cell(70, 5, "Ranking por rendimiento efectivo")
    _tabla(pdf, ["Instrumento", "Rendimiento (%)"], [[x["clave"], _n(x["efectivo"], True)] for x in orden], (34, 34), None, {(i, 1): _color(x["efectivo"]) for i, x in enumerate(orden)}, size=9.5, alto=7, y=45, x=212, tope=70)

    # 3 cada acción frente a su índice
    _pagina(pdf, "Cada acción frente a su índice", "Línea de color: la acción. Negra: S&P 500. Gris: IPC. Las acciones cotizan en dólares, así que el S&P 500 es su referencia directa.")
    pos = [(14, 36), (110, 36), (206, 36), (14, 114), (110, 114)]
    for (x0, y0), it in zip(pos, acc):
        s = [(it["clave"], ac[it["clave"]], col_acc[it["clave"]], 0.7, False)]
        if sp:
            s.append(("S&P 500", ac["S&P 500"], NEGRO, 0.5, True))
        if ipc:
            s.append(("IPC", ac["IPC"], GRIS, 0.5, True))
        b = fichas_[it["clave"]]["betas"].get("S&P 500")
        _lineas(pdf, x0, y0, 90, 74, s, fechas, f"{it['clave']} · {it['nombre']}" + (f"   (beta frente al S&P 500: {b['beta']:.2f})" if b else ""))
    pdf.set_xy(206, 122)
    pdf.set_font("Barlow", "B", 9.5)
    pdf.set_text_color(*NEGRO)
    pdf.cell(75, 5, "Cómo leerlo")
    pdf.set_xy(206, 129)
    pdf.set_font("Barlow", "", 8.8)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(76, 4.4, "Cuando la línea de color va arriba de la negra, la acción rindió más que el mercado de EE. UU. en ese tramo. La beta indica cuánto se mueve la acción por cada 1 % que se mueve el S&P 500.")

    # 4 precio de cierre y rendimiento
    _pagina(pdf, "Precio de cierre y rendimiento", "El rendimiento efectivo cubre todo el periodo; el promedio diario es la media de las variaciones día a día.")
    filas, est = [], {}
    for i, x in enumerate(items):
        row = [x["clave"], _n(x["pi"]), _n(x["pf"]), _n(x["pmax"]), _n(x["pmin"]), _n(x["efectivo"], True), _n(x["stats"]["media"], True), _n(x["stats"]["desv"])]
        for ix in idx:
            row.append("-" if x["indice"] else _n(x["efectivo"] - ix["efectivo"], True))
        filas.append(row)
        est[(i, 5)] = _color(x["efectivo"])
        for k, ix in enumerate(idx):
            if not x["indice"]:
                est[(i, 8 + k)] = _color(x["efectivo"] - ix["efectivo"])
    _tabla(pdf, ["Instrumento", "Precio inicial", "Precio final", "Máximo", "Mínimo", "Rendimiento efectivo (%)", "Promedio diario Rprom (%)", "Desviación diaria (%)"] + [f"Diferencia con {x['clave']} (puntos)" for x in idx],
           filas, (30, 24, 24, 24, 24, 30, 30, 26, 30, 30), None, est, size=9, alto=6.4, y=36)
    cuerpo = {len(items) - 1 - k: (35, 31, 32) for k in range(len(idx))}
    _barras(pdf, 14, 116, 130, 76, [x["clave"] for x in items], [x["efectivo"] for x in items], "Rendimiento efectivo del periodo (%)", cuerpo)
    _barras(pdf, 150, 116, 130, 76, [x["clave"] for x in items], [x["stats"]["media"] for x in items], "Rendimiento promedio diario Rprom (%)", cuerpo)

    # 5 riesgo y estadística
    _pagina(pdf, "Riesgo y estadística", "La desviación estándar y la beta resumen cuánto se mueve cada acción y qué tan unida va a su índice.")
    filas = [[x["clave"], _n(x["stats"]["media"], True), _n(x["stats"]["desv"]), _n(x["stats"]["var"]), _n(x["stats"]["asimetria"], True), _n(x["stats"]["curtosis"], True), _n(x["stats"]["min"], True),
              _n(x["stats"]["max"], True), str(x["stats"]["n"])] for x in items]
    y1 = _tabla(pdf, ["Instrumento", "Media (%)", "Desviación estándar", "Varianza", "Asimetría", "Curtosis", "Mínimo (%)", "Máximo (%)", "Días trabajados"], filas, (30, 26, 32, 26, 26, 26, 28, 28, 28), None, None, size=9, alto=6.2, y=36)
    enc = ["Acción"]
    for x in idx:
        enc += [f"Beta {x['clave']}", f"Correlación {x['clave']}"]
    filas = []
    for it in acc:
        fila = [it["clave"]]
        for x in idx:
            b = fichas_[it["clave"]]["betas"].get(x["clave"])
            fila += [f"{b['beta']:.2f}" if b else "s/d", f"{b['corr']:.2f}" if b else "s/d"]
        filas.append(fila)
    y2 = _tabla(pdf, enc, filas, (30, 40, 40, 40, 40), None, None, size=9, alto=6.2, y=y1 + 8)
    pdf.set_xy(14, y2 + 5)
    pdf.set_font("Barlow", "", 9)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(269, 4.6, "Estadística con las mismas definiciones de Excel (muestra). Cov(índice, acción) y Var(índice) de cada acción están en su hoja del Excel.")

    # 6 ficha de las acciones
    _pagina(pdf, "Ficha de las acciones", "Tipo de acción, serie, clasificación, capital y bursatilidad de cada empresa, con cifras reales.")
    g = lambda it, k: fichas_[it["clave"]][k]
    mm = lambda v: f"{v:,.2f}" if v is not None else "s/d"
    filas = [
        ["Tipo de acción y serie"] + ["Comunes, clase única"] * len(acc),
        ["Clasificación (SEC)"] + [SIC_ES.get(g(x, "sic"), g(x, "sic")) or "s/d" for x in acc],
        ["Sector"] + [SECTOR[x["ticker"]] for x in acc],
        ["Constitución"] + [CONSTITUCION[x["ticker"]] for x in acc],
        ["Acciones en circulación (millones)"] + [f"{g(x, 'F')['acciones'] / 1e6:,.0f}" for x in acc],
        ["Valor par por acción (USD)"] + [f"{g(x, 'par'):.8f}".rstrip("0").rstrip(".") if g(x, "par") else "s/d" for x in acc],
        ["Capital social (millones USD)"] + [mm(g(x, "capital_social")) for x in acc],
        ["Capital contable (millones USD)"] + [mm(g(x, "cif").get("Capital contable", (None,))[0]) for x in acc],
        ["Valor de mercado (millones USD)"] + [f"{x['pf'] * g(x, 'F')['acciones'] / 1e6:,.0f}" for x in acc],
        ["Importe operado diario (millones USD)"] + [mm(g(x, "burs")["importe"]) if g(x, "burs") else "s/d" for x in acc],
        ["Bursatilidad (1 = la más operada)"] + [str(g(x, "burs")["posicion"]) if g(x, "burs") else "s/d" for x in acc],
        ["Ingresos (millones USD)"] + [mm(g(x, "cif").get("Ingresos", (None,))[0]) for x in acc],
        ["Utilidad neta (millones USD)"] + [mm(g(x, "cif").get("Utilidad neta", (None,))[0]) for x in acc],
        ["Cambio en 12 meses (%)"] + [_n(x.get("cambio_12m"), True) for x in acc],
    ]
    est = {(len(filas) - 1, j + 1): _color(x.get("cambio_12m") or 0) for j, x in enumerate(acc)}
    _tabla(pdf, ["Concepto"] + [x["clave"] for x in acc], filas, (62, 41, 41, 41, 41, 41), ["LEFT"] + ["CENTER"] * len(acc), est, size=8.8, alto=5.8, y=34)
    pdf.set_y(pdf.get_y() + 3)
    pdf.set_x(14)
    pdf.set_font("Barlow", "I", 8)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(269, 4, "Cifras de la SEC (EDGAR), último ejercicio presentado, y precios de Yahoo Finance. Bursatilidad: indicador propio con el volumen diario de Yahoo Finance; el índice oficial de la BMV (alta, media, baja, mínima) no se publica para estas emisoras.")

    # 7 deuda
    tasas = [x for x in deu if not x["es_monto"]]
    _pagina(pdf, "Deuda", "CETES, Bonos y Udibonos son deuda del Gobierno Federal, de menor riesgo. El papel comercial y los certificados bursátiles los emiten empresas.")
    filas = []
    for x in deu:
        F = fichas.DEUDA.get(x["nombre"], {})
        u = " mdp" if x["es_monto"] else " %"
        filas.append([x["corto"], (F.get("emisor") or "").split(" (")[0], x["riesgo"], x["objetivo"], f"{x['ult']:.2f}{u}", f"{x['min']:.2f}{u}", f"{x['max']:.2f}{u}", f"{x['media']:.2f}{u}"])
    yd = _tabla(pdf, ["Instrumento", "Emisor", "Riesgo", "Objetivo", "Última cifra", "Mínimo", "Máximo", "Promedio"], filas, (30, 40, 48, 56, 24, 22, 22, 24), ["LEFT"] * 4 + ["RIGHT"] * 4, None, size=8.4, alto=5.6, y=40)
    tf = sorted({f for x in tasas for f, _ in x["serie"]})
    if tasas and tf:
        sd = []
        for n, x in enumerate(tasas):
            m, ult, arr = dict(x["serie"]), None, []
            for f in tf:
                ult = m.get(f, ult)
                arr.append(ult)
            sd.append((x["corto"], arr, COLORES[n % 5], 0.6, False))
        _lineas(pdf, 14, yd + 5, 269, 192 - (yd + 5), sd, tf, "Tasa de cada subasta o colocación semanal (%)", signo=False)

    # 8 conclusiones y método
    _pagina(pdf, "Conclusiones y método")
    pdf.set_x(14)
    pdf.set_font("Barlow", "B", 11.5)
    pdf.set_text_color(*GUINDA)
    pdf.cell(269, 7, "Acciones", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 9.6)
    pdf.set_text_color(*NEGRO)
    for it in acc:
        pdf.set_x(14)
        pdf.multi_cell(269, 4.8, "•  " + _conclusion(it, fichas_[it["clave"]], sp), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)
    pdf.set_x(14)
    pdf.set_font("Barlow", "B", 11.5)
    pdf.set_text_color(*GUINDA)
    pdf.cell(269, 8, "Deuda", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 9.6)
    pdf.set_text_color(*NEGRO)
    pdf.set_x(14)
    pdf.multi_cell(269, 4.8, "•  " + "; ".join(f"{x['corto']} {x['ult']:.2f} %" for x in tasas) + " en su última subasta o colocación. El papel comercial no tuvo colocaciones en el periodo.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_x(14)
    pdf.set_font("Barlow", "B", 11.5)
    pdf.set_text_color(*GUINDA)
    pdf.cell(269, 8, "Método", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 9.2)
    pdf.set_text_color(*NEGRO)
    met = ["Variación diaria Ra = ((precio de hoy / precio anterior) - 1) x 100. Rendimiento efectivo = ((precio final / precio inicial) - 1) x 100. Rprom = promedio de los Ra. Diferencia = Ra - Rprom. Beta = Cov(índice, acción) / Var(índice).",
           "Precios: Yahoo Finance (referencia). Empresas: SEC EDGAR. Deuda: Banco de México. Riesgo y objetivo de cada instrumento: material del equipo.",
           "El periodo empieza el 1 de marzo y termina el 25 de noviembre de 2026" + ("." if d["completo"] else "; este corte llega al último cierre disponible y el archivo se completa al generarlo de nuevo después de esa fecha."),
           "El Excel adjunto trae las fórmulas de la clase en la hoja de cada instrumento, además de la ficha completa de cada acción."]
    for t in met:
        pdf.set_x(14)
        pdf.multi_cell(269, 4.6, "•  " + t, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.6)
    return bytes(pdf.output())
