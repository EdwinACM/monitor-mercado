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
    filas = sorted(([e["t"], d["fecha"], e["cierre"], e["v"], e["s"], "Sí" if e["c"] else "No", e["r5"], {True: "Sí", False: "No", None: "Por evaluar"}[e["a"]]] for d in arc["dias"] for e in d["e"]), key=lambda r: (r[0], r[1]))
    _hoja(wb, "Cierres y decisiones", ["Emisora", "Fecha", "Cierre", "Decisión", "Puntaje", "¿Cambió?", "Rend. a 5 sesiones %", "¿Acertó?"], filas, [12, 12, 12, 20, 9, 10, 18, 12], formatos={2: "#,##0.00", 6: "0.00"})
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
    pdf.set_fill_color(*BLANCO)
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


# ------------------------------------------------- estadística por emisora
def estadisticas(x):
    """Medidas de riesgo y rendimiento calculadas con los cierres diarios del periodo (rendimientos simples)."""
    c, f = x["serie"]["cierre"], x["serie"]["fechas"]
    r = [(c[i] / c[i - 1] - 1) * 100 for i in range(1, len(c)) if c[i - 1]]
    if len(r) < 5:
        return {}
    n = len(r)
    media = sum(r) / n
    desv = (sum((v - media) ** 2 for v in r) / (n - 1)) ** 0.5
    orden = sorted(r)
    k = max(1, int(n * 0.05))
    asim = sum(((v - media) / desv) ** 3 for v in r) / n if desv else 0
    imax, imin = max(range(len(c)), key=c.__getitem__), min(range(len(c)), key=c.__getitem__)
    mejor, peor = max(range(1, len(c)), key=lambda i: c[i] / c[i - 1]), min(range(1, len(c)), key=lambda i: c[i] / c[i - 1])
    return {"sesiones": n, "media_diaria": media, "desv_diaria": desv, "var95": -orden[k - 1], "cvar95": -sum(orden[:k]) / k,
            "dias_alza": sum(1 for v in r if v > 0) / n * 100, "asimetria": asim,
            "maximo": (c[imax], f[imax]), "minimo": (c[imin], f[imin]),
            "mejor": ((c[mejor] / c[mejor - 1] - 1) * 100, f[mejor]), "peor": ((c[peor] / c[peor - 1] - 1) * 100, f[peor]),
            "rango_1d": desv}


