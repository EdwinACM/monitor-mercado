"""Ejercicio de rendimientos de las acciones y del IPC: Excel (con las fórmulas de la clase) y presentación ejecutiva en PDF.

Rendimiento del activo en cada día:   Ra = ((precio de hoy / precio del día anterior) - 1) x 100
Rendimiento efectivo del periodo:     ((precio final / precio inicial) - 1) x 100
Rendimiento promedio (Rprom):         promedio de los Ra del periodo
Diferencia de rendimiento:            Ra - Rprom (y su cuadrado)

El periodo empieza el 1 de marzo de 2026 y termina el 25 de noviembre de 2026 (o en el último cierre disponible si esa fecha aún no llega).
"""
import math
from datetime import date, datetime
from statistics import mean, median, stdev, variance

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import excel as X
import fichas
import reportes as R
import server

FIN_ANALISIS = date(2026, 11, 25)
G, GRIS_S, GSUAVE = "750946", "E8E9EA", "F7ECF1"
COLORES = [(29, 99, 193), (200, 72, 15), (10, 127, 88), (168, 109, 0), (194, 59, 120)]
NEGRO, GRIS, BLANCO, GUINDA = (35, 31, 32), (99, 101, 105), (255, 255, 255), (117, 9, 70)
GUINDA_SUAVE, GRIS_SUAVE = (247, 236, 241), (232, 233, 234)
SUBE, BAJA = (0, 100, 63), (179, 38, 30)
TZ = server.TZ
NOMBRES = {"IPC": "S&P/BMV IPC (Índice de Precios y Cotizaciones)"}


# ----------------------------------------------------------------------------- datos
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "KO"]
SECTOR = {"AAPL": "Tecnología", "MSFT": "Tecnología y software", "NVDA": "Semiconductores e inteligencia artificial", "TSLA": "Automóviles eléctricos", "KO": "Consumo (bebidas)"}
# Riesgo y objetivo de cada instrumento de deuda, según el material del equipo
DEUDA_EQ = {
    "CETES 28 días": ("CETES", "Muy bajo", "Financiar al Gobierno Federal."),
    "BONOS M 10 años": ("BONOS", "Bajo", "Obtener financiamiento de largo plazo para el gobierno."),
    "UDIBONOS 10 años": ("UDIBONOS", "Bajo", "Mantener el poder adquisitivo de la inversión."),
    "PAPEL COMERCIAL": ("PAPEL COMERCIAL", "Medio: depende de la empresa emisora", "Obtener recursos rápidamente."),
    "CERTIFICADOS BURSÁTILES": ("CERTIFICADOS BURSÁTILES", "Variable según la solvencia del emisor", "Financiar proyectos, expansión o capital de trabajo."),
}


def preparar(fin=None):
    """Series de cierre del periodo para 5 acciones de EE. UU. y el IPC, más las tasas de 5 instrumentos de deuda."""
    import contexto
    hoy = datetime.now(TZ).date()
    fin = min(fin or FIN_ANALISIS, FIN_ANALISIS, hoy)
    ini = server.INICIO
    hist = server._historiales()
    res, _ = contexto.series(fin)
    ipc = [(f, v) for f, v in res.get("ipc", []) if ini.isoformat() <= f <= fin.isoformat()]
    items = []
    for t in TICKERS:
        rows = [(r["fecha"], r["cierre"]) for r in hist.get(t, []) if ini.isoformat() <= r["fecha"] <= fin.isoformat()]
        if len(rows) >= 3:
            it = _instrumento(t, server.ACCIONES[t], server.META[t]["moneda"], t, rows)
            todos = [(r["fecha"], r["cierre"]) for r in hist.get(t, [])]
            hace = (date.fromisoformat(rows[-1][0]) - __import__("datetime").timedelta(days=365)).isoformat()
            ant = [c for f, c in todos if f <= hace]
            it["cambio_12m"] = (rows[-1][1] / ant[-1] - 1) * 100 if ant else None
            it["max52"] = max(c for f, c in todos if f > hace)
            it["min52"] = min(c for f, c in todos if f > hace)
            items.append(it)
    if len(ipc) >= 3:
        items.append(_instrumento("IPC", NOMBRES["IPC"], "puntos", "IPC", ipc))
    if not items:
        raise ValueError("No hay precios en el periodo.")
    fechas = sorted({f for it in items for f, _ in it["serie"]})
    deuda = []
    desde_d = ini.isoformat()
    for sd in server.deuda(date.today() - __import__("datetime").timedelta(days=300)):
        if sd["nombre"] not in DEUDA_EQ:
            continue
        datos = [x for x in sd["datos"] if desde_d <= x["fecha"] <= fin.isoformat()]
        if len(datos) < 2:
            continue
        es_monto = sd["tipo"] == "monto"
        vals = [x["valor"] / 1000 if es_monto else x["valor"] for x in datos]
        var = [None] + [((vals[i] - vals[i - 1]) if es_monto else (vals[i] - vals[i - 1]) * 100) for i in range(1, len(vals))]
        deuda.append({"nombre": sd["nombre"], "corto": DEUDA_EQ[sd["nombre"]][0], "riesgo": DEUDA_EQ[sd["nombre"]][1], "objetivo": DEUDA_EQ[sd["nombre"]][2], "tipo": sd["tipo"], "unidad": sd["unidad"],
                      "serie": [(x["fecha"], v) for x, v in zip(datos, vals)], "var": var, "es_monto": es_monto,
                      "media": mean(vals), "min": min(vals), "max": max(vals), "ult": vals[-1], "fult": datos[-1]["fecha"], "ini": vals[0], "extra": datos[-1].get("extra", {})})
    return {"inicio": ini.isoformat(), "fin": fin.isoformat(), "ultimo": max(f for it in items for f, _ in it["serie"]), "items": items, "fechas": fechas, "deuda": deuda,
            "completo": fin >= FIN_ANALISIS, "generado": datetime.now(TZ)}


def _stats(ra):
    n = len(ra)
    m, s = mean(ra), stdev(ra)
    mo = None
    cuenta = {}
    for v in ra:
        cuenta[round(v, 10)] = cuenta.get(round(v, 10), 0) + 1
    mx = max(cuenta.values())
    if mx > 1:
        mo = next(v for v in ra if cuenta[round(v, 10)] == mx)
    asim = n / ((n - 1) * (n - 2)) * sum(((v - m) / s) ** 3 for v in ra) if n > 2 and s else None
    curt = (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3)) * sum(((v - m) / s) ** 4 for v in ra) - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))) if n > 3 and s else None
    return {"n": n, "media": m, "error": s / math.sqrt(n), "mediana": median(ra), "moda": mo, "desv": s, "var": variance(ra), "curtosis": curt, "asimetria": asim,
            "rango": max(ra) - min(ra), "min": min(ra), "max": max(ra), "suma": sum(ra)}


def _instrumento(clave, nombre, moneda, ticker, serie):
    p = [v for _, v in serie]
    ra = [(p[i] / p[i - 1] - 1) * 100 for i in range(1, len(p))]
    st = _stats(ra)
    efectivo = (p[-1] / p[0] - 1) * 100
    return {"clave": clave, "nombre": nombre, "moneda": moneda, "ticker": ticker, "serie": serie, "ra": ra, "stats": st, "efectivo": efectivo,
            "pi": p[0], "pf": p[-1], "fi": serie[0][0], "ff": serie[-1][0], "pmax": max(p), "pmin": min(p),
            "dif": [r - st["media"] for r in ra], "sumdif2": sum((r - st["media"]) ** 2 for r in ra)}


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


def _beta_ipc(d, it):
    ipc = next((x for x in d["items"] if x["clave"] == "IPC"), None)
    if not ipc or it["clave"] == "IPC":
        return None
    a, b = _por_fecha(it), _por_fecha(ipc)
    com = [f for f in d["fechas"] if f in a and f in b]
    if len(com) < 10:
        return None
    ra = [(a[com[i]] / a[com[i - 1]] - 1) * 100 for i in range(1, len(com))]
    rb = [(b[com[i]] / b[com[i - 1]] - 1) * 100 for i in range(1, len(com))]
    mb, ma = mean(rb), mean(ra)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (len(ra) - 1)
    vb, va = variance(rb), variance(ra)
    n = len(ra)
    pc, pv = cov * (n - 1) / n, vb * (n - 1) / n  # covarianza y varianza poblacionales, como COVAR y VARP de Excel
    return {"beta": cov / vb if vb else None, "corr": cov / math.sqrt(va * vb) if va and vb else None, "n": n, "cov": pc, "var": pv}


# ------------------------------------------------------------------------------ Excel
AMARILLO = PatternFill("solid", fgColor="FFFF00")


def _tit(ws, fila, texto, size=14):
    ws.cell(fila, 1, texto).font = Font(bold=True, size=size, color=G)


def _enc(ws, fila, col, texto, ancho=None):
    c = ws.cell(fila, col, texto)
    c.fill, c.font = PatternFill("solid", fgColor=G), Font(bold=True, color="FFFFFF")
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    if ancho:
        ws.column_dimensions[get_column_letter(col)].width = ancho
    return c


