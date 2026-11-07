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
def preparar(fin=None):
    """Series de cierre del periodo para las 10 acciones y el IPC, con sus rendimientos y estadística."""
    import contexto
    hoy = datetime.now(TZ).date()
    fin = min(fin or FIN_ANALISIS, FIN_ANALISIS, hoy)
    ini = server.INICIO
    hist = server._historiales()
    res, _ = contexto.series(fin)
    ipc = [(f, v) for f, v in res.get("ipc", []) if ini.isoformat() <= f <= fin.isoformat()]
    items = []
    for t in server.ACCIONES:
        rows = [(r["fecha"], r["cierre"]) for r in hist.get(t, []) if ini.isoformat() <= r["fecha"] <= fin.isoformat()]
        if len(rows) >= 3:
            items.append(_instrumento(t.replace(".MX", ""), server.ACCIONES[t], server.META[t]["moneda"], t, rows))
    if len(ipc) >= 3:
        items.append(_instrumento("IPC", NOMBRES["IPC"], "puntos", "IPC", ipc))
    if not items:
        raise ValueError("No hay precios en el periodo.")
    fechas = sorted({f for it in items for f, _ in it["serie"]})
    return {"inicio": ini.isoformat(), "fin": fin.isoformat(), "ultimo": max(f for it in items for f, _ in it["serie"]), "items": items, "fechas": fechas,
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
    return {"beta": cov / vb if vb else None, "corr": cov / math.sqrt(va * vb) if va and vb else None, "n": len(ra)}


# ------------------------------------------------------------------------------ Excel
def _tit(ws, fila, texto, ancho=8, size=14):
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


def libro(d):
    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True
    items = d["items"]
    sub = f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}"
    hojas = {}

    # ---- Léeme
    ws = wb.active
    ws.title = "Léeme"
    ws.sheet_view.showGridLines = False
    for r in (1, 2):
        for c in range(1, 9):
            ws.cell(r, c).fill = PatternFill("solid", fgColor=G)
    ws["A1"], ws["A2"] = "Rendimientos de las acciones y del IPC", sub
    ws["A1"].font, ws["A2"].font = Font(bold=True, size=16, color="FFFFFF"), Font(size=10.5, color="FFFFFF")
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 100
    ws.row_dimensions[1].height = 26
    filas = [
        ("Periodo", f"Del {R.fecha_corta(d['inicio'])} (inicio de la app) al {R.fecha_corta(d['ultimo'])}. " + ("El análisis ya cubre hasta el 25 de noviembre de 2026." if d["completo"] else
                  f"El análisis termina el 25 de noviembre de 2026; este archivo llega al último cierre disponible y se completa al volver a generarlo después de esa fecha.")),
        ("Instrumentos", "Las 10 acciones de la app (5 de la BMV y 5 de EE. UU.) y el IPC (S&P/BMV IPC). Cada una tiene su hoja con el formato del ejercicio de clase."),
        ("Precio de cierre", "Último precio de cada sesión, en la moneda de cada acción (pesos para las de la BMV, dólares para las de EE. UU.; el IPC, en puntos). Fuente: Yahoo Finance (referencia, no oficial)."),
        ("Rendimiento del activo (Ra)", "Variación diaria: ((precio de hoy / precio del día anterior) - 1) x 100. El primer día no tiene variación."),
        ("Rendimiento efectivo", "Rendimiento de todo el periodo: ((precio final / precio inicial) - 1) x 100."),
        ("Rendimiento promedio (Rprom)", "Promedio de los Ra diarios (suma de los rendimientos entre el número de días trabajados)."),
        ("Diferencia de rendimiento", "Ra - Rprom en cada día, y esa diferencia elevada al cuadrado; con ellas se obtiene la varianza."),
        ("Días trabajados", "Número de variaciones diarias del periodo (sesiones menos una)."),
        ("Hojas", "Precios y variaciones: todos los instrumentos por fecha, con su variación. Resumen: efectivo, promedio y diferencia contra el IPC. Gráficas: rendimientos acumulados y comparación. "
                  "Estadística: media, desviación, curtosis y demás medidas, y beta contra el IPC. Datos de las empresas: valor de mercado y cifras financieras reales. Una hoja por instrumento con las fórmulas."),
        ("Monedas", "Las acciones de EE. UU. están en dólares y el IPC en pesos (puntos): al compararlas, el rendimiento de las de EE. UU. no incluye el efecto del tipo de cambio sobre el peso."),
        ("Días sin operación", "Si una bolsa no operó un día (por ejemplo un festivo), ese instrumento queda en blanco esa fecha y su variación se calcula contra su cierre anterior disponible."),
        ("Cálculos", "Las hojas de cada instrumento usan fórmulas de Excel (promedio, desviación estándar, varianza, curtosis, asimetría), así que puedes revisarlas y cambiarlas."),
        ("Aviso", R.AVISO),
    ]
    for i, (a, b) in enumerate(filas, 4):
        ws.cell(i, 1, a).font = Font(bold=True)
        c = ws.cell(i, 2, b)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(i, 1).alignment = Alignment(vertical="top")
        ws.row_dimensions[i].height = max(18, 15 * (len(b) // 95 + 1))
        for j in (1, 2):
            ws.cell(i, j).border = Border(bottom=FILA)
            if i % 2:
                ws.cell(i, j).fill = PatternFill("solid", fgColor=GSUAVE)

    # ---- hojas por instrumento (formato de la clase, con fórmulas)
    for it in items:
        hojas[it["clave"]] = _hoja_instrumento(wb, it)

    # ---- precios y variaciones (todos juntos)
    _hoja_ancha(wb, d)
    # ---- resumen, gráficas, estadística, empresas
    _hoja_resumen(wb, d, hojas)
    _hoja_graficas(wb, d)
    _hoja_estadistica(wb, d)
    _hoja_empresas(wb, d)
    orden = ["Léeme", "Resumen", "Precios y variaciones", "Gráficas", "Estadística", "Datos de las empresas"] + [it["clave"] for it in items]
    wb._sheets = [wb[n] for n in orden]
    for w in wb.worksheets:
        w.page_setup.orientation, w.page_setup.fitToWidth, w.page_setup.fitToHeight = "landscape", 1, 0
        w.sheet_properties.pageSetUpPr = __import__("openpyxl").worksheet.properties.PageSetupProperties(fitToPage=True)
    return X._guardar(wb)


def _hoja_instrumento(wb, it):
    ws = wb.create_sheet(it["clave"])
    ws.sheet_view.showGridLines = False
    n = len(it["serie"])
    r0 = 5
    ultima = r0 + n - 1
    _tit(ws, 1, f"Rendimiento de precio de cierre: {it['nombre']}")
    ws["A2"] = "Ra = ((precio final - precio inicial) / precio inicial) x 100, con el precio del día anterior como precio inicial de cada día."
    ws["A2"].font = Font(italic=True, color="636569", size=10)
    enc = ["N", "Fecha", f"Precio de cierre ({it['moneda']})", "Rendimiento del activo Ra (%)", "Rendimiento promedio Rprom (%)", "Diferencia Ra - Rprom", "Diferencia al cuadrado"]
    anchos = [6, 13, 18, 19, 19, 17, 17]
    for j, (t, a) in enumerate(zip(enc, anchos), 1):
        _enc(ws, 4, j, t, a)
    ws.row_dimensions[4].height = 44
    for i, (f, p) in enumerate(it["serie"]):
        r = r0 + i
        ws.cell(r, 1, i + 1)
        c = ws.cell(r, 2, _f(f))
        c.number_format = "dd/mm/yyyy"
        c = ws.cell(r, 3, round(p, 4))
        c.number_format = "#,##0.00"
        if i:
            ws.cell(r, 4, f"=((C{r}/C{r - 1})-1)*100")
            ws.cell(r, 5, f"=AVERAGE($D${r0 + 1}:$D${ultima})")
            ws.cell(r, 6, f"=D{r}-E{r}")
            ws.cell(r, 7, f"=F{r}^2")
        for j in (4, 5, 6, 7):
            ws.cell(r, j).number_format = "0.00"
        for j in range(1, 8):
            ws.cell(r, j).border = Border(bottom=FILA)
            if i % 2:
                ws.cell(r, j).fill = PatternFill("solid", fgColor=GSUAVE)
    # estadística descriptiva, como en la clase
    rng = f"$D${r0 + 1}:$D${ultima}"
    for j, w in zip((9, 10, 11), (34, 16, 70)):
        ws.column_dimensions[get_column_letter(j)].width = w
    _enc(ws, 4, 9, "Estadística del rendimiento Ra")
    _enc(ws, 4, 10, "Valor")
    _enc(ws, 4, 11, "Cómo se calcula")
    stats = [("Media", f"=AVERAGE({rng})", "Suma de los rendimientos entre el número de días."),
             ("Error típico", f"=STDEV({rng})/SQRT(COUNT({rng}))", "Desviación estándar entre la raíz del número de datos."),
             ("Mediana", f"=MEDIAN({rng})", "Valor central de los rendimientos ordenados de menor a mayor."),
             ("Moda", f'=IFERROR(MODE({rng}),"No se repite")', "Valor que más se repite; si ninguno se repite no hay moda."),
             ("Desviación estándar", f"=STDEV({rng})", "Qué tanto se alejan los rendimientos de su media (muestra)."),
             ("Varianza de la muestra", f"=VAR({rng})", "Cuadrado de la desviación estándar: suma de las diferencias al cuadrado entre los días menos uno."),
             ("Curtosis", f"=KURT({rng})", "Qué tan pesadas son las colas frente a una distribución normal (0 es normal)."),
             ("Coeficiente de asimetría", f"=SKEW({rng})", "Positivo: más rendimientos extremos al alza; negativo: a la baja."),
             ("Rango", f"=MAX({rng})-MIN({rng})", "Diferencia entre el rendimiento mayor y el menor."),
             ("Mínimo", f"=MIN({rng})", "Peor rendimiento diario."), ("Máximo", f"=MAX({rng})", "Mejor rendimiento diario."),
             ("Suma", f"=SUM({rng})", "Suma de los rendimientos diarios."), ("Días trabajados", f"=COUNT({rng})", "Número de variaciones diarias del periodo.")]
    for k, (a, f, e) in enumerate(stats):
        r = 5 + k
        ws.cell(r, 9, a).font = Font(bold=True)
        c = ws.cell(r, 10, f)
        c.number_format = "0" if a == "Días trabajados" else "0.00"
        ws.cell(r, 11, e).font = Font(size=9.5, color="636569")
        for j in (9, 10, 11):
            ws.cell(r, j).border = Border(bottom=FILA)
    base = 5 + len(stats) + 1
    _enc(ws, base, 9, "Rendimiento del periodo")
    _enc(ws, base, 10, "Valor")
    _enc(ws, base, 11, "Cómo se calcula")
    res = [("Precio inicial", f"=C{r0}", "Cierre del primer día del periodo.", "#,##0.00"), ("Precio final", f"=C{ultima}", "Cierre del último día del periodo.", "#,##0.00"),
           ("Rendimiento efectivo (%)", f"=((C{ultima}/C{r0})-1)*100", "((precio final / precio inicial) - 1) x 100.", "0.00"),
           ("Rendimiento promedio diario Rprom (%)", f"=AVERAGE({rng})", "Promedio de los Ra diarios.", "0.00"),
           ("Suma de diferencias al cuadrado", f"=SUM($G${r0 + 1}:$G${ultima})", "Suma de (Ra - Rprom) al cuadrado; entre los días menos uno da la varianza.", "0.00")]
    for k, (a, f, e, nf) in enumerate(res):
        r = base + 1 + k
        ws.cell(r, 9, a).font = Font(bold=True)
        c = ws.cell(r, 10, f)
        c.number_format = nf
        ws.cell(r, 11, e).font = Font(size=9.5, color="636569")
        for j in (9, 10, 11):
            ws.cell(r, j).border = Border(bottom=FILA)
    ws.freeze_panes = "A5"
    return {"hoja": it["clave"], "r0": r0, "ultima": ultima, "efectivo": f"J{base + 3}", "promedio": f"J{base + 4}", "desv": "J9", "n": "J17", "pi": f"J{base + 1}", "pf": f"J{base + 2}"}


def _hoja_ancha(wb, d):
    ws = wb.create_sheet("Precios y variaciones")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    _tit(ws, 1, "Precios de cierre y variación diaria de todos los instrumentos")
    ws["A2"] = "Variación (%) = ((cierre de hoy / cierre anterior) - 1) x 100. Precios en la moneda de cada acción; el IPC, en puntos."
    ws["A2"].font = Font(italic=True, color="636569", size=10)
    _enc(ws, 4, 1, "Fecha", 12)
    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    mapas = [(_por_fecha(it)) for it in items]
    prev = [None] * len(items)
    for k, it in enumerate(items):
        c0 = 2 + 2 * k
        _enc(ws, 4, c0, it["clave"])
        _enc(ws, 4, c0 + 1, it["clave"])
        ws.merge_cells(start_row=4, start_column=c0, end_row=4, end_column=c0 + 1)
        _enc(ws, 5, c0, f"Precio de cierre ({it['moneda']})", 14)
        _enc(ws, 5, c0 + 1, "Variación (%)", 12)
    ws.row_dimensions[5].height = 44
    for i, f in enumerate(d["fechas"]):
        r = 6 + i
        c = ws.cell(r, 1, _f(f))
        c.number_format = "dd/mm/yyyy"
        for k, (it, m) in enumerate(zip(items, mapas)):
            if f in m:
                c0 = 2 + 2 * k
                ws.cell(r, c0, round(m[f], 4)).number_format = "#,##0.00"
                if prev[k] is not None:
                    ws.cell(r, c0 + 1, (m[f] / prev[k] - 1) * 100).number_format = "0.00"
                prev[k] = m[f]
        for j in range(1, 2 + 2 * len(items)):
            ws.cell(r, j).border = Border(bottom=FILA)
            if i % 2:
                ws.cell(r, j).fill = PatternFill("solid", fgColor=GSUAVE)
    ws.freeze_panes = "B6"


def _hoja_resumen(wb, d, hojas):
    ws = wb.create_sheet("Resumen")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    ipc = next((x for x in items if x["clave"] == "IPC"), None)
    _tit(ws, 1, "Resumen: precio de cierre, rendimiento efectivo y rendimiento promedio")
    ws["A2"] = f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}. Las cifras se leen de las hojas de cada instrumento."
    ws["A2"].font = Font(italic=True, color="636569", size=10)
    cols = ["Instrumento", "Moneda", "Precio inicial", "Precio final", "Máximo del periodo", "Mínimo del periodo", "Rendimiento efectivo (%)", "Rendimiento promedio diario Rprom (%)",
            "Desviación estándar diaria (%)", "Días trabajados", "Diferencia contra el IPC (puntos)"]
    anchos = [50, 10, 14, 14, 14, 14, 16, 18, 16, 11, 17]
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
        ws.cell(r, 5, round(it["pmax"], 4))
        ws.cell(r, 6, round(it["pmin"], 4))
        if ipc and it is not ipc:
            ws.cell(r, 11, f"=G{r}-$G${5 + len(items) - 1}")
        for j in (3, 4, 5, 6):
            ws.cell(r, j).number_format = "#,##0.00"
        for j in (7, 8, 9, 11):
            ws.cell(r, j).number_format = "0.00"
        ws.cell(r, 10).number_format = "0"
        ws.cell(r, 1).hyperlink = f"#'{h['hoja']}'!A1"
        ws.cell(r, 1).font = Font(color=G, underline="single", bold=True)
        for j in range(1, 12):
            ws.cell(r, j).border = Border(bottom=FILA)
            if i % 2:
                ws.cell(r, j).fill = PatternFill("solid", fgColor=GSUAVE)
    r = 7 + len(items)
    ws.cell(r, 1, "Diferencia contra el IPC: rendimiento efectivo de la acción menos el rendimiento efectivo del IPC en el mismo periodo, en puntos porcentuales.").font = Font(italic=True, color="636569", size=9.5)
    ws.freeze_panes = "B5"


def _hoja_graficas(wb, d):
    ws = wb.create_sheet("Gráficas")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    _tit(ws, 1, "Rendimientos para comparar")
    ws["A2"] = "Rendimiento acumulado (%) = ((precio de hoy / precio inicial) - 1) x 100. Los días sin operación arrastran el último cierre."
    ws["A2"].font = Font(italic=True, color="636569", size=10)
    # datos a la derecha (columna Z en adelante) para no estorbar las gráficas
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
    idx = {it["clave"]: k for k, it in enumerate(items)}
    colores = ["1D63C1", "C8480F", "0A7F58", "A86D00", "C23B78"]

    def lineas(titulo, claves, ancla):
        ch = LineChart()
        ch.title, ch.height, ch.width = titulo, 9, 24
        ch.y_axis.number_format = "0.00"
        ch.x_axis.number_format = "dd/mm"
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.tickLblSkip = max(1, len(d["fechas"]) // 10)
        ch.y_axis.title = "Rendimiento acumulado (%)"
        for n, k in enumerate(claves):
            col = c0 + 1 + idx[k]
            ch.add_data(Reference(ws, min_col=col, min_row=4, max_row=ult), titles_from_data=True)
            s = ch.series[-1]
            s.graphicalProperties.line.solidFill = "231F20" if k == "IPC" else colores[n % 5]
            s.graphicalProperties.line.width = 28000 if k == "IPC" else 17000
            if k == "IPC":
                s.graphicalProperties.line.dashStyle = "dash"
            s.marker.symbol, s.smooth = "none", False
        ch.set_categories(Reference(ws, min_col=c0, min_row=5, max_row=ult))
        ws.add_chart(ch, ancla)

    mx = [it["clave"] for it in items if it["moneda"] == "MXN"] + ["IPC"]
    us = [it["clave"] for it in items if it["moneda"] == "USD"] + ["IPC"]
    lineas("Rendimiento acumulado: acciones de la BMV frente al IPC", [k for k in mx if k in idx], "A4")
    lineas("Rendimiento acumulado: acciones de EE. UU. frente al IPC", [k for k in us if k in idx], "A24")
    # barras con efectivo y promedio
    ws.cell(4, c0 + 15, "Instrumento")
    ws.cell(4, c0 + 16, "Rendimiento efectivo (%)")
    ws.cell(4, c0 + 17, "Rendimiento promedio diario (%)")
    for k, it in enumerate(items):
        ws.cell(5 + k, c0 + 15, it["clave"])
        ws.cell(5 + k, c0 + 16, round(it["efectivo"], 4)).number_format = "0.00"
        ws.cell(5 + k, c0 + 17, round(it["stats"]["media"], 4)).number_format = "0.00"
    for n, (col, titulo, ancla) in enumerate(((c0 + 16, "Rendimiento efectivo del periodo (%)", "A44"), (c0 + 17, "Rendimiento promedio diario Rprom (%)", "A64"))):
        b = BarChart()
        b.type, b.title, b.height, b.width, b.legend = "col", titulo, 9, 24, None
        b.y_axis.number_format = "0.00"
        b.x_axis.delete = b.y_axis.delete = False
        b.add_data(Reference(ws, min_col=col, min_row=4, max_row=4 + len(items)), titles_from_data=True)
        b.set_categories(Reference(ws, min_col=c0 + 15, min_row=5, max_row=4 + len(items)))
        b.series[0].graphicalProperties.solidFill = G
        ws.add_chart(b, ancla)


def _hoja_estadistica(wb, d):
    ws = wb.create_sheet("Estadística")
    ws.sheet_view.showGridLines = False
    items = d["items"]
    _tit(ws, 1, "Estadística descriptiva de los rendimientos diarios (Ra, en %)")
    ws["A2"] = "Misma estadística de la hoja de cada instrumento, una columna por instrumento."
    ws["A2"].font = Font(italic=True, color="636569", size=10)
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
        for j in range(1, 2 + len(items)):
            ws.cell(r, j).border = Border(bottom=FILA)
            if i % 2:
                ws.cell(r, j).fill = PatternFill("solid", fgColor=GSUAVE)
    r0 = 5 + len(medidas) + 2
    ws.cell(r0, 1, "Relación con el IPC (rendimientos diarios en las fechas en que operaron los dos)").font = Font(bold=True, size=12, color=G)
    for j, t in enumerate(["Instrumento", "Beta frente al IPC", "Correlación con el IPC", "Días usados"], 1):
        _enc(ws, r0 + 1, j, t)
    ws.row_dimensions[r0 + 1].height = 32
    for i, it in enumerate([x for x in items if x["clave"] != "IPC"]):
        b = _beta_ipc(d, it)
        r = r0 + 2 + i
        ws.cell(r, 1, it["clave"]).font = Font(bold=True)
        if b:
            ws.cell(r, 2, b["beta"]).number_format = "0.00"
            ws.cell(r, 3, b["corr"]).number_format = "0.00"
            ws.cell(r, 4, b["n"])
        for j in range(1, 5):
            ws.cell(r, j).border = Border(bottom=FILA)
    ws.cell(r0 + 14, 1, "Beta: cuánto se mueve la acción por cada 1 % que se mueve el IPC. Correlación de -1 a +1.").font = Font(italic=True, color="636569", size=9.5)
    ws.freeze_panes = "B5"


def _hoja_empresas(wb, d):
    ws = wb.create_sheet("Datos de las empresas")
    ws.sheet_view.showGridLines = False
    _tit(ws, 1, "Datos reales de las empresas")
    ws["A2"] = "Fuente: reportes a la SEC (EDGAR) y reportes anuales de Walmart de México y Kimberly-Clark de México. Valor de mercado = precio final por acciones en circulación."
    ws["A2"].font = Font(italic=True, color="636569", size=10)
    cols = ["Emisora", "Denominación", "Moneda", "Precio final", "Acciones en circulación", "Fecha del dato de acciones", "Valor de mercado (millones)", "Último ejercicio", "Ingresos (millones)",
            "Utilidad neta (millones)", "Activos totales (millones)", "Capital contable (millones)", "Utilidad por acción", "Constitución", "Domicilio"]
    anchos = [11, 40, 9, 12, 20, 22, 18, 22, 16, 16, 16, 16, 12, 60, 60]
    for j, (t, a) in enumerate(zip(cols, anchos), 1):
        _enc(ws, 4, j, t, a)
    ws.row_dimensions[4].height = 44
    fila = 5
    for it in d["items"]:
        if it["clave"] == "IPC":
            continue
        F = fichas.datos(it["ticker"])
        if not F:
            continue
        fin = F.get("financieros")
        cif = {et: (a, b) for et, a, b, pa in fin["filas"]} if fin else {}
        vals = [it["clave"], F["denominacion"], it["moneda"], it["pf"], F["acciones"], F["acciones_fecha"],
                it["pf"] * F["acciones"] / 1e6 if F.get("capitalizacion", True) else "No aplica (unidad con varias series)", fin["periodos"][0] if fin else "No consta",
                cif.get("Ingresos", (None,))[0], cif.get("Utilidad neta", (None,))[0], cif.get("Activos totales", (None,))[0], cif.get("Capital contable", (None,))[0],
                cif.get("Utilidad por acción", (None,))[0], F["constitucion"], F["domicilio"]]
        for j, v in enumerate(vals, 1):
            c = ws.cell(fila, j, v)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="right" if isinstance(v, (int, float)) else "left")
            if isinstance(v, float) or (isinstance(v, int) and j != 5):
                c.number_format = "#,##0.00"
            if j == 5:
                c.number_format = "#,##0"
            c.border = Border(bottom=FILA)
            if fila % 2:
                c.fill = PatternFill("solid", fgColor=GSUAVE)
        ws.row_dimensions[fila].height = 48
        fila += 1
    ws.cell(fila + 1, 1, "Las cifras financieras están en millones de la moneda de cada empresa (pesos o dólares) y salvo la utilidad por acción. El detalle completo de cada empresa está en el informe de mercados.").font = Font(italic=True, color="636569", size=9.5)
    ws.freeze_panes = "C5"


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


def _grafica_lineas(pdf, x0, y0, w, h, series, fechas, titulo):
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
        txt = f"{nombre} {ult:+.2f} %"
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
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    ganan = [x for x in acc if ipc and x["efectivo"] > ipc["efectivo"]]
    sub = f"Del {R.fecha_corta(d['inicio'])} al {R.fecha_corta(d['ultimo'])}"
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
    pdf.set_xy(20, 112)
    pdf.set_font("BarlowC", "B", 40)
    pdf.cell(250, 16, "Rendimiento de acciones y del IPC", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font("Barlow", "", 16)
    pdf.cell(250, 9, "Precio de cierre, rendimiento efectivo, rendimiento promedio y su diferencia", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font("Barlow", "", 13)
    pdf.cell(250, 8, f"{sub} · 10 acciones de la BMV, Nasdaq y NYSE, y el S&P/BMV IPC")
    pdf.set_xy(20, 188)
    pdf.set_font("Barlow", "", 10)
    pdf.cell(250, 5, f"Elaborado el {R.fecha_corta(d['generado'].date().isoformat())}. " + ("Análisis completo hasta el 25 de noviembre de 2026." if d["completo"] else "El análisis termina el 25 de noviembre de 2026; este corte llega al último cierre disponible."))

    # 2 resumen ejecutivo
    _pagina(pdf, "Resumen ejecutivo", sub)
    _tarjetas(pdf, [("Rendimiento efectivo del IPC", f"{_n(ipc['efectivo'], True)} %" if ipc else "s/d", _color(ipc["efectivo"]) if ipc else None),
                    (f"Mejor: {mejor['clave']}", f"{_n(mejor['efectivo'], True)} %", _color(mejor["efectivo"])), (f"Peor: {peor['clave']}", f"{_n(peor['efectivo'], True)} %", _color(peor["efectivo"])),
                    ("Acciones que superan al IPC", f"{len(ganan)} de {len(acc)}", None)], 28)
    pdf.set_xy(14, 60)
    pdf.set_font("Barlow", "", 11.5)
    pdf.set_text_color(*NEGRO)
    pos = [x for x in acc if x["efectivo"] > 0]
    mas_volatil = max(items, key=lambda x: x["stats"]["desv"])
    menos = min(items, key=lambda x: x["stats"]["desv"])
    lineas = [
        f"El periodo cubre {len(d['fechas'])} fechas de operación. {len(pos)} de las {len(acc)} acciones tuvieron rendimiento efectivo positivo en su moneda.",
        (f"El IPC rindió {_n(ipc['efectivo'], True)} % de {_n(ipc['pi'])} a {_n(ipc['pf'])} puntos, con un rendimiento promedio diario de {_n(ipc['stats']['media'], True)} %." if ipc else ""),
        f"La acción con mayor rendimiento efectivo fue {mejor['nombre']} ({_n(mejor['efectivo'], True)} %) y la de menor, {peor['nombre']} ({_n(peor['efectivo'], True)} %).",
        f"La más volátil fue {mas_volatil['clave']}, con desviación estándar diaria de {_n(mas_volatil['stats']['desv'])} %; la menos volátil, {menos['clave']} ({_n(menos['stats']['desv'])} %).",
        "El rendimiento efectivo mide todo el periodo; el promedio diario (Rprom) es la media de las variaciones día a día, y la diferencia Ra - Rprom muestra cuánto se aleja cada día de ese promedio.",
    ]
    for t in lineas:
        if t:
            pdf.set_x(14)
            pdf.multi_cell(265, 6.2, "•  " + t, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2.2)
    _barras(pdf, 14, 118, 265, 78, [x["clave"] for x in items], [x["efectivo"] for x in items], "Rendimiento efectivo del periodo (%) · el IPC en negro", len(items) - 1 if ipc else None)
    # 3 precios de cierre
    _pagina(pdf, "1. Precio de cierre", sub)
    filas = [[x["clave"] if x["clave"] == "IPC" else f"{x['clave']} · {x['nombre']}", x["moneda"], _n(x["pi"]), R.fecha_corta(x["fi"]), _n(x["pf"]), R.fecha_corta(x["ff"]), _n(x["pmax"]), _n(x["pmin"])] for x in items]
    _tabla(pdf, ["Instrumento", "Moneda", "Precio inicial", "Fecha inicial", "Precio final", "Fecha final", "Máximo", "Mínimo"], filas, (88, 20, 28, 26, 28, 26, 25, 24), None, size=9, alto=6.2)
    pdf.set_xy(14, 150)
    pdf.set_font("Barlow", "I", 9)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(265, 4.6, "Precios de cierre en la moneda de cada acción: pesos (BMV) y dólares (Nasdaq y NYSE); el IPC, en puntos. Fuente: Yahoo Finance (referencia, no oficial).")
    # 4 rendimientos
    _pagina(pdf, "2. Rendimiento efectivo, promedio y diferencia", sub)
    filas, est = [], {}
    for i, x in enumerate(items):
        dif = None if not ipc or x is ipc else x["efectivo"] - ipc["efectivo"]
        filas.append([x["clave"], _n(x["efectivo"], True), _n(x["stats"]["media"], True), _n(x["stats"]["max"], True), _n(x["stats"]["min"], True), _n(x["stats"]["desv"]), _n(x["sumdif2"]),
                      _n(dif, True) if dif is not None else "-"])
        est[(i, 1)] = _color(x["efectivo"])
        if dif is not None:
            est[(i, 7)] = _color(dif)
    _tabla(pdf, ["Instrumento", "Efectivo del periodo (%)", "Promedio diario Rprom (%)", "Mejor día Ra (%)", "Peor día Ra (%)", "Desv. estándar diaria", "Suma de (Ra - Rprom) al cuadrado", "Diferencia con el IPC (puntos)"],
           filas, (30, 33, 33, 28, 28, 28, 42, 36), None, est, size=9, alto=5.8)
    pdf.set_xy(14, 130)
    pdf.set_font("Barlow", "I", 8.8)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(265, 4.5, "Ra = ((precio de hoy / precio del día anterior) - 1) x 100. Efectivo = ((precio final / precio inicial) - 1) x 100. Rprom = promedio de los Ra. "
                              "La diferencia Ra - Rprom de cada día y su cuadrado están en la hoja de cada instrumento del Excel; la suma de los cuadrados entre los días menos uno es la varianza.")
    # 5 gráficas acumuladas
    _pagina(pdf, "3. Rendimientos acumulados para comparar", sub)
    idx = {x["clave"]: x for x in items}
    ac = {x["clave"]: _acumulado(d, x) for x in items}

    def serie(claves):
        out = []
        for n, k in enumerate(claves):
            if k in idx:
                out.append((k, ac[k], NEGRO if k == "IPC" else COLORES[n % 5], 0.75 if k == "IPC" else 0.5, k == "IPC"))
        return out
    mx = [x["clave"] for x in acc if x["moneda"] == "MXN"] + ["IPC"]
    us = [x["clave"] for x in acc if x["moneda"] == "USD"] + ["IPC"]
    _grafica_lineas(pdf, 14, 26, 134, 100, serie(mx), d["fechas"], "Acciones de la BMV y el IPC (rendimiento acumulado, %)")
    _grafica_lineas(pdf, 150, 26, 134, 100, serie(us), d["fechas"], "Acciones de EE. UU. y el IPC (rendimiento acumulado, %)")
    _barras(pdf, 14, 130, 134, 66, [x["clave"] for x in items], [x["efectivo"] for x in items], "Rendimiento efectivo del periodo (%)", len(items) - 1 if ipc else None)
    _barras(pdf, 150, 130, 134, 66, [x["clave"] for x in items], [x["stats"]["media"] for x in items], "Rendimiento promedio diario Rprom (%)", len(items) - 1 if ipc else None)
    # 6 estadística
    _pagina(pdf, "4. Estadística descriptiva del rendimiento diario", sub)
    filas = [[x["clave"], _n(x["stats"]["media"], True), _n(x["stats"]["error"]), _n(x["stats"]["mediana"], True), _n(x["stats"]["desv"]), _n(x["stats"]["var"]), _n(x["stats"]["asimetria"], True),
              _n(x["stats"]["curtosis"], True), _n(x["stats"]["rango"]), _n(x["stats"]["min"], True), _n(x["stats"]["max"], True), str(x["stats"]["n"])] for x in items]
    _tabla(pdf, ["Instrumento", "Media", "Error típico", "Mediana", "Desv. estándar", "Varianza", "Asimetría", "Curtosis", "Rango", "Mínimo", "Máximo", "Días trabajados"], filas,
           (30, 22, 22, 22, 24, 22, 22, 22, 22, 22, 22, 21), None, size=8.8, alto=5.8)
    pdf.set_xy(14, 138)
    betas = [(x["clave"], _beta_ipc(d, x)) for x in acc]
    betas = [(k, b) for k, b in betas if b]
    if betas:
        pdf.set_font("Barlow", "B", 10)
        pdf.set_text_color(*NEGRO)
        pdf.cell(265, 5, "Relación con el IPC (rendimientos diarios)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        _tabla(pdf, ["Instrumento"] + [k for k, _ in betas], [["Beta"] + [_n(b["beta"]) for _, b in betas], ["Correlación"] + [_n(b["corr"]) for _, b in betas]],
               tuple([30] + [23.5] * len(betas)), None, size=8.8, alto=5.6)
    # 7 empresas
    _pagina(pdf, "5. Datos reales de las empresas", sub)
    filas = []
    for x in acc:
        F = fichas.datos(x["ticker"])
        if not F:
            continue
        fin = F.get("financieros")
        cif = {et: (a, b) for et, a, b, pa in fin["filas"]} if fin else {}
        vm = f"{x['pf'] * F['acciones'] / 1e6:,.0f}" if F.get("capitalizacion", True) else "n/a"
        filas.append([x["clave"], x["moneda"], f"{F['acciones'] / 1e6:,.0f}", vm, fin["periodos"][0] if fin else "s/d",
                      f"{cif['Ingresos'][0]:,.0f}" if "Ingresos" in cif else "s/d", f"{cif['Utilidad neta'][0]:,.0f}" if "Utilidad neta" in cif else "s/d",
                      f"{cif['Activos totales'][0]:,.0f}" if "Activos totales" in cif else "s/d", f"{cif['Capital contable'][0]:,.0f}" if "Capital contable" in cif else "s/d"])
    _tabla(pdf, ["Emisora", "Moneda", "Acciones en circulación (millones)", "Valor de mercado (millones)", "Último ejercicio", "Ingresos (millones)", "Utilidad neta (millones)", "Activos (millones)", "Capital contable (millones)"],
           filas, (24, 17, 34, 32, 44, 26, 26, 26, 36), None, size=8.4, alto=5.4)
    pdf.set_xy(14, 150)
    pdf.set_font("Barlow", "I", 8.6)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(265, 4.4, "Cifras en millones de la moneda de cada empresa. Fuentes: formularios 10-K y 20-F de la SEC (EDGAR) y reportes anuales de Walmart de México y Kimberly-Clark de México. "
                              "Valor de mercado = precio final por acciones en circulación (no se calcula para KOFUBL ni KIMBERA porque cotizan una sola de sus series). El detalle por empresa está en el informe de mercados.")
    # 8 conclusiones y método
    _pagina(pdf, "6. Conclusiones, método y fuentes", sub)
    pdf.set_xy(14, 28)
    pdf.set_font("Barlow", "B", 12)
    pdf.set_text_color(*GUINDA)
    pdf.cell(265, 6, "Conclusiones", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 10.5)
    pdf.set_text_color(*NEGRO)
    conc = [
        (f"De las {len(acc)} acciones, {len(ganan)} superaron al IPC en rendimiento efectivo ({', '.join(x['clave'] for x in ganan) if ganan else 'ninguna'})." if ipc else ""),
        f"{mejor['clave']} fue la de mayor rendimiento efectivo ({_n(mejor['efectivo'], True)} %) y {peor['clave']} la de menor ({_n(peor['efectivo'], True)} %).",
        f"Mayor dispersión diaria: {mas_volatil['clave']} ({_n(mas_volatil['stats']['desv'])} %). Menor: {menos['clave']} ({_n(menos['stats']['desv'])} %).",
        "Un promedio diario cercano a cero con una desviación alta indica que los precios suben y bajan mucho sin avanzar; por eso conviene mirar juntos el efectivo, el promedio y la dispersión.",
        "Las acciones de EE. UU. se miden en dólares y el IPC en pesos, así que esa comparación incluye el efecto del tipo de cambio.",
    ]
    for t in conc:
        if t:
            pdf.set_x(14)
            pdf.multi_cell(265, 5.6, "•  " + t, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.4)
    pdf.ln(2)
    pdf.set_x(14)
    pdf.set_font("Barlow", "B", 12)
    pdf.set_text_color(*GUINDA)
    pdf.cell(265, 6, "Método y fuentes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Barlow", "", 9.8)
    pdf.set_text_color(*NEGRO)
    met = [
        "Rendimiento del activo Ra = ((precio de hoy / precio del día anterior) - 1) x 100. Rendimiento efectivo = ((precio final / precio inicial) - 1) x 100. Rendimiento promedio Rprom = media de los Ra. Diferencia = Ra - Rprom.",
        "Estadística calculada con las mismas definiciones de Excel (desviación estándar y varianza de la muestra, curtosis y asimetría muestrales). Días trabajados = número de variaciones diarias.",
        "Precios de cierre: Yahoo Finance (referencia, no oficial). IPC: S&P/BMV IPC. Cifras de las empresas: SEC EDGAR y reportes anuales. Los días en que una bolsa no operó se dejan en blanco en el Excel.",
        "El periodo inicia el 1 de marzo de 2026 y termina el 25 de noviembre de 2026." + ("" if d["completo"] else " Este corte llega al último cierre disponible; al volver a generar el archivo después del 25 de noviembre incluirá todo el periodo."),
        "Archivo de Excel adjunto: una hoja por instrumento con las fórmulas, todos los precios y variaciones por fecha, gráficas, estadística y datos de las empresas.",
    ]
    for t in met:
        pdf.set_x(14)
        pdf.multi_cell(265, 5, "•  " + t, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.2)
    return bytes(pdf.output())