def _factores(x, ctx):
    """Lo que hoy podría mover el precio, con cifras reales del entorno y de la sensibilidad de la emisora."""
    ind = {i["id"]: i for i in ctx["indicadores"]}
    sens = next((s for s in ctx["sensibilidades"] if s["ticker"] == x["ticker"]), None)
    efe = next((e for e in ctx["efecto_cambiario"] if e["ticker"] == x["ticker"]), None)
    us = x["pais"] != "México"
    out = []

    def ch(k):
        return ind[k]["cambio"] if k in ind else None
    if sens and sens.get("beta_sp500") is not None:
        sp = f" El S&P 500 {'avanzó' if (ch('sp500') or 0) >= 0 else 'retrocedió'} {n2(abs(ch('sp500')))} % en el periodo." if ch("sp500") is not None else ""
        out.append(f"Bolsa de EE. UU. Su beta frente al S&P 500 es {n2(sens['beta_sp500'])} y su correlación {n2(sens['corr_sp500'])}: por cada 1 % que se mueve el S&P 500, esta emisora tiende a moverse {n2(sens['beta_sp500'])} %.{sp}")
    if us and efe:
        out.append(f"Tipo de cambio. En dólares rindió {pct(efe['ret_usd'])} y, como el dólar varió {pct(efe['ret_dolar'])} frente al peso, en pesos rindió {pct(efe['ret_pesos'])}. Un peso más débil suma rendimiento a quien invierte desde México; uno más fuerte lo resta.")
    elif sens and sens.get("corr_dolar") is not None:
        out.append(f"Dólar. Su correlación con el tipo de cambio es {n2(sens['corr_dolar'])}: " + ("tiende a subir cuando el peso se aprecia." if sens["corr_dolar"] < -0.1 else "tiende a subir cuando el peso se deprecia." if sens["corr_dolar"] > 0.1 else "casi no se relaciona con el dólar."))
    if "ust10y" in ind and "tasa_obj" in ind:
        out.append(f"Tasas. El Tesoro de EE. UU. a 10 años rinde {n2(ind['ust10y']['fin']['valor'])} % ({cambio(ind['ust10y']['cambio'], 'pb')} en el periodo) y la tasa objetivo de Banxico es {n2(ind['tasa_obj']['fin']['valor'])} %. "
                   "Tasas más altas encarecen el crédito y hacen más atractivos los bonos frente a las acciones" + (", lo que suele presionar más a las empresas de crecimiento." if x["ticker"] in ("MSFT", "NVDA", "TSLA", "AAPL") else "."))
    if "vix" in ind:
        v = ind["vix"]["fin"]["valor"]
        out.append(f"Riesgo del mercado. El VIX está en {n2(v)} ({'calma' if v < 20 else 'nerviosismo moderado' if v < 30 else 'estrés'}). Con un VIX alto las caídas de las acciones tienden a ser más bruscas y simultáneas.")
    if not us and "ipc" in ind and sens and sens.get("corr_ipc") is not None:
        out.append(f"Mercado mexicano. El S&P/BMV IPC cambió {pct(ind['ipc']['cambio'])} en el periodo; la correlación de esta emisora con el IPC es {n2(sens['corr_ipc'])}.")
    return out


def _sugerencia(x, e):
    d = x["veredicto"]
    s, r = x["stats"]["soporte"], x["stats"]["resistencia"]
    m = x["moneda"]
    rango = f" En una sesión normal el precio se mueve alrededor de ±{n2(e.get('desv_diaria', 0))} % (una desviación estándar diaria)." if e else ""
    if d in ("COMPRA FUERTE", "COMPRAR"):
        base = f"La lectura técnica favorece comprar o aumentar poco a poco. Referencias: soporte en {precio(s, m)} y resistencia en {precio(r, m)}; si el precio cierra por debajo del soporte, la señal pierde validez y conviene revisar la posición."
    elif d in ("VENTA FUERTE", "VENDER"):
        base = f"La lectura técnica sugiere reducir o no abrir posición. Referencias: soporte en {precio(s, m)} y resistencia en {precio(r, m)}; un cierre por encima de la resistencia sería una señal de que la caída se está agotando."
    else:
        base = f"La lectura técnica es neutral: conviene mantener lo que ya se tiene y esperar una señal clara. Referencias: soporte en {precio(s, m)} y resistencia en {precio(r, m)}."
    return base + rango + " Ninguna decisión debe superar tu tolerancia al riesgo: diversifica y no concentres tu dinero en una sola emisora."