def _f(d):
    return datetime.strptime(d, "%Y-%m-%d").date()


FILA = Side(style="thin", color=GRIS_S)


def _borde(ws, r, c1, c2, par=False):
    for j in range(c1, c2 + 1):
        ws.cell(r, j).border = Border(bottom=FILA)
        if par:
            ws.cell(r, j).fill = PatternFill("solid", fgColor=GSUAVE)


def _nota(ws, fila, texto, col=1):
    ws.cell(fila, col, texto).font = Font(italic=True, color="636569", size=10)


def libro(d):
    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True
    items = d["items"]
    sub = f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}"
    ws = wb.active
    ws.title = "Léeme"
    ws.sheet_view.showGridLines = False
    for r in (1, 2):
        for c in range(1, 9):
            ws.cell(r, c).fill = PatternFill("solid", fgColor=G)
    ws["A1"], ws["A2"] = "Rendimientos de 5 acciones, el IPC y 5 instrumentos de deuda", sub
    ws["A1"].font, ws["A2"].font = Font(bold=True, size=16, color="FFFFFF"), Font(size=10.5, color="FFFFFF")
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 100
    ws.row_dimensions[1].height = 26
    filas = [
        ("Periodo", f"Del {R.fecha_corta(d['inicio'])} (inicio de la app) al {R.fecha_corta(d['ultimo'])}. " + ("El análisis ya cubre hasta el 25 de noviembre de 2026." if d["completo"] else
                  "El análisis termina el 25 de noviembre de 2026; este archivo llega al último cierre disponible y se completa al volver a generarlo después de esa fecha.")),
        ("Instrumentos", "Acciones: Apple (AAPL), Microsoft (MSFT), NVIDIA (NVDA), Tesla (TSLA) y Coca-Cola (KO), y el S&P/BMV IPC. Deuda: CETES, Bonos, Udibonos, papel comercial y certificados bursátiles."),
        ("Precio de cierre", "Último precio de cada sesión, en dólares para las acciones y en puntos para el IPC. Fuente: Yahoo Finance (referencia, no oficial)."),
        ("Rendimiento del activo (Ra)", "Variación diaria: ((precio de hoy / precio del día anterior) - 1) x 100. El primer día no tiene variación."),
        ("Rendimiento efectivo", "Rendimiento de todo el periodo: ((precio final / precio inicial) - 1) x 100."),
        ("Rendimiento promedio (Rprom)", "Promedio de los Ra diarios (suma de los rendimientos entre el número de días trabajados)."),
        ("Diferencia de rendimiento", "Ra - Rprom en cada día, y esa diferencia al cuadrado; con ellas se obtiene la varianza."),
        ("Beta frente al IPC", "Cov(IPC, acción) / Var(IPC), con los rendimientos diarios de las fechas en que operaron los dos."),
        ("Hojas", "Información general: sector, precio, comportamiento y datos reales de cada acción. Precios y variaciones: las 5 acciones y el IPC por fecha. Resumen y Gráficas: comparación de rendimientos. "
                  "Estadística: medidas de cada acción y del IPC. Una hoja por acción y por el IPC con las fórmulas de la clase. Deuda: tasas semanales, variaciones y ficha de cada instrumento. Conclusiones."),
        ("Monedas", "Las acciones están en dólares y el IPC en pesos (puntos): al compararlos, el rendimiento de las acciones no incluye el efecto del tipo de cambio sobre el peso."),
        ("Días sin operación", "Si una bolsa no operó un día (por ejemplo un festivo), ese instrumento queda en blanco esa fecha y su variación se calcula contra su cierre anterior disponible."),
        ("Cálculos", "Las hojas de cada acción usan fórmulas de Excel (promedio, desviación estándar, varianza, curtosis, asimetría, covarianza), así que puedes revisarlas y cambiarlas."),
        ("Aviso", R.AVISO),
    ]
    for i, (a, b) in enumerate(filas, 4):
        ws.cell(i, 1, a).font = Font(bold=True)
        c = ws.cell(i, 2, b)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(i, 1).alignment = Alignment(vertical="top")
        ws.row_dimensions[i].height = max(18, 15 * (len(b) // 95 + 1))
        _borde(ws, i, 1, 2, i % 2 == 1)
    ipc = next((x for x in items if x["clave"] == "IPC"), None)
    hojas = {}
    _hoja_general(wb, d)
    _hoja_ancha(wb, d)
    for it in items:
        hojas[it["clave"]] = _hoja_instrumento(wb, d, it, ipc)
    _hoja_resumen(wb, d, hojas)
    _hoja_graficas(wb, d)
    _hoja_estadistica(wb, d)
    _hoja_deuda(wb, d)
    _hoja_conclusiones(wb, d)
    orden = ["Léeme", "Información general", "Precios y variaciones", "Resumen", "Gráficas", "Estadística"] + [it["clave"] for it in items] + ["Deuda tasas", "Instrumentos de deuda", "Conclusiones"]
    wb._sheets = [wb[n] for n in orden]
    for w in wb.worksheets:
        w.page_setup.orientation, w.page_setup.fitToWidth, w.page_setup.fitToHeight = "landscape", 1, 0
        w.sheet_properties.pageSetUpPr = __import__("openpyxl").worksheet.properties.PageSetupProperties(fitToPage=True)
    return X._guardar(wb)


def _hoja_instrumento(wb, d, it, ipc):
    """Formato de la clase: datos a la izquierda, tabla de rendimientos, estadística, rendimientos ordenados y bloque contra el IPC."""
    ws = wb.create_sheet(it["clave"])
    ws.sheet_view.showGridLines = False
    n = len(it["serie"])
    r0 = 5
    ult = r0 + n - 1
    _tit(ws, 1, f"Rendimiento de precio de cierre: {it['nombre']}")
    _nota(ws, 2, "Ra = ((precio final - precio inicial) / precio inicial) x 100, con el precio del día anterior como precio inicial de cada día.")
    # datos tal como llegan (amarillo)
    _enc(ws, 4, 1, "Date", 12)
    _enc(ws, 4, 2, f"Precios Cierre {it['clave']}", 16)
    ws.column_dimensions["C"].width = 3
    for i, (f, p) in enumerate(it["serie"]):
        r = r0 + i
        c = ws.cell(r, 1, _f(f))
        c.number_format = "dd/mm/yyyy"
        c.fill = AMARILLO
        c = ws.cell(r, 2, round(p, 4))
        c.number_format = "#,##0.00"
        c.fill = AMARILLO
    # tabla de rendimientos
    enc = ["N", "Date", f"Precios Cierre {it['clave']} ({it['moneda']})", "Ra = ((Pf - Pi) / Pi) x 100\\nRendimiento del activo", "Rendimiento prom.\\nRprom", "Diferencia de rendimiento\\nRa - Rprom", "Diferencia del rendimiento al cuadrado"]
    for j, (t, a) in enumerate(zip(enc, [6, 12, 18, 20, 16, 20, 20]), 4):
        _enc(ws, 4, j, t.replace("\\n", "\n"), a)
    ws.row_dimensions[4].height = 48
    rng = f"$G${r0 + 1}:$G${ult}"
    for i in range(n):
        r = r0 + i
        ws.cell(r, 4, i + 1)
        ws.cell(r, 5, f"=A{r}").number_format = "dd/mm/yyyy"
        ws.cell(r, 6, f"=B{r}").number_format = "#,##0.00"
        if i:
            ws.cell(r, 7, f"=((F{r}/F{r - 1})-1)*100")
            ws.cell(r, 8, f"=AVERAGE({rng})")
            ws.cell(r, 9, f"=G{r}-H{r}")
            ws.cell(r, 10, f"=I{r}^2")
        for j in (7, 8, 9, 10):
            ws.cell(r, j).number_format = "0.0000"
        _borde(ws, r, 4, 10, i % 2 == 1)
        if 1 <= i <= 6:  # como en la clase, los primeros rendimientos resaltados
            ws.cell(r, 7).fill = AMARILLO
    # estadística descriptiva (columnas L:N) como en la clase
    for j, w in zip((12, 13, 14), (28, 16, 72)):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.column_dimensions["K"].width = 3
    _enc(ws, 4, 12, "Columna1")
    _enc(ws, 4, 13, "Ra")
    _enc(ws, 4, 14, "Cómo se calcula")
    est = [("Media", f"=AVERAGE({rng})", "Sumatoria del rendimiento del activo entre el número de días."),
           ("Error típico", f"=STDEV({rng})/SQRT(COUNT({rng}))", "Desviación estándar entre la raíz del número de datos."),
           ("Mediana", f"=MEDIAN({rng})", "Valor central de los rendimientos ordenados de menor a mayor."),
           ("Moda", f'=IFERROR(MODE({rng}),"No se repite")', "Valor que más se repite; si ninguno se repite no hay moda."),
           ("Desviación estándar", f"=STDEV({rng})", "En Excel: más funciones, estadísticas, desviación estándar (muestra)."),
           ("Varianza de la muestra", f"=VAR({rng})", "En Excel: más funciones, estadísticas, VAR (varianza de la muestra)."),
           ("Curtosis", f"=KURT({rng})", "En Excel: más funciones, estadísticas, CURTOSIS. Colas más pesadas que la normal si es mayor que 0."),
           ("Coeficiente de asimetría", f"=SKEW({rng})", "En Excel: más funciones, estadísticas, COEFICIENTE.ASIMETRIA. Positivo: más extremos al alza."),
           ("Rango", f"=MAX({rng})-MIN({rng})", "Es la diferencia entre el número menor y el mayor."),
           ("Mínimo", f"=MIN({rng})", "Peor rendimiento diario."), ("Máximo", f"=MAX({rng})", "Mejor rendimiento diario."),
           ("Suma", f"=SUM({rng})", "Suma de los rendimientos diarios."), ("DIAS TRABAJADOS", f"=COUNT({rng})", "Número de variaciones diarias del periodo.")]
    for k, (a, f, e) in enumerate(est):
        r = 5 + k
        ws.cell(r, 12, a).font = Font(bold=True)
        c = ws.cell(r, 13, f)
        c.number_format = "0" if a == "DIAS TRABAJADOS" else "0.0000"
        ws.cell(r, 14, e).font = Font(size=9.5, color="636569")
        _borde(ws, r, 12, 14)
    base = 5 + len(est) + 1
    _enc(ws, base, 12, "Rendimiento del periodo")
    _enc(ws, base, 13, "Valor")
    _enc(ws, base, 14, "Cómo se calcula")
    res = [("Precio inicial", f"=B{r0}", "Cierre del primer día del periodo.", "#,##0.00"), ("Precio final", f"=B{ult}", "Cierre del último día del periodo.", "#,##0.00"),
           ("Rendimiento efectivo (%)", f"=((B{ult}/B{r0})-1)*100", "((precio final / precio inicial) - 1) x 100.", "0.0000"),
           ("Rendimiento promedio Rprom (%)", f"=AVERAGE({rng})", "Promedio de los Ra diarios.", "0.0000"),
           ("Suma de diferencias al cuadrado", f"=SUM($J${r0 + 1}:$J${ult})", "Suma de (Ra - Rprom) al cuadrado; entre los días menos uno da la varianza.", "0.0000")]
    for k, (a, f, e, nf) in enumerate(res):
        r = base + 1 + k
        ws.cell(r, 12, a).font = Font(bold=True)
        ws.cell(r, 13, f).number_format = nf
        ws.cell(r, 14, e).font = Font(size=9.5, color="636569")
        _borde(ws, r, 12, 14)
    # rendimientos ordenados (como la columna de la clase)
    ws.column_dimensions["O"].width = 3
    _enc(ws, 4, 16, "N", 6)
    _enc(ws, 4, 17, "Rendimientos ordenados de menor a mayor", 22)
    for k in range(1, n):
        r = r0 + k - 1
        ws.cell(r, 16, k)
        ws.cell(r, 17, f"=SMALL({rng},P{r})").number_format = "0.0000"
        _borde(ws, r, 16, 17, k % 2 == 0)
    ws.column_dimensions["R"].width = 3
    # bloque contra el IPC (Date | Cierre IPC | Rendimiento IPC | Rendimiento emisora), con Cov, Var y Beta
    celdas = {"hoja": it["clave"], "r0": r0, "ult": ult, "efectivo": f"M{base + 3}", "promedio": f"M{base + 4}", "pi": f"M{base + 1}", "pf": f"M{base + 2}", "desv": "M9", "n": "M17"}
    if ipc is not None and it["clave"] != "IPC":
        a, b = _por_fecha(it), _por_fecha(ipc)
        com = [f for f in d["fechas"] if f in a and f in b]
        for j, (t, w) in enumerate(zip(["Date", "Cierre IPC", "Rendimiento IPC", f"Cierre {it['clave']}", f"Rendimiento {it['clave']}"], [12, 13, 15, 13, 15]), 19):
            _enc(ws, 4, j, t, w)
        ws.row_dimensions[4].height = 48
        u = r0 + len(com) - 1
        for i, f in enumerate(com):
            r = r0 + i
            ws.cell(r, 19, _f(f)).number_format = "dd/mm/yyyy"
            ws.cell(r, 20, round(b[f], 4)).number_format = "#,##0.00"
            ws.cell(r, 22, round(a[f], 4)).number_format = "#,##0.00"
            if i:
                ws.cell(r, 21, f"=((T{r}/T{r - 1})-1)*100").number_format = "0.0000"
                ws.cell(r, 23, f"=((V{r}/V{r - 1})-1)*100").number_format = "0.0000"
            _borde(ws, r, 19, 23, i % 2 == 1)
        ru, re_ = f"$U${r0 + 1}:$U${u}", f"$W${r0 + 1}:$W${u}"
        ws.column_dimensions["X"].width = 3
        ws.column_dimensions["Y"].width = 24
        ws.column_dimensions["Z"].width = 14
        for k, (et, f, nf) in enumerate([(f"Cov(IPC, {it['clave']})", f"=COVAR({ru},{re_})", "0.0000"), ("Var(IPC)", f"=VARP({ru})", "0.0000"), ("Beta", "=Z5/Z6", "0.0000"),
                                         ("Correlación", f"=CORREL({ru},{re_})", "0.0000")]):
            r = 5 + k
            ws.cell(r, 25, et).font = Font(bold=True)
            c = ws.cell(r, 26, f)
            c.number_format = nf
            ws.cell(r, 25).fill = ws.cell(r, 26).fill = AMARILLO
        _nota(ws, 10, "Beta = Cov(IPC, acción) / Var(IPC).", 25)
        _nota(ws, 11, f"Fechas en que operaron los dos: {len(com)}.", 25)
        celdas.update({"beta": "Z7", "corr": "Z8", "cov": "Z5", "var": "Z6"})
    ws.freeze_panes = "A5"
    return celdas


def _hoja_ancha(wb, d):
    ws = wb.create_sheet("Precios y variaciones")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    _tit(ws, 1, "Precios de cierre y variación diaria: 5 acciones y el IPC")
    _nota(ws, 2, "Fecha | precio de cierre | variación | siguiente instrumento... | precio de cierre del IPC | variación del IPC. Variación (%) = ((cierre de hoy / cierre anterior) - 1) x 100.")
    _enc(ws, 4, 1, "Fecha", 12)
    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    mapas = [_por_fecha(it) for it in items]
    prev = [None] * len(items)
    for k, it in enumerate(items):
        c0 = 2 + 2 * k
        nombre = it["clave"] if it["clave"] != "IPC" else "IPC (S&P/BMV)"
        _enc(ws, 4, c0, nombre)
        _enc(ws, 4, c0 + 1, nombre)
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
        _enc(ws, 5, c0, f"Precio de cierre ({it['moneda']})", 15)
        _enc(ws, 5, c0 + 1, "Variación (%)", 13)
    ws.row_dimensions[5].height = 44
    for i, f in enumerate(d["fechas"]):
        r = 6 + i
        ws.cell(r, 1, _f(f)).number_format = "dd/mm/yyyy"
        for k, (it, m) in enumerate(zip(items, mapas)):
            if f in m:
                c0 = 2 + 2 * k
                ws.cell(r, c0, round(m[f], 4)).number_format = "#,##0.00"
                if prev[k] is not None:
                    ws.cell(r, c0 + 1, (m[f] / prev[k] - 1) * 100).number_format = "0.00"
                prev[k] = m[f]
        _borde(ws, r, 1, 1 + 2 * len(items), i % 2 == 1)
    ws.freeze_panes = "B6"


def _hoja_resumen(wb, d, hojas):
    ws = wb.create_sheet("Resumen")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    ipc = next((x for x in items if x["clave"] == "IPC"), None)
    _tit(ws, 1, "Resumen: precio de cierre, rendimiento efectivo y rendimiento promedio")
    _nota(ws, 2, f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}. Las cifras se leen de las hojas de cada instrumento.")
    cols = ["Instrumento", "Moneda", "Precio inicial", "Precio final", "Máximo del periodo", "Mínimo del periodo", "Rendimiento efectivo (%)", "Rendimiento promedio diario Rprom (%)",
            "Desviación estándar diaria (%)", "Días trabajados", "Beta frente al IPC", "Diferencia contra el IPC (puntos)"]
    anchos = [50, 10, 14, 14, 14, 14, 16, 18, 16, 11, 12, 17]
    for j, (t, a) in enumerate(zip(cols, anchos), 1):
        _enc(ws, 4, j, t, a)
    ws.row_dimensions[4].height = 58
    for i, it in enumerate(items):
        r = 5 + i
        h = hojas[it["clave"]]
        q = f"'{h['hoja']}'!"
        ws.cell(r, 1, f"{it['clave']} · {it['nombre']}" if it["clave"] != "IPC" else it["nombre"])
        ws.cell(r, 2, it["moneda"])
        for j, ref in ((3, h["pi"]), (4, h["pf"]), (7, h["efectivo"]), (8, h["promedio"]), (9, h["desv"]), (10, h["n"])):
            ws.cell(r, j, f"={q}{ref}")
        if h.get("beta"):
            ws.cell(r, 11, f"={q}{h['beta']}")
        ws.cell(r, 5, round(it["pmax"], 4))
        ws.cell(r, 6, round(it["pmin"], 4))
        if ipc and it is not ipc:
            ws.cell(r, 12, f"=G{r}-$G${5 + len(items) - 1}")
        for j in (3, 4, 5, 6):
            ws.cell(r, j).number_format = "#,##0.00"
        for j in (7, 8, 9, 11, 12):
            ws.cell(r, j).number_format = "0.00"
        ws.cell(r, 10).number_format = "0"
        ws.cell(r, 1).hyperlink = f"#'{h['hoja']}'!A1"
        ws.cell(r, 1).font = Font(color=G, underline="single", bold=True)
        _borde(ws, r, 1, 12, i % 2 == 1)
    _nota(ws, 7 + len(items), "Diferencia contra el IPC: rendimiento efectivo de la acción menos el del IPC en el mismo periodo, en puntos porcentuales.")
    ws.freeze_panes = "B5"


def _hoja_graficas(wb, d):
    ws = wb.create_sheet("Gráficas")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    _tit(ws, 1, "Rendimientos para comparar")
    _nota(ws, 2, "Rendimiento acumulado (%) = ((precio de hoy / precio inicial) - 1) x 100. Los días sin operación arrastran el último cierre.")
    c0 = 30
    _enc(ws, 4, c0, "Fecha", 12)
    for k, it in enumerate(items):
        _enc(ws, 4, c0 + 1 + k, it["clave"], 11)
    acum = [_acumulado(d, it) for it in items]
    for i, f in enumerate(d["fechas"]):
        r = 5 + i
        ws.cell(r, c0, _f(f)).number_format = "dd/mm/yyyy"
        for k in range(len(items)):
            v = acum[k][i]
            if v is not None:
                ws.cell(r, c0 + 1 + k, round(v, 4)).number_format = "0.00"
    ult = 4 + len(d["fechas"])
    colores = ["1D63C1", "C8480F", "0A7F58", "A86D00", "C23B78"]
    ch = LineChart()
    ch.title, ch.height, ch.width = "Rendimiento acumulado de las 5 acciones frente al IPC (%)", 11, 26
    ch.y_axis.number_format = "0.00"
    ch.x_axis.number_format = "dd/mm"
    ch.x_axis.delete = ch.y_axis.delete = False
    ch.x_axis.tickLblSkip = max(1, len(d["fechas"]) // 10)
    ch.y_axis.title = "Rendimiento acumulado (%)"
    for k, it in enumerate(items):
        ch.add_data(Reference(ws, min_col=c0 + 1 + k, min_row=4, max_row=ult), titles_from_data=True)
        s = ch.series[-1]
        s.graphicalProperties.line.solidFill = "231F20" if it["clave"] == "IPC" else colores[k % 5]
        s.graphicalProperties.line.width = 28000 if it["clave"] == "IPC" else 18000
        if it["clave"] == "IPC":
            s.graphicalProperties.line.dashStyle = "dash"
        s.marker.symbol, s.smooth = "none", False
    ch.set_categories(Reference(ws, min_col=c0, min_row=5, max_row=ult))
    ws.add_chart(ch, "A4")
    ws.cell(4, c0 + 9, "Instrumento")
    ws.cell(4, c0 + 10, "Rendimiento efectivo (%)")
    ws.cell(4, c0 + 11, "Rendimiento promedio diario (%)")
    for k, it in enumerate(items):
        ws.cell(5 + k, c0 + 9, it["clave"])
        ws.cell(5 + k, c0 + 10, round(it["efectivo"], 4)).number_format = "0.00"
        ws.cell(5 + k, c0 + 11, round(it["stats"]["media"], 4)).number_format = "0.00"
    for col, titulo, ancla in ((c0 + 10, "Rendimiento efectivo del periodo (%)", "A28"), (c0 + 11, "Rendimiento promedio diario Rprom (%)", "A50")):
        b = BarChart()
        b.type, b.title, b.height, b.width, b.legend = "col", titulo, 10, 26, None
        b.y_axis.number_format = "0.00"
        b.x_axis.delete = b.y_axis.delete = False
        b.add_data(Reference(ws, min_col=col, min_row=4, max_row=4 + len(items)), titles_from_data=True)
        b.set_categories(Reference(ws, min_col=c0 + 9, min_row=5, max_row=4 + len(items)))
        b.series[0].graphicalProperties.solidFill = G
        ws.add_chart(b, ancla)


def _hoja_estadistica(wb, d):
    ws = wb.create_sheet("Estadística")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    _tit(ws, 1, "Estadística descriptiva de los rendimientos diarios (Ra, en %)")
    _nota(ws, 2, "Misma estadística de la hoja de cada acción, una columna por instrumento.")
    _enc(ws, 4, 1, "Medida", 26)
    for k, it in enumerate(items):
        _enc(ws, 4, 2 + k, it["clave"], 11)
    medidas = [("Media", "media"), ("Error típico", "error"), ("Mediana", "mediana"), ("Moda", "moda"), ("Desviación estándar", "desv"), ("Varianza de la muestra", "var"),
               ("Curtosis", "curtosis"), ("Coeficiente de asimetría", "asimetria"), ("Rango", "rango"), ("Mínimo", "min"), ("Máximo", "max"), ("Suma", "suma"), ("Días trabajados", "n")]
    for i, (et, k) in enumerate(medidas):
        r = 5 + i
        ws.cell(r, 1, et).font = Font(bold=True)
        for j, it in enumerate(items):
            v = it["stats"][k]
            c = ws.cell(r, 2 + j, "No se repite" if v is None and k == "moda" else v)
            c.number_format = "0" if k == "n" else "0.00"
            c.alignment = Alignment(horizontal="right")
        _borde(ws, r, 1, 1 + len(items), i % 2 == 1)
    r0 = 5 + len(medidas) + 2
    ws.cell(r0, 1, "Relación con el IPC (rendimientos diarios en las fechas en que operaron los dos)").font = Font(bold=True, size=12, color=G)
    for j, t in enumerate(["Acción", "Cov(IPC, acción)", "Var(IPC)", "Beta", "Correlación", "Días usados"], 1):
        _enc(ws, r0 + 1, j, t)
    ws.row_dimensions[r0 + 1].height = 32
    for i, it in enumerate([x for x in items if x["clave"] != "IPC"]):
        b = _beta_ipc(d, it)
        r = r0 + 2 + i
        ws.cell(r, 1, it["clave"]).font = Font(bold=True)
        if b:
            for j, v in enumerate([b["cov"], b["var"], b["beta"], b["corr"]], 2):
                ws.cell(r, j, v).number_format = "0.0000"
            ws.cell(r, 6, b["n"])
        _borde(ws, r, 1, 6)
    _nota(ws, r0 + 8, "Beta: cuánto se mueve la acción por cada 1 % que se mueve el IPC (Cov / Var). Correlación de -1 a +1.")
    ws.freeze_panes = "B5"


def _info_general(d, it):
    """Información general de una acción: sector, comportamiento real, razón y conclusión con cifras reales."""
    F = fichas.datos(it["ticker"]) or {}
    import glosario
    g = next((a for a in glosario.guia({it["ticker"]: it["nombre"]}, server.META, {})["acciones"] if a["ticker"] == it["ticker"]), {})
    fin = F.get("financieros")
    cif = {et: (a, b) for et, a, b, pa in fin["filas"]} if fin else {}
    crec = lambda k: ((cif[k][0] / cif[k][1] - 1) * 100) if k in cif and cif[k][1] else None
    vol = it["stats"]["desv"] * math.sqrt(252)
    nivel = "baja" if vol < 20 else "media" if vol < 35 else "alta"
    b = _beta_ipc(d, it)
    razon = []
    if fin and crec("Ingresos") is not None:
        razon.append(f"En su último ejercicio ({fin['periodos'][0]}) los ingresos cambiaron {crec('Ingresos'):+.2f} % y la utilidad neta {crec('Utilidad neta'):+.2f} %." if crec("Utilidad neta") is not None else
                     f"En su último ejercicio ({fin['periodos'][0]}) los ingresos cambiaron {crec('Ingresos'):+.2f} %.")
    razon.append(g.get("que_la_mueve", ""))
    concl = (f"{it['nombre']} {'subió' if it['efectivo'] > 0 else 'bajó'} {abs(it['efectivo']):.2f} % en el periodo, con volatilidad anual de {vol:.2f} % ({nivel})"
             + (f" y beta de {b['beta']:.2f} frente al IPC." if b else ".") + f" Su rendimiento promedio diario fue de {it['stats']['media']:+.2f} % con desviación estándar de {it['stats']['desv']:.2f} %.")
    return {"sector": SECTOR[it["ticker"]], "sic": F.get("sic"), "razon": " ".join(x for x in razon if x), "conclusion": concl, "F": F, "fin": fin, "cif": cif, "vol": vol, "nivel": nivel, "beta": b,
            "crec_ing": crec("Ingresos"), "crec_util": crec("Utilidad neta")}


def _hoja_general(wb, d):
    ws = wb.create_sheet("Información general")
    ws.sheet_view.showGridLines = False
    _tit(ws, 1, "Información general de las acciones")
    _nota(ws, 2, "Cifras reales: precios de Yahoo Finance (referencia) y datos de las empresas de la SEC (EDGAR). El sector es el que usó el equipo; entre paréntesis, la clasificación de la SEC.")
    cols = ["Acción", "Sector", "Moneda", "Precio actual", "Fecha del precio", "Cambio en los últimos 12 meses (%)", "Rendimiento efectivo del periodo (%)", "Máximo de 12 meses", "Mínimo de 12 meses",
            "Valor de mercado (millones de dólares)", "Último ejercicio", "Ingresos (millones)", "Utilidad neta (millones)", "Variación de ingresos (%)", "Variación de utilidad neta (%)",
            "Razón del comportamiento", "Conclusión", "Constitución", "Domicilio"]
    anchos = [28, 34, 9, 12, 13, 15, 15, 13, 13, 17, 22, 15, 15, 13, 13, 70, 70, 50, 40]
    for j, (t, a) in enumerate(zip(cols, anchos), 1):
        _enc(ws, 4, j, t, a)
    ws.row_dimensions[4].height = 62
    for i, it in enumerate([x for x in d["items"] if x["clave"] != "IPC"]):
        gi = _info_general(d, it)
        F, cif = gi["F"], gi["cif"]
        vals = [f"{it['clave']} · {it['nombre']}", f"{gi['sector']} ({gi['sic']})" if gi["sic"] else gi["sector"], it["moneda"], it["pf"], _f(it["ff"]), it.get("cambio_12m"), it["efectivo"], it.get("max52"), it.get("min52"),
                it["pf"] * F["acciones"] / 1e6 if F.get("acciones") else None, gi["fin"]["periodos"][0] if gi["fin"] else "No consta", cif.get("Ingresos", (None,))[0], cif.get("Utilidad neta", (None,))[0],
                gi["crec_ing"], gi["crec_util"], gi["razon"], gi["conclusion"], F.get("constitucion"), F.get("domicilio")]
        r = 5 + i
        for j, v in enumerate(vals, 1):
            c = ws.cell(r, j, v)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(v, (int, float)) else "left")
            if isinstance(v, float) or (isinstance(v, int) and j not in (3,)):
                c.number_format = "#,##0.00"
            if j == 5:
                c.number_format = "dd/mm/yyyy"
        _borde(ws, r, 1, len(cols), i % 2 == 1)
        ws.row_dimensions[r].height = 118
    ws.freeze_panes = "B5"
    _nota(ws, 11, "Cambio de 12 meses: último cierre contra el cierre de hace un año. Valor de mercado: precio por acciones en circulación (SEC). Cifras financieras en millones de dólares del último ejercicio fiscal presentado.")


def _hoja_deuda(wb, d):
    ws = wb.create_sheet("Deuda tasas")
    ws.sheet_view.showGridLines = False
    deu = d["deuda"]
    _tit(ws, 1, "Instrumentos de deuda: tasas semanales y variaciones")
    _nota(ws, 2, "La deuda no tiene precio de cierre diario: se muestra la tasa de cada subasta o colocación semanal (Banco de México). Variación en puntos base (pb); en papel comercial, cambio del monto en millones de pesos.")
    _enc(ws, 4, 1, "Fecha", 12)
    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    for k, x in enumerate(deu):
        c0 = 2 + 2 * k
        _enc(ws, 4, c0, x["corto"])
        _enc(ws, 4, c0 + 1, x["corto"])
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
        _enc(ws, 5, c0, "Monto colocado (millones de pesos)" if x["es_monto"] else ("Tasa real (%)" if "real" in x["unidad"] else "Tasa (%)"), 17)
        _enc(ws, 5, c0 + 1, "Variación del monto (mdp)" if x["es_monto"] else "Variación (pb)", 14)
    ws.row_dimensions[5].height = 44
    fechas = sorted({f for x in deu for f, _ in x["serie"]})
    mapas = [{f: (v, vr) for (f, v), vr in zip(x["serie"], x["var"])} for x in deu]
    for i, f in enumerate(fechas):
        r = 6 + i
        ws.cell(r, 1, _f(f)).number_format = "dd/mm/yyyy"
        for k, m in enumerate(mapas):
            if f in m:
                v, vr = m[f]
                ws.cell(r, 2 + 2 * k, round(v, 4)).number_format = "0.00"
                if vr is not None:
                    ws.cell(r, 3 + 2 * k, vr).number_format = "0.00"
        _borde(ws, r, 1, 1 + 2 * len(deu), i % 2 == 1)
    ult = 5 + len(fechas)
    r0 = ult + 2
    ws.cell(r0, 1, "Estadística").font = Font(bold=True, size=12, color=G)
    etq = [("Media", "AVERAGE({})"), ("Desviación estándar", "STDEV({})"), ("Mínimo", "MIN({})"), ("Máximo", "MAX({})"), ("Rango", "MAX({0})-MIN({0})"), ("Datos", "COUNT({})")]
    for i, (et, f) in enumerate(etq):
        r = r0 + 1 + i
        ws.cell(r, 1, et).font = Font(bold=True)
        for k in range(len(deu)):
            for col in (2 + 2 * k, 3 + 2 * k):
                L = get_column_letter(col)
                rng = f"{L}6:{L}{ult}"
                c = ws.cell(r, col, "=" + f.format(rng))
                c.number_format = "0" if et == "Datos" else "0.00"
        _borde(ws, r, 1, 1 + 2 * len(deu), i % 2 == 1)
    _nota(ws, r0 + 8, "Papel comercial: en el periodo no hubo colocaciones, por eso su monto es 0.00. Los certificados bursátiles son los de corto plazo.")
    ws.freeze_panes = "B6"
    # ficha de cada instrumento
    w2 = wb.create_sheet("Instrumentos de deuda")
    w2.sheet_view.showGridLines = False
    _tit(w2, 1, "Instrumentos de deuda: información general")
    _nota(w2, 2, "Riesgo y objetivo: material del equipo. Características: Banco de México (El mercado de valores gubernamentales en México). Tasas: cifras reales de las subastas del periodo.")
    cols = ["Instrumento", "Emisor", "Plazo", "Pago de intereses", "Valor nominal", "Tasa", "Riesgo", "Objetivo", "Última cifra", "Fecha", "Mínimo del periodo", "Máximo del periodo", "Promedio del periodo", "Primera emisión", "Respaldo", "Fuente"]
    anchos = [24, 30, 38, 44, 22, 52, 28, 38, 12, 12, 13, 13, 13, 40, 38, 50]
    for j, (t, a) in enumerate(zip(cols, anchos), 1):
        _enc(w2, 4, j, t, a)
    w2.row_dimensions[4].height = 40
    for i, x in enumerate(deu):
        F = fichas.DEUDA.get(x["nombre"], {})
        unidad = "millones de pesos" if x["es_monto"] else "%"
        vals = [x["corto"], F.get("emisor"), F.get("plazo"), F.get("intereses"), F.get("nominal"), F.get("tasa"), x["riesgo"], x["objetivo"], x["ult"], _f(x["fult"]), x["min"], x["max"], x["media"],
                F.get("primera"), F.get("garantia"), F["fuentes"][0][0] + " " + F["fuentes"][0][1] if F.get("fuentes") else ""]
        r = 5 + i
        for j, v in enumerate(vals, 1):
            c = w2.cell(r, j, v)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(v, (int, float)) else "left")
            if isinstance(v, float):
                c.number_format = "0.00"
            if j == 10:
                c.number_format = "dd/mm/yyyy"
        w2.cell(r, 9).number_format = "0.00"
        _borde(w2, r, 1, len(cols), i % 2 == 1)
        w2.row_dimensions[r].height = 120
    _nota(w2, 11, "Las cifras de tasa están en % anual (Udibonos, % real); en papel comercial son millones de pesos colocados por semana.")
    w2.freeze_panes = "B5"


def _hoja_conclusiones(wb, d):
    ws = wb.create_sheet("Conclusiones")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 120
    _tit(ws, 1, "Conclusiones")
    acc = [x for x in d["items"] if x["clave"] != "IPC"]
    ipc = next((x for x in d["items"] if x["clave"] == "IPC"), None)
    lineas = ["Acciones"]
    for it in acc:
        lineas.append("• " + _info_general(d, it)["conclusion"])
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    sup = [x["clave"] for x in acc if ipc and x["efectivo"] > ipc["efectivo"]]
    lineas.append(f"• Conclusión general: {mejor['clave']} fue la de mayor rendimiento efectivo ({mejor['efectivo']:+.2f} %) y {peor['clave']} la de menor ({peor['efectivo']:+.2f} %)."
                  + (f" El IPC rindió {ipc['efectivo']:+.2f} % y lo superaron {', '.join(sup) if sup else 'ninguna'}." if ipc else "") + " Cada acción se comportó distinto según su sector, su volatilidad y su relación con el IPC.")
    lineas.append("")
    lineas.append("Instrumentos de deuda")
    for x in d["deuda"]:
        u = "millones de pesos colocados" if x["es_monto"] else "%"
        if x["es_monto"]:
            lineas.append(f"• {x['corto']}: {x['ult']:,.2f} {u} en la última semana; en el periodo se colocaron {sum(v for _, v in x['serie']):,.2f} millones de pesos. Riesgo: {x['riesgo'].lower()}.")
        else:
            lineas.append(f"• {x['corto']}: última tasa {x['ult']:.2f} % ({R.fecha_corta(x['fult'])}), mínimo {x['min']:.2f} %, máximo {x['max']:.2f} % y promedio {x['media']:.2f} %. Riesgo: {x['riesgo'].lower()}.")
    lineas.append("• Conclusión general: CETES, Bonos y Udibonos son deuda del Gobierno Federal, de menor riesgo; el papel comercial y los certificados bursátiles los emiten empresas, y su riesgo depende de la solvencia del emisor.")
    for i, t in enumerate(lineas, 3):
        c = ws.cell(i, 1, t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if t in ("Acciones", "Instrumentos de deuda"):
            c.font = Font(bold=True, size=12, color=G)
        else:
            ws.row_dimensions[i].height = max(16, 15 * (len(t) // 115 + 1))


# ------------------------------------------------------------------------------- PDF
class _PDF(FPDF):
    total = 8

    def header(self):
        pass

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-10)
        self.set_font("Barlow", "", 8)
        self.set_text_color(*GRIS)
        self.set_x(14)
        self.cell(230, 5, "Instituto Politécnico Nacional · Escuela Superior de Economía · Seminario de Titulación 2026 · Herramienta educativa, no constituye asesoría financiera")
        self.cell(40, 5, f"{self.page_no()} de {self.total}", align="R")


def _nuevo():
    pdf = _PDF(orientation="L", format="A4")
    for est, arch in (("", "Barlow-Regular"), ("B", "Barlow-Bold"), ("I", "Barlow-Italic")):
        pdf.add_font("Barlow", est, str(R.FUENTES_TTF / f"{arch}.ttf"))
    pdf.add_font("BarlowC", "B", str(R.FUENTES_TTF / "BarlowSemiCondensed-Bold.ttf"))
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(False)
    return pdf


def _pagina(pdf, titulo, sub=None):
    pdf.add_page()
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, 297, 20, "F")
    pdf.image(str(R.MARCA / "ipn-escudo-blanco.png"), x=14, y=3, h=14)
    pdf.set_xy(32, 4)
    pdf.set_font("BarlowC", "B", 20)
    pdf.set_text_color(*BLANCO)
    pdf.cell(220, 8, titulo)
    if sub:
        pdf.set_xy(32, 12.2)
        pdf.set_font("Barlow", "", 9.5)
        pdf.cell(220, 5, sub)
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(274, 3, 14, 14, "F")
    pdf.image(str(R.MARCA / "ese-escudo.png"), x=275, y=4, w=12, h=12)
    pdf.set_y(26)


def _tabla(pdf, cols, filas, anchos, aligns=None, estilos=None, size=8.6, alto=5.6):
    aligns = aligns or ["LEFT"] + ["RIGHT"] * (len(cols) - 1)
    k = min(1.0, 268.0 / sum(anchos))
    anchos = tuple(a * k for a in anchos)
    pdf.set_fill_color(*BLANCO)
    pdf.set_text_color(*NEGRO)
    pdf.set_font("Barlow", "", size)
    with pdf.table(col_widths=anchos, text_align=aligns, line_height=alto, borders_layout="HORIZONTAL_LINES",
                   headings_style=R.FontFace(emphasis="BOLD", color=BLANCO, fill_color=GUINDA), cell_fill_color=GUINDA_SUAVE, cell_fill_mode="ROWS",
                   padding=(1.1, 1.6, 1.1, 1.6), width=sum(anchos)) as t:
        r = t.row()
        for c in cols:
            r.cell(c)
        for i, f in enumerate(filas):
            r = t.row()
            for j, v in enumerate(f):
                col = (estilos or {}).get((i, j))
                r.cell(str(v), style=R.FontFace(color=col) if col else None)


def _n(x, signo=False):
    return "s/d" if x is None else (f"{x:+,.2f}" if signo else f"{x:,.2f}")


def _color(x):
    return SUBE if x > 0 else BAJA if x < 0 else NEGRO


def _tarjetas(pdf, items, y):
    w = (297 - 28) / len(items)
    for i, (et, val, col) in enumerate(items):
        x = 14 + i * w
        pdf.set_fill_color(*GUINDA_SUAVE)
        pdf.rect(x + 1, y, w - 2, 24, "F")
        pdf.set_fill_color(*GUINDA)
        pdf.rect(x + 1, y, 1.4, 24, "F")
        pdf.set_xy(x + 5, y + 2.5)
        pdf.set_font("Barlow", "", 9)
        pdf.set_text_color(*GRIS)
        pdf.cell(w - 8, 4.5, et)
        pdf.set_xy(x + 5, y + 9)
        pdf.set_font("BarlowC", "B", 20)
        pdf.set_text_color(*(col or NEGRO))
        pdf.cell(w - 8, 11, val)


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


def _grafica_lineas(pdf, x0, y0, w, h, series, fechas, titulo, signo=True):
    """series: [(nombre, [valores o None], color, grosor, punteada)]"""
    pdf.set_xy(x0, y0)
    pdf.set_font("Barlow", "B", 10)
    pdf.set_text_color(*NEGRO)
    pdf.cell(w, 5, titulo)
    y0 += 7
    vals = [v for s in series for v in s[1] if v is not None]
    lo, hi = min(vals), max(vals)
    marcas = _ticks(lo, hi)
    lo, hi = marcas[0], marcas[-1]
    px0, pw, ph = x0 + 14, w - 16, h - 22
    py = lambda v: y0 + ph - (v - lo) / (hi - lo) * ph
    n = len(fechas)
    pdf.set_font("Barlow", "", 7.5)
    pdf.set_line_width(0.15)
    for v in marcas:
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.line(px0, py(v), px0 + pw, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(x0, py(v) - 1.8)
        pdf.cell(13, 3.6, f"{v:g} %", align="R")
    if lo < 0 < hi:
        pdf.set_draw_color(*GRIS)
        pdf.set_line_width(0.3)
        pdf.line(px0, py(0), px0 + pw, py(0))
    for nombre, vs, col, gr, punt in series:
        pdf.set_draw_color(*col)
        pdf.set_line_width(gr)
        prev = None
        for i, v in enumerate(vs):
            if v is None:
                prev = None
                continue
            xx = px0 + i / max(1, n - 1) * pw
            if prev is not None:
                if punt and i % 2:
                    prev = (xx, py(v))
                    continue
                pdf.line(prev[0], prev[1], xx, py(v))
            prev = (xx, py(v))
    pdf.set_line_width(0.2)
    pdf.set_text_color(*GRIS)
    for i in (0, n // 3, 2 * n // 3, n - 1):
        pdf.set_xy(min(max(px0 + i / max(1, n - 1) * pw - 10, x0), x0 + w - 20), y0 + ph + 1.5)
        pdf.cell(20, 3.6, R.fecha_corta(fechas[i]), align="C")
    # leyenda
    yl, xl = y0 + ph + 7, px0
    pdf.set_font("Barlow", "", 8)
    for nombre, vs, col, gr, punt in series:
        ult = next((v for v in reversed(vs) if v is not None), 0)
        txt = f"{nombre} {ult:+.2f} %" if signo else f"{nombre} {ult:.2f} %"
        ancho = pdf.get_string_width(txt) + 12
        if xl + ancho > x0 + w:
            xl, yl = px0, yl + 4.6
        pdf.set_fill_color(*col)
        pdf.rect(xl, yl + 1.3, 5, 1.6, "F")
        pdf.set_xy(xl + 6.5, yl)
        pdf.set_text_color(*NEGRO)
        pdf.cell(ancho - 6.5, 5, txt)
        xl += ancho


def _barras(pdf, x0, y0, w, h, nombres, valores, titulo, ipc_idx=None):
    pdf.set_xy(x0, y0)
    pdf.set_font("Barlow", "B", 10)
    pdf.set_text_color(*NEGRO)
    pdf.cell(w, 5, titulo)
    y0 += 8
    marcas = _ticks(min(0, min(valores)), max(0, max(valores)), 4)
    lo, hi = marcas[0], marcas[-1]
    ph = h - 20
    py = lambda v: y0 + (hi - v) / (hi - lo) * ph
    px0, pw = x0 + 14, w - 16
    pdf.set_draw_color(*GRIS_SUAVE)
    pdf.set_line_width(0.15)
    pdf.set_font("Barlow", "", 7.5)
    for v in marcas:
        pdf.line(px0, py(v), px0 + pw, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(x0, py(v) - 1.8)
        pdf.cell(13, 3.6, f"{v:g}", align="R")
    bw = pw / len(valores)
    for i, v in enumerate(valores):
        col = NEGRO if i == ipc_idx else GUINDA
        pdf.set_fill_color(*col)
        top, bot = (py(v), py(0)) if v >= 0 else (py(0), py(v))
        pdf.rect(px0 + i * bw + bw * 0.18, top, bw * 0.64, max(0.3, bot - top), "F")
        pdf.set_text_color(*GRIS)
        pdf.set_font("Barlow", "", 7)
        pdf.set_xy(px0 + i * bw - 2, py(lo) + 1.2)
        pdf.cell(bw + 4, 3.5, nombres[i], align="C")
        pdf.set_text_color(*NEGRO)
        pdf.set_xy(px0 + i * bw - 2, (top - 3.8) if v >= 0 else (bot + 0.4))
        pdf.cell(bw + 4, 3.5, f"{v:.2f}", align="C")
    pdf.set_line_width(0.2)


def presentacion(d):
    pdf = _nuevo()
    items = d["items"]
    ipc = next((x for x in items if x["clave"] == "IPC"), None)
    acc = [x for x in items if x["clave"] != "IPC"]
    deu = d["deuda"]
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    ganan = [x for x in acc if ipc and x["efectivo"] > ipc["efectivo"]]
    sub = f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}"
    gens = {x["clave"]: _info_general(d, x) for x in acc}
    # 1 portada
    pdf.add_page()
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.image(str(R.MARCA / "ipn-escudo-blanco.png"), x=20, y=22, h=62)
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(238, 24, 40, 40, "F")
    pdf.image(str(R.MARCA / "ese-escudo.png"), x=241, y=27, w=34, h=34)
    pdf.set_text_color(*BLANCO)
    pdf.set_xy(80, 30)
    pdf.set_font("Barlow", "B", 18)
    pdf.cell(150, 8, "INSTITUTO POLITÉCNICO NACIONAL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(80)
    pdf.set_font("Barlow", "B", 14)
    pdf.cell(150, 7, "ESCUELA SUPERIOR DE ECONOMÍA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(80)
    pdf.set_font("Barlow", "", 12)
    pdf.cell(150, 7, "Seminario de Titulación 2026")
    pdf.set_xy(20, 108)
    pdf.set_font("BarlowC", "B", 38)
    pdf.cell(250, 16, "Rendimiento de acciones, IPC y deuda", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font("Barlow", "", 16)
    pdf.cell(250, 9, "Precio de cierre, rendimiento efectivo, rendimiento promedio y su diferencia", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font("Barlow", "", 13)
    pdf.cell(250, 8, f"{sub} · Apple, Microsoft, NVIDIA, Tesla y Coca-Cola · S&P/BMV IPC · Cetes, Bonos, Udibonos, papel comercial y certificados bursátiles")
    pdf.set_xy(20, 188)
    pdf.set_font("Barlow", "", 10)
    pdf.cell(250, 5, f"Elaborado el {R.fecha_corta(d['generado'].date().isoformat())}. " + ("Análisis completo hasta el 25 de noviembre de 2026." if d["completo"] else "El análisis termina el 25 de noviembre de 2026; este corte llega al último cierre disponible."))

    # 2 resumen ejecutivo
    _pagina(pdf, "Resumen ejecutivo", sub)
    _tarjetas(pdf, [("Rendimiento efectivo del IPC", f"{_n(ipc['efectivo'], True)} %" if ipc else "s/d", _color(ipc["efectivo"]) if ipc else None),
                    (f"Mejor: {mejor['clave']}", f"{_n(mejor['efectivo'], True)} %", _color(mejor["efectivo"])), (f"Peor: {peor['clave']}", f"{_n(peor['efectivo'], True)} %", _color(peor["efectivo"])),
                    ("Acciones que superan al IPC", f"{len(ganan)} de {len(acc)}", None)], 28)
    pdf.set_xy(14, 58)
    pdf.set_font("Barlow", "", 11)
    pdf.set_text_color(*NEGRO)
    mas, menos = max(items, key=lambda x: x["stats"]["desv"]), min(items, key=lambda x: x["stats"]["desv"])
    tasas = [x for x in deu if not x["es_monto"]]
    lineas = [
        f"El periodo cubre {len(d['fechas'])} fechas de operación. {len([x for x in acc if x['efectivo'] > 0])} de las {len(acc)} acciones tuvieron rendimiento efectivo positivo en dólares.",
        (f"El IPC rindió {_n(ipc['efectivo'], True)} % de {_n(ipc['pi'])} a {_n(ipc['pf'])} puntos, con un rendimiento promedio diario de {_n(ipc['stats']['media'], True)} %." if ipc else ""),
        f"Mayor rendimiento efectivo: {mejor['nombre']} ({_n(mejor['efectivo'], True)} %). Menor: {peor['nombre']} ({_n(peor['efectivo'], True)} %). Más volátil: {mas['clave']} (desviación diaria {_n(mas['stats']['desv'])} %).",
        ("Deuda: " + "; ".join(f"{x['corto']} {x['ult']:.2f} %" for x in tasas) + " en su última subasta o colocación.") if tasas else "",
    ]
    for t in lineas:
        if t:
            pdf.set_x(14)
            pdf.multi_cell(265, 5.8, "•  " + t, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.8)
    _barras(pdf, 14, 108, 265, 90, [x["clave"] for x in items], [x["efectivo"] for x in items], "Rendimiento efectivo del periodo (%) · el IPC en negro", len(items) - 1 if ipc else None)

    # 3 información general de las acciones
    _pagina(pdf, "1. Información general de las acciones", sub)
    filas = []
    for x in acc:
        g = gens[x["clave"]]
        F, cif = g["F"], g["cif"]
        filas.append([f"{x['clave']} · {x['nombre']}", g["sector"], _n(x["pf"]), _n(x.get("cambio_12m"), True) + " %" if x.get("cambio_12m") is not None else "s/d",
                      f"{x['pf'] * F['acciones'] / 1e6:,.0f}" if F.get("acciones") else "s/d", f"{cif['Ingresos'][0]:,.0f}" if "Ingresos" in cif else "s/d",
                      f"{cif['Utilidad neta'][0]:,.0f}" if "Utilidad neta" in cif else "s/d", _n(g["crec_ing"], True) + " %" if g["crec_ing"] is not None else "s/d", _n(g["crec_util"], True) + " %" if g["crec_util"] is not None else "s/d"])
    est = {(i, 3): _color(float(f[3].split()[0].replace(",", ""))) for i, f in enumerate(filas) if f[3] != "s/d"}
    _tabla(pdf, ["Acción", "Sector", "Precio actual (USD)", "Cambio 12 meses", "Valor de mercado (millones USD)", "Ingresos (millones USD)", "Utilidad neta (millones USD)", "Ingresos vs. ejercicio previo", "Utilidad vs. ejercicio previo"],
           filas, (46, 44, 24, 24, 30, 26, 28, 25, 25), ["LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"], est, size=8.4, alto=5.4)
    pdf.set_y(pdf.get_y() + 4)
    pdf.set_font("Barlow", "B", 10)
    pdf.set_text_color(*GUINDA)
    pdf.set_x(14)
    pdf.cell(265, 5, "Razón del comportamiento", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 8.6)
    pdf.set_text_color(*NEGRO)
    for x in acc:
        pdf.set_x(14)
        pdf.multi_cell(265, 4.2, f"{x['clave']}: {gens[x['clave']]['razon']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)
    pdf.set_font("Barlow", "I", 8)
    pdf.set_text_color(*GRIS)
    pdf.set_x(14)
    pdf.multi_cell(265, 4, "Fuentes: precios de Yahoo Finance (referencia, no oficial); cifras de las empresas de los formularios 10-K de la SEC (EDGAR), del último ejercicio fiscal presentado.", new_x="LMARGIN", new_y="NEXT")

    # 4 precio de cierre, rendimiento efectivo y promedio
    _pagina(pdf, "2. Precio de cierre, rendimiento efectivo y promedio", sub)
    filas, est = [], {}
    for i, x in enumerate(items):
        dif = None if not ipc or x is ipc else x["efectivo"] - ipc["efectivo"]
        filas.append([x["clave"], x["moneda"], _n(x["pi"]), _n(x["pf"]), _n(x["pmax"]), _n(x["pmin"]), _n(x["efectivo"], True), _n(x["stats"]["media"], True), _n(x["stats"]["desv"]),
                      _n(dif, True) if dif is not None else "-"])
        est[(i, 6)] = _color(x["efectivo"])
        if dif is not None:
            est[(i, 9)] = _color(dif)
    _tabla(pdf, ["Instrumento", "Moneda", "Precio inicial", "Precio final", "Máximo", "Mínimo", "Rendimiento efectivo (%)", "Rendimiento promedio diario Rprom (%)", "Desviación estándar diaria (%)", "Diferencia con el IPC (puntos)"],
           filas, (30, 20, 25, 25, 25, 25, 28, 32, 30, 30), None, est, size=9, alto=6)
    pdf.set_xy(14, 100)
    pdf.set_font("Barlow", "B", 10)
    pdf.set_text_color(*GUINDA)
    pdf.cell(265, 5, "Diferencia de rendimiento (Ra - Rprom)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    filas2 = [[x["clave"], _n(x["stats"]["media"], True), _n(x["stats"]["max"], True), _n(x["stats"]["max"] - x["stats"]["media"], True), _n(x["stats"]["min"], True), _n(x["stats"]["min"] - x["stats"]["media"], True), _n(x["sumdif2"]),
               _n(x["sumdif2"] / (len(x["ra"]) - 1))] for x in items]
    _tabla(pdf, ["Instrumento", "Rprom (%)", "Mejor día Ra (%)", "Ra - Rprom del mejor día", "Peor día Ra (%)", "Ra - Rprom del peor día", "Suma de (Ra - Rprom) al cuadrado", "Varianza (suma / (días - 1))"],
           filas2, (30, 28, 30, 36, 30, 36, 44, 40), None, None, size=8.8, alto=5.4)
    pdf.set_xy(14, 168)
    pdf.set_font("Barlow", "I", 8.8)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(265, 4.5, "Ra = ((precio de hoy / precio del día anterior) - 1) x 100. Efectivo = ((precio final / precio inicial) - 1) x 100. Rprom = promedio de los Ra. Las acciones están en dólares y el IPC en pesos (puntos).")

    # 5 gráficas
    _pagina(pdf, "3. Rendimientos acumulados para comparar", sub)
    ac = {x["clave"]: _acumulado(d, x) for x in items}
    series = [(x["clave"], ac[x["clave"]], NEGRO if x["clave"] == "IPC" else COLORES[n % 5], 0.8 if x["clave"] == "IPC" else 0.55, x["clave"] == "IPC") for n, x in enumerate(items)]
    _grafica_lineas(pdf, 14, 26, 265, 92, series, d["fechas"], "Rendimiento acumulado de las 5 acciones y el IPC (%)")
    _barras(pdf, 14, 124, 134, 74, [x["clave"] for x in items], [x["efectivo"] for x in items], "Rendimiento efectivo del periodo (%)", len(items) - 1 if ipc else None)
    _barras(pdf, 150, 124, 134, 74, [x["clave"] for x in items], [x["stats"]["media"] for x in items], "Rendimiento promedio diario Rprom (%)", len(items) - 1 if ipc else None)

    # 6 estadística
    _pagina(pdf, "4. Estadística descriptiva y relación con el IPC", sub)
    filas = [[x["clave"], _n(x["stats"]["media"], True), _n(x["stats"]["error"]), _n(x["stats"]["mediana"], True), _n(x["stats"]["desv"]), _n(x["stats"]["var"]), _n(x["stats"]["asimetria"], True),
              _n(x["stats"]["curtosis"], True), _n(x["stats"]["rango"]), _n(x["stats"]["min"], True), _n(x["stats"]["max"], True), str(x["stats"]["n"])] for x in items]
    _tabla(pdf, ["Instrumento", "Media", "Error típico", "Mediana", "Desv. estándar", "Varianza", "Asimetría", "Curtosis", "Rango", "Mínimo", "Máximo", "Días trabajados"], filas,
           (30, 22, 22, 22, 24, 22, 22, 22, 22, 22, 22, 21), None, size=8.8, alto=6)
    pdf.set_xy(14, 98)
    pdf.set_font("Barlow", "B", 10)
    pdf.set_text_color(*GUINDA)
    pdf.cell(265, 5, "Beta frente al IPC (rendimientos diarios en las fechas en que operaron los dos)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    bs = [(x["clave"], _beta_ipc(d, x)) for x in acc]
    bs = [(k, b) for k, b in bs if b]
    if bs:
        _tabla(pdf, ["Medida"] + [k for k, _ in bs], [["Cov(IPC, acción)"] + [f"{b['cov']:.4f}" for _, b in bs], ["Var(IPC)"] + [f"{b['var']:.4f}" for _, b in bs],
                                                   ["Beta = Cov / Var"] + [f"{b['beta']:.4f}" for _, b in bs], ["Correlación"] + [f"{b['corr']:.2f}" for _, b in bs]],
               tuple([46] + [36] * len(bs)), None, size=9.2, alto=6)
    pdf.set_xy(14, 150)
    pdf.set_font("Barlow", "I", 8.8)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(265, 4.5, "Estadística calculada con las mismas definiciones de Excel (muestra). Beta: cuánto se mueve la acción por cada 1 % que se mueve el IPC. Una beta baja indica poca relación con el IPC en estas fechas; las acciones cotizan en dólares y el IPC en pesos.")

    # 7 deuda
    _pagina(pdf, "5. Instrumentos de deuda", sub)
    filas = []
    for x in deu:
        F = fichas.DEUDA.get(x["nombre"], {})
        u = " mdp" if x["es_monto"] else " %"
        filas.append([x["corto"], (F.get("emisor") or "").split(" (")[0], x["riesgo"], f"{x['ult']:.2f}{u}", f"{x['min']:.2f}{u}", f"{x['max']:.2f}{u}", f"{x['media']:.2f}{u}", R.fecha_corta(x["fult"])])
    _tabla(pdf, ["Instrumento", "Emisor", "Riesgo", "Última cifra", "Mínimo", "Máximo", "Promedio", "Fecha"], filas, (36, 50, 56, 26, 24, 24, 26, 23), ["LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"], size=8.6, alto=5.6)
    tfechas = sorted({f for x in tasas for f, _ in x["serie"]})
    if tasas and tfechas:
        sd = []
        for n, x in enumerate(tasas):
            m, ult, arr = dict(x["serie"]), None, []
            for f in tfechas:
                if f in m:
                    ult = m[f]
                arr.append(ult)
            sd.append((x["corto"], arr, COLORES[n % 5], 0.6, False))
        _grafica_lineas(pdf, 14, 98, 265, 96, sd, tfechas, "Tasas de las subastas y colocaciones semanales (%)", signo=False)
    # 8 conclusiones
    _pagina(pdf, "6. Conclusiones, método y fuentes", sub)
    pdf.set_xy(14, 28)
    pdf.set_font("Barlow", "B", 12)
    pdf.set_text_color(*GUINDA)
    pdf.cell(265, 6, "Conclusiones", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 9.6)
    pdf.set_text_color(*NEGRO)
    conc = [gens[x["clave"]]["conclusion"] for x in acc]
    conc.append(f"En conjunto, {mejor['clave']} fue la de mayor rendimiento efectivo y {peor['clave']} la de menor" + (f"; el IPC rindió {_n(ipc['efectivo'], True)} % y lo superaron {', '.join(x['clave'] for x in ganan) if ganan else 'ninguna'}." if ipc else "."))
    conc.append("Deuda: CETES, Bonos y Udibonos son deuda del Gobierno Federal, de menor riesgo; el papel comercial y los certificados bursátiles los emiten empresas y su riesgo depende de la solvencia del emisor.")
    for t in conc:
        pdf.set_x(14)
        pdf.multi_cell(265, 4.8, "•  " + t, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    pdf.ln(1)
    pdf.set_x(14)
    pdf.set_font("Barlow", "B", 12)
    pdf.set_text_color(*GUINDA)
    pdf.cell(265, 6, "Método y fuentes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 9.2)
    pdf.set_text_color(*NEGRO)
    met = [
        "Ra = ((precio de hoy / precio del día anterior) - 1) x 100. Efectivo = ((precio final / precio inicial) - 1) x 100. Rprom = media de los Ra. Diferencia = Ra - Rprom. Beta = Cov(IPC, acción) / Var(IPC).",
        "Precios de cierre: Yahoo Finance (referencia, no oficial). Cifras de las empresas: SEC EDGAR. Deuda: Banco de México (subastas y colocaciones semanales). Riesgo y objetivo de cada instrumento: material del equipo.",
        "El periodo inicia el 1 de marzo de 2026 y termina el 25 de noviembre de 2026." + ("" if d["completo"] else " Este corte llega al último cierre disponible; al volver a generar el archivo después del 25 de noviembre incluirá todo el periodo."),
        "Excel adjunto: una hoja por acción y por el IPC con las fórmulas de la clase, precios y variaciones por fecha, información general, gráficas, estadística, deuda y conclusiones.",
    ]
    for t in met:
        pdf.set_x(14)
        pdf.multi_cell(265, 4.6, "•  " + t, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)
    return bytes(pdf.output())
