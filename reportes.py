"""Reportes en formato IPN (guinda #750946, negro #231F20, gris #636569, blanco): PDF, Excel y Markdown.

Por día  (pdf_dia, xlsx_dia, md_dia): decisión de cada instrumento, por qué, qué hacer y qué pasó después, con el entorno del día.
Por periodo (pdf_periodo, xlsx_periodo): todo el periodo consultado, que siempre arranca el 1 de marzo de 2026 o después.
"""
import io
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF
from fpdf.fonts import FontFace
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import glosario

RAIZ = Path(__file__).parent
FUENTES_TTF = RAIZ / "fonts"
MARCA = RAIZ / "recursos"
TZ = ZoneInfo("America/Mexico_City")

GUINDA, NEGRO, GRIS, BLANCO = (117, 9, 70), (35, 31, 32), (99, 101, 105), (255, 255, 255)
GUINDA_SUAVE, GRIS_SUAVE = (247, 236, 241), (232, 233, 234)
SUBE, BAJA = (0, 100, 63), (179, 38, 30)  # colores funcionales (no son del manual del IPN)
HEX = lambda c: "%02X%02X%02X" % c

AVISO = "Herramienta educativa basada en indicadores técnicos; no constituye asesoría financiera. El rendimiento pasado no garantiza resultados futuros."
INSTITUCION = ("INSTITUTO POLITÉCNICO NACIONAL", "ESCUELA SUPERIOR DE ECONOMÍA", "Seminario de Titulación 2026")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ------------------------------------------------------------------ formato
def fecha_larga(f):
    d = date.fromisoformat(f)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(f):
    y, m, d = f.split("-")
    return f"{d}/{m}/{y}"


def n2(x, signo=False):
    if x is None:
        return "s/d"
    return f"{x:+,.2f}" if signo else f"{x:,.2f}"


def pct(x, signo=True):
    return "s/d" if x is None else (f"{x:+,.2f}%" if signo else f"{x:,.2f}%")


def precio(x, moneda="MXN"):
    return "s/d" if x is None else (f"US${x:,.2f}" if moneda == "USD" else f"${x:,.2f}")


def cambio(x, unidad):
    return "s/d" if x is None else (f"{x:+,.2f} pb" if unidad == "pb" else f"{x:+,.2f}%")


def posterior(e):
    if e.get("ret_5") is None:
        return "Aún no hay suficientes sesiones posteriores para evaluar esta decisión."
    ac = {True: "la decisión acertó", False: "la decisión no acertó", None: "sin evaluar"}[e.get("acierto")]
    r10 = f" y a 10 sesiones {pct(e['ret_10'])}" if e.get("ret_10") is not None else ""
    return f"A 5 sesiones el precio cambió {pct(e['ret_5'])}{r10}: {ac}."


def _sin_signo_raro(t):
    return str(t).replace("−", "-")


# ===================================================================== Markdown
def md_dia(reg):
    L = [f"# Análisis del {fecha_larga(reg['fecha'])}", "", "Instituto Politécnico Nacional · Escuela Superior de Economía · Seminario de Titulación 2026", "",
         reg["mercado"]["texto"], ""]
    ent = (reg.get("entorno") or {}).get("indicadores") or []
    if ent:
        L += ["## Entorno del día", "", "| Indicador | Valor | Cambio contra la sesión previa | Fuente |", "|---|---:|---:|---|"]
        L += [f"| {x['nombre']} | {n2(x['valor'])} | {cambio(x['cambio'], x['cambio_unidad'])} | {'oficial' if x['oficial'] else 'referencia'} |" for x in ent]
        L += [""]
    L += ["## Decisiones del día", "", "| Emisora | Mercado | Cierre | Var. % | Decisión | Puntaje | Confianza | Cambió |", "|---|---|---:|---:|---|---:|---|---|"]
    for e in reg["emisoras"]:
        L.append(f"| {e['nombre']} | {e.get('mercado') or ''} | {precio(e['cierre'], e.get('moneda'))} | {pct(e['var_pct'])} | **{e['decision']}** | {e['score']:+d} | {e['confianza']} | {'Sí' if e.get('cambio') else 'No'} |")
    for e in reg["emisoras"]:
        L += ["", f"### {e['nombre']}: {e['decision']}", "", "**Por qué:**", ""]
        L += [f"- {p}" for p in e["por_que"]]
        L += ["", f"**Qué hacer:** {e['accion']}", "", f"**Qué pasó después:** {posterior(e)}"]
    L += ["", "## Deuda gubernamental y privada", ""]
    for x in reg["deuda"]:
        L += [f"### {x['nombre']}: {x['decision']}", ""] + [f"- {p}" for p in x["por_que"]] + [""]
    L += [f"_{AVISO}_", ""]
    return "\n".join(L)


# ======================================================================== Excel
_fino = Side(style="thin", color=HEX(GRIS_SUAVE))


