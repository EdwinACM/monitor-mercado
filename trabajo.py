"""Trabajo escrito del ejercicio de rendimientos: carátula, índice, introducción, características de los
activos y de las emisoras, tabla de variaciones diarias, gráficas, estadística y decisión.

Tamaño carta, vertical. Usa los mismos datos que `ejercicio.preparar()` y las mismas fórmulas.
Se arma en dos pasadas: la primera registra en qué página quedó cada sección y la segunda escribe el índice.
"""
import math
from datetime import datetime

from fpdf import FPDF

import ejercicio as EJ
import glosario
import reportes as R
import server

W, H = 215.9, 279.4
ML = 18.0
ANCHO = W - 2 * ML
GUINDA, NEGRO, GRIS, BLANCO = EJ.GUINDA, EJ.NEGRO, EJ.GRIS, EJ.BLANCO
GUINDA_SUAVE, GRIS_SUAVE = EJ.GUINDA_SUAVE, EJ.GRIS_SUAVE
SUBE, BAJA, COLORES = EJ.SUBE, EJ.BAJA, EJ.COLORES
AUTOR = "Edwin Cruz"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _flarga(f):
    x = datetime.strptime(f, "%Y-%m-%d").date()
    return f"{x.day} de {MESES[x.month - 1]} de {x.year}"

SECCIONES = ["Introducción y objetivo de aprendizaje", "Características de los activos", "Las emisoras",
             "Variación porcentual diaria", "Gráfica de las variaciones", "Estadística de los rendimientos",
             "Conclusión y toma de decisión"]


class _Doc(FPDF):
    seccion = ""
    desbordes = []
    total = 0

    def header(self):
        if self.page_no() == 1:
            return
        self.set_draw_color(*GUINDA)
        self.set_line_width(0.5)
        self.line(ML, 17, W - ML, 17)
        self.set_xy(ML, 11)
        self.set_font("Barlow", "", 8)
        self.set_text_color(*GRIS)
        self.cell(ANCHO - 30, 4.5, self.seccion)
        self.cell(30, 4.5, "Seminario de Titulación 2026", align="R")
        self.set_xy(ML, self.t_margin)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(*GRIS_SUAVE)
        self.set_line_width(0.2)
        self.line(ML, self.get_y() - 1, W - ML, self.get_y() - 1)
        self.set_font("Barlow", "", 7.5)
        self.set_text_color(*GRIS)
        self.set_x(ML)
        self.cell(ANCHO - 20, 4, "Instituto Politécnico Nacional · Escuela Superior de Economía")
        self.cell(20, 4, f"{self.page_no()}", align="R")


def _doc():
    pdf = _Doc(orientation="P", format=(W, H))
    pdf.desbordes = []
    for est, arch in (("", "Barlow-Regular"), ("B", "Barlow-Bold"), ("I", "Barlow-Italic")):
        pdf.add_font("Barlow", est, str(R.FUENTES_TTF / f"{arch}.ttf"))
    pdf.add_font("BarlowM", "", str(R.FUENTES_TTF / "Barlow-Medium.ttf"))
    pdf.add_font("BarlowC", "B", str(R.FUENTES_TTF / "BarlowSemiCondensed-Bold.ttf"))
    pdf.set_margins(ML, 24, ML)
    pdf.set_auto_page_break(False)
    return pdf


def _pagina(pdf, seccion, titulo=None, numero=None):
    pdf.seccion = seccion
    pdf.add_page()
    pdf.set_y(26)
    if titulo:
        _titulo(pdf, titulo, numero)
    return pdf.get_y()