def _grafica(pdf, series, fechas, fmt=lambda v: n2(v), h=44, etiquetas=None):
    """Gráfica de líneas dibujada con primitivas del PDF. series: [{vals, color, w}]; la primera es la principal."""
    if pdf.get_y() + h + 12 > 277:
        pdf.add_page()
    x0, w, y0 = 33, 161, pdf.get_y() + 2
    vals = [v for s in series for v in s["vals"] if v is not None]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    py = lambda v: y0 + h - (v - lo) / (hi - lo) * h
    n = len(series[0]["vals"])
    px = lambda i: x0 + i / max(1, n - 1) * w
    pdf.set_font("Barlow", "", 7.2)
    pdf.set_draw_color(*GRIS_SUAVE)
    pdf.set_line_width(0.15)
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        pdf.line(x0, py(v), x0 + w, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(16, py(v) - 1.8)
        pdf.cell(16, 3.6, fmt(v), align="R")
    for s in series[::-1]:
        pdf.set_draw_color(*s["color"])
        pdf.set_line_width(s.get("w", 0.5))
        prev = None
        for i, v in enumerate(s["vals"]):
            if v is None:
                prev = None
                continue
            if prev is not None:
                pdf.line(px(i - 1), py(prev), px(i), py(v))
            prev = v
    pdf.set_line_width(0.2)
    u = series[0]["vals"][-1]
    pdf.set_fill_color(*series[0]["color"])
    pdf.ellipse(px(n - 1) - 0.9, py(u) - 0.9, 1.8, 1.8, "F")
    pdf.set_text_color(*GRIS)
    for i in (0, n // 2, n - 1):
        pdf.set_xy(min(max(px(i) - 10, x0 - 2), x0 + w - 18), y0 + h + 1)
        pdf.cell(20, 3.6, fecha_corta(fechas[i]), align="C")
    pdf.set_y(y0 + h + 6)
    if etiquetas:
        pdf.set_x(x0)
        for txt, col in etiquetas:
            pdf.set_fill_color(*col)
            pdf.rect(pdf.get_x(), pdf.get_y() + 1.1, 4, 1.6, "F")
            pdf.set_x(pdf.get_x() + 5.5)
            pdf.set_font("Barlow", "", 7.6)
            pdf.set_text_color(*GRIS)
            pdf.cell(pdf.get_string_width(txt) + 5, 4, txt)
        pdf.ln(5)


def _tarjetas(pdf, items):
    """Fila de tarjetas con una cifra grande: items = [(etiqueta, valor, color|None)]."""
    if pdf.get_y() > 245:
        pdf.add_page()
    n = len(items)
    w = 178 / n
    y = pdf.get_y()
    for i, (et, val, col) in enumerate(items):
        x = 16 + i * w
        pdf.set_fill_color(*GUINDA_SUAVE)
        pdf.rect(x + 0.8, y, w - 1.6, 17, "F")
        pdf.set_fill_color(*GUINDA)
        pdf.rect(x + 0.8, y, 1.2, 17, "F")
        pdf.set_xy(x + 3.5, y + 1.6)
        pdf.set_font("Barlow", "", 7.6)
        pdf.set_text_color(*GRIS)
        pdf.cell(w - 6, 4, et)
        pdf.set_xy(x + 3.5, y + 6.5)
        pdf.set_font("BarlowC", "B", 14)
        pdf.set_text_color(*(col or NEGRO))
        pdf.cell(w - 6, 8, val)
    pdf.set_y(y + 21)


def _cabecera_ficha(pdf, titulo, sub, decision, veredicto):
    pdf.add_page()
    col = SUBE if veredicto in ("COMPRA FUERTE", "COMPRAR") else BAJA if veredicto in ("VENTA FUERTE", "VENDER") else GRIS
    y = pdf.get_y() - 2
    pdf.set_fill_color(*GUINDA)
    pdf.rect(16, y, 178, 15, "F")
    pdf.set_xy(20, y + 1.8)
    pdf.set_font("BarlowC", "B", 15)
    pdf.set_text_color(*BLANCO)
    pdf.cell(118, 6, titulo)
    pdf.set_xy(20, y + 8.3)
    pdf.set_font("Barlow", "", 8.6)
    pdf.cell(118, 4.5, sub)
    ancho = 40
    pdf.set_fill_color(*BLANCO)
    pdf.rect(194 - ancho - 3, y + 3, ancho, 9, "F")
    pdf.set_xy(194 - ancho - 3, y + 3.2)
    pdf.set_font("Barlow", "B", 10)
    pdf.set_text_color(*col)
    pdf.cell(ancho, 8.6, decision, align="C")
    pdf.set_y(y + 19)


def _ficha_accion(pdf, x, ctx, e, g, hist):
    s = x["stats"]
    _cabecera_ficha(pdf, f"{x['nombre']} ({x['ticker'].replace('.MX', '')})", f"{x['mercado']} · {x['moneda']} · cierre del {fecha_corta(x['fecha'])}", x["decision"], x["veredicto"])
    _tarjetas(pdf, [(f"Cierre ({x['moneda']})", precio(x["cierre"], x["moneda"]), None), ("Cambio del día", pct(x["var_pct"]), _color_var(x["var_pct"])),
                    ("Rendimiento del periodo", pct(x["ret_periodo"]), _color_var(x["ret_periodo"])), ("Puntaje de -100 a +100", f"{x['score']:+d}", None)])
    sr = x["serie"]
    _h3(pdf, "Precio de cierre del periodo", GUINDA)
    _grafica(pdf, [{"vals": sr["cierre"], "color": GUINDA, "w": 0.55}, {"vals": sr["sma20"], "color": GRIS, "w": 0.3}, {"vals": sr["sma50"], "color": (160, 162, 166), "w": 0.3}], sr["fechas"],
             fmt=lambda v: n2(v), etiquetas=[("Cierre", GUINDA), ("Media de 20 sesiones", GRIS), ("Media de 50 sesiones", (160, 162, 166))])
    _h3(pdf, "Estadística del periodo", GUINDA)
    f = []
    if e:
        f = [["Volatilidad anual", pct(s["vol_anual"], False), "Pérdida diaria probable (VaR 95 %)", pct(e["var95"], False)],
             ["Caída máxima del periodo", pct(s["max_drawdown"]), "Pérdida si ocurre lo peor (CVaR 95 %)", pct(e["cvar95"], False)],
             ["Rendimiento / riesgo", n2(s["ratio_rend_riesgo"]), "Días al alza", pct(e["dias_alza"], False)],
             ["Mejor día", f"{pct(e['mejor'][0])} ({fecha_corta(e['mejor'][1])})", "Peor día", f"{pct(e['peor'][0])} ({fecha_corta(e['peor'][1])})"],
             ["Máximo del periodo", f"{precio(e['maximo'][0], x['moneda'])} ({fecha_corta(e['maximo'][1])})", "Mínimo del periodo", f"{precio(e['minimo'][0], x['moneda'])} ({fecha_corta(e['minimo'][1])})"],
             ["RSI (14 sesiones)", n2(x["rsi"]), "Rend. 5 y 20 sesiones", f"{pct(x['ret5'])} y {pct(x['ret20'])}"],
             ["Soporte (20 ses.)", precio(s["soporte"], x["moneda"]), "Resistencia (20 ses.)", precio(s["resistencia"], x["moneda"])]]
    else:
        f = [["Volatilidad anual", pct(s["vol_anual"], False), "Caída máxima", pct(s["max_drawdown"])]]
    _tabla(pdf, ["Medida", "Valor", "Medida", "Valor"], f, (48, 42, 52, 36), ["LEFT", "RIGHT", "LEFT", "RIGHT"], size=8.2)
    _p(pdf, "VaR 95 %: con los datos del periodo, en 95 de cada 100 sesiones la pérdida diaria no pasó de esa cifra. CVaR: promedio de las pérdidas en el 5 % de las peores sesiones. "
            "Rendimiento / riesgo: rendimiento del periodo entre su volatilidad; más alto es mejor.", size=8.2, italic=True, color=GRIS)
    _h3(pdf, "Cierres y decisiones de las últimas 8 sesiones", GUINDA)
    filas, est = [], {}
    for i, h in enumerate(hist[-8:][::-1]):
        filas.append([fecha_corta(h["fecha"]), precio(h["cierre"], x["moneda"]), pct(h["var_pct"]) if h.get("var_pct") is not None else "-", h["decision"], f"{h['s']:+d}",
                      pct(h["r5"]) if h["r5"] is not None else "por evaluar", {True: "Sí", False: "No", None: "-"}[h["a"]]])
        if h.get("var_pct") is not None:
            est[(i, 2)] = _color_var(h["var_pct"])
    _tabla(pdf, ["Fecha", "Cierre", "Var. %", "Decisión", "Puntaje", "Rend. a 5 ses.", "¿Acertó?"], filas, (22, 28, 20, 36, 18, 28, 26), None, est, size=8.2)
    _h3(pdf, "Qué es", GUINDA)
    _p(pdf, g.get("que_es", ""), size=9.2)
    _p(pdf, "Qué la mueve. " + g.get("que_la_mueve", ""), size=9.2)
    fac = _factores(x, ctx)
    if fac:
        _h3(pdf, "Qué podría mover su precio ahora", GUINDA)
        for t in fac:
            _li(pdf, t, size=9.2)
    _h3(pdf, f"Por qué la decisión es {x['decision'].lower()}", GUINDA)
    filas = [[c["criterio"], f"{c['puntos']:+d} de {c['max']}", c["detalle"]] for c in x["componentes"]]
    _tabla(pdf, ["Criterio", "Puntos", "Qué se observó"], filas, (44, 22, 112), ["LEFT", "RIGHT", "LEFT"], {(i, 1): _color_var(c["puntos"]) for i, c in enumerate(x["componentes"])}, size=8.2)
    _p(pdf, f"Confianza {x['confianza'].lower()} · tendencia de 30 sesiones {x['tendencia']['etiqueta']}. " + x["accion"], size=9.2)
    _h3(pdf, "Sugerencia", GUINDA)
    _p(pdf, _sugerencia(x, e), size=9.2)
    b = x["backtest"]
    if b["n_compra"] >= 8 or b["n_venta"] >= 8:
        _p(pdf, f"Prueba histórica (a {b['horizonte']} sesiones, {b['muestra']} sesiones): comprar acertó {n2(b['aciertos_compra'])} % en {b['n_compra']} casos y vender {n2(b['aciertos_venta'])} % en {b['n_venta']}. "
                f"Rendimiento medio de cualquier sesión: {pct(b['base_rend_medio'])}. Es una prueba dentro de la misma muestra: calibra la confianza, no la garantiza.", size=8.6, italic=True, color=GRIS)
    if (g.get("fuente") or {}).get("nombre"):
        _p(pdf, f"Fuente oficial: {g['fuente']['nombre']} ({g['fuente']['url']}). Precios: Yahoo Finance (referencia).", size=8.2, color=GRIS, align="L")


def _ficha_deuda(pdf, x, ctx, g):
    tipo = x["tipo"]
    _cabecera_ficha(pdf, x["nombre"], f"{x['emisor']} · {x['unidad']}", x["decision"], x["senal"] if x["senal"] in ("COMPRAR", "VENDER") else "MANTENER")
    val = "s/d" if x["valor"] is None else (f"${n2(x['valor'] / 1000)} mdp" if tipo == "monto" else f"${x['valor']:,.5f}" if tipo == "precio" else n2(x["valor"]) + (" %" if x["unidad"].startswith("%") else ""))
    cam = f"{n2(x['var_pb'], True)} pb" if x.get("var_pb") is not None else "-"
    _tarjetas(pdf, [(f"Última cifra ({fecha_corta(x['fecha'])})", val, None), ("Cambio vs. anterior", cam, _color_var(x.get("var_pb") or 0)),
                    ("Puntaje z (12 subastas)", n2(x["z"], True) if x.get("z") is not None else "-", None), ("Tendencia", x["tendencia"].capitalize(), None)])
    datos = x["datos"]
    if len(datos) >= 3:
        _h3(pdf, "Evolución en el periodo" if tipo != "monto" else "Monto colocado por semana (millones de pesos)", GUINDA)
        v = [d["valor"] / (1000 if tipo == "monto" else 1) for d in datos]
        ma = [None if i < 3 else sum(v[i - 3:i + 1]) / 4 for i in range(len(v))]
        _grafica(pdf, [{"vals": v, "color": GUINDA, "w": 0.55}, {"vals": ma, "color": GRIS, "w": 0.3}], [d["fecha"] for d in datos], fmt=lambda t: n2(t) if tipo != "precio" else f"{t:.3f}",
                 etiquetas=[("Valor en cada subasta o semana", GUINDA), ("Promedio móvil de 4", GRIS)], h=40)
    _h3(pdf, "Últimos resultados", GUINDA)
    ex = x["extras"]
    cols = ["Fecha", "Valor"] + (["Cambio (pb)"] if tipo == "tasa" else []) + [e_.split(" (")[0] for e_ in ex]
    filas = []
    for d in datos[-8:][::-1]:
        fila = [fecha_corta(d["fecha"]), f"{d['valor']:,.5f}" if tipo == "precio" else n2(d["valor"])]
        if tipo == "tasa":
            fila.append(n2(d["var_pb"], True) if d.get("var_pb") is not None else "-")
        fila += [n2((d.get("extra") or {}).get(e_)) if (d.get("extra") or {}).get(e_) is not None else "-" for e_ in ex]
        filas.append(fila)
    anch = [24] + [30] * (len(cols) - 1)
    k = 178 / sum(anch)
    _tabla(pdf, cols, filas, tuple(a * k for a in anch), None, size=8.2)
    _h3(pdf, "Qué es", GUINDA)
    _p(pdf, g.get("que_es", ""), size=9.2)
    _p(pdf, "Qué lo mueve. " + g.get("que_lo_mueve", ""), size=9.2)
    ind = {i["id"]: i for i in ctx["indicadores"]}
    fac = []
    if "tasa_obj" in ind:
        fac.append(f"Banxico. La tasa objetivo es {n2(ind['tasa_obj']['fin']['valor'])} % ({cambio(ind['tasa_obj']['cambio'], 'pb')} en el periodo). Las tasas de los CETES y los bonos siguen de cerca esa referencia.")
    for d in ctx["diferenciales"]:
        fac.append(f"{d['nombre']}: {n2(d['pb'], True)} pb. {d['lectura']}")
    if "infl_mx" in ind:
        fac.append(f"Inflación en México: {n2(ind['infl_mx']['fin']['valor'])} % anual. Si sube, el mercado exige más rendimiento y los precios de los bonos bajan; en Udibonos el capital se ajusta con la inflación.")
    if "fx" in ind:
        fac.append(f"Tipo de cambio: {n2(ind['fx']['fin']['valor'])} pesos por dólar ({pct(ind['fx']['cambio'])} en el periodo). Un peso débil presiona a Banxico a mantener tasas altas y afecta el apetito de extranjeros por bonos mexicanos.")
    if fac:
        _h3(pdf, "Qué podría mover su rendimiento ahora", GUINDA)
        for t in fac[:5]:
            _li(pdf, t, size=9.2)
    _h3(pdf, "Lectura y decisión", GUINDA)
    for q in x["por_que"]:
        _li(pdf, q, size=9.2)
    _p(pdf, "Si las tasas suben, el precio de los bonos ya emitidos baja; fijar tasa conviene cuando el rendimiento está alto frente a sus últimas subastas. Es un apoyo educativo, no asesoría financiera.", size=8.6, italic=True, color=GRIS)
    if (g.get("fuente") or {}).get("nombre"):
        _p(pdf, f"Fuente oficial: {g['fuente']['nombre']} ({g['fuente']['url']}).", size=8.2, color=GRIS, align="L")


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

    _h2(pdf, "4. Tablero de cierres y decisiones")
    for etiqueta, pais_mx in (("Acciones de México (Bolsa Mexicana de Valores, pesos)", True), ("Acciones de Estados Unidos (Nasdaq y NYSE, dólares)", False)):
        grupo = [x for x in acc if (x["pais"] == "México") == pais_mx]
        if not grupo:
            continue
        _h3(pdf, etiqueta, GUINDA)
        filas = [[x["nombre"], precio(x["serie"]["cierre"][0], x["moneda"]), precio(x["cierre"], x["moneda"]), pct(x["var_pct"]), pct(x["ret_periodo"]), x["decision"], f"{x['score']:+d}"] for x in grupo]
        est = {(i, j): _color_var(v) for i, x in enumerate(grupo) for j, v in ((3, x["var_pct"]), (4, x["ret_periodo"]))}
        _tabla(pdf, ["Emisora", "Cierre inicial", "Cierre final", "Var. día", "Rend. periodo", "Decisión", "Puntaje"], filas, (50, 25, 25, 18, 24, 26, 10), None, est, size=8.2)
    _h3(pdf, "Deuda gubernamental y privada", GUINDA)
    filas = [[x["nombre"], "s/d" if x["valor"] is None else (n2(x["valor"] / 1000) + " mdp" if x["tipo"] == "monto" else n2(x["valor"])), n2(x.get("var_pb"), True) if x.get("var_pb") is not None else "-",
              n2(x["z"], True) if x.get("z") is not None else "-", x["tendencia"], x["decision"]] for x in an["deuda"]]
    _tabla(pdf, ["Instrumento", "Última cifra", "Cambio (pb)", "Z", "Tendencia", "Decisión"], filas, (48, 28, 24, 14, 26, 38), None, size=8.2)
    _p(pdf, "Las fichas siguientes siguen el mismo orden: primero las acciones de México, luego las de Estados Unidos y al final la deuda. Cada ficha trae el cierre, la gráfica del periodo, la estadística de riesgo, qué es, qué podría mover su precio, por qué la decisión y una sugerencia.", size=9, italic=True)

    hist = {}
    for d in arc["dias"]:
        for en in d["e"]:
            hist.setdefault(en["y"], []).append({"fecha": d["fecha"], "cierre": en["cierre"], "decision": en["v"].capitalize(), "s": en["s"], "r5": en["r5"], "a": en["a"]})
    for h in hist.values():
        for i, r in enumerate(h):
            r["var_pct"] = (r["cierre"] / h[i - 1]["cierre"] - 1) * 100 if i and h[i - 1]["cierre"] else None
    gl = {a_["ticker"]: a_ for a_ in glosario.guia({x["ticker"]: x["nombre"] for x in acc}, __import__("server").META, {})["acciones"]}
    gd = {d["nombre"]: d for d in glosario.guia({}, {}, {n: {"codigo": "", "emisor": ""} for n in glosario.DEUDA})["deuda"]}
    _h2(pdf, "5. Fichas por emisora e instrumento")
    pdf.pie = "Informe de mercados · fichas"
    for x in acc:
        _ficha_accion(pdf, x, ctx, estadisticas(x), gl.get(x["ticker"], {}), hist.get(x["ticker"], []))
    for x in an["deuda"]:
        _ficha_deuda(pdf, x, ctx, gd.get(x["nombre"], {}))
    if ctx["privados"]:
        pdf.add_page()
        _h3(pdf, "Papel comercial y certificados bursátiles por mes (Banxico, cuadros CF302 y CF304)", GUINDA)
        filas = [[m["mes"][:7], n2(m["tasa_cb_cp"]), n2(m["tasa_cb_mp"]), n2((m["col_cp"] or 0) / 1e6), n2((m["col_pc"] or 0) / 1e6), n2((m["col_mlp"] or 0) / 1e6)] for m in ctx["privados"]]
        _tabla(pdf, ["Mes", "Tasa CB corto plazo %", "Tasa CB mediano plazo %", "Colocado corto plazo (mdp)", "Colocado papel comercial (mdp)", "Colocado mediano y largo (mdp)"], filas, (18, 28, 30, 36, 36, 30), None, size=8)
        _p(pdf, "mdp = millones de pesos. Una tasa de 0.00 significa que no hubo colocaciones de ese instrumento en el mes.", size=8.6, italic=True)
    pdf.pie = f"Informe de mercados · {fecha_corta(p['desde'])} al {fecha_corta(p['hasta'])}"

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