def _hoja(wb, nombre, cols, filas, anchos, titulo=None, formatos=None, envolver=()):
    ws = wb.create_sheet(nombre[:31])
    r0 = 1
    if titulo:
        ws.cell(1, 1, titulo).font = Font(bold=True, size=13, color=HEX(GUINDA))
        r0 = 3
    for j, c in enumerate(cols, 1):
        x = ws.cell(r0, j, c)
        x.fill, x.font = PatternFill("solid", fgColor=HEX(GUINDA)), Font(bold=True, color="FFFFFF")
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, f in enumerate(filas, r0 + 1):
        for j, v in enumerate(f, 1):
            c = ws.cell(i, j, v)
            c.border = Border(bottom=_fino)
            if j - 1 in envolver:
                c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="justify")
            if formatos and j - 1 in formatos and isinstance(v, (int, float)):
                c.number_format = formatos[j - 1]
        if i % 2 == 0:
            for j in range(1, len(cols) + 1):
                ws.cell(i, j).fill = PatternFill("solid", fgColor=HEX(GUINDA_SUAVE))
    for j, w in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws


def _portada_xlsx(wb, titulo, subtitulo, parrafos):
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_view.showGridLines = False
    for r in range(1, 6):
        for c in range(1, 12):
            ws.cell(r, c).fill = PatternFill("solid", fgColor=HEX(GUINDA))
    try:
        img = XLImage(str(MARCA / "ipn-escudo-blanco.png"))
        img.width, img.height = 52, 76
        ws.add_image(img, "A1")
    except Exception:
        pass
    ws["C1"], ws["C2"], ws["C3"] = INSTITUCION
    ws["C1"].font, ws["C2"].font, ws["C3"].font = Font(bold=True, size=14, color="FFFFFF"), Font(bold=True, size=12, color="FFFFFF"), Font(size=11, color="FFFFFF")
    ws["A7"], ws["A8"] = titulo, subtitulo
    ws["A7"].font, ws["A8"].font = Font(bold=True, size=18, color=HEX(GUINDA)), Font(size=11, color=HEX(GRIS))
    r = 10
    for p in parrafos:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=10)
        c = ws.cell(r, 1, p)
        c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="justify")
        ws.row_dimensions[r].height = max(30, 15 * (len(p) // 120 + 1))
        r += 1
    ws.cell(r + 1, 1, AVISO).font = Font(italic=True, size=9, color=HEX(GRIS))
    for j in range(1, 12):
        ws.column_dimensions[get_column_letter(j)].width = 14
    ws.column_dimensions["A"].width = 12
    return ws


def _bytes(wb):
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def xlsx_dia(reg):
    wb = Workbook()
    _portada_xlsx(wb, f"Análisis del {fecha_larga(reg['fecha'])}", "Decisión, por qué, qué hacer y qué pasó después", [reg["mercado"]["texto"]])
    ent = (reg.get("entorno") or {}).get("indicadores") or []
    if ent:
        _hoja(wb, "Entorno del día", ["Indicador", "Fecha", "Valor", "Cambio", "Unidad del cambio", "Fuente"],
              [[x["nombre"], x["fecha"], x["valor"], x["cambio"], x["cambio_unidad"], "Oficial" if x["oficial"] else "Referencia (no oficial)"] for x in ent],
              [44, 12, 12, 12, 16, 30], formatos={2: "#,##0.00", 3: "0.00"})
    filas = [[reg["fecha"], e["nombre"], e.get("mercado"), e.get("moneda"), e["cierre"], e["var_pct"], e["decision"], e["score"], e["confianza"],
              "Sí" if e.get("cambio") else "No", "\n".join(e["por_que"]), e["accion"], e.get("ret_5"), e.get("ret_10"),
              {True: "Sí", False: "No", None: "Por evaluar"}[e.get("acierto")]] for e in reg["emisoras"]]
    ws = _hoja(wb, "Decisiones", ["Fecha", "Emisora", "Mercado", "Moneda", "Cierre", "Var. %", "Decisión", "Puntaje", "Confianza", "¿Cambió?",
                                  "Por qué", "Qué hacer", "Rend. 5 ses. %", "Rend. 10 ses. %", "¿Acertó?"], filas,
               [12, 30, 10, 9, 11, 9, 24, 9, 11, 10, 80, 50, 12, 12, 12], formatos={4: "#,##0.00", 5: "0.00", 12: "0.00", 13: "0.00"}, envolver=(10, 11))
    verde, rojo = PatternFill("solid", fgColor="CFEBDD"), PatternFill("solid", fgColor="F6D3CF")
    for fila in ws.iter_rows(min_row=2):
        d = fila[6]
        d.fill = verde if "Comprar" in str(d.value) else rojo if "Vender" in str(d.value) else PatternFill()
        d.font = Font(bold=True)
    _hoja(wb, "Criterios", ["Emisora", "Criterio", "Puntos"], [[e["nombre"], c[0], c[1]] for e in reg["emisoras"] for c in e["componentes"]], [30, 40, 10])
    _hoja(wb, "Deuda", ["Instrumento", "Emisor", "Última cifra", "Valor", "Cambio (pb)", "Z", "Tendencia", "Decisión", "Por qué"],
          [[x["nombre"], x["emisor"], x["fecha"], x["valor"], x["var_pb"], x["z"], x["tendencia"], x["decision"], "\n".join(x["por_que"])] for x in reg["deuda"]],
          [28, 24, 14, 12, 12, 8, 16, 24, 90], formatos={3: "0.00", 4: "0.00", 5: "0.00"}, envolver=(8,))
    return _bytes(wb)


def xlsx_periodo(inf):
    an, ctx, arc, sim = inf["analisis"], inf["contexto"], inf["archivo"], inf["simulacion"]
    p = inf["periodo"]
    wb = Workbook()
    _portada_xlsx(wb, "Informe de mercados", f"Periodo del {fecha_corta(p['desde'])} al {fecha_corta(p['hasta'])} · último cierre {fecha_corta(p['ultimo_cierre'] or p['hasta'])}",
                  [an["mercado"]["texto"], *ctx["lectura"]])
    _hoja(wb, "Entorno", ["Indicador", "Grupo", "Inicio", "Fecha inicio", "Fin", "Fecha fin", "Cambio", "Unidad del cambio", "Fuente", "Tipo de fuente", "Qué es"],
          [[x["nombre"], x["grupo"], x["ini"]["valor"], x["ini"]["fecha"], x["fin"]["valor"], x["fin"]["fecha"], x["cambio"], x["cambio_unidad"],
            x["fuente"]["nombre"], "Oficial" if x["fuente"]["oficial"] else "Referencia (no oficial)", x["que_es"]] for x in ctx["indicadores"]],
          [40, 18, 12, 12, 12, 12, 11, 12, 52, 22, 90], formatos={2: "#,##0.00", 4: "#,##0.00", 6: "0.00"}, envolver=(10,))
    _hoja(wb, "Sensibilidad EE. UU.", ["Emisora", "País", "Moneda", "Sesiones", "Correlación con S&P 500", "Beta frente a S&P 500", "Correlación con el dólar", "Correlación con el IPC"],
          [[s["nombre"], s["pais"], s["moneda"], s["n"], s["corr_sp500"], s["beta_sp500"], s["corr_dolar"], s["corr_ipc"]] for s in ctx["sensibilidades"]],
          [34, 10, 9, 10, 18, 18, 18, 16], formatos={4: "0.00", 5: "0.00", 6: "0.00", 7: "0.00"})
    _hoja(wb, "Efecto cambiario", ["Acción de EE. UU.", "Desde", "Hasta", "Rend. en dólares %", "Variación del dólar %", "Rend. en pesos %"],
          [[e["nombre"], e["desde"], e["hasta"], e["ret_usd"], e["ret_dolar"], e["ret_pesos"]] for e in ctx["efecto_cambiario"]], [30, 12, 12, 18, 20, 18], formatos={3: "0.00", 4: "0.00", 5: "0.00"})
    acc = [x for x in an["acciones"] if "error" not in x]
    _hoja(wb, "Acciones", ["Emisora", "Mercado", "Moneda", "Cierre inicial", "Cierre final", "Rend. periodo %", "Volatilidad anual %", "Caída máxima %", "Decisión al cierre", "Puntaje",
                           "Confianza", "Tendencia", "RSI", "Por qué"],
          [[x["nombre"], x["mercado"], x["moneda"], x["serie"]["cierre"][0], x["cierre"], x["ret_periodo"], x["stats"]["vol_anual"], x["stats"]["max_drawdown"], x["decision"], x["score"],
            x["confianza"], x["tendencia"]["etiqueta"], x["rsi"], "\n".join(x["por_que"])] for x in acc],
          [32, 9, 8, 13, 13, 14, 15, 14, 24, 9, 11, 12, 8, 90], formatos={3: "#,##0.00", 4: "#,##0.00", 5: "0.00", 6: "0.00", 7: "0.00", 12: "0.00"}, envolver=(13,))
    _hoja(wb, "Deuda", ["Instrumento", "Emisor", "Unidad", "Última cifra", "Valor", "Cambio (pb)", "Z", "Tendencia", "Decisión", "Por qué"],
          [[x["nombre"], x["emisor"], x["unidad"], x["fecha"], x["valor"], x["var_pb"], x["z"], x["tendencia"], x["decision"], "\n".join(x["por_que"])] for x in an["deuda"]],
          [28, 24, 30, 13, 14, 12, 8, 16, 24, 90], formatos={4: "#,##0.00", 5: "0.00", 6: "0.00"}, envolver=(9,))
    if ctx["privados"]:
        _hoja(wb, "Papel comercial y CB", ["Mes", "Tasa papel comercial %", "Tasa CB corto plazo %", "Tasa CB mediano plazo en pesos %", "Colocado corto plazo (miles de pesos)",
                                           "Colocado papel comercial", "Colocado CB corto plazo", "Colocado mediano y largo plazo"],
              [[m["mes"][:7], m["tasa_pc"], m["tasa_cb_cp"], m["tasa_cb_mp"], m["col_cp"], m["col_pc"], m["col_cb_cp"], m["col_mlp"]] for m in ctx["privados"]],
              [10, 18, 18, 22, 26, 22, 22, 24], formatos={1: "0.00", 2: "0.00", 3: "0.00", 4: "#,##0", 5: "#,##0", 6: "#,##0", 7: "#,##0"})
    filas = [[d["fecha"], e["t"], e["v"], e["s"], "Sí" if e["c"] else "No", e["r5"], {True: "Sí", False: "No", None: "Por evaluar"}[e["a"]]] for d in arc["dias"] for e in d["e"]]
    _hoja(wb, "Decisiones por día", ["Fecha", "Emisora", "Decisión", "Puntaje", "¿Cambió?", "Rend. a 5 sesiones %", "¿Acertó?"], filas, [12, 12, 20, 9, 10, 18, 12], formatos={5: "0.00"})
    _hoja(wb, "Aciertos", ["Decisión", "Casos evaluados", "Aciertos", "% de aciertos", "Rend. medio a 5 sesiones %"],
          [[a["decision"], a["casos"], a["aciertos"], a["pct"], a["ret5_medio"]] for a in arc["aciertos"]], [16, 16, 12, 14, 24], formatos={3: "0.00", 4: "0.00"})
    if sim.get("fechas"):
        m = sim["metricas"]
        _hoja(wb, "Simulación", ["Medida", "Siguiendo las decisiones", "Comprar y mantener"],
              [["Rendimiento del periodo %", m["ret_estrategia"], m["ret_comprar_mantener"]], ["Valor final (pesos)", sim["estrategia"][-1], sim["comprar_mantener"][-1]],
               ["Caída máxima %", m["caida_estrategia"], m["caida_comprar_mantener"]], ["Operaciones", m["operaciones"], None]], [30, 26, 22],
              formatos={1: "#,##0.00", 2: "#,##0.00"})
    g = glosario.guia(an and {x["ticker"]: x["nombre"] for x in an["acciones"] if "nombre" in x}, __import__("server").META, {n: {"codigo": d["codigo"], "emisor": d["emisor"]} for n, d in __import__("server").DEUDA.items() if not d.get("oculto")})
    filas = [[a["nombre"], "Acción", a.get("mercado"), a["que_es"], a["que_la_mueve"], (a["fuente"] or {}).get("nombre"), (a["fuente"] or {}).get("url")] for a in g["acciones"]]
    filas += [[d["nombre"], "Deuda", d["emisor"], d["que_es"], d["que_lo_mueve"], (d["fuente"] or {}).get("nombre"), (d["fuente"] or {}).get("url")] for d in g["deuda"]]
    _hoja(wb, "Qué es cada cosa", ["Instrumento", "Tipo", "Mercado o emisor", "Qué es", "Qué lo mueve", "Fuente oficial", "Enlace"], filas, [28, 9, 24, 80, 60, 40, 60], envolver=(3, 4))
    _hoja(wb, "Fuentes", ["Fuente", "Tipo", "Enlace"], [[f["nombre"], "Oficial" if f["oficial"] else "Referencia (no oficial)", f["url"]] for f in ctx["fuentes"]], [80, 24, 90])
    return _bytes(wb)


# ========================================================================== PDF
def _pdf_clase():
    class PDF(FPDF):
        pie = "Alzea"

        def header(self):
            if self.page_no() == 1:
                return
            self.set_fill_color(*GUINDA)
            self.rect(0, 0, 210, 7, "F")
            self.set_xy(16, 1.6)
            self.set_font("Barlow", "B", 7.5)
            self.set_text_color(*BLANCO)
            self.cell(120, 4, f"Instituto Politécnico Nacional · Escuela Superior de Economía · {self.pie}")
            self.set_y(14)

        def footer(self):
            self.set_y(-14)
            self.set_draw_color(*GRIS_SUAVE)
            self.line(16, self.get_y(), 194, self.get_y())
            self.set_font("Barlow", "", 7.5)
            self.set_text_color(*GRIS)
            self.set_x(16)
            self.cell(150, 5, "Herramienta educativa · no constituye asesoría financiera", new_x="RIGHT")
            self.cell(28, 5, f"Página {self.page_no()} de {{nb}}", align="R")

    pdf = PDF(format="A4")
    for est, arch in (("", "Barlow-Regular"), ("B", "Barlow-Bold"), ("I", "Barlow-Italic")):
        pdf.add_font("Barlow", est, str(FUENTES_TTF / f"{arch}.ttf"))
    pdf.add_font("BarlowC", "B", str(FUENTES_TTF / "BarlowSemiCondensed-Bold.ttf"))
    pdf.alias_nb_pages()
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(True, 20)
    return pdf


def _banda(pdf, titulo, subtitulo, alto=64, grande=True):
    """Encabezado institucional: banda guinda con el escudo del IPN en blanco y el de la ESE."""
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, 210, alto, "F")
    h_esc = alto - 18
    pdf.image(str(MARCA / "ipn-escudo-blanco.png"), x=16, y=9, h=h_esc)
    x = 16 + h_esc * 164 / 240 + 8
    pdf.set_text_color(*BLANCO)
    pdf.set_xy(x, 12)
    pdf.set_font("Barlow", "B", 15 if grande else 12)
    pdf.cell(110, 7, INSTITUCION[0], new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x)
    pdf.set_font("Barlow", "B", 12 if grande else 10)
    pdf.cell(110, 6, INSTITUCION[1], new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x)
    pdf.set_font("Barlow", "", 10)
    pdf.cell(110, 6, INSTITUCION[2], new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(x, alto - 20)
    pdf.set_font("BarlowC", "B", 24 if grande else 18)
    pdf.cell(120, 10, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x)
    pdf.set_font("Barlow", "", 10.5)
    pdf.cell(120, 6, subtitulo)
    d = 28 if grande else 22
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(194 - d, 10, d, d, "F")
    pdf.image(str(MARCA / "ese-escudo.png"), x=194 - d + 2, y=12, w=d - 4, h=d - 4)
    pdf.set_y(alto + 8)


def _h2(pdf, txt):
    if pdf.get_y() > 245:
        pdf.add_page()
    pdf.ln(5)
    pdf.set_font("BarlowC", "B", 14.5)
    pdf.set_text_color(*GUINDA)
    pdf.cell(0, 7, txt, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*GUINDA)
    pdf.set_line_width(0.6)
    pdf.line(16, pdf.get_y(), 194, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(3)


def _h3(pdf, txt, color=NEGRO):
    if pdf.get_y() > 255:
        pdf.add_page()
    pdf.ln(2)
    pdf.set_font("Barlow", "B", 11)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5.5, _sin_signo_raro(txt), new_x="LMARGIN", new_y="NEXT")


def _p(pdf, txt, size=9.8, bold=False, italic=False, color=NEGRO, espacio=1.8, sangria=0, align="J"):
    pdf.set_font("Barlow", "B" if bold else "I" if italic else "", size)
    pdf.set_text_color(*color)
    pdf.set_x(16 + sangria)
    pdf.multi_cell(178 - sangria, 5, _sin_signo_raro(txt), align=align, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(espacio)


def _li(pdf, txt, size=9.6):
    pdf.set_font("Barlow", "", size)
    pdf.set_text_color(*NEGRO)
    pdf.set_x(20)
    pdf.cell(4, 5, "•")
    pdf.multi_cell(170, 5, _sin_signo_raro(txt), align="J", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.6)


def _tabla(pdf, cols, filas, anchos, aligns=None, estilos=None, size=8.6):
    """Tabla con encabezado guinda y renglones alternados. `estilos`: {(fila, col): color} para sube/baja."""
    aligns = aligns or ["LEFT"] + ["RIGHT"] * (len(cols) - 1)
    pdf.set_font("Barlow", "", size)
    with pdf.table(col_widths=anchos, text_align=aligns, line_height=5.2, borders_layout="HORIZONTAL_LINES",
                   headings_style=FontFace(emphasis="BOLD", color=BLANCO, fill_color=GUINDA), cell_fill_color=GUINDA_SUAVE, cell_fill_mode="ROWS",
                   padding=(1.2, 1.5, 1.2, 1.5)) as t:
        r = t.row()
        for c in cols:
            r.cell(_sin_signo_raro(c))
        for i, f in enumerate(filas):
            r = t.row()
            for j, v in enumerate(f):
                col = (estilos or {}).get((i, j))
                r.cell(_sin_signo_raro(v), style=FontFace(color=col) if col else None)
    pdf.ln(2)


def _color_var(x):
    return None if x is None or abs(x) < 1e-9 else (SUBE if x > 0 else BAJA)


def _entorno_dia(pdf, reg):
    ent = (reg.get("entorno") or {}).get("indicadores") or []
    if not ent:
        return
    _h2(pdf, "Entorno del día")
    filas = [[x["nombre"], n2(x["valor"]), cambio(x["cambio"], x["cambio_unidad"]), "Oficial" if x["oficial"] else "Referencia"] for x in ent]
    est = {(i, 2): _color_var(x["cambio"]) for i, x in enumerate(ent)}
    _tabla(pdf, ["Indicador", "Valor al cierre", "Cambio contra la sesión previa", "Fuente"], filas, (68, 30, 50, 30), ["LEFT", "RIGHT", "RIGHT", "LEFT"], est)


def pdf_dia(reg):
    pdf = _pdf_clase()
    pdf.pie = f"Análisis del {fecha_corta(reg['fecha'])}"
    pdf.add_page()
    _banda(pdf, "Análisis del día", fecha_larga(reg["fecha"]), alto=52, grande=False)
    _p(pdf, reg["mercado"]["texto"])
    _entorno_dia(pdf, reg)
    _h2(pdf, "Decisiones del día")
    filas = [[e["nombre"], e.get("mercado") or "", precio(e["cierre"], e.get("moneda")), pct(e["var_pct"]), e["decision"], f"{e['score']:+d}", e["confianza"]] for e in reg["emisoras"]]
    est = {(i, 3): _color_var(e["var_pct"]) for i, e in enumerate(reg["emisoras"])}
    _tabla(pdf, ["Emisora", "Mercado", "Cierre", "Var. %", "Decisión", "Puntaje", "Confianza"], filas, (50, 18, 24, 18, 36, 14, 18), ["LEFT", "LEFT", "RIGHT", "RIGHT", "LEFT", "RIGHT", "LEFT"], est)
    for e in reg["emisoras"]:
        _h3(pdf, f"{e['nombre']}: {e['decision']}", GUINDA)
        _p(pdf, "Por qué", bold=True, espacio=0.5)
        for q in e["por_que"]:
            _li(pdf, q)
        _p(pdf, "Qué hacer: " + e["accion"], espacio=0.8)
        _p(pdf, "Qué pasó después: " + posterior(e))
    _h2(pdf, "Deuda gubernamental y privada")
    for x in reg["deuda"]:
        _h3(pdf, f"{x['nombre']}: {x['decision']}", GUINDA)
        for q in x["por_que"]:
            _li(pdf, q)
    return bytes(pdf.output())


def pdf_periodo(inf):
    an, ctx, arc, sim = inf["analisis"], inf["contexto"], inf["archivo"], inf["simulacion"]
    p = inf["periodo"]
    ahora = datetime.now(TZ)
    pdf = _pdf_clase()
    pdf.pie = f"Informe de mercados · {fecha_corta(p['desde'])} al {fecha_corta(p['hasta'])}"
    pdf.add_page()
    _banda(pdf, "Informe de mercados", "Acciones de la BMV, Nasdaq y NYSE · deuda · entorno global")
    en_curso = (p["ultimo_cierre"] == ahora.date().isoformat()) and __import__("server").mercado_abierto()
    _p(pdf, f"Periodo consultado: del {fecha_larga(p['desde'])} al {fecha_larga(p['hasta'])}. Último dato disponible: {fecha_larga(p['ultimo_cierre'] or p['hasta'])}"
            f"{' (sesión en curso: las cifras del día son parciales)' if en_curso else ''}. "
            f"Elaborado el {fecha_corta(ahora.date().isoformat())} a las {ahora:%H:%M} (hora del centro de México). El periodo siempre inicia el 1 de marzo de 2026 o después.", color=GRIS, size=9.2)
    _h2(pdf, "Resumen")
    _p(pdf, an["mercado"].get("texto_periodo") or an["mercado"]["texto"])
    claves = {x["id"]: x for x in ctx["indicadores"]}
    for k, nom in (("fx", "Tipo de cambio FIX (pesos por dólar)"), ("sp500", "S&P 500"), ("ipc", "S&P/BMV IPC"), ("ust10y", "Tesoro de EE. UU. a 10 años (%)"),
                   ("tasa_obj", "Tasa objetivo de Banxico (%)"), ("vix", "VIX")):
        if k in claves:
            x = claves[k]
            _li(pdf, f"{nom}: {n2(x['fin']['valor'])} al {fecha_corta(x['fin']['fecha'])} ({cambio(x['cambio'], x['cambio_unidad'])} desde el {fecha_corta(x['ini']['fecha'])}).")

    _h2(pdf, "1. Qué se analiza y cómo")
    acc = [x for x in an["acciones"] if "error" not in x]
    mx = [x["nombre"] for x in acc if x["pais"] == "México"]
    us = [x["nombre"] for x in acc if x["pais"] != "México"]
    _p(pdf, f"Acciones de México (Bolsa Mexicana de Valores): {', '.join(mx)}. Acciones de Estados Unidos (Nasdaq y NYSE): {', '.join(us)}. "
            f"Deuda: {', '.join(x['nombre'] for x in an['deuda'])}.")
    _p(pdf, "Para cada acción se calcula un puntaje de -100 a +100 con seis criterios (tendencia por medias móviles, MACD, RSI, bandas de Bollinger, momentum a 20 sesiones y regresión lineal de 30 sesiones). "
            "Con +20 o más la decisión es comprar; con -20 o menos, vender; entre ambos, mantener. En deuda se compara el rendimiento de la última subasta con el promedio de las últimas 12 (puntaje z). "
            "Las decisiones son un ejercicio educativo y se contrastan con lo que ocurrió después (sección 6).")

    _h2(pdf, "2. Entorno global y fuentes oficiales")
    for t in ctx["lectura"]:
        _p(pdf, t)
    filas = [[x["nombre"], f"{n2(x['ini']['valor'])}", f"{n2(x['fin']['valor'])}", cambio(x["cambio"], x["cambio_unidad"]), ("Oficial: " if x["fuente"]["oficial"] else "Referencia: ") + x["fuente"]["nombre"].split(" · ")[0]]
             for x in ctx["indicadores"]]
    est = {(i, 3): _color_var(x["cambio"]) for i, x in enumerate(ctx["indicadores"])}
    _tabla(pdf, ["Indicador", "Inicio", "Fin", "Cambio", "Fuente"], filas, (58, 22, 22, 26, 50), ["LEFT", "RIGHT", "RIGHT", "RIGHT", "LEFT"], est, size=8.2)
    if ctx["diferenciales"]:
        _h3(pdf, "Diferenciales de tasas", GUINDA)
        for d in ctx["diferenciales"]:
            _li(pdf, f"{d['nombre']}: {n2(d['pb'], True)} pb ({d['detalle']}). {d['lectura']}")
    _h2(pdf, "3. Qué tan ligados están tus instrumentos a EE. UU. y al dólar")
    if ctx["sensibilidades"]:
        filas = [[s["nombre"], s["pais"], f"{s['n']}", n2(s["corr_sp500"]), n2(s["beta_sp500"]), n2(s["corr_dolar"]), n2(s["corr_ipc"]) if s["corr_ipc"] is not None else "-"] for s in ctx["sensibilidades"]]
        _tabla(pdf, ["Emisora", "País", "Sesiones", "Corr. S&P 500", "Beta S&P 500", "Corr. dólar", "Corr. IPC"], filas, (50, 20, 17, 22, 22, 24, 23), None, size=8.4)
        _p(pdf, "La correlación (de -1 a +1) mide si los rendimientos diarios se mueven juntos; la beta mide cuánto se mueve la acción por cada 1 % que se mueve el S&P 500. "
                "La correlación con el dólar usa el tipo de cambio de cierre de Banxico: un valor negativo significa que la acción tiende a subir cuando el peso se aprecia. "
                "Ninguna de estas cifras prueba que un mercado cause al otro.", size=9, italic=True)
    if ctx["efecto_cambiario"]:
        _h3(pdf, "Acciones de EE. UU. vistas desde México", GUINDA)
        filas = [[e["nombre"], pct(e["ret_usd"]), pct(e["ret_dolar"]), pct(e["ret_pesos"])] for e in ctx["efecto_cambiario"]]
        est = {(i, j): _color_var(v) for i, e in enumerate(ctx["efecto_cambiario"]) for j, v in ((1, e["ret_usd"]), (2, e["ret_dolar"]), (3, e["ret_pesos"]))}
        _tabla(pdf, ["Acción", "Rend. en dólares", "Variación del dólar", "Rend. en pesos"], filas, (62, 38, 40, 38), None, est)

    _h2(pdf, "4. Acciones: qué son y qué dicen las decisiones")
    filas = [[x["nombre"], x["mercado"], precio(x["serie"]["cierre"][0], x["moneda"]), precio(x["cierre"], x["moneda"]), pct(x["ret_periodo"]), pct(x["stats"]["vol_anual"], False),
              x["decision"], f"{x['score']:+d}"] for x in acc]
    est = {(i, 4): _color_var(x["ret_periodo"]) for i, x in enumerate(acc)}
    _tabla(pdf, ["Emisora", "Mercado", "Cierre inicial", "Cierre final", "Rend. periodo", "Volatilidad", "Decisión", "Puntaje"], filas, (36, 16, 23, 23, 20, 20, 26, 14), None, est, size=8.2)
    gl = {a["ticker"]: a for a in glosario.guia({x["ticker"]: x["nombre"] for x in acc}, __import__("server").META, {})["acciones"]}
    for x in acc:
        g = gl.get(x["ticker"], {})
        _h3(pdf, f"{x['nombre']} ({x['ticker'].replace('.MX', '')}) · {x['mercado']} · {x['moneda']}", GUINDA)
        _p(pdf, f"Qué es. {g.get('que_es', '')}", size=9.2, espacio=0.8)
        _p(pdf, f"Qué la mueve. {g.get('que_la_mueve', '')}", size=9.2, espacio=0.8)
        _p(pdf, f"Decisión al cierre del {fecha_corta(x['fecha'])}: {x['decision']} (puntaje {x['score']:+d}, confianza {x['confianza'].lower()}). " + " ".join(x["por_que"][1:4]), size=9.2, espacio=0.8)
        if (g.get("fuente") or {}).get("nombre"):
            _p(pdf, f"Fuente oficial: {g['fuente']['nombre']} ({g['fuente']['url']}).", size=8.4, color=GRIS, align="L")

    _h2(pdf, "5. Deuda gubernamental y privada")
    filas = [[x["nombre"], x["emisor"], "s/d" if x["valor"] is None else (n2(x["valor"] / 1000) + " mdp" if x["tipo"] == "monto" else n2(x["valor"])), n2(x.get("var_pb"), True) if x.get("var_pb") is not None else "-",
              n2(x["z"], True) if x.get("z") is not None else "-", x["tendencia"], x["decision"]] for x in an["deuda"]]
    _tabla(pdf, ["Instrumento", "Emisor", "Última cifra", "Cambio (pb)", "Z", "Tendencia", "Decisión"], filas, (38, 32, 24, 20, 12, 26, 26), None, size=8.2)
    gd = {d["nombre"]: d for d in glosario.guia({}, {}, {n: {"codigo": "", "emisor": ""} for n in glosario.DEUDA})["deuda"]}
    for x in an["deuda"]:
        g = gd.get(x["nombre"], {})
        _h3(pdf, f"{x['nombre']} · {x['emisor']}", GUINDA)
        _p(pdf, f"Qué es. {g.get('que_es', '')}", size=9.2, espacio=0.8)
        _p(pdf, f"Qué lo mueve. {g.get('que_lo_mueve', '')}", size=9.2, espacio=0.8)
        _p(pdf, f"Lectura. {x['texto']}", size=9.2, espacio=0.8)
        if (g.get("fuente") or {}).get("nombre"):
            _p(pdf, f"Fuente oficial: {g['fuente']['nombre']} ({g['fuente']['url']}).", size=8.4, color=GRIS, align="L")
    if ctx["privados"]:
        _h3(pdf, "Papel comercial y certificados bursátiles por mes (Banxico, cuadros CF302 y CF304)", GUINDA)
        filas = [[m["mes"][:7], n2(m["tasa_cb_cp"]), n2(m["tasa_cb_mp"]), n2((m["col_cp"] or 0) / 1e6), n2((m["col_pc"] or 0) / 1e6), n2((m["col_mlp"] or 0) / 1e6)] for m in ctx["privados"]]
        _tabla(pdf, ["Mes", "Tasa CB corto plazo %", "Tasa CB mediano plazo %", "Colocado corto plazo (mdp)", "Colocado papel comercial (mdp)", "Colocado mediano y largo (mdp)"], filas, (18, 28, 30, 36, 36, 30), None, size=8)
        _p(pdf, "mdp = millones de pesos. Una tasa de 0.00 significa que no hubo colocaciones de ese instrumento en el mes.", size=8.6, italic=True)

    _h2(pdf, "6. ¿Acertaron las decisiones?")
    filas = [[a["decision"], str(a["casos"]), str(a["aciertos"]), pct(a["pct"], False), pct(a["ret5_medio"])] for a in arc["aciertos"]]
    _tabla(pdf, ["Decisión", "Casos evaluados", "Aciertos", "% de aciertos", "Rend. medio a 5 sesiones"], filas, (40, 36, 30, 32, 40), None, size=8.8)
    _p(pdf, "Comprar acierta si el precio subió a 5 sesiones; vender, si bajó; mantener, si se movió 2 % o menos. Un porcentaje cercano a 50 % indica que la regla no supera al azar en el periodo.", size=9, italic=True)
    if arc["cambios"]:
        _h3(pdf, "Últimos cambios de decisión", GUINDA)
        for c in arc["cambios"][:10]:
            _li(pdf, f"{fecha_corta(c['fecha'])} · {c['ticker']}: de {(c['de'] or 'sin dato').lower()} a {c['a'].lower()}.")
    if sim.get("fechas"):
        m = sim["metricas"]
        _h2(pdf, "7. Simulación")
        _p(pdf, f"Con $100,000.00 repartidos en partes iguales entre las {len(sim['por_emisora'])} emisoras (acciones de EE. UU. medidas en pesos), seguir las decisiones habría terminado en {pct(m['ret_estrategia'])} "
                f"y comprar y mantener en {pct(m['ret_comprar_mantener'])}. Caída máxima: {pct(m['caida_estrategia'])} contra {pct(m['caida_comprar_mantener'])}. "
                f"Se compra con +20 o más, se sale con -20 o menos, se opera al cierre siguiente y cada operación paga {n2(sim['costo_pct'])} % de comisión.")

    _h2(pdf, "Anexo. Qué significa cada indicador y cómo se relaciona con tus instrumentos")
    for x in ctx["indicadores"]:
        _p(pdf, f"{x['nombre']}. {x['que_es']} {x['como_afecta']}", size=9, espacio=1.2)

    _h2(pdf, "8. Fuentes")
    for f in ctx["fuentes"]:
        _li(pdf, f"{f['nombre']} ({'oficial' if f['oficial'] else 'referencia, no oficial'}): {f['url']}", size=8.8)
    _li(pdf, "Precios de las acciones: Yahoo Finance (proveedor de datos de mercado; no es una fuente oficial). Para reportes oficiales de las empresas: SEC EDGAR (EE. UU.) y Bolsa Mexicana de Valores / CNBV (México).", size=8.8)
    _li(pdf, "Subastas, CETES, Bonos M, Udibonos, Bondes F, BPAG28, papel comercial y certificados bursátiles: Banco de México, cuadros CF107, CF115, CF133, CF302 y CF304 del SIE.", size=8.8)
    _p(pdf, AVISO, italic=True, size=9, color=GRIS)
    return bytes(pdf.output())
