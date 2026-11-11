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
from openpyxl.chart.series import SeriesLabel
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.formatting.rule import CellIsRule
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
F_RET = "+0.00;-0.00;0.00"  # el color verde/rojo lo pone el formato condicional (_colorear)
F_PX = "#,##0.00"
LETRA = get_column_letter


def _fnt(**kw):
    return Font(name=FUENTE, size=kw.pop("size", 10), **kw)


def _tit(ws, titulo, sub=None):
    ws.sheet_view.showGridLines = False
    ws.row_dimensions[1].height = 30
    ws.cell(1, 1, titulo).font = _fnt(bold=True, size=18, color=G)
    if sub:
        ws.cell(2, 1, sub).font = _fnt(color=GTXT)
    ws.sheet_properties.tabColor = G


def _enc(ws, fila, col, texto, ancho=None, alto=None, color=None):
    c = ws.cell(fila, col, texto)
    c.fill, c.font = PatternFill("solid", fgColor=color or G), _fnt(bold=True, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if ancho:
        ws.column_dimensions[LETRA(col)].width = ancho
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


def _colorear(ws, rango):
    """Verde si es positivo y rojo si es negativo."""
    ws.conditional_formatting.add(rango, CellIsRule(operator="greaterThan", formula=["0"], font=Font(color="00643F")))
    ws.conditional_formatting.add(rango, CellIsRule(operator="lessThan", formula=["0"], font=Font(color="B3261E")))


def _f(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


PLAZO = {"CETES": "28 días (máximo 1 año)", "BONOS": "3 a 30 años (aquí, 10)", "UDIBONOS": "3, 10 y 30 años (aquí, 10)", "PAPEL COMERCIAL": "Corto plazo", "CERTIFICADOS BURSÁTILES": "Corto plazo"}
INTERES = {"CETES": "A descuento, sin cupones", "BONOS": "Cupón cada 182 días", "UDIBONOS": "Cupón cada 182 días, en UDIS", "PAPEL COMERCIAL": "A descuento", "CERTIFICADOS BURSÁTILES": "Periódicos o a descuento"}
NOMINAL = {"CETES": "$10", "BONOS": "$100", "UDIBONOS": "100 UDIS", "PAPEL COMERCIAL": "Según la emisión", "CERTIFICADOS BURSÁTILES": "Según la emisión"}
TASA = {"CETES": "De descuento", "BONOS": "Fija", "UDIBONOS": "Real fija", "PAPEL COMERCIAL": "De mercado", "CERTIFICADOS BURSÁTILES": "Fija o variable"}
EMISOR = {"CETES": "Gobierno Federal", "BONOS": "Gobierno Federal", "UDIBONOS": "Gobierno Federal", "PAPEL COMERCIAL": "Empresas privadas", "CERTIFICADOS BURSÁTILES": "Empresas privadas"}


def libro(d):
    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True
    items, acc, idx = d["items"], _acciones(d), _indices(d)
    burs = _bursatilidad(d)
    fichas_ = {x["clave"]: _ficha(d, x, burs) for x in acc}
    ws_res = wb.active
    ws_res.title = "Resumen"
    ws_acc, ws_dat, ws_est, ws_deu = (wb.create_sheet(n) for n in ("Acciones", "Datos", "Estadística", "Deuda"))
    pos = _hoja_datos(ws_dat, d)
    cols_est = _hoja_estadistica(ws_est, d, pos)
    _hoja_resumen(ws_res, ws_dat, ws_est, d, pos, cols_est)
    _hoja_acciones(ws_acc, d, acc, fichas_)
    _hoja_deuda(ws_deu, d)
    for w in wb.worksheets:
        w.page_setup.orientation, w.page_setup.fitToWidth, w.page_setup.fitToHeight = "landscape", 1, 0
        w.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    return X._guardar(wb)


def _hoja_datos(ws, d):
    """Fecha | precio | variación de cada instrumento; a la derecha Ra - Rprom, su cuadrado y el rendimiento acumulado."""
    items = d["items"]
    n = len(items)
    N = len(d["fechas"])
    r0, ult = 6, 5 + N
    _tit(ws, "Datos: precio de cierre y variación diaria", "Variación = ((cierre de hoy / cierre anterior) - 1) x 100. Acciones en USD; IPC y S&P 500 en puntos. Sin dato = la bolsa no operó.")
    ws.column_dimensions["A"].width = 12
    _enc(ws, 4, 1, "Fecha", alto=20)
    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    pos = {}
    mapas = [_por_fecha(it) for it in items]
    prev = [None] * n
    c_dif, c_sq, c_acu = 2 + 2 * n + 1, 2 + 2 * n + 1 + n + 1, 2 + 2 * n + 1 + 2 * (n + 1)
    for k, it in enumerate(items):
        cp, cv = 2 + 2 * k, 3 + 2 * k
        pos[it["clave"]] = {"precio": cp, "var": cv, "dif": c_dif + k, "sq": c_sq + k, "acu": c_acu + 1 + k}
        color = GOSC if it["indice"] else G
        _enc(ws, 4, cp, it["clave"], color=color)
        _enc(ws, 4, cv, it["clave"], color=color)
        ws.merge_cells(start_row=4, start_column=cp, end_row=4, end_column=cv)
        _enc(ws, 5, cp, "Precio de cierre", 13, color=color)
        _enc(ws, 5, cv, "Variación (%)", 12, color=color)
        _enc(ws, 4, c_dif + k, "Ra - Rprom", 11, color=color)
        _enc(ws, 5, c_dif + k, it["clave"], color=color)
        _enc(ws, 4, c_sq + k, "(Ra - Rprom)²", 11, color=color)
        _enc(ws, 5, c_sq + k, it["clave"], color=color)
        _enc(ws, 4, c_acu + 1 + k, "Rend. acumulado (%)", 11, color=color)
        _enc(ws, 5, c_acu + 1 + k, it["clave"], color=color)
    _enc(ws, 4, c_acu, "Fecha", 12)
    ws.merge_cells(start_row=4, start_column=c_acu, end_row=5, end_column=c_acu)
    for c in (2 + 2 * n, c_dif + n, c_sq + n):
        ws.column_dimensions[LETRA(c)].width = 3
    acu = [_acumulado(d, it) for it in items]
    for i, f in enumerate(d["fechas"]):
        r = r0 + i
        ws.cell(r, 1, _f(f)).number_format = "dd/mm/yyyy"
        ws.cell(r, c_acu, _f(f)).number_format = "dd/mm/yyyy"
        for k, (it, m) in enumerate(zip(items, mapas)):
            cp, cv = 2 + 2 * k, 3 + 2 * k
            if f in m:
                ws.cell(r, cp, round(m[f], 4)).number_format = F_PX
                if prev[k] is not None:
                    ws.cell(r, cv, (m[f] / prev[k] - 1) * 100).number_format = F_RET
                    L = LETRA(cv)
                    ws.cell(r, c_dif + k, f'=IF({L}{r}="","",{L}{r}-AVERAGE({L}${r0}:{L}${ult}))').number_format = "0.0000"
                    ws.cell(r, c_sq + k, f'=IF({LETRA(c_dif + k)}{r}="","",{LETRA(c_dif + k)}{r}^2)').number_format = "0.0000"
                prev[k] = m[f]
            if acu[k][i] is not None:
                ws.cell(r, c_acu + 1 + k, round(acu[k][i], 4)).number_format = "0.00"
        for j in range(1, c_acu + n + 1):
            ws.cell(r, j).font = _fnt()
        _borde(ws, r, 1, 1 + 2 * n, i % 2 == 1)
    for k in range(n):
        _colorear(ws, f"{LETRA(3 + 2 * k)}{r0}:{LETRA(3 + 2 * k)}{ult}")
        _colorear(ws, f"{LETRA(c_acu + 1 + k)}{r0}:{LETRA(c_acu + 1 + k)}{ult}")
    ws.freeze_panes = "B6"
    pos["_fil"] = (r0, ult)
    pos["_acu_fecha"] = c_acu
    return pos


def _hoja_estadistica(ws, d, pos):
    """Estadística de la clase para cada instrumento (fórmulas sobre la hoja Datos) y relación con los índices."""
    items, acc, idx = d["items"], _acciones(d), _indices(d)
    r0, ult = pos["_fil"]
    _tit(ws, "Estadística del rendimiento diario (Ra, en %)")
    ws.column_dimensions["A"].width = 34
    _enc(ws, 4, 1, "Medida")
    cols = {}
    for k, it in enumerate(items):
        cols[it["clave"]] = 2 + k
        _enc(ws, 4, 2 + k, it["clave"], 12, color=GOSC if it["indice"] else G)
    rng = lambda it: f"Datos!${LETRA(pos[it['clave']]['var'])}${r0}:${LETRA(pos[it['clave']]['var'])}${ult}"
    sqr = lambda it: f"Datos!${LETRA(pos[it['clave']]['sq'])}${r0}:${LETRA(pos[it['clave']]['sq'])}${ult}"
    filas = [("Precio inicial", lambda it, c: it["pi"], F_PX), ("Precio final", lambda it, c: it["pf"], F_PX),
             ("Rendimiento efectivo (%)", lambda it, c: f"=(({c}6/{c}5)-1)*100", F_RET),
             ("Rendimiento promedio diario, Rprom (%)", lambda it, c: f"=AVERAGE({rng(it)})", F_RET),
             ("Error típico", lambda it, c: f"=STDEV({rng(it)})/SQRT(COUNT({rng(it)}))", "0.0000"), ("Mediana", lambda it, c: f"=MEDIAN({rng(it)})", "0.0000"),
             ("Moda", lambda it, c: f'=IFERROR(MODE({rng(it)}),"No se repite")', "0.0000"), ("Desviación estándar", lambda it, c: f"=STDEV({rng(it)})", "0.0000"),
             ("Varianza de la muestra", lambda it, c: f"=VAR({rng(it)})", "0.0000"), ("Curtosis", lambda it, c: f"=KURT({rng(it)})", "0.0000"),
             ("Coeficiente de asimetría", lambda it, c: f"=SKEW({rng(it)})", "0.0000"), ("Rango", lambda it, c: f"=MAX({rng(it)})-MIN({rng(it)})", "0.0000"),
             ("Mínimo", lambda it, c: f"=MIN({rng(it)})", "0.0000"), ("Máximo", lambda it, c: f"=MAX({rng(it)})", "0.0000"), ("Suma", lambda it, c: f"=SUM({rng(it)})", "0.0000"),
             ("Días trabajados", lambda it, c: f"=COUNT({rng(it)})", "0"), ("Suma de (Ra - Rprom)²", lambda it, c: f"=SUM({sqr(it)})", "0.0000")]
    fila_de = {}
    for i, (et, fn, nf) in enumerate(filas):
        r = 5 + i
        fila_de[et] = r
        ws.cell(r, 1, et).font = _fnt(bold=True)
        for it in items:
            c = LETRA(cols[it["clave"]])
            cell = ws.cell(r, cols[it["clave"]], fn(it, c))
            cell.number_format, cell.font, cell.alignment = nf, _fnt(), Alignment(horizontal="right")
        _borde(ws, r, 1, 1 + len(items), i % 2 == 1)
    _colorear(ws, f"B7:{LETRA(1 + len(items))}8")
    r1 = 5 + len(filas) + 1
    _seccion(ws, r1, "Relación con los índices (fechas en que operaron los dos)", 1, 1 + len(items))
    enc = ["Medida"] + [x["clave"] for x in acc]
    r2 = r1 + 1
    for j, t in enumerate(enc, 1):
        _enc(ws, r2, j, t, color=GOSC if j == 1 else None)
    r = r2 + 1
    for ix in idx:
        for etq, key, nf in ((f"Cov({ix['clave']}, acción)", "cov", "0.0000"), (f"Var({ix['clave']})", "var", "0.0000"), (f"Beta frente al {ix['clave']}", "beta", "0.00"), (f"Correlación con {ix['clave']}", "corr", "0.00")):
            ws.cell(r, 1, etq).font = _fnt(bold=True)
            for j, it in enumerate(acc, 2):
                b = _beta(d, it, ix)
                c = ws.cell(r, j, b[key] if b else None)
                c.number_format, c.font, c.alignment = nf, _fnt(), Alignment(horizontal="right")
            _borde(ws, r, 1, 1 + len(acc), (r % 2) == 0)
            r += 1
    ws.freeze_panes = "B5"
    return {"cols": cols, "filas": fila_de}


def _hoja_resumen(ws, wd, we, d, pos, ce):
    items, acc, idx = d["items"], _acciones(d), _indices(d)
    r0, ult = pos["_fil"]
    _tit(ws, "Rendimiento de 5 acciones frente al S&P 500 y al IPC", f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])} · Fuentes: Yahoo Finance, SEC EDGAR, Banco de México")
    cols = ["Instrumento", "Precio inicial", "Precio final", "Máximo", "Mínimo", "Rendimiento efectivo (%)", "Rendimiento promedio diario Rprom (%)", "Desviación estándar diaria (%)"] + \
          [f"Beta {x['clave']}" for x in idx] + [f"Diferencia con el {x['clave']} (puntos)" for x in idx]
    anchos = [30, 13, 13, 13, 13, 16, 18, 16] + [11] * len(idx) + [16] * len(idx)
    for j, (t, a) in enumerate(zip(cols, anchos), 1):
        _enc(ws, 4, j, t, a)
    ws.row_dimensions[4].height = 54
    fila = ce["filas"]
    cc = ce["cols"]
    fr = {x["clave"]: 5 + i for i, x in enumerate(items)}
    for i, it in enumerate(items):
        r = 5 + i
        c = LETRA(cc[it["clave"]])
        ws.cell(r, 1, f"{it['clave']} · {it['nombre']}" if not it["indice"] else it["nombre"])
        for j, key in ((2, "Precio inicial"), (3, "Precio final"), (6, "Rendimiento efectivo (%)"), (7, "Rendimiento promedio diario, Rprom (%)"), (8, "Desviación estándar")):
            ws.cell(r, j, f"=Estadística!{c}{fila[key]}")
        ws.cell(r, 4, round(it["pmax"], 4))
        ws.cell(r, 5, round(it["pmin"], 4))
        for k, ix in enumerate(idx):
            if not it["indice"]:
                col_est = LETRA(2 + acc.index(it))
                rb = [rr for rr in range(1, 80) if we.cell(rr, 1).value == f"Beta frente al {ix['clave']}"]
                if rb:
                    ws.cell(r, 9 + k, f"=Estadística!{col_est}{rb[0]}").number_format = "0.00"
                ws.cell(r, 9 + len(idx) + k, f"=F{r}-$F${fr[ix['clave']]}").number_format = F_RET
        for j in (2, 3, 4, 5):
            ws.cell(r, j).number_format = F_PX
        for j in (6, 7):
            ws.cell(r, j).number_format = F_RET
        ws.cell(r, 8).number_format = "0.00"
        for j in range(1, len(cols) + 1):
            ws.cell(r, j).font = _fnt(bold=(j == 1))
        _borde(ws, r, 1, len(cols), i % 2 == 1)
        if it["indice"]:
            for j in range(1, len(cols) + 1):
                ws.cell(r, j).fill = PatternFill("solid", fgColor="EFEFEF")
    _colorear(ws, f"F5:G{4 + len(items)}")
    _colorear(ws, f"{LETRA(9 + len(idx))}5:{LETRA(8 + 2 * len(idx))}{4 + len(items)}")
    # gráfica de rendimiento acumulado (datos en la hoja Datos)
    ch = LineChart()
    ch.title, ch.height, ch.width = "Rendimiento acumulado (%)", 11.5, 24
    ch.y_axis.number_format, ch.x_axis.number_format = "0.00", "dd/mm"
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.x_axis.tickLblSkip = max(1, len(d["fechas"]) // 8)
    ch.x_axis.tickLblPos = "low"
    colores = [AZUL, NARANJA, "0A7F58", "A86D00", "C23B78", "7F7F7F", "231F20"]
    for k, it in enumerate(items):
        ch.add_data(Reference(wd, min_col=pos[it["clave"]]["acu"], min_row=5, max_row=ult), titles_from_data=True)
        s = ch.series[-1]
        s.graphicalProperties.line.solidFill = colores[k]
        s.graphicalProperties.line.width = 26000 if it["indice"] else 17000
        if it["indice"]:
            s.graphicalProperties.line.dashStyle = "dash"
        s.marker.symbol, s.smooth = "none", False
    ch.set_categories(Reference(wd, min_col=pos["_acu_fecha"], min_row=6, max_row=ult))
    ws.add_chart(ch, f"A{6 + len(items) + 2}")
    # barras: efectivo y promedio
    for n, (clave, titulo, ancla) in enumerate((("Rendimiento efectivo (%)", "Rendimiento efectivo del periodo (%)", f"I{6 + len(items) + 2}"), ("Rendimiento promedio diario, Rprom (%)", "Rendimiento promedio diario Rprom (%)", f"I{6 + len(items) + 14}"))):
        b = BarChart()
        b.type, b.title, b.height, b.width, b.legend = "col", titulo, 5.6, 15, None
        b.y_axis.number_format = "0.00"
        b.x_axis.tickLblPos = "low"
        b.x_axis.delete = b.y_axis.delete = False
        b.add_data(Reference(we, min_col=1, max_col=1 + len(items), min_row=fila[clave]), from_rows=True, titles_from_data=True)
        b.set_categories(Reference(we, min_col=2, max_col=1 + len(items), min_row=4))
        b.series[0].graphicalProperties.solidFill = G
        b.series[0].invertIfNegative = False
        ws.add_chart(b, ancla)
    ws.freeze_panes = "B5"


def _hoja_acciones(ws, d, acc, fichas_):
    _tit(ws, "Acciones: ficha", "Cifras de la SEC (EDGAR) y de Yahoo Finance. USD.")
    ws.column_dimensions["A"].width = 44
    _enc(ws, 4, 1, "Concepto", alto=30)
    for j, it in enumerate(acc, 2):
        _enc(ws, 4, j, f"{it['clave']}\n{it['nombre']}", 24)
    num = lambda v, fmt: (v, fmt)
    bloques = [
        ("Identificación", [
            ("Empresa", lambda it, f: f["F"].get("denominacion")), ("Bolsa", lambda it, f: f["F"].get("clave")), ("Sector", lambda it, f: SECTOR[it["ticker"]]),
            ("Clasificación (SEC)", lambda it, f: SIC_ES.get(f["sic"], f["sic"]) if f["sic"] else None), ("Tipo de acción", lambda it, f: "Comunes"), ("Serie", lambda it, f: "Clase única"),
            ("Constitución", lambda it, f: CONSTITUCION[it["ticker"]]), ("Domicilio", lambda it, f: f["F"].get("domicilio", "").replace(", EE. UU.", ""))]),
        ("Capital", [
            ("Acciones autorizadas", lambda it, f: num(f["autorizadas"], "#,##0")), ("Acciones emitidas", lambda it, f: num(f["emitidas"], "#,##0")),
            ("Acciones en circulación", lambda it, f: num(f["F"].get("acciones"), "#,##0")), ("Valor par por acción", lambda it, f: num(f["par"], "0.00000000")),
            ("Capital social (millones)", lambda it, f: num(f["capital_social"], "#,##0.00")), ("Capital contable (millones)", lambda it, f: num(f["cif"].get("Capital contable", (None,))[0], "#,##0.00"))]),
        ("Mercado y bursatilidad", [
            ("Precio final", lambda it, f: num(it["pf"], F_PX)), ("Valor de mercado (millones)", lambda it, f: num(it["pf"] * f["F"]["acciones"] / 1e6 if f["F"].get("acciones") else None, "#,##0.00")),
            ("Cambio en 12 meses (%)", lambda it, f: num(it.get("cambio_12m"), F_RET)), ("Máximo de 12 meses", lambda it, f: num(it.get("max52"), F_PX)), ("Mínimo de 12 meses", lambda it, f: num(it.get("min52"), F_PX)),
            ("Importe operado diario (millones)", lambda it, f: num(f["burs"]["importe"] if f["burs"] else None, "#,##0.00")),
            ("Volumen diario (millones de acciones)", lambda it, f: num(f["burs"]["volumen"] if f["burs"] else None, "#,##0.00")),
            ("Rotación diaria (% de acciones en circulación)", lambda it, f: num(f["burs"]["rotacion"] if f["burs"] else None, "0.000")),
            ("Posición de bursatilidad (1 = la más operada)", lambda it, f: num(f["burs"]["posicion"] if f["burs"] else None, "0"))]),
        ("Finanzas del último ejercicio (millones)", [
            ("Cierre del ejercicio", lambda it, f: f["fin"]["periodos"][0] if f["fin"] else None), ("Ingresos", lambda it, f: num(f["cif"].get("Ingresos", (None,))[0], "#,##0.00")),
            ("Variación de ingresos (%)", lambda it, f: num(f["crec_ing"], F_RET)), ("Utilidad neta", lambda it, f: num(f["cif"].get("Utilidad neta", (None,))[0], "#,##0.00")),
            ("Variación de utilidad neta (%)", lambda it, f: num(f["crec_util"], F_RET)), ("Activos totales", lambda it, f: num(f["cif"].get("Activos totales", (None,))[0], "#,##0.00")),
            ("Pasivos totales", lambda it, f: num(f["cif"].get("Pasivos totales", (None,))[0], "#,##0.00")), ("Utilidad por acción", lambda it, f: num(f["cif"].get("Utilidad por acción", (None,))[0], "0.00")),
            ("Dividendo por acción", lambda it, f: num(f["cif"].get("Dividendo por acción", (None,))[0], "0.00"))]),
        ("Riesgo en el periodo", [
            ("Volatilidad anual (%)", lambda it, f: num(f["vol"], "0.00")), ("Beta frente al S&P 500", lambda it, f: num((f["betas"].get("S&P 500") or {}).get("beta"), "0.00")),
            ("Beta frente al IPC", lambda it, f: num((f["betas"].get("IPC") or {}).get("beta"), "0.00"))]),
    ]
    r = 5
    for titulo, filas in bloques:
        _seccion(ws, r, titulo, 1, 1 + len(acc))
        r += 1
        for etq, fn in filas:
            ws.cell(r, 1, etq).font = _fnt(bold=True)
            ws.cell(r, 1).alignment = Alignment(vertical="top")
            largo = 0
            for j, it in enumerate(acc, 2):
                val = fn(it, fichas_[it["clave"]])
                fmt = None
                if isinstance(val, tuple):
                    val, fmt = val
                c = ws.cell(r, j, val if val is not None else "-")
                c.font = _fnt()
                c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(val, (int, float)) else "left")
                if fmt and isinstance(val, (int, float)):
                    c.number_format = fmt
                if isinstance(val, str):
                    largo = max(largo, len(val))
            ws.row_dimensions[r].height = max(15, 14 * (largo // 26 + 1))
            _borde(ws, r, 1, 1 + len(acc), (r % 2) == 0)
            r += 1
    ws.cell(r + 1, 1, "Bursatilidad: indicador propio con el volumen de Yahoo Finance; el índice oficial de la BMV no se publica para estas emisoras.").font = _fnt(italic=True, color=GTXT, size=9)
    ws.freeze_panes = "B5"


def _hoja_deuda(ws, d):
    deu = d["deuda"]
    _tit(ws, "Deuda: ficha y tasas semanales", "Banco de México. Riesgo y objetivo: material del equipo. Variación en puntos base (pb).")
    ws.column_dimensions["A"].width = 24
    _enc(ws, 4, 1, "Concepto", alto=22)
    for j, x in enumerate(deu):
        _enc(ws, 4, 2 + 2 * j, x["corto"], 15)
        _enc(ws, 4, 3 + 2 * j, x["corto"], 13)
        ws.merge_cells(start_row=4, start_column=2 + 2 * j, end_row=4, end_column=3 + 2 * j)
    ficha = [("Emisor", lambda x: EMISOR[x["corto"]]), ("Plazo", lambda x: PLAZO[x["corto"]]), ("Intereses", lambda x: INTERES[x["corto"]]), ("Valor nominal", lambda x: NOMINAL[x["corto"]]),
             ("Tasa", lambda x: TASA[x["corto"]]), ("Riesgo", lambda x: x["riesgo"]), ("Objetivo", lambda x: x["objetivo"]),
             ("Última cifra", lambda x: (x["ult"], "0.00")), ("Fecha", lambda x: R.fecha_corta(x["fult"])), ("Mínimo", lambda x: (x["min"], "0.00")), ("Máximo", lambda x: (x["max"], "0.00")), ("Promedio", lambda x: (x["media"], "0.00"))]
    for i, (et, fn) in enumerate(ficha, 5):
        ws.cell(i, 1, et).font = _fnt(bold=True)
        ws.cell(i, 1).alignment = Alignment(vertical="top")
        largo = 0
        for j, x in enumerate(deu):
            v = fn(x)
            fmt = None
            if isinstance(v, tuple):
                v, fmt = v
            ws.merge_cells(start_row=i, start_column=2 + 2 * j, end_row=i, end_column=3 + 2 * j)
            c = ws.cell(i, 2 + 2 * j, v)
            c.font = _fnt()
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(v, (int, float)) else "left")
            if fmt:
                c.number_format = fmt
            if isinstance(v, str):
                largo = max(largo, len(v))
        ws.row_dimensions[i].height = max(15, 14 * (largo // 26 + 1))
        _borde(ws, i, 1, 1 + 2 * len(deu), i % 2 == 0)
    ws.cell(5 + len(ficha), 1, "Unidades: % anual (Udibonos, % real); papel comercial, millones de pesos colocados por semana (sin colocaciones en el periodo).").font = _fnt(italic=True, color=GTXT, size=9)
    top = 5 + len(ficha) + 2
    _seccion(ws, top, "Tasas semanales", 1, 1 + 2 * len(deu))
    _enc(ws, top + 1, 1, "Fecha", alto=22)
    ws.merge_cells(start_row=top + 1, start_column=1, end_row=top + 2, end_column=1)
    for k, x in enumerate(deu):
        _enc(ws, top + 1, 2 + 2 * k, x["corto"])
        _enc(ws, top + 1, 3 + 2 * k, x["corto"])
        ws.merge_cells(start_row=top + 1, start_column=2 + 2 * k, end_row=top + 1, end_column=3 + 2 * k)
        _enc(ws, top + 2, 2 + 2 * k, "Monto (mdp)" if x["es_monto"] else ("Tasa real (%)" if "real" in x["unidad"] else "Tasa (%)"))
        _enc(ws, top + 2, 3 + 2 * k, "Var. (mdp)" if x["es_monto"] else "Var. (pb)")
    fechas = sorted({f for x in deu for f, _ in x["serie"]})
    mapas = [{f: (v, vr) for (f, v), vr in zip(x["serie"], x["var"])} for x in deu]
    r0 = top + 3
    for i, f in enumerate(fechas):
        r = r0 + i
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
    ult = r0 + len(fechas) - 1
    for k in range(len(deu)):
        _colorear(ws, f"{LETRA(3 + 2 * k)}{r0}:{LETRA(3 + 2 * k)}{ult}")
    rs = ult + 2
    for i, (et, fx) in enumerate([("Media", "AVERAGE"), ("Desviación estándar", "STDEV"), ("Mínimo", "MIN"), ("Máximo", "MAX")]):
        r = rs + i
        ws.cell(r, 1, et).font = _fnt(bold=True)
        for k in range(len(deu)):
            for col in (2 + 2 * k, 3 + 2 * k):
                L = LETRA(col)
                c = ws.cell(r, col, f"={fx}({L}{r0}:{L}{ult})")
                c.number_format, c.font = "0.00", _fnt()
        _borde(ws, r, 1, 1 + 2 * len(deu), i % 2 == 1)
    tasas = [(k, x) for k, x in enumerate(deu) if not x["es_monto"]]
    ch = LineChart()
    ch.title, ch.height, ch.width, ch.dispBlanksAs = "Tasa de cada subasta o colocación (%)", 9, 17, "span"
    ch.y_axis.number_format, ch.x_axis.number_format = "0.00", "dd/mm"
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.x_axis.tickLblSkip = max(1, len(fechas) // 6)
    palette = [AZUL, NARANJA, "0A7F58", "C23B78"]
    for n, (k, x) in enumerate(tasas):
        ch.add_data(Reference(ws, min_col=2 + 2 * k, min_row=r0, max_row=ult), titles_from_data=False)
        s = ch.series[-1]
        s.tx = SeriesLabel(v=x["corto"])
        s.graphicalProperties.line.solidFill = palette[n % 4]
        s.graphicalProperties.line.width = 19000
        s.marker.symbol, s.marker.size, s.smooth = "circle", 4, False
        s.marker.graphicalProperties.solidFill = palette[n % 4]
    ch.set_categories(Reference(ws, min_col=1, min_row=r0, max_row=ult))
    ws.add_chart(ch, f"{LETRA(2 + 2 * len(deu) + 1)}{top + 1}")
    ws.freeze_panes = "B5"


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
    msg = (f"Mayor rendimiento: {mejor['clave']} {mejor['efectivo']:+.2f} %  |  Menor: {peor['clave']} {peor['efectivo']:+.2f} %  |  Superan al S&P 500 ({sp['efectivo']:+.2f} %): {len(ganan)} de {len(acc)}") if sp else ""
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
    _pagina(pdf, "Cada acción frente a su índice", "Color: acción  |  Negro: S&P 500  |  Gris: IPC  |  Rendimiento acumulado (%)")
    pos = [(14, 34), (110, 34), (206, 34), (14, 114), (110, 114)]
    for (x0, y0), it in zip(pos, acc):
        s = [(it["clave"], ac[it["clave"]], col_acc[it["clave"]], 0.7, False)]
        if sp:
            s.append(("S&P 500", ac["S&P 500"], NEGRO, 0.5, True))
        if ipc:
            s.append(("IPC", ac["IPC"], GRIS, 0.5, True))
        b = fichas_[it["clave"]]["betas"].get("S&P 500")
        _lineas(pdf, x0, y0, 90, 72, s, fechas, f"{it['clave']} · {it['nombre']}" + (f"   (beta frente al S&P 500: {b['beta']:.2f})" if b else ""))
    pdf.set_xy(206, 118)
    pdf.set_font("Barlow", "B", 9.5)
    pdf.set_text_color(*NEGRO)
    pdf.cell(75, 5, "Frente al S&P 500")
    filas = []
    for it in acc:
        b = fichas_[it["clave"]]["betas"].get("S&P 500")
        filas.append([it["clave"], _n(it["efectivo"], True), _n(it["efectivo"] - sp["efectivo"], True) if sp else "-", f"{b['beta']:.2f}" if b else "s/d"])
    est = {}
    for i, it in enumerate(acc):
        est[(i, 1)] = _color(it["efectivo"])
        if sp:
            est[(i, 2)] = _color(it["efectivo"] - sp["efectivo"])
    _tabla(pdf, ["Acción", "Rend. (%)", "Dif. (pts)", "Beta"], filas, (19, 19, 19, 17), None, est, size=8.6, alto=6.4, y=125, x=206, tope=76)

    # 4 precio de cierre y rendimiento
    _pagina(pdf, "Precio de cierre y rendimiento", "Efectivo = ((precio final / precio inicial) - 1) x 100  |  Rprom = media de las variaciones diarias")
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
    _pagina(pdf, "Riesgo y estadística", "Variación diaria en %  |  Estadística de muestra, como en Excel")
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

    # 6 ficha de las acciones
    _pagina(pdf, "Ficha de las acciones", "Datos reales: SEC (EDGAR) y Yahoo Finance  |  Cifras en USD")
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
    _pagina(pdf, "Deuda", "Subastas y colocaciones semanales  |  Fuente: Banco de México")
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
    filas, est = [], {}
    for i, it in enumerate(acc):
        f = fichas_[it["clave"]]
        b = f["betas"].get("S&P 500")
        dif = it["efectivo"] - sp["efectivo"] if sp else None
        filas.append([it["clave"], _n(it["efectivo"], True), _n(dif, True) if dif is not None else "-", f"{f['vol']:.2f}", f["nivel"].capitalize(), f"{b['beta']:.2f}" if b else "s/d",
                      "Supera al S&P 500" if dif is not None and dif > 0 else "Por debajo del S&P 500"])
        est[(i, 1)] = _color(it["efectivo"])
        if dif is not None:
            est[(i, 2)] = _color(dif)
    yc = _tabla(pdf, ["Acción", "Rend. efectivo (%)", "Dif. S&P 500 (pts)", "Volatilidad anual (%)", "Volatilidad", "Beta S&P 500", "Resultado"], filas, (30, 40, 44, 38, 30, 30, 57), ["LEFT"] + ["RIGHT"] * 3 + ["CENTER"] * 2 + ["LEFT"], est, size=9.2, alto=7, y=34)
    tasas_ = [x for x in deu if not x["es_monto"]]
    filas = [[x["corto"], f"{x['ult']:.2f}", f"{x['min']:.2f}", f"{x['max']:.2f}", f"{x['media']:.2f}"] for x in tasas_]
    yd2 = _tabla(pdf, ["Deuda (tasa, %)", "Última", "Mínimo", "Máximo", "Promedio"], filas, (46, 26, 26, 26, 26), ["LEFT"] + ["RIGHT"] * 4, None, size=9, alto=6.4, y=yc + 10, x=14, tope=150)
    fm = [["Variación diaria Ra", "((precio de hoy / precio anterior) - 1) x 100"], ["Rendimiento efectivo", "((precio final / precio inicial) - 1) x 100"], ["Rendimiento promedio Rprom", "Promedio de los Ra"],
          ["Diferencia", "Ra - Rprom, y su cuadrado"], ["Beta", "Cov(índice, acción) / Var(índice), con las fechas en que operaron los dos"],
          ["Periodo", f"1 de marzo al {'25 de noviembre' if d['completo'] else R.fecha_corta(d['ultimo']) + ' (el análisis termina el 25 de noviembre de 2026)'}"],
          ["Fuentes", "Yahoo Finance (precios), SEC EDGAR (empresas), Banco de México (deuda), material del equipo (riesgo y objetivo)"]]
    _tabla(pdf, ["Método", "Definición"], fm, (32, 79), ["LEFT", "LEFT"], None, size=8, alto=4.6, y=yc + 10, x=172, tope=111)
    return bytes(pdf.output())