def _titulo(pdf, titulo, numero=None):
    y = pdf.get_y()
    if numero:
        pdf.set_xy(ML, y)
        pdf.set_font("BarlowC", "B", 26)
        pdf.set_text_color(*GRIS_SUAVE)
        pdf.cell(14, 11, str(numero))
    pdf.set_xy(ML + (14 if numero else 0), y)
    pdf.set_font("BarlowC", "B", 20)
    pdf.set_text_color(*GUINDA)
    pdf.cell(ANCHO - (14 if numero else 0), 11, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _sub(pdf, texto, esp=4):
    pdf.ln(esp)
    pdf.set_x(ML)
    pdf.set_font("Barlow", "B", 11)
    pdf.set_text_color(*NEGRO)
    pdf.cell(ANCHO, 6, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _p(pdf, texto, size=10.2, alto=5.1, color=None, italic=False, ancho=None, esp=2.4):
    pdf.set_x(ML)
    pdf.set_font("Barlow", "I" if italic else "", size)
    pdf.set_text_color(*(color or NEGRO))
    pdf.multi_cell(ancho or ANCHO, alto, texto, new_x="LMARGIN", new_y="NEXT", align="J")
    pdf.ln(esp)


def _n(x, signo=False, dec=2):
    if x is None:
        return "-"
    return f"{x:+,.{dec}f}" if signo else f"{x:,.{dec}f}"


def _color(x):
    return SUBE if (x or 0) > 0 else BAJA if (x or 0) < 0 else NEGRO


def _tabla(pdf, cols, filas, anchos, aligns=None, estilos=None, size=8.4, alto=5.2, y=None, cabecera=True, pad=1.0):
    """Tabla con encabezado guinda, filas alternadas y bordes finos. Devuelve la y final."""
    aligns = aligns or ["LEFT"] + ["RIGHT"] * (len(cols) - 1)
    k = ANCHO / sum(anchos)
    anchos = tuple(a * k for a in anchos)
    if y:
        pdf.set_y(y)
    pdf.set_x(ML)
    pdf.set_font("Barlow", "", size)
    pdf.set_text_color(*NEGRO)
    pdf.set_fill_color(*BLANCO)
    with pdf.table(col_widths=anchos, text_align=aligns, line_height=alto, borders_layout="HORIZONTAL_LINES",
                   headings_style=R.FontFace(emphasis="BOLD", color=BLANCO, fill_color=GUINDA),
                   cell_fill_color=GUINDA_SUAVE, cell_fill_mode="ROWS", padding=(pad, 1.6, pad, 1.6),
                   width=ANCHO, align="LEFT", first_row_as_headings=cabecera, repeat_headings=1) as t:
        if cabecera:
            r = t.row()
            for c in cols:
                r.cell(c)
        for i, f in enumerate(filas):
            r = t.row()
            for j, v in enumerate(f):
                col = (estilos or {}).get((i, j))
                r.cell(str(v), style=R.FontFace(color=col) if col else None)
    return pdf.get_y()


def _grafica(pdf, x0, y0, w, h, series, fechas, titulo=None, rango=None, leyenda=False, grosor=0.4, fechas_n=3, ejes=True):
    """series: [(nombre, valores, color)]. Rango fijo opcional para comparar paneles entre sí."""
    if titulo:
        pdf.set_xy(x0, y0)
        pdf.set_font("Barlow", "B", 8.4)
        pdf.set_text_color(*NEGRO)
        pdf.cell(w, 4.6, titulo)
        y0 += 5.4
    vals = [v for s in series for v in s[1] if v is not None]
    marcas = EJ._ticks(*(rango or (min(vals), max(vals))), 4)
    lo, hi = marcas[0], marcas[-1]
    px0, pw = (x0 + 10, w - 11) if ejes else (x0, w)
    ph = h - (12 if leyenda else 7 if ejes else 0)
    py = lambda v: y0 + ph - (v - lo) / (hi - lo) * ph
    n = len(fechas)
    pdf.set_font("Barlow", "", 6.4)
    pdf.set_line_width(0.1)
    for v in (marcas if ejes else []):
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.line(px0, py(v), px0 + pw, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(x0 - 1, py(v) - 1.6)
        pdf.cell(10, 3.2, f"{v:g}", align="R")
    if lo < 0 < hi:
        pdf.set_draw_color(*(GRIS if ejes else GRIS_SUAVE))
        pdf.set_line_width(0.22 if ejes else 0.3)
        pdf.line(px0, py(0), px0 + pw, py(0))
    for nombre, vs, col in series:
        pdf.set_draw_color(*col)
        pdf.set_line_width(grosor)
        prev = None
        for i, v in enumerate(vs):
            if v is None:
                prev = None
                continue
            xx = px0 + i / max(1, n - 1) * pw
            if prev is not None:
                pdf.line(prev[0], prev[1], xx, py(v))
            prev = (xx, py(v))
    pdf.set_line_width(0.2)
    pdf.set_text_color(*GRIS)
    pdf.set_font("Barlow", "", 6.4)
    idx = () if not ejes else (0, n - 1) if fechas_n <= 2 else (0, n // 2, n - 1)
    for i in idx:
        pdf.set_xy(min(max(px0 + i / max(1, n - 1) * pw - 9, x0), x0 + w - 18), y0 + ph + 1)
        pdf.cell(18, 3.2, R.fecha_corta(fechas[i]), align="C")
    if leyenda:
        xl, yl = px0, y0 + ph + 5.4
        pdf.set_font("Barlow", "", 7.4)
        for nombre, vs, col in series:
            ancho = pdf.get_string_width(nombre) + 10
            if xl + ancho > x0 + w:
                xl, yl = px0, yl + 4
            pdf.set_fill_color(*col)
            pdf.rect(xl, yl + 1.1, 4.6, 1.5, "F")
            pdf.set_xy(xl + 5.8, yl)
            pdf.set_text_color(*NEGRO)
            pdf.cell(ancho - 5.8, 4, nombre)
            xl += ancho
    return y0 + h


# ------------------------------------------------------------------------------ datos de apoyo
def _variaciones(d):
    """Por instrumento, {fecha: variación porcentual frente a su cierre anterior}."""
    return {it["clave"]: {it["serie"][i + 1][0]: v for i, v in enumerate(it["ra"])} for it in d["items"]}


def _acumulados(d, items):
    return {it["clave"]: EJ._acumulado(d, it) for it in items}


def _contexto(d):
    acc = EJ._acciones(d)
    ipc = next(x for x in d["items"] if x["clave"] == "IPC")
    sp = next(x for x in d["items"] if x["clave"] == "S&P 500")
    burs = EJ._bursatilidad(d)
    fichas_ = {x["clave"]: EJ._ficha(d, x, burs) for x in acc}
    guia = {g["ticker"]: g for g in glosario.guia({x["ticker"]: x["nombre"] for x in acc}, server.META, {})["acciones"]}
    return acc, ipc, sp, fichas_, guia


def _decision(it, sp, f):
    if it["efectivo"] <= sp["efectivo"]:
        return "Vender", BAJA
    return ("Comprar", SUBE) if f["vol"] < 35 else ("Mantener", NEGRO)


# ------------------------------------------------------------------------------ secciones
def _caratula(pdf, d, acc, ipc):
    pdf.add_page()
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, W, 62, "F")
    pdf.image(str(R.MARCA / "ipn-escudo-blanco.png"), x=ML, y=13, h=36)
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(W - ML - 34, 14, 34, 34, "F")
    pdf.image(str(R.MARCA / "ese-escudo.png"), x=W - ML - 32, y=16, w=30, h=30)
    pdf.set_text_color(*BLANCO)
    for y, txt, fnt, sz in ((18, "INSTITUTO POLITÉCNICO NACIONAL", "B", 15), (26.5, "ESCUELA SUPERIOR DE ECONOMÍA", "B", 11.5),
                            (34, "Seminario de Titulación 2026", "", 10.5)):
        pdf.set_xy(ML + 42, y)
        pdf.set_font("Barlow", fnt, sz)
        pdf.cell(110, 7, txt)
    pdf.set_xy(ML, 96)
    pdf.set_font("Barlow", "B", 10.5)
    pdf.set_text_color(*GUINDA)
    pdf.cell(ANCHO, 6, "EJERCICIO DE RENDIMIENTOS", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_x(ML)
    pdf.set_font("BarlowC", "B", 33)
    pdf.set_text_color(*NEGRO)
    pdf.multi_cell(ANCHO, 14, "Rendimiento de cinco acciones\nfrente al IPC", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_draw_color(*GUINDA)
    pdf.set_line_width(1.1)
    pdf.line(ML, pdf.get_y(), ML + 46, pdf.get_y())
    pdf.ln(5)
    pdf.set_x(ML)
    pdf.set_font("Barlow", "", 12.5)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(ANCHO, 6.4, "Apple, Microsoft, NVIDIA, Tesla y Coca-Cola\n"
                               f"Precios de cierre del {_flarga(d['inicio'])} al {_flarga(d['ultimo'])}", new_x="LMARGIN", new_y="NEXT")
    ac = _acumulados(d, acc + [ipc])
    series = [(x["clave"], ac[x["clave"]], (176, 176, 180) if x["indice"] else (193, 148, 173)) for x in acc + [ipc]]
    _grafica(pdf, ML, 184, ANCHO, 40, series, d["fechas"], grosor=0.4, ejes=False)
    pdf.set_draw_color(*GRIS_SUAVE)
    pdf.set_line_width(0.2)
    pdf.line(ML, 232, W - ML, 232)
    pdf.set_xy(ML, 225)
    pdf.set_font("Barlow", "", 7.6)
    pdf.set_text_color(*GRIS)
    pdf.cell(ANCHO, 4, "Rendimiento acumulado de los seis activos durante el periodo")
    pdf.set_xy(ML, 240)
    pdf.set_font("Barlow", "B", 12)
    pdf.set_text_color(*NEGRO)
    pdf.cell(ANCHO, 6, AUTOR, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(ML)
    pdf.set_font("Barlow", "", 10.5)
    pdf.set_text_color(*GRIS)
    pdf.cell(ANCHO, 5.6, f"Entrega: {_flarga(EJ.FIN_ANALISIS.isoformat())}")


def _indice_intro(pdf, d, paginas, acc, ipc, sp):
    _pagina(pdf, "Índice e introducción", "Índice")
    y = pdf.get_y()
    for i, nombre in enumerate(SECCIONES, 1):
        pdf.set_xy(ML, y)
        pdf.set_font("Barlow", "", 10)
        pdf.set_text_color(*NEGRO)
        pdf.cell(10, 5.6, f"{i}.")
        ancho_t = pdf.get_string_width(nombre)
        pdf.cell(ancho_t + 2, 5.6, nombre)
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.set_line_width(0.2)
        pdf.line(ML + 12 + ancho_t + 2, y + 4.2, W - ML - 8, y + 4.2)
        pdf.set_xy(W - ML - 10, y)
        pdf.set_text_color(*GRIS)
        pdf.cell(10, 5.6, str(paginas.get(nombre, "")), align="R")
        y += 6.2
    pdf.set_y(y + 4)
    _titulo(pdf, "Introducción")
    _p(pdf, "En el seminario armamos las tablas de rendimientos a mano, con pocos días y precios de ejemplo. Este trabajo hace lo mismo "
            "con datos reales y con el periodo completo: toma el precio de cierre de cinco acciones que cotizan en Estados Unidos, Apple, "
            f"Microsoft, NVIDIA, Tesla y Coca-Cola, del {_flarga(d['inicio'])} al {_flarga(d['ultimo'])}, y lo compara contra el "
            "S&P/BMV IPC, el índice de la Bolsa Mexicana de Valores.")
    _p(pdf, "De cada día saqué la variación porcentual frente al cierre anterior. Esa columna es la base de todo lo demás: el rendimiento "
            "promedio diario, la dispersión de los rendimientos y la distancia de cada día respecto a su propio promedio. El rendimiento "
            "efectivo se calcula aparte, con el primer y el último precio del periodo, porque mide el resultado acumulado y no el día típico.")
    _p(pdf, "Los precios de cierre vienen de Yahoo Finance. Los datos de cada empresa, acciones en circulación, valor par, capital y cifras "
            "del último ejercicio, están tomados de los reportes anuales que presentan a la Securities and Exchange Commission de Estados Unidos.")
    _p(pdf, "Hay que tener presente algo al comparar: las cinco acciones cotizan en dólares y el IPC está en pesos, así que una parte de la "
            "diferencia entre ellas viene del tipo de cambio. Por eso, cuando el punto es medir contra el mercado en el que realmente operan, "
            f"uso además el S&P 500, que en este periodo rindió {sp['efectivo']:+.2f} %.")
    _titulo(pdf, "Objetivo de aprendizaje")
    _p(pdf, "Aplicar a datos reales de mercado las fórmulas de rendimiento y de estadística descriptiva del seminario, y llegar con ellas a una "
            "decisión de inversión que se pueda sostener con números. En concreto:", esp=1.6)
    puntos = ["Calcular la variación porcentual diaria de cada acción y del índice, y ordenarlas en una sola tabla.",
              "Obtener el rendimiento efectivo del periodo y el rendimiento promedio diario, y distinguir para qué sirve cada uno.",
              "Medir la dispersión con desviación estándar, varianza, rango, curtosis y coeficiente de asimetría, y leer qué dice cada medida sobre el riesgo.",
              "Comparar cada acción contra el índice y decidir, con esos números, cuál comprar, cuál mantener y cuál vender."]
    for i, t in enumerate(puntos, 1):
        pdf.set_x(ML)
        pdf.set_font("Barlow", "B", 10.2)
        pdf.set_text_color(*GUINDA)
        pdf.cell(6, 5.1, f"{i}.")
        pdf.set_font("Barlow", "", 10.2)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(ANCHO - 6, 5.1, t, new_x="LMARGIN", new_y="NEXT", align="J")
        pdf.ln(1.2)


def _activos(pdf, d, acc, ipc, fichas_):
    _pagina(pdf, "Características de los activos", "Características de los activos", 2)
    _p(pdf, "Las cinco emisoras son acciones comunes de una sola clase, que cotizan en el Nasdaq y en la Bolsa de Nueva York. Una acción común "
            "da derecho a voto en la asamblea y a cobrar dividendos cuando la empresa los decreta. No promete ningún pago fijo, y ahí está la "
            "diferencia con un instrumento de deuda, donde el emisor se obliga a pagar una tasa en una fecha conocida.")
    _p(pdf, "El valor par de la tabla es un valor contable, no de mercado. Apple lo tiene en una cienmilésima de dólar y Coca-Cola en 0.25 dólares; "
            "multiplicado por las acciones emitidas da el capital social, que queda muy por debajo del valor de mercado. La distancia entre esas dos "
            "cifras es lo que el mercado está dispuesto a pagar hoy por la empresa, más allá de lo que dicen sus libros.")
    _p(pdf, "El S&P/BMV IPC no es una emisora y no se puede comprar directamente. Es un índice que resume el comportamiento conjunto de las emisoras "
            "más operadas de la Bolsa Mexicana de Valores, y aquí funciona como vara de medir: sirve para saber si un activo se movió mejor o peor "
            "que el mercado al que se compara.")
    mm = lambda v: f"{v:,.0f}" if v is not None else "s/d"
    filas = [
        ["Bolsa"] + [server.META[x["ticker"]]["mercado"] for x in acc],
        ["Tipo de acción"] + ["Común"] * len(acc),
        ["Serie"] + ["Clase única"] * len(acc),
        ["Acciones en circulación (millones)"] + [mm(fichas_[x["clave"]]["F"]["acciones"] / 1e6) for x in acc],
        ["Valor par (USD)"] + [(f"{fichas_[x['clave']]['par']:.8f}".rstrip("0").rstrip(".") if fichas_[x["clave"]]["par"] else "s/d") for x in acc],
        ["Capital social (millones de USD)"] + [_n(fichas_[x["clave"]]["capital_social"]) for x in acc],
        ["Capital contable (millones de USD)"] + [mm(fichas_[x["clave"]]["cif"].get("Capital contable", (None,))[0]) for x in acc],
        ["Valor de mercado (millones de USD)"] + [mm(x["pf"] * fichas_[x["clave"]]["F"]["acciones"] / 1e6) for x in acc],
        ["Importe operado al día (millones de USD)"] + [mm((fichas_[x["clave"]]["burs"] or {}).get("importe")) for x in acc],
        ["Lugar por bursatilidad entre las cinco"] + [str((fichas_[x["clave"]]["burs"] or {}).get("posicion", "s/d")) for x in acc],
    ]
    _sub(pdf, "Datos del título")
    y = _tabla(pdf, ["Concepto"] + [x["clave"] for x in acc], filas, (58, 24.4, 24.4, 24.4, 24.4, 24.4),
               ["LEFT"] + ["RIGHT"] * len(acc), None, size=8.4, alto=5.4, y=pdf.get_y())
    pdf.set_y(y + 1)
    _p(pdf, "La bursatilidad ordena a las cinco por el importe que se opera al día. El índice oficial de la Bolsa Mexicana de Valores, que clasifica "
            "a las emisoras en alta, media, baja y mínima, no se publica para empresas estadounidenses, así que el lugar de la tabla sale del volumen "
            "diario multiplicado por el precio de cierre.", size=9, alto=4.6, color=GRIS)
    _sub(pdf, "El índice de referencia", esp=1)
    filas = [["S&P/BMV IPC", "Bolsa Mexicana de Valores", "Pesos", _n(ipc["pi"]), _n(ipc["pf"]), _n(ipc["efectivo"], True), str(ipc["stats"]["n"])]]
    _tabla(pdf, ["Índice", "Mercado", "Unidad", "Nivel inicial", "Nivel final", "Rendimiento (%)", "Días"], filas,
           (34, 44, 20, 24, 24, 24, 14), ["LEFT", "LEFT", "LEFT"] + ["RIGHT"] * 4, {(0, 5): _color(ipc["efectivo"])}, size=8.6, alto=5.6, y=pdf.get_y())


def _emisoras(pdf, d, acc, fichas_, guia):
    _pagina(pdf, "Las emisoras", "Las emisoras", 3)
    _p(pdf, "A qué se dedica cada empresa, qué mueve su precio y cómo le fue en su último ejercicio fiscal, con las cifras que presentó a la "
            "Securities and Exchange Commission.", size=9.4, alto=4.6, esp=2)
    for it in acc:
        f, g = fichas_[it["clave"]], guia.get(it["ticker"], {})
        y0 = pdf.get_y()
        pdf.set_xy(ML + 4, y0)
        pdf.set_font("Barlow", "B", 11)
        pdf.set_text_color(*GUINDA)
        pdf.cell(86, 5.4, f"{it['clave']} · {f['F'].get('denominacion') or it['nombre']}")
        pdf.set_font("Barlow", "B", 9)
        pdf.set_text_color(*NEGRO)
        pdf.cell(ANCHO - 90, 5.4, EJ.SECTOR[it["ticker"]], align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(ML + 4)
        pdf.set_font("Barlow", "", 8.2)
        pdf.set_text_color(*GRIS)
        sic = EJ.SIC_ES.get(f["sic"], f["sic"]) or "s/d"
        pdf.cell(ANCHO - 4, 4.0, f"{server.META[it['ticker']]['mercado']} · {sic} (clasificación SEC) · Constitución: {EJ.CONSTITUCION[it['ticker']].split(';')[0]}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.6)
        pdf.set_x(ML + 4)
        pdf.set_font("Barlow", "", 8.6)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(ANCHO - 4, 4.3, g.get("que_es", ""), new_x="LMARGIN", new_y="NEXT", align="J")
        pdf.set_x(ML + 4)
        pdf.set_font("Barlow", "I", 8.6)
        pdf.set_text_color(*GRIS)
        pdf.multi_cell(ANCHO - 4, 4.3, "Qué la mueve: " + g.get("que_la_mueve", ""), new_x="LMARGIN", new_y="NEXT", align="J")
        pdf.ln(1.2)
        ing, uti = f["cif"].get("Ingresos", (None,))[0], f["cif"].get("Utilidad neta", (None,))[0]
        datos = [("Ingresos", f"{ing:,.0f} mdd" if ing else "s/d"), ("Utilidad neta", f"{uti:,.0f} mdd" if uti else "s/d"),
                 ("Precio inicial", f"{it['pi']:,.2f}"), ("Precio final", f"{it['pf']:,.2f}"), ("Rendimiento", f"{it['efectivo']:+.2f} %")]
        x, yy = ML + 4, pdf.get_y()
        for k, (et, v) in enumerate(datos):
            pdf.set_xy(x, yy)
            pdf.set_font("Barlow", "", 7.2)
            pdf.set_text_color(*GRIS)
            pdf.cell(34, 3.4, et, new_x="LEFT", new_y="NEXT")
            pdf.set_font("Barlow", "B", 9)
            pdf.set_text_color(*(_color(it["efectivo"]) if k == 4 else NEGRO))
            pdf.cell(34, 4.4, v)
            x += 35
        pdf.set_draw_color(*GUINDA)
        pdf.set_line_width(0.9)
        pdf.line(ML, y0 + 0.8, ML, yy + 7.8)
        pdf.set_y(yy + 12.6)


def _tabla_variaciones(pdf, d, acc, ipc, var):
    """Todas las fechas en una hoja: la tabla se parte en tres bloques que se leen de izquierda a derecha."""
    items = acc + [ipc]
    _pagina(pdf, "Variación porcentual diaria", "Variación porcentual diaria", 4)
    _p(pdf, "Variación = ((cierre del día / cierre anterior) - 1) x 100. Fechas de 2026. Un guion indica que esa bolsa no operó ese día.",
       size=8.6, alto=4.4, color=GRIS, esp=1.6)
    fechas = [f for f in d["fechas"] if any(f in var[x["clave"]] for x in items)]
    bloques, sep = 3, 3.2
    por = math.ceil(len(fechas) / bloques)
    bw = (ANCHO - sep * (bloques - 1)) / bloques
    wf = 9.0
    wc = (bw - wf) / len(items)
    y0 = pdf.get_y()
    hh = 4.6
    rh = min(3.6, (H - 19 - y0 - hh) / por)
    for b in range(bloques):
        x0 = ML + b * (bw + sep)
        pdf.set_fill_color(*GUINDA)
        pdf.rect(x0, y0, bw, hh, "F")
        pdf.set_font("Barlow", "B", 6.2)
        pdf.set_text_color(*BLANCO)
        pdf.set_xy(x0, y0)
        pdf.cell(wf, hh, "Fecha", align="C")
        for it in items:
            pdf.cell(wc, hh, it["clave"], align="R")
        pdf.set_font("Barlow", "", 5.9)
        for k, f in enumerate(fechas[b * por:(b + 1) * por]):
            y = y0 + hh + k * rh
            if k % 2:
                pdf.set_fill_color(*GUINDA_SUAVE)
                pdf.rect(x0, y, bw, rh, "F")
            pdf.set_xy(x0, y)
            pdf.set_text_color(*NEGRO)
            pdf.cell(wf, rh, f"{f[8:10]}/{f[5:7]}", align="C")
            for it in items:
                v = var[it["clave"]].get(f)
                pdf.set_text_color(*(_color(v) if v is not None else GRIS))
                pdf.cell(wc, rh, "-" if v is None else f"{v:+.2f}", align="R")
        pdf.set_draw_color(*GUINDA)
        pdf.set_line_width(0.3)
        n_b = len(fechas[b * por:(b + 1) * por])
        pdf.line(x0, y0 + hh + n_b * rh, x0 + bw, y0 + hh + n_b * rh)


def _graficas(pdf, d, acc, ipc, var):
    items = acc + [ipc]
    _pagina(pdf, "Gráfica de las variaciones", "Gráfica de las variaciones", 5)
    _p(pdf, "La primera gráfica dibuja la tabla completa: las seis columnas de variación diaria, una encima de otra. Lo que se ve es que los seis se "
            "mueven alrededor de cero casi todos los días y que los picos no están repartidos parejo. Debajo, cada activo aparece por separado con la "
            "misma escala vertical, para que la comparación entre paneles sea directa.", esp=3)
    fechas = [f for f in d["fechas"] if any(f in var[x["clave"]] for x in items)]
    series = [(x["clave"], [var[x["clave"]].get(f) for f in fechas], COLORES[i % 5] if not x["indice"] else NEGRO) for i, x in enumerate(items)]
    todos = [v for _, vs, _ in series for v in vs if v is not None]
    rango = (min(todos), max(todos))
    y = _grafica(pdf, ML, pdf.get_y(), ANCHO, 64, series, fechas, "Variación diaria de las cinco acciones y del IPC (%)", rango=rango, leyenda=True, grosor=0.25)
    y += 4
    for i, x in enumerate(items):
        col, ren = i % 2, i // 2
        _grafica(pdf, ML + col * (ANCHO / 2 + 2), y + ren * 34, ANCHO / 2 - 2, 30,
                 [(x["clave"], [var[x["clave"]].get(f) for f in fechas], COLORES[i % 5] if not x["indice"] else NEGRO)], fechas,
                 f"{x['clave']} · desviación estándar {x['stats']['desv']:.2f} %", rango=rango, grosor=0.3, fechas_n=2)
    pdf.set_y(y + 3 * 34 + 2)
    orden = sorted(items, key=lambda x: -x["stats"]["desv"])
    pico = max(((x, f, v) for x in items for f, v in var[x["clave"]].items()), key=lambda t: abs(t[2]))
    _p(pdf, f"Los paneles más anchos son los de {orden[0]['clave']} y {orden[1]['clave']}, con desviación estándar de {orden[0]['stats']['desv']:.2f} % y "
            f"{orden[1]['stats']['desv']:.2f} %; los más estrechos, los de {orden[-2]['clave']} y {orden[-1]['clave']}. La escala de los seis paneles la fija el "
            f"salto de {pico[0]['clave']} del {R.fecha_corta(pico[1])}, de {pico[2]:+.2f} % en un solo día.", size=9, alto=4.6, color=GRIS)


def _estadistica(pdf, d, acc, ipc, var):
    items = acc + [ipc]
    _pagina(pdf, "Estadística de los rendimientos", "Estadística de los rendimientos", 6)
    _p(pdf, "Todas las medidas salen de la columna de variación diaria, con las definiciones que usa Excel para una muestra. El rendimiento "
            "efectivo se calcula con los precios inicial y final, no con el promedio de las variaciones.", size=9.4, alto=4.7, esp=2)
    y = pdf.get_y()
    pdf.set_fill_color(*GUINDA_SUAVE)
    pdf.rect(ML, y, ANCHO, 17, "F")
    for i, (etq, fo) in enumerate((("Variación diaria", "ra"), ("Rendimiento efectivo", "re"), ("Rendimiento promedio", "rprom"))):
        x0 = ML + i * ANCHO / 3
        pdf.set_xy(x0, y + 1.6)
        pdf.set_font("Barlow", "B", 7.6)
        pdf.set_text_color(*GUINDA)
        pdf.cell(ANCHO / 3, 3.6, etq, align="C")
        w, _h = EJ._tam_formula(fo, 0.028)
        EJ._formula(pdf, fo, x0 + (ANCHO / 3 - w) / 2, y + 11, 0.028)
    pdf.set_y(y + 20)
    e = lambda it, k: it["stats"][k]
    filas = [["Precio o nivel inicial"] + [_n(x["pi"]) for x in items],
             ["Precio o nivel final"] + [_n(x["pf"]) for x in items],
             ["Rendimiento efectivo (%)"] + [_n(x["efectivo"], True) for x in items],
             ["Rendimiento promedio diario (%)"] + [_n(e(x, "media"), True, 4) for x in items],
             ["Error típico"] + [_n(e(x, "error"), False, 4) for x in items],
             ["Mediana"] + [_n(e(x, "mediana"), True, 4) for x in items],
             ["Moda"] + [(_n(e(x, "moda"), True, 4) if e(x, "moda") is not None else "No se repite") for x in items],
             ["Desviación estándar"] + [_n(e(x, "desv"), False, 4) for x in items],
             ["Varianza de la muestra"] + [_n(e(x, "var"), False, 4) for x in items],
             ["Curtosis"] + [_n(e(x, "curtosis"), True, 4) for x in items],
             ["Coeficiente de asimetría"] + [_n(e(x, "asimetria"), True, 4) for x in items],
             ["Rango"] + [_n(e(x, "rango"), False, 4) for x in items],
             ["Mínimo (%)"] + [_n(e(x, "min"), True) for x in items],
             ["Máximo (%)"] + [_n(e(x, "max"), True) for x in items],
             ["Suma (%)"] + [_n(e(x, "suma"), True) for x in items],
             ["Días trabajados"] + [str(e(x, "n")) for x in items],
             ["Suma de (Ra - Rprom)²"] + [_n(x["sumdif2"]) for x in items]]
    est = {(2, j + 1): _color(x["efectivo"]) for j, x in enumerate(items)}
    est.update({(3, j + 1): _color(e(x, "media")) for j, x in enumerate(items)})
    _tabla(pdf, ["Medida"] + [x["clave"] for x in items], filas, (50, 21.6, 21.6, 21.6, 21.6, 21.6, 21.6),
           ["LEFT"] + ["RIGHT"] * len(items), est, size=7.8, alto=3.7, y=pdf.get_y(), pad=0.6)
    pdf.ln(3)
    junta = lambda L: " y ".join([", ".join(L[:-1]), L[-1]]) if len(L) > 1 else (L[0] if L else "ninguno")
    med = sorted(items, key=lambda x: e(x, "media"))
    vol = sorted(items, key=lambda x: e(x, "desv"))
    k_med = sum(1 for x in items if e(x, "mediana") > e(x, "media"))
    k_cur = sum(1 for x in items if (e(x, "curtosis") or 0) > 0)
    k_asi = sum(1 for x in items if (e(x, "asimetria") or 0) < 0)
    n_moda = sum(1 for x in items if e(x, "moda") is not None)
    rmax = max(items, key=lambda x: e(x, "rango"))
    _sub(pdf, "Cómo se lee la tabla", esp=0)
    T = dict(size=9, alto=4.5, esp=1.6)
    _p(pdf, f"El rendimiento promedio diario va de {e(med[0], 'media'):+.4f} % en {med[0]['clave']} a {e(med[-1], 'media'):+.4f} % en {med[-1]['clave']}: "
            f"describe el día típico, mientras que el efectivo encadena los {e(med[-1], 'n')} días del periodo. El error típico de {med[-1]['clave']} "
            f"({e(med[-1], 'error'):.4f}) es del tamaño de su propia media, así que con nueve meses el promedio diario no basta para afirmar que una acción "
            "gana más que otra.", **T)
    if k_med * 2 >= len(items):
        t_med = f"En {k_med} de los {len(items)} activos la mediana queda arriba de la media: unas pocas sesiones muy malas jalaron el promedio hacia abajo."
    else:
        t_med = f"En {len(items) - k_med} de los {len(items)} activos la media queda arriba de la mediana: unas pocas sesiones muy buenas levantaron el promedio."
    _p(pdf, t_med + (f" Solo {n_moda} activos repiten una variación exacta, así que la moda casi no aporta." if n_moda else
                     " Ningún activo repite una variación exacta, por eso la moda no aporta."), **T)
    _p(pdf, f"La desviación estándar mide el riesgo: {vol[0]['clave']} se movió {e(vol[0], 'desv'):.2f} % al día y {vol[-1]['clave']} {e(vol[-1], 'desv'):.2f} %, "
            f"{e(vol[-1], 'desv') / e(vol[0], 'desv'):.1f} veces más. La varianza es la misma idea al cuadrado, y el rango más amplio es el de {rmax['clave']}, "
            f"{e(rmax, 'rango'):.2f} puntos entre su peor y su mejor día.", **T)
    neg = [x["clave"] for x in items if (e(x, "asimetria") or 0) < 0]
    _p(pdf, ("La curtosis es positiva en los " + str(len(items)) if k_cur == len(items) else f"La curtosis es positiva en {k_cur} de los {len(items)}") +
            " activos, así que los días extremos fueron más frecuentes que en una distribución normal. La asimetría es positiva en "
            f"{len(items) - k_asi}, donde las subidas extremas superaron a las caídas extremas; en {junta(neg)} pasó lo contrario. La última fila, "
            "la suma de (Ra - Rprom)², dividida entre los días menos uno da la varianza de la muestra.", **T)


def _conclusion(pdf, d, acc, ipc, sp, fichas_):
    _pagina(pdf, "Conclusión y toma de decisión", "Conclusión y toma de decisión", 7)
    filas, est, dec = [], {}, {}
    for i, it in enumerate(acc):
        f = fichas_[it["clave"]]
        b = f["betas"].get("S&P 500")
        dif = it["efectivo"] - sp["efectivo"]
        d_, c_ = _decision(it, sp, f)
        dec[it["clave"]] = (d_, dif, b, f)
        filas.append([it["clave"], _n(it["efectivo"], True), _n(dif, True), _n(it["stats"]["desv"]), _n(f["vol"]),
                      _n(b["beta"]) if b else "s/d", _n(it["stats"]["media"] / it["stats"]["desv"], False, 3), d_])
        est[(i, 1)] = _color(it["efectivo"])
        est[(i, 2)] = _color(dif)
        est[(i, 7)] = c_
    NUM = {0: "ninguna", 1: "una", 2: "dos", 3: "tres", 4: "cuatro", 5: "las cinco"}
    arriba = sum(1 for x in acc if x["efectivo"] > max(sp["efectivo"], ipc["efectivo"]))
    abajo = sum(1 for x in acc if x["efectivo"] < min(sp["efectivo"], ipc["efectivo"]))
    _p(pdf, f"En el periodo analizado el S&P 500 rindió {sp['efectivo']:+.2f} % y el IPC {ipc['efectivo']:+.2f} %. Contra esas dos referencias, "
            f"{NUM[arriba]} de las cinco acciones quedaron arriba de ambas y {NUM[abajo]} abajo de ambas. La tabla reúne el resultado y el riesgo de cada una, "
            "y la última columna es la decisión que sale de ellos.", size=9.4, alto=4.7, esp=2)
    y = _tabla(pdf, ["Acción", "Rendimiento efectivo (%)", "Diferencia con el S&P 500 (pts)", "Desviación diaria (%)", "Volatilidad anual (%)", "Beta S&P 500", "Rend. / riesgo", "Decisión"],
               filas, (18, 26, 28, 24, 24, 20, 20, 22), ["LEFT"] + ["RIGHT"] * 6 + ["CENTER"], est, size=8, alto=4.4, y=pdf.get_y(), pad=0.7)
    pdf.set_y(y + 3)
    _p(pdf, "La regla: si la acción rindió más que el S&P 500 y su volatilidad anual es baja o media (menor a 35 %), comprar; si rindió más con "
            "volatilidad alta, mantener; si quedó debajo del índice, vender. Comparo contra el S&P 500 porque las cinco cotizan en dólares. La beta dice "
            "cuánto se mueve la acción por cada punto del índice, y rendimiento entre riesgo es el promedio diario dividido entre la desviación estándar.",
       size=9.4, alto=4.7, esp=2)
    beta_max = max(acc, key=lambda x: (dec[x["clave"]][2] or {}).get("beta") or -9)["clave"]
    for it in acc:
        d_, dif, b, f = dec[it["clave"]]
        if b and b["beta"] > 1.3 and it["clave"] == beta_max:
            com = f"Es la más sensible al mercado del grupo: por cada punto que se movió el S&P 500, ella se movió {b['beta']:.2f}."
        elif b and b["beta"] < 0:
            com = "Se movió al revés del índice durante buena parte del periodo, así que amortigua una cartera cargada de tecnología."
        elif b and b["beta"] > 1.3:
            com = f"También amplifica al mercado, aunque menos: {b['beta']:.2f} puntos por cada uno del S&P 500, así que una caída del índice le pega más fuerte que al promedio."
        elif b and b["beta"] > 0.8:
            com = "Se mueve casi al mismo ritmo que el mercado."
        else:
            com = "Su precio dependió más de lo suyo que del mercado en general."
        peor, mejor = min(it["ra"]), max(it["ra"])
        fpeor = it["serie"][it["ra"].index(peor) + 1][0]
        fmejor = it["serie"][it["ra"].index(mejor) + 1][0]
        com += f" Su peor día fue el {R.fecha_corta(fpeor)} ({peor:+.2f} %) y el mejor el {R.fecha_corta(fmejor)} ({mejor:+.2f} %)."
        pdf.set_x(ML)
        pdf.set_font("Barlow", "B", 9.2)
        pdf.set_text_color(*GUINDA)
        pdf.cell(29, 4.5, f"{it['clave']} · {d_}")
        pdf.set_font("Barlow", "", 9.2)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(ANCHO - 29, 4.5, f"Rindió {it['efectivo']:+.2f} %, {abs(dif):.2f} puntos {'arriba' if dif > 0 else 'abajo'} del S&P 500, con una volatilidad anual "
                                        f"de {f['vol']:.2f} % ({f['nivel']}) y una beta de {b['beta']:.2f}. {com}", new_x="LMARGIN", new_y="NEXT", align="J")
        pdf.ln(1.2)
    comprar = [x["clave"] for x in acc if dec[x["clave"]][0] == "Comprar"]
    mantener = [x["clave"] for x in acc if dec[x["clave"]][0] == "Mantener"]
    vender = [x["clave"] for x in acc if dec[x["clave"]][0] == "Vender"]
    junta = lambda L: " y ".join([", ".join(L[:-1]), L[-1]]) if len(L) > 1 else (L[0] if L else "ninguna")
    _sub(pdf, "Decisión final", esp=1)
    texto = (f"Con estos números armaría la cartera alrededor de {junta(comprar)}: le ganaron al índice sin pedir a cambio la volatilidad de las demás. " if comprar else "")
    if mantener:
        texto += f"Dejaría {junta(mantener)} como posición secundaria, porque el rendimiento está, pero viene con oscilaciones diarias más grandes. "
    peores = sorted(acc, key=lambda x: -x["stats"]["desv"])[:len(vender)]
    extra = " y además fueron las más volátiles del grupo, la peor combinación posible" if {x["clave"] for x in peores} == set(vender) else ""
    texto += f"Y saldría de {junta(vender)}: perdieron frente al índice{extra}."
    _p(pdf, texto, size=9.4, alto=4.7, esp=1.6)
    _p(pdf, f"El límite del ejercicio: son {acc[0]['stats']['n']} días de un solo periodo y la estadística describe lo que ya pasó. Para invertir en serio "
            "habría que repetirlo en varios periodos, revisar los estados financieros completos y considerar el tipo de cambio, que para un inversionista "
            "mexicano cambia el resultado de cualquier acción comprada en dólares.", size=9.4, alto=4.7, esp=1.6)
    _p(pdf, "Fuentes: Yahoo Finance (precios de cierre) y Securities and Exchange Commission, EDGAR (datos y cifras de las empresas).",
       size=8.6, alto=4.4, color=GRIS)


def _armar(d, paginas):
    acc, ipc, sp, fichas_, guia = _contexto(d)
    var = _variaciones(d)
    pdf = _doc()
    _caratula(pdf, d, acc, ipc)
    reg = {}
    pasos = [(SECCIONES[0], lambda: _indice_intro(pdf, d, paginas, acc, ipc, sp)),
             (SECCIONES[1], lambda: _activos(pdf, d, acc, ipc, fichas_)),
             (SECCIONES[2], lambda: _emisoras(pdf, d, acc, fichas_, guia)),
             (SECCIONES[3], lambda: _tabla_variaciones(pdf, d, acc, ipc, var)),
             (SECCIONES[4], lambda: _graficas(pdf, d, acc, ipc, var)),
             (SECCIONES[5], lambda: _estadistica(pdf, d, acc, ipc, var)),
             (SECCIONES[6], lambda: _conclusion(pdf, d, acc, ipc, sp, fichas_))]
    for nombre, fn in pasos:
        reg[nombre] = pdf.page_no() + 1
        fn()
        if pdf.get_y() > H - 19:
            pdf.desbordes.append((nombre, round(pdf.get_y(), 1)))
    if pdf.desbordes:
        print("[AVISO] secciones que no caben en su hoja:", pdf.desbordes)
    return bytes(pdf.output()), reg


def trabajo(d):
    """Documento completo en dos pasadas, para que el índice traiga las páginas correctas."""
    _, reg = _armar(d, {})
    salida, reg2 = _armar(d, reg)
    return _armar(d, reg2)[0] if reg2 != reg else salida
