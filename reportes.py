"""Reportes del análisis diario: Markdown, Excel y PDF (decisión, porqué y qué pasó después)."""
import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

AVISO = "Herramienta educativa basada en indicadores técnicos; no constituye asesoría financiera."
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def fecha_larga(f):
    d = date.fromisoformat(f)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def n2(x, signo=False):
    return "s/d" if x is None else (f"{x:+.2f}" if signo else f"{x:.2f}")


def posterior(e):
    if e.get("ret_5") is None:
        return "Aún no hay suficientes sesiones posteriores para evaluar esta decisión."
    ac = {True: "la decisión acertó", False: "la decisión no acertó", None: "sin evaluar"}[e.get("acierto")]
    r10 = f" y a 10 sesiones {n2(e['ret_10'], True)}%" if e.get("ret_10") is not None else ""
    return f"A 5 sesiones el precio cambió {n2(e['ret_5'], True)}%{r10}: {ac}."


# ---------------------------------------------------------------- Markdown
def md_dia(reg):
    L = [f"# Análisis del {fecha_larga(reg['fecha'])}", "", reg["mercado"]["texto"], "",
         "## Decisiones del día", "",
         "| Emisora | Cierre | Var. % | Decisión | Puntaje | Confianza | Cambió |", "|---|---:|---:|---|---:|---|---|"]
    for e in reg["emisoras"]:
        L.append(f"| {e['nombre']} | ${n2(e['cierre'])} | {n2(e['var_pct'], True)}% | **{e['decision']}** | {e['score']:+d} | {e['confianza']} | {'Sí' if e.get('cambio') else 'No'} |")
    for e in reg["emisoras"]:
        L += ["", f"### {e['nombre']}: {e['decision']}", "", "**Por qué:**", ""]
        L += [f"- {p}" for p in e["por_que"]]
        L += ["", f"**Qué hacer:** {e['accion']}", "", f"**Qué pasó después:** {posterior(e)}"]
    L += ["", "## Deuda gubernamental", ""]
    for x in reg["deuda"]:
        L += [f"### {x['nombre']}: {x['decision']}", ""] + [f"- {p}" for p in x["por_que"]] + [""]
    L += [f"_{AVISO}_", ""]
    return "\n".join(L)


# ------------------------------------------------------------------- Excel
def xlsx_dia(reg):
    G, hf = PatternFill("solid", fgColor="15191D"), Font(bold=True, color="FFFFFF")
    verde, rojo = PatternFill("solid", fgColor="CFEBDD"), PatternFill("solid", fgColor="F6D3CF")
    wrap = Alignment(wrap_text=True, vertical="top")
    wb = Workbook()

    def hoja(ws, cols, filas, anchos):
        ws.append(cols)
        for c in ws[1]:
            c.fill, c.font, c.alignment = G, hf, Alignment(horizontal="center", vertical="center", wrap_text=True)
        for f in filas:
            ws.append(f)
        for i, w in enumerate(anchos):
            ws.column_dimensions[get_column_letter(i + 1)].width = w
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "Decisiones"
    filas = [[reg["fecha"], e["nombre"], e["cierre"], e["var_pct"], e["decision"], e["score"], e["confianza"],
              "Sí" if e.get("cambio") else "No", "\n".join(e["por_que"]), e["accion"], e.get("ret_5"), e.get("ret_10"),
              {True: "Sí", False: "No", None: "Por evaluar"}[e.get("acierto")]] for e in reg["emisoras"]]
    hoja(ws, ["Fecha", "Emisora", "Cierre", "Var. %", "Decisión", "Puntaje", "Confianza", "¿Cambió?", "Por qué", "Qué hacer",
              "Rend. 5 ses. %", "Rend. 10 ses. %", "¿Acertó?"], filas, [12, 30, 10, 9, 22, 9, 11, 10, 80, 50, 12, 12, 12])
    for fila in ws.iter_rows(min_row=2):
        for c in fila:
            c.alignment = wrap
        for j in (2, 3, 10, 11):
            fila[j].number_format = "0.00"
        d = fila[4]
        d.fill = verde if "Comprar" in str(d.value) else rojo if "Vender" in str(d.value) else PatternFill()
        d.font = Font(bold=True)
    ws2 = wb.create_sheet("Criterios")
    hoja(ws2, ["Emisora", "Criterio", "Puntos"], [[e["nombre"], c[0], c[1]] for e in reg["emisoras"] for c in e["componentes"]], [30, 40, 10])
    ws3 = wb.create_sheet("Deuda")
    hoja(ws3, ["Instrumento", "Emisor", "Última subasta", "Valor", "Cambio (pb)", "Z", "Tendencia", "Decisión", "Por qué"],
         [[x["nombre"], x["emisor"], x["fecha"], x["valor"], x["var_pb"], x["z"], x["tendencia"], x["decision"], "\n".join(x["por_que"])] for x in reg["deuda"]],
         [20, 18, 14, 10, 12, 8, 12, 22, 90])
    for fila in ws3.iter_rows(min_row=2):
        for c in fila:
            c.alignment = wrap
        for j in (3, 4, 5):
            fila[j].number_format = "0.00"
    ws4 = wb.create_sheet("Resumen")
    ws4.append([f"Análisis del {fecha_larga(reg['fecha'])}"]); ws4["A1"].font = Font(bold=True, size=14)
    ws4.append([reg["mercado"]["texto"]]); ws4["A2"].alignment = Alignment(wrap_text=True, vertical="top", horizontal="justify")
    ws4.append([AVISO]); ws4.column_dimensions["A"].width = 120; ws4.row_dimensions[2].height = 60
    wb.move_sheet("Resumen", offset=-3)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------- PDF
_MAPA = {"−": "-", "–": "-", "—": "-", "≥": ">=", "≤": "<=", "→": "->", "“": '"', "”": '"', "’": "'", "σ": "sigma", "•": "-"}


def lat(s):
    for a, b in _MAPA.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def pdf_dia(reg):
    from fpdf import FPDF

    class PDF(FPDF):
        def footer(self):
            self.set_y(-13)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(90, 100, 110)
            self.cell(0, 6, lat(f"{AVISO}  Página {self.page_no()}/{{nb}}"), align="C")

    pdf = PDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_margins(16, 16, 16)
    pdf.set_auto_page_break(True, 18)
    pdf.add_page()
    W = pdf.w - 32

    def titulo(txt, size=13, espacio=4):
        pdf.ln(espacio)
        pdf.set_font("Helvetica", "B", size)
        pdf.set_text_color(11, 17, 23)
        pdf.cell(0, 7, lat(txt), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(11, 17, 23)
        pdf.set_line_width(0.5)
        pdf.line(16, pdf.get_y(), 16 + W, pdf.get_y())
        pdf.ln(2.5)

    def parrafo(txt, bold=False, size=10, color=(30, 40, 50)):
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(0, 5.2, lat(txt), align="J", new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(242, 169, 0)
    pdf.rect(16, 14, W, 1.6, "F")
    pdf.set_y(19)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(11, 17, 23)
    pdf.cell(0, 9, "Pizarra", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 6, lat(f"Análisis del {fecha_larga(reg['fecha'])}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    parrafo(reg["mercado"]["texto"])

    titulo("Decisiones del día")
    cols = [("Emisora", 62, "L"), ("Cierre", 22, "R"), ("Var. %", 20, "R"), ("Decisión", 36, "L"), ("Puntaje", 18, "R"), ("Confianza", 22, "L")]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(21, 25, 29)
    pdf.set_text_color(255, 255, 255)
    for n, w, al in cols:
        pdf.cell(w, 7, n, fill=True, align=al)
    pdf.ln(7)
    pdf.set_text_color(11, 17, 23)
    for e in reg["emisoras"]:
        d = e["decision"]
        fondo = (207, 235, 221) if "Comprar" in d else (246, 211, 207) if "Vender" in d else (236, 239, 242)
        pdf.set_font("Helvetica", "", 9)
        vals = [e["nombre"][:36], f"${n2(e['cierre'])}", n2(e["var_pct"], True) + "%", d, f"{e['score']:+d}", e["confianza"]]
        for (n, w, al), v in zip(cols, vals):
            if n == "Decisión":
                pdf.set_fill_color(*fondo)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(w, 7, lat(v), fill=True, align=al, border="B")
                pdf.set_font("Helvetica", "", 9)
            else:
                pdf.cell(w, 7, lat(v), align=al, border="B")
        pdf.ln(7)

    for e in reg["emisoras"]:
        titulo(f"{e['nombre']}: {e['decision']}", 12, 5)
        parrafo("Por qué:", bold=True)
        for p in e["por_que"]:
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 40, 50)
            pdf.multi_cell(W - 4, 5.2, lat("- " + p), align="J", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        parrafo("Qué hacer: " + e["accion"])
        pdf.ln(0.5)
        parrafo("Qué pasó después: " + posterior(e))

    titulo("Deuda gubernamental", 13, 6)
    for x in reg["deuda"]:
        parrafo(f"{x['nombre']}: {x['decision']}", bold=True)
        for p in x["por_que"]:
            pdf.set_x(20)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 40, 50)
            pdf.multi_cell(W - 4, 5.2, lat("- " + p), align="J", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
    return bytes(pdf.output())
