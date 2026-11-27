"""Trabajo escrito del ejercicio de rendimientos, en 8 hojas tamaño carta: carátula; índice e introducción;
características de los activos; las emisoras; tabla de variaciones diarias; gráficas; estadística; conclusión.

Usa los mismos datos que `ejercicio.preparar()`. Se arma en dos pasadas: la primera registra en qué hoja quedó
cada apartado y la segunda escribe el índice. Si un apartado no cabe en su hoja, avisa al generar.
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
PIE = H - 19
GUINDA, NEGRO, GRIS, BLANCO = EJ.GUINDA, EJ.NEGRO, EJ.GRIS, EJ.BLANCO
GUINDA_SUAVE, GRIS_SUAVE = EJ.GUINDA_SUAVE, EJ.GRIS_SUAVE
SUBE, BAJA, COLORES = EJ.SUBE, EJ.BAJA, EJ.COLORES
TINTA_SUBE, TINTA_BAJA = (222, 240, 230), (249, 226, 223)
AUTOR, ASESOR, INTEGRANTES = EJ.AUTOR, EJ.ASESOR, EJ.INTEGRANTES
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
SECCIONES = ["Introducción y objetivo de aprendizaje", "Características de los activos", "Las emisoras",
             "Variación porcentual diaria", "Gráficas de las variaciones", "Estadística de los rendimientos",
             "Conclusión y toma de decisión"]


def _flarga(f):
    x = datetime.strptime(f, "%Y-%m-%d").date()
    return f"{x.day} de {MESES[x.month - 1]} de {x.year}"


class _Doc(FPDF):
    seccion = ""

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*GUINDA)
        self.rect(0, 0, 6, H, "F")
        self.set_draw_color(*GRIS_SUAVE)
        self.set_line_width(0.2)
        self.line(ML, 17, W - ML, 17)
        self.set_xy(ML, 11.5)
        self.set_font("Barlow", "B", 7.6)
        self.set_text_color(*GUINDA)
        self.cell(ANCHO - 60, 4.5, "RENDIMIENTO DE CINCO ACCIONES FRENTE AL IPC")
        self.set_xy(ML, self.t_margin)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-13)
        self.set_font("Barlow", "", 7.4)
        self.set_text_color(*GRIS)
        self.set_x(ML)
        self.cell(ANCHO - 20, 4, "Seminario de Titulación · Escuela Superior de Economía, IPN")
        self.set_font("Barlow", "B", 8.4)
        self.set_text_color(*GUINDA)
        self.cell(20, 4, f"{self.page_no()}", align="R")


def _doc():
    pdf = _Doc(orientation="P", format=(W, H))
    pdf.desbordes = []
    for est, arch in (("", "Barlow-Regular"), ("B", "Barlow-Bold"), ("I", "Barlow-Italic")):
        pdf.add_font("Barlow", est, str(R.FUENTES_TTF / f"{arch}.ttf"))
    pdf.add_font("BarlowC", "B", str(R.FUENTES_TTF / "BarlowSemiCondensed-Bold.ttf"))
    pdf.set_margins(ML, 24, ML)
    pdf.set_auto_page_break(False)
    return pdf


# ------------------------------------------------------------------------------ piezas de composición
def _pagina(pdf, seccion, numero, titular):
    """Apertura de cada hoja: rótulo con número y apartado, y un titular que dice lo que muestra la hoja."""
    pdf.seccion = seccion
    pdf.add_page()
    pdf.set_xy(ML, 25)
    pdf.set_font("Barlow", "B", 8.4)
    pdf.set_text_color(*GUINDA)
    pdf.cell(ANCHO, 4.6, (f"{numero:02d}    " if numero else "") + seccion.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.4)
    pdf.set_x(ML)
    pdf.set_font("BarlowC", "B", 19.5)
    pdf.set_text_color(*NEGRO)
    pdf.multi_cell(ANCHO, 8.4, titular, new_x="LMARGIN", new_y="NEXT", align="L")
    y = pdf.get_y() + 2.4
    pdf.set_draw_color(*GUINDA)
    pdf.set_line_width(0.9)
    pdf.line(ML, y, ML + 16, y)
    pdf.set_y(y + 4.6)


def _sub(pdf, texto, esp=3, x=None, ancho=None):
    pdf.ln(esp)
    pdf.set_x(x or ML)
    pdf.set_font("Barlow", "B", 10.6)
    pdf.set_text_color(*NEGRO)
    pdf.cell(ancho or ANCHO, 5.6, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.8)


def _p(pdf, texto, size=9.8, alto=4.9, color=None, italic=False, ancho=None, esp=2.2, x=None):
    pdf.set_x(x or ML)
    pdf.set_font("Barlow", "I" if italic else "", size)
    pdf.set_text_color(*(color or NEGRO))
    pdf.multi_cell(ancho or ANCHO, alto, texto, new_x="LEFT", new_y="NEXT", align="J")
    pdf.set_x(ML)
    pdf.ln(esp)


def _n(x, signo=False, dec=2):
    if x is None:
        return "-"
    return f"{x:+,.{dec}f}" if signo else f"{x:,.{dec}f}"


def _color(x):
    return SUBE if (x or 0) > 0 else BAJA if (x or 0) < 0 else NEGRO


def _junta(L, vacio="ninguna"):
    return " y ".join([", ".join(L[:-1]), L[-1]]) if len(L) > 1 else (L[0] if L else vacio)


def _tabla(pdf, cols, filas, anchos, aligns=None, estilos=None, size=8.4, alto=4.2, y=None, pad=0.8, x=None, ancho=None):
    """Tabla con encabezado guinda, filas alternadas y líneas finas. Devuelve la y final."""
    ancho = ancho or ANCHO
    aligns = aligns or ["LEFT"] + ["RIGHT"] * (len(cols) - 1)
    k = ancho / sum(anchos)
    anchos = tuple(a * k for a in anchos)
    if y:
        pdf.set_y(y)
    pdf.set_left_margin(x or ML)
    pdf.set_x(x or ML)
    pdf.set_font("Barlow", "", size)
    pdf.set_text_color(*NEGRO)
    pdf.set_draw_color(*GRIS_SUAVE)
    pdf.set_fill_color(*BLANCO)
    with pdf.table(col_widths=anchos, text_align=aligns, line_height=alto, borders_layout="HORIZONTAL_LINES",
                   headings_style=R.FontFace(emphasis="BOLD", color=BLANCO, fill_color=GUINDA),
                   cell_fill_color=GUINDA_SUAVE, cell_fill_mode="ROWS", padding=(pad, 1.6, pad, 1.6),
                   width=ancho, align="LEFT") as t:
        r = t.row()
        for c in cols:
            r.cell(c)
        for i, f in enumerate(filas):
            r = t.row()
            for j, v in enumerate(f):
                st = (estilos or {}).get((i, j))
                r.cell(str(v), style=st if isinstance(st, R.FontFace) else (R.FontFace(color=st) if st else None))
    pdf.set_left_margin(ML)
    return pdf.get_y()


def _trazo(pdf, x, y, w, h, valores, color, grosor=0.4, lim=None):
    """Línea simple escalada a su propio mínimo y máximo (o a lim). Devuelve la función de escala vertical."""
    vs = [v for v in valores if v is not None]
    lo, hi = lim or (min(vs), max(vs))
    hi = hi if hi > lo else lo + 1
    py = lambda v: y + h - (v - lo) / (hi - lo) * h
    n = len(valores)
    pdf.set_draw_color(*color)
    pdf.set_line_width(grosor)
    prev = None
    for i, v in enumerate(valores):
        if v is None:
            prev = None
            continue
        p = (x + i / max(1, n - 1) * w, py(v))
        if prev:
            pdf.line(*prev, *p)
        prev = p
    return py


def _ejes(pdf, x0, y0, w, h, lo, hi, n_ticks=4, fmt="{:g}"):
    marcas = EJ._ticks(lo, hi, n_ticks)
    lo, hi = marcas[0], marcas[-1]
    py = lambda v: y0 + h - (v - lo) / (hi - lo) * h
    pdf.set_font("Barlow", "", 6.4)
    for v in marcas:
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.set_line_width(0.1)
        pdf.line(x0, py(v), x0 + w, py(v))
        pdf.set_text_color(*GRIS)
        pdf.set_xy(x0 - 10.5, py(v) - 1.6)
        pdf.cell(9.5, 3.2, fmt.format(v), align="R")
    if lo < 0 < hi:
        pdf.set_draw_color(*GRIS)
        pdf.set_line_width(0.25)
        pdf.line(x0, py(0), x0 + w, py(0))
    return lo, hi, py


def _fechas_eje(pdf, x0, y, w, fechas, n=3):
    pdf.set_font("Barlow", "", 6.4)
    pdf.set_text_color(*GRIS)
    idx = (0, len(fechas) - 1) if n == 2 else (0, len(fechas) // 2, len(fechas) - 1)
    for i in idx:
        xx = x0 + i / max(1, len(fechas) - 1) * w
        pdf.set_xy(min(max(xx - 9, x0 - 2), x0 + w - 16), y)
        pdf.cell(18, 3.2, R.fecha_corta(fechas[i]), align="C")


# ------------------------------------------------------------------------------ datos de apoyo
def _variaciones(d):
    """Por instrumento, {fecha: variación porcentual frente a su cierre anterior}."""
    return {it["clave"]: {it["serie"][i + 1][0]: v for i, v in enumerate(it["ra"])} for it in d["items"]}


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
    return ("Comprar", SUBE) if f["vol"] < 35 else ("Mantener", GRIS)


def _color_activo(i, it):
    return NEGRO if it["indice"] else COLORES[i % 5]


# ------------------------------------------------------------------------------ 1. carátula
def _caratula(pdf, d, acc, ipc):
    pdf.add_page()
    alto_g = 176
    pdf.set_fill_color(*GUINDA)
    pdf.rect(0, 0, W, alto_g, "F")
    pdf.image(str(R.MARCA / "ipn-escudo-blanco.png"), x=ML, y=14, h=30)
    pdf.set_fill_color(*BLANCO)
    pdf.ellipse(W - ML - 29, 14.5, 29, 29, "F")
    pdf.image(str(R.MARCA / "ese-escudo.png"), x=W - ML - 27.3, y=16.2, w=25.6, h=25.6)
    pdf.set_text_color(*BLANCO)
    for y, txt, fnt, sz in ((18, "INSTITUTO POLITÉCNICO NACIONAL", "B", 13.5), (25.5, "ESCUELA SUPERIOR DE ECONOMÍA", "B", 10.5),
                            (32, "Seminario de Titulación", "", 9.6)):
        pdf.set_xy(ML + 34, y)
        pdf.set_font("Barlow", fnt, sz)
        pdf.cell(110, 6, txt)
    pdf.set_xy(ML, 71)
    pdf.set_font("BarlowC", "B", 36)
    pdf.set_text_color(*BLANCO)
    pdf.multi_cell(ANCHO, 14, "Rendimiento de cinco\nacciones frente al IPC", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(ML)
    pdf.set_font("Barlow", "", 11.5)
    pdf.set_text_color(240, 220, 230)
    pdf.cell(ANCHO, 7, f"Apple, Microsoft, NVIDIA, Tesla y Coca-Cola · {_flarga(d['inicio'])} al {_flarga(d['ultimo'])}")
    # trazo del rendimiento acumulado de los seis activos, en blanco sobre guinda
    items = acc + [ipc]
    ac = {x["clave"]: EJ._acumulado(d, x) for x in items}
    todos = [v for x in items for v in ac[x["clave"]] if v is not None]
    gx, gy, gw, gh = ML, 118, ANCHO - 30, 46
    lo, hi = min(todos), max(todos)
    py = lambda v: gy + gh - (v - lo) / (hi - lo) * gh
    with pdf.local_context(stroke_opacity=0.35):
        pdf.set_draw_color(*BLANCO)
        pdf.set_line_width(0.2)
        pdf.line(gx, py(0), gx + gw, py(0))
    for x in items:
        with pdf.local_context(stroke_opacity=0.5 if x["indice"] else 0.95):
            _trazo(pdf, gx, gy, gw, gh, ac[x["clave"]], BLANCO, 0.45 if not x["indice"] else 0.35, lim=(lo, hi))
    finales = sorted(((ac[x["clave"]][-1], x["clave"]) for x in items), reverse=True)
    usadas = []
    for v, c in finales:
        yy = py(v) - 1.6
        while any(abs(yy - u) < 3.4 for u in usadas):
            yy += 3.4
        usadas.append(yy)
        pdf.set_xy(gx + gw + 2, yy)
        pdf.set_font("Barlow", "B", 7)
        pdf.set_text_color(*BLANCO)
        pdf.cell(28, 3.2, f"{c} {v:+.1f} %")
    pdf.set_xy(gx, gy + gh + 2)
    pdf.set_font("Barlow", "", 7)
    pdf.set_text_color(232, 196, 214)
    pdf.cell(gw, 3.4, "Rendimiento acumulado en el periodo, en porcentaje")
    # quienes presentan
    y = alto_g + 12
    pdf.set_xy(ML, y)
    pdf.set_font("Barlow", "B", 7.8)
    pdf.set_text_color(*GUINDA)
    pdf.cell(100, 4, "PRESENTAN", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.6)
    for nombre in INTEGRANTES:
        pdf.set_x(ML)
        pdf.set_font("Barlow", "B", 10.6)
        pdf.set_text_color(*NEGRO)
        pdf.cell(110, 5.6, nombre, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3.4)
    pdf.set_x(ML)
    pdf.set_font("Barlow", "B", 7.8)
    pdf.set_text_color(*GUINDA)
    pdf.cell(100, 4, "ASESOR", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(ML)
    pdf.set_font("Barlow", "B", 10.6)
    pdf.set_text_color(*NEGRO)
    pdf.cell(110, 5.6, ASESOR)
    pdf.set_xy(W - ML - 70, y)
    pdf.set_font("Barlow", "B", 7.8)
    pdf.set_text_color(*GUINDA)
    pdf.cell(70, 4, "LICENCIATURA EN ECONOMÍA", align="R")
    pdf.set_font("Barlow", "", 10)
    pdf.set_text_color(*GRIS)
    for k, t in enumerate(("Ciudad de México",)):
        pdf.set_xy(W - ML - 70, y + 4.6 + k * 5.6)
        pdf.cell(70, 5.6, t, align="R")


# ------------------------------------------------------------------------------ 2. índice e introducción
def _indice_intro(pdf, d, paginas, acc, ipc, sp):
    _pagina(pdf, "Índice e introducción", 0, "Índice")
    y = pdf.get_y()
    col_w = (ANCHO - 10) / 2
    for i, nombre in enumerate(SECCIONES):
        c, r = i // 4, i % 4
        x, yy = ML + c * (col_w + 10), y + r * 6.4
        pdf.set_xy(x, yy)
        pdf.set_font("BarlowC", "B", 10)
        pdf.set_text_color(*GUINDA)
        pdf.cell(8, 5.6, f"{i + 1:02d}")
        pdf.set_font("Barlow", "", 9.6)
        pdf.set_text_color(*NEGRO)
        tw = pdf.get_string_width(nombre)
        pdf.cell(tw + 2, 5.6, nombre)
        pdf.set_draw_color(*GRIS_SUAVE)
        pdf.set_line_width(0.2)
        pdf.line(x + 10 + tw + 1, yy + 4.1, x + col_w - 7, yy + 4.1)
        pdf.set_xy(x + col_w - 6, yy)
        pdf.set_font("Barlow", "B", 9.6)
        pdf.set_text_color(*GUINDA)
        pdf.cell(6, 5.6, str(paginas.get(nombre, "")), align="R")
    pdf.set_y(y + 4 * 6.4 + 5)
    pdf.set_x(ML)
    pdf.set_font("BarlowC", "B", 17)
    pdf.set_text_color(*GUINDA)
    pdf.cell(ANCHO, 9, "Introducción", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.6)
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    pdf.set_x(ML)
    pdf.set_font("Barlow", "B", 12)
    pdf.set_text_color(*GUINDA)
    pdf.multi_cell(ANCHO, 5.8, f"En {acc[0]['stats']['n']} días de mercado, {mejor['nombre']} ganó {mejor['efectivo']:+.2f} % y {peor['nombre']} perdió "
                               f"{abs(peor['efectivo']):.2f} %, mientras el IPC apenas se movió {ipc['efectivo']:+.2f} %.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2.4)
    _p(pdf, "En el seminario se vio cómo leer la pizarra de precios de una acción, cómo calcular su variación y su rendimiento y cómo describirlos con "
            "estadística. Este trabajo aplica esos cálculos a datos reales y al periodo completo: el último hecho de cinco acciones que cotizan en Estados "
            "Unidos, Apple, Microsoft, NVIDIA, Tesla y "
            f"Coca-Cola, del {_flarga(d['inicio'])} al {_flarga(d['ultimo'])}, comparado con el S&P/BMV IPC de la Bolsa Mexicana de Valores.")
    _p(pdf, "De cada día se calculó la variación porcentual frente al último hecho del día anterior, y de esa columna salen el rendimiento promedio, la "
            "dispersión y la distancia de cada día respecto a su promedio. El rendimiento efectivo se calcula aparte, con el primer y el último precio, "
            "porque mide lo que ganó o perdió quien compró al inicio y vendió al final. No descuenta comisiones; con la comisión máxima de 1.0 % más IVA "
            "que marcan las láminas para la renta variable, el resultado neto de quien compra y vende sería algo menor.")
    _p(pdf, "Los precios vienen de Yahoo Finance y los datos de cada empresa, de los reportes anuales que entregan a la Securities and Exchange Commission. "
            "La comparación tiene un detalle, las acciones cotizan en dólares y el IPC en pesos, por lo que una parte de la diferencia es tipo de cambio. "
            f"Por ello también se usa el S&P 500, que en el mismo periodo rindió {sp['efectivo']:+.2f} %.")
    pdf.ln(2)
    pdf.set_x(ML)
    pdf.set_font("BarlowC", "B", 17)
    pdf.set_text_color(*GUINDA)
    pdf.cell(ANCHO, 9, "Objetivo de aprendizaje", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    _p(pdf, "Aplicar a datos reales las fórmulas de rendimiento y de estadística descriptiva vistas en el seminario, y llegar con ellas a una decisión de "
            "inversión que se pueda defender con números. En concreto:", esp=1.4)
    puntos = ["Calcular la variación porcentual diaria de cada acción y del índice, y ordenarlas en una sola tabla.",
              "Obtener el rendimiento efectivo del periodo y el rendimiento promedio diario, y distinguir para qué sirve cada uno.",
              "Medir la dispersión con desviación estándar, varianza, rango, curtosis y coeficiente de asimetría, y leer qué dice cada una sobre el riesgo.",
              "Comparar cada acción contra el índice y decidir con esos números cuál comprar, cuál mantener y cuál vender."]
    for i, t in enumerate(puntos, 1):
        y = pdf.get_y()
        pdf.set_fill_color(*GUINDA)
        pdf.ellipse(ML + 0.4, y + 0.6, 4, 4, "F")
        pdf.set_xy(ML + 0.4, y + 0.6)
        pdf.set_font("Barlow", "B", 7.4)
        pdf.set_text_color(*BLANCO)
        pdf.cell(4, 4, str(i), align="C")
        pdf.set_xy(ML + 7, y)
        pdf.set_font("Barlow", "", 9.6)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(ANCHO - 7, 4.9, t, new_x="LMARGIN", new_y="NEXT", align="J")
        pdf.ln(1.2)


# ------------------------------------------------------------------------------ 3. características de los activos
def _multiplos(it, f):
    """Valor en libros, P/VL, UPA y P/U como se definen en las láminas del mercado accionario."""
    acciones = f["F"]["acciones"]
    cc = f["cif"].get("Capital contable", (None,))[0]
    upa = f["cif"].get("Utilidad por acción", (None,))[0]
    vl = cc * 1e6 / acciones if cc and acciones else None
    return {"vl": vl, "pvl": it["pf"] / vl if vl else None, "upa": upa, "pu": it["pf"] / upa if upa else None,
            "div": f["cif"].get("Dividendo por acción", (None,))[0]}


def _activos(pdf, d, acc, ipc, fichas_):
    m = {x["clave"]: _multiplos(x, fichas_[x["clave"]]) for x in acc}
    nom = {x["clave"]: x["nombre"] for x in acc}
    con_pvl = [k for k in m if m[k]["pvl"]]
    alto_v, bajo_v = max(con_pvl, key=lambda k: m[k]["pvl"]), min(con_pvl, key=lambda k: m[k]["pvl"])
    todas_prima = all(m[k]["pvl"] > 1 for k in con_pvl)
    _pagina(pdf, "Características de los activos", 2,
            "Las cinco cotizan con prima: su precio supera su valor en libros" if todas_prima else "Precio de mercado frente a valor en libros")
    _p(pdf, "Una acción es un título de crédito que representa una parte alícuota del capital social de una empresa, y su emisor siempre es una "
            "persona moral. Las cinco emisoras colocan acciones ordinarias de una sola serie, que dan derecho a recibir dividendos, a la parte "
            "proporcional en caso de liquidación, a la suscripción preferente de nuevas acciones y a votar en la asamblea de accionistas.")
    _p(pdf, "El valor nominal es la parte proporcional del capital social pagado y queda fijo en el título; en Estados Unidos se le llama valor par "
            "y Apple lo fija en una cienmilésima de dólar. El valor de mercado, en cambio, lo determinan la oferta y la demanda cada día, y el último "
            "hecho de cada sesión es el precio que se usa para calcular los rendimientos.")
    _p(pdf, "Para saber si una acción está cara frente a sus libros se usa el múltiplo precio/valor en libros (P/VL), donde el valor en libros es el "
            "capital contable entre el número de acciones. Si el P/VL es mayor que 1 la acción cotiza con prima, porque el mercado le reconoce "
            f"historia, imagen o crecimiento; si es menor que 1, cotiza con descuento. Aquí va de {m[bajo_v]['pvl']:.1f} veces en {nom[bajo_v]} a "
            f"{m[alto_v]['pvl']:.1f} en {nom[alto_v]}.")
    mm = lambda v: f"{v:,.0f}" if v is not None else "s/d"
    dd = lambda v, dec=2: f"{v:,.{dec}f}" if v is not None else "s/d"
    F = lambda x: fichas_[x["clave"]]
    filas = [
        ["Tipo de acción"] + ["Ordinaria"] * len(acc),
        ["Serie"] + ["Única"] * len(acc),
        ["Bolsa"] + [server.META[x["ticker"]]["mercado"] for x in acc],
        ["Valor nominal o par (USD)"] + [(f"{F(x)['par']:.8f}".rstrip("0").rstrip(".") if F(x)["par"] else "s/d") for x in acc],
        ["Acciones en circulación (millones)"] + [mm(F(x)["F"]["acciones"] / 1e6) for x in acc],
        ["Capital social (millones de USD)"] + [dd(F(x)["capital_social"]) for x in acc],
        ["Capital contable (millones de USD)"] + [mm(F(x)["cif"].get("Capital contable", (None,))[0]) for x in acc],
        ["Valor en libros por acción (USD)"] + [dd(m[x["clave"]]["vl"]) for x in acc],
        [f"Último hecho al {R.fecha_corta(d['ultimo'])} (USD)"] + [dd(x["pf"]) for x in acc],
        ["Precio / valor en libros (P/VL, veces)"] + [dd(m[x["clave"]]["pvl"], 1) for x in acc],
        ["Utilidad por acción, UPA (USD)"] + [dd(m[x["clave"]]["upa"]) for x in acc],
        ["Precio / utilidad (P/U, veces)"] + [dd(m[x["clave"]]["pu"], 1) for x in acc],
        ["Importe operado al día (millones de USD)"] + [mm((F(x)["burs"] or {}).get("importe")) for x in acc],
        ["Lugar por importe operado"] + [str((F(x)["burs"] or {}).get("posicion", "s/d")) for x in acc],
    ]
    est = {(9, j + 1): R.FontFace(emphasis="BOLD", color=GUINDA) for j in range(len(acc))}
    _sub(pdf, "Datos del título", esp=1.6)
    y = _tabla(pdf, ["Concepto"] + [x["clave"] for x in acc], filas, (60, 24, 24, 24, 24, 24), estilos=est, size=8.1, alto=3.9, pad=0.75, y=pdf.get_y())
    pdf.set_y(y + 1.4)
    _p(pdf, "Valores de la SEC (EDGAR), último ejercicio anual de cada empresa; UPA del ejercicio anual. La bursatilidad oficial de la BMV es un índice "
            "de 0 a 10 (nula, mínima, baja, media y alta) que combina importe negociado, número de operaciones, días operados y rotación. No se publica para "
            "emisoras de Estados Unidos y no hay dato público del número de operaciones, por eso aquí se ordenan por el importe operado al día.",
       size=7.9, alto=3.9, color=GRIS, esp=1)
    _sub(pdf, "El índice de referencia", esp=1.4)
    _p(pdf, "El IPC es el principal índice de la Bolsa Mexicana de Valores. Mide la variación de precios de una muestra de 35 emisoras de distintos "
            "sectores, elegidas por su bursatilidad y ponderadas por su valor de capitalización, y su variación diaria se calcula igual que el "
            "rendimiento de una acción: nivel de hoy entre nivel de ayer, menos uno, por cien.", size=9.2, alto=4.6, esp=1.6)
    _tabla(pdf, ["Índice", "Mercado", "Unidad", "Nivel inicial", "Nivel final", "Rendimiento (%)", "Días"],
           [["S&P/BMV IPC", "Bolsa Mexicana de Valores", "Puntos", _n(ipc["pi"]), _n(ipc["pf"]), _n(ipc["efectivo"], True), str(ipc["stats"]["n"])]],
           (32, 46, 18, 24, 24, 26, 12), ["LEFT", "LEFT", "LEFT"] + ["RIGHT"] * 4, {(0, 5): _color(ipc["efectivo"])}, size=8.3, alto=4.2, y=pdf.get_y())


# ------------------------------------------------------------------------------ 4. las emisoras
def _emisoras(pdf, d, acc, fichas_, guia):
    _pagina(pdf, "Las emisoras", 3, "Tres tecnológicas, una automotriz y una refresquera")
    _p(pdf, "Cada bloque reúne lo que debe contener el título de una acción (denominación, domicilio, constitución y objeto social) y los "
            "indicadores de la pizarra de precios: último hecho, máximo, mínimo, utilidad por acción y múltiplos.", size=9, alto=4.5, esp=2)
    for i, it in enumerate(acc):
        f = fichas_[it["clave"]]
        g = guia.get(it["ticker"], {})
        m = _multiplos(it, f)
        col = COLORES[i % 5]
        y0 = pdf.get_y()
        pdf.set_xy(ML + 4, y0)
        pdf.set_font("BarlowC", "B", 13)
        pdf.set_text_color(*col)
        pdf.cell(16, 5.6, it["clave"])
        pdf.set_font("Barlow", "B", 10.4)
        pdf.set_text_color(*NEGRO)
        pdf.cell(80, 5.6, f["F"].get("denominacion") or it["nombre"])
        pdf.set_font("Barlow", "B", 8.2)
        pdf.set_text_color(*GRIS)
        pdf.cell(ANCHO - 100, 5.6, EJ.SECTOR[it["ticker"]].upper(), align="R", new_x="LMARGIN", new_y="NEXT")
        dom = ", ".join((f["F"].get("domicilio") or "").replace(", EE. UU.", "").split(", ")[-2:])
        pdf.set_x(ML + 4)
        pdf.set_font("Barlow", "", 7.8)
        pdf.cell(ANCHO - 4, 3.8, f"{server.META[it['ticker']]['mercado']} · Domicilio: {dom} · Constitución: {EJ.CONSTITUCION[it['ticker']].split(';')[0]} · "
                                 f"{EJ.SIC_ES.get(f['sic'], f['sic']) or 's/d'} (SEC)", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)
        # objeto social a la izquierda y precio del periodo a la derecha
        yo = pdf.get_y()
        tw = ANCHO - 4 - 58
        pdf.set_xy(ML + 4, yo)
        pdf.set_font("Barlow", "", 8.5)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(tw, 4.2, "Objeto social: " + g.get("que_es", "").replace(f" Cotiza en el {server.META[it['ticker']]['mercado']}.", "")
                       .replace(" Cotiza en el Nasdaq.", "").replace(" Cotiza en la Bolsa de Nueva York (NYSE).", ""), new_x="LMARGIN", new_y="NEXT", align="J")
        y_txt = pdf.get_y()
        sx = ML + 4 + tw + 6
        pdf.set_xy(sx, yo)
        pdf.set_font("Barlow", "", 6.6)
        pdf.set_text_color(*GRIS)
        pdf.cell(52, 3, "Último hecho, 1 de marzo a 25 de noviembre")
        _trazo(pdf, sx, yo + 4, 52, 7.5, [v for _, v in it["serie"]], col, 0.45)
        pdf.set_xy(sx, yo + 12)
        pdf.set_font("Barlow", "B", 7.2)
        pdf.set_text_color(*NEGRO)
        pdf.cell(26, 3.2, f"{it['pi']:,.2f}")
        pdf.cell(26, 3.2, f"{it['pf']:,.2f}", align="R")
        pdf.set_y(max(y_txt, yo + 15.5) + 1.2)
        # indicadores de la pizarra
        yy = pdf.get_y()
        piezas = [("Último hecho", f"{it['pf']:,.2f}", NEGRO), ("Máx. / mín.", f"{it['pmax']:,.2f} / {it['pmin']:,.2f}", NEGRO),
                  ("UPA", f"{m['upa']:,.2f}" if m["upa"] else "s/d", NEGRO), ("P/U", f"{m['pu']:,.1f}" if m["pu"] else "s/d", NEGRO),
                  ("P/VL", f"{m['pvl']:,.1f}" if m["pvl"] else "s/d", NEGRO),
                  ("Dividendo por acción", f"{m['div']:,.2f}" if m["div"] else "No paga", NEGRO),
                  ("Variación del periodo", f"{it['efectivo']:+.2f} %", _color(it["efectivo"]))]
        anchos = [20, 34, 15, 15, 15, 30, 0]
        anchos[-1] = ANCHO - 4 - sum(anchos[:-1])
        x = ML + 4
        for (et, v, c), w in zip(piezas, anchos):
            pdf.set_xy(x, yy)
            pdf.set_font("Barlow", "", 6.8)
            pdf.set_text_color(*GRIS)
            pdf.cell(w, 3.2, et, align="R" if et.startswith("Variación") else "L", new_x="LEFT", new_y="NEXT")
            pdf.set_font("BarlowC" if et.startswith("Variación") else "Barlow", "B", 11 if et.startswith("Variación") else 8.8)
            pdf.set_text_color(*c)
            pdf.cell(w, 4.6, v, align="R" if et.startswith("Variación") else "L")
            x += w
        pdf.set_draw_color(*col)
        pdf.set_line_width(1.1)
        pdf.line(ML, y0 + 0.6, ML, yy + 8.2)
        pdf.set_y(yy + 10.4)
    _p(pdf, "Cifras en dólares. UPA y dividendo del último ejercicio anual reportado a la SEC; P/U y P/VL con el último hecho del 25 de noviembre.",
       size=7.6, alto=3.8, color=GRIS, esp=0)


# ------------------------------------------------------------------------------ 5. tabla de variaciones
def _tabla_variaciones(pdf, d, acc, ipc, var):
    """Todas las fechas en una hoja: la tabla se parte en tres bloques que se leen de izquierda a derecha."""
    items = acc + [ipc]
    obs = [v for x in items for v in var[x["clave"]].values()]
    tranquilos = sum(1 for v in obs if abs(v) < 3) / len(obs) * 100
    _pagina(pdf, "Variación porcentual diaria", 4, f"En {tranquilos:.0f} % de los registros la variación del día fue menor a 3 %")
    y = pdf.get_y()
    pdf.set_xy(ML, y)
    pdf.set_font("Barlow", "", 8.2)
    pdf.set_text_color(*GRIS)
    pdf.cell(118, 4.4, "Variación % = último hecho del día frente al del día anterior. Fechas de 2026. Guion: esa bolsa no operó.")
    for k, (tinta, etq) in enumerate(((TINTA_SUBE, "Subió 3 % o más"), (TINTA_BAJA, "Bajó 3 % o más"))):
        xx = ML + 122 + k * 29
        pdf.set_fill_color(*tinta)
        pdf.rect(xx, y + 0.9, 4, 2.8, "F")
        pdf.set_xy(xx + 5, y)
        pdf.cell(24, 4.4, etq)
    pdf.set_y(y + 6)
    fechas = [f for f in d["fechas"] if any(f in var[x["clave"]] for x in items)]
    bloques, sep = 3, 3.2
    por = math.ceil(len(fechas) / bloques)
    bw = (ANCHO - sep * (bloques - 1)) / bloques
    wf = 9.0
    wc = (bw - wf) / len(items)
    y0 = pdf.get_y()
    hh = 4.8
    rh = min(3.6, (PIE - y0 - hh) / por)
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
        tramo = fechas[b * por:(b + 1) * por]
        for k, f in enumerate(tramo):
            yy = y0 + hh + k * rh
            if k % 2:
                pdf.set_fill_color(250, 246, 248)
                pdf.rect(x0, yy, bw, rh, "F")
            pdf.set_xy(x0, yy)
            pdf.set_text_color(*GRIS)
            pdf.cell(wf, rh, f"{f[8:10]}/{f[5:7]}", align="C")
            for j, it in enumerate(items):
                v = var[it["clave"]].get(f)
                xc = x0 + wf + j * wc
                if v is not None and abs(v) >= 3:
                    pdf.set_fill_color(*(TINTA_SUBE if v > 0 else TINTA_BAJA))
                    pdf.rect(xc + 0.4, yy + 0.2, wc - 0.4, rh - 0.4, "F")
                pdf.set_xy(xc, yy)
                pdf.set_font("Barlow", "B" if v is not None and abs(v) >= 3 else "", 5.9)
                pdf.set_text_color(*(_color(v) if v is not None else GRIS))
                pdf.cell(wc, rh, "-" if v is None else f"{v:+.2f}", align="R")
        pdf.set_draw_color(*GUINDA)
        pdf.set_line_width(0.3)
        pdf.line(x0, y0 + hh + len(tramo) * rh, x0 + bw, y0 + hh + len(tramo) * rh)
    pdf.set_y(y0 + hh + por * rh)


# ------------------------------------------------------------------------------ 6. gráficas
def _barras_dia(pdf, x0, y0, w, h, valores, color, lim):
    """Una barra por día, hacia arriba si subió y hacia abajo si bajó. Las que pasan del límite se marcan con su valor."""
    n = len(valores)
    bw = w / n
    py = lambda v: y0 + h / 2 - v / lim * (h / 2)
    pdf.set_draw_color(*GRIS)
    pdf.set_line_width(0.15)
    pdf.line(x0, y0 + h / 2, x0 + w, y0 + h / 2)
    for i, v in enumerate(valores):
        if v is None:
            continue
        vv = max(-lim, min(lim, v))
        top, bot = sorted((py(0), py(vv)))
        pdf.set_fill_color(*(color if v >= 0 else BAJA))
        pdf.rect(x0 + i * bw + bw * 0.12, top, bw * 0.76, max(0.15, bot - top), "F")
        if abs(v) > lim:
            pdf.set_font("Barlow", "B", 6)
            pdf.set_text_color(*_color(v))
            ty = y0 if v > 0 else y0 + h - 3
            xb = x0 + i * bw
            if xb > x0 + w - 14:
                pdf.set_xy(xb - 11, ty)
                pdf.cell(10.5, 3, f"{v:+.1f}", align="R")
            else:
                pdf.set_xy(xb + bw + 0.5, ty)
                pdf.cell(10.5, 3, f"{v:+.1f}", align="L")


def _graficas(pdf, d, acc, ipc, var):
    items = acc + [ipc]
    mejor, peor = max(acc, key=lambda x: x["efectivo"]), min(acc, key=lambda x: x["efectivo"])
    _pagina(pdf, "Gráficas de las variaciones", 5, f"{mejor['nombre']} terminó con {mejor['efectivo']:+.2f} % y {peor['nombre']} con {peor['efectivo']:+.2f} %")
    _p(pdf, "Arriba, lo que suman las variaciones día con día: el rendimiento acumulado de cada activo. Abajo, la tabla anterior dibujada como barras, una "
            "por día, todas con la misma escala para poder compararlas.", size=9.2, alto=4.6, esp=1.6)
    fechas = [f for f in d["fechas"] if any(f in var[x["clave"]] for x in items)]
    # rendimiento acumulado con etiquetas al final de cada línea
    y = pdf.get_y() + 1
    pdf.set_xy(ML, y)
    pdf.set_font("Barlow", "B", 8.6)
    pdf.set_text_color(*NEGRO)
    pdf.cell(ANCHO, 4.6, "Rendimiento acumulado (%)")
    ac = {x["clave"]: EJ._acumulado(d, x) for x in items}
    ac = {k: [v for f, v in zip(d["fechas"], vs) if f in set(fechas)] for k, vs in ac.items()}
    todos = [v for vs in ac.values() for v in vs if v is not None]
    gx, gy, gw, gh = ML + 11, y + 6.5, ANCHO - 36, 56
    lo, hi, py = _ejes(pdf, gx, gy, gw, gh, min(todos), max(todos))
    for i, x in enumerate(items):
        _trazo(pdf, gx, gy, gw, gh, ac[x["clave"]], _color_activo(i, x), 0.55 if not x["indice"] else 0.5, lim=(lo, hi))
    usadas = []
    for v, i, x in sorted(((ac[x["clave"]][-1], i, x) for i, x in enumerate(items)), key=lambda t: -t[0]):
        yy = py(v) - 1.6
        while any(abs(yy - u) < 3.4 for u in usadas):
            yy += 3.4
        usadas.append(yy)
        pdf.set_xy(gx + gw + 1.5, yy)
        pdf.set_font("Barlow", "B", 7)
        pdf.set_text_color(*_color_activo(i, x))
        pdf.cell(24, 3.2, f"{x['clave']} {v:+.1f}")
    _fechas_eje(pdf, gx, gy + gh + 1, gw, fechas)
    # barras de la variación diaria, una fila por activo
    lim = 10.0
    y = gy + gh + 9
    pdf.set_xy(ML, y)
    pdf.set_font("Barlow", "B", 8.6)
    pdf.set_text_color(*NEGRO)
    pdf.cell(ANCHO, 4.6, f"Variación diaria (%), escala de -{lim:g} a +{lim:g}")
    y += 8.5
    fila_h = (PIE - 14 - y) / len(items)
    for i, x in enumerate(items):
        yy = y + i * fila_h
        pdf.set_xy(ML, yy + fila_h / 2 - 5)
        pdf.set_font("BarlowC", "B", 10.5)
        pdf.set_text_color(*_color_activo(i, x))
        pdf.cell(20, 5, x["clave"])
        pdf.set_xy(ML, yy + fila_h / 2)
        pdf.set_font("Barlow", "", 6.6)
        pdf.set_text_color(*GRIS)
        pdf.cell(20, 3.4, f"desv. {x['stats']['desv']:.2f} %")
        _barras_dia(pdf, ML + 22, yy + 1.5, ANCHO - 22, fila_h - 4.5, [var[x["clave"]].get(f) for f in fechas], _color_activo(i, x), lim)
    _fechas_eje(pdf, ML + 22, y + len(items) * fila_h - 2.4, ANCHO - 22, fechas)
    orden = sorted(items, key=lambda x: -x["stats"]["desv"])
    pdf.set_y(y + len(items) * fila_h + 2.4)
    _p(pdf, f"Las franjas más anchas son las de {orden[0]['clave']} y {orden[1]['clave']}; las más angostas, las de {orden[-2]['clave']} y {orden[-1]['clave']}. "
            "Los números junto a una barra son días que se salieron de la escala.", size=8.2, alto=4.1, color=GRIS, esp=0)


# ------------------------------------------------------------------------------ 7. estadística
def _dispersion(pdf, x0, y0, w, h, items):
    """Riesgo contra rendimiento: desviación estándar diaria en el eje horizontal, rendimiento efectivo en el vertical."""
    pdf.set_xy(x0, y0)
    pdf.set_font("Barlow", "B", 8.4)
    pdf.set_text_color(*NEGRO)
    pdf.cell(w, 4.4, "Riesgo contra rendimiento", new_x="LEFT", new_y="NEXT")
    pdf.set_font("Barlow", "", 6.8)
    pdf.set_text_color(*GRIS)
    pdf.cell(w, 3.4, "Vertical: rendimiento efectivo (%). Arriba y a la izquierda es mejor.")
    gx, gy, gw, gh = x0 + 11, y0 + 12, w - 13, h - 20
    ys = [x["efectivo"] for _, x in items]
    lo, hi, py = _ejes(pdf, gx, gy, gw, gh, min(ys + [0]), max(ys + [0]))
    xs = [x["stats"]["desv"] for _, x in items]
    xm = EJ._ticks(0, max(xs), 4)
    px = lambda v: gx + v / xm[-1] * gw
    pdf.set_font("Barlow", "", 6.4)
    pdf.set_text_color(*GRIS)
    for v in xm:
        pdf.set_xy(px(v) - 5, gy + gh + 0.8)
        pdf.cell(10, 3.2, f"{v:g}", align="C")
    pdf.set_xy(gx, gy + gh + 4.4)
    pdf.cell(gw, 3.2, "Desviación estándar diaria (%)", align="C")
    for i, x in items:
        cx, cy = px(x["stats"]["desv"]), py(x["efectivo"])
        pdf.set_fill_color(*_color_activo(i, x))
        pdf.ellipse(cx - 1.5, cy - 1.5, 3, 3, "F")
        pdf.set_xy(cx + 2, cy - 1.7)
        pdf.set_font("Barlow", "B", 7)
        pdf.set_text_color(*_color_activo(i, x))
        pdf.cell(14, 3.4, x["clave"])


def _estadistica(pdf, d, acc, ipc, var):
    items = acc + [ipc]
    vol_ = sorted(items, key=lambda x: x["stats"]["desv"])
    nombre_ = lambda x: "el IPC" if x["indice"] else x["nombre"]
    _pagina(pdf, "Estadística de los rendimientos", 6, f"{nombre_(vol_[-1]).capitalize() if vol_[-1]['indice'] else nombre_(vol_[-1])} fue "
            f"{vol_[-1]['stats']['desv'] / vol_[0]['stats']['desv']:.1f} veces más volátil que {nombre_(vol_[0])}")
    _p(pdf, "Todas las medidas salen de la columna de variación diaria, con las definiciones que usa Excel para una muestra. El rendimiento efectivo "
            "se calcula con los precios inicial y final, no con el promedio de las variaciones.", size=9.2, alto=4.6, esp=1.8)
    y = pdf.get_y()
    pdf.set_draw_color(*GRIS_SUAVE)
    pdf.set_line_width(0.25)
    pdf.line(ML, y, ML + ANCHO, y)
    pdf.line(ML, y + 16, ML + ANCHO, y + 16)
    for i, (etq, fo) in enumerate((("Variación diaria", "ra"), ("Rendimiento efectivo", "re"), ("Rendimiento promedio", "rprom"))):
        x0 = ML + i * ANCHO / 3
        pdf.set_xy(x0, y + 1.4)
        pdf.set_font("Barlow", "B", 7.4)
        pdf.set_text_color(*GUINDA)
        pdf.cell(ANCHO / 3, 3.4, etq, align="C")
        w, _h = EJ._tam_formula(fo, 0.027)
        EJ._formula(pdf, fo, x0 + (ANCHO / 3 - w) / 2, y + 10.2, 0.027)
    pdf.set_y(y + 18.5)
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
    est = {}
    for j, x in enumerate(items):
        est[(2, j + 1)] = R.FontFace(emphasis="BOLD", color=_color(x["efectivo"]))
        est[(3, j + 1)] = _color(e(x, "media"))
    j_max = max(range(len(acc)), key=lambda j: acc[j]["stats"]["desv"])
    est[(7, j_max + 1)] = R.FontFace(emphasis="BOLD", color=GUINDA)
    y = _tabla(pdf, ["Medida"] + [x["clave"] for x in items], filas, (50, 21.6, 21.6, 21.6, 21.6, 21.6, 21.6),
               ["LEFT"] + ["RIGHT"] * len(items), est, size=7.7, alto=3.5, y=pdf.get_y(), pad=0.55)
    # lectura a la izquierda, riesgo contra rendimiento a la derecha
    y += 4
    med = sorted(items, key=lambda x: e(x, "media"))
    vol = sorted(items, key=lambda x: e(x, "desv"))
    k_med = sum(1 for x in items if e(x, "mediana") > e(x, "media"))
    k_cur = sum(1 for x in items if (e(x, "curtosis") or 0) > 0)
    neg = [x["clave"] for x in items if (e(x, "asimetria") or 0) < 0]
    n_moda = sum(1 for x in items if e(x, "moda") is not None)
    tw = ANCHO - 72
    pdf.set_y(y)
    _sub(pdf, "Cómo se lee", esp=0, ancho=tw)
    T = dict(size=8.7, alto=4.3, esp=1.4, ancho=tw)
    _p(pdf, f"El promedio diario va de {e(med[0], 'media'):+.4f} % en {med[0]['clave']} a {e(med[-1], 'media'):+.4f} % en {med[-1]['clave']} y describe el "
            f"día típico, mientras que el efectivo encadena los {e(med[-1], 'n')} días. El error típico de {med[-1]['clave']} ({e(med[-1], 'error'):.4f}) es del "
            "tamaño de su media, así que el promedio diario no basta para decir que una acción gana más que otra.", **T)
    t_med = (f"En {k_med} de los {len(items)} la mediana queda arriba de la media, por unas pocas sesiones muy malas." if k_med * 2 >= len(items) else
             f"En {len(items) - k_med} de los {len(items)} la media queda arriba de la mediana, por unas pocas sesiones muy buenas.")
    _p(pdf, t_med + (" La moda casi no aporta: ningún activo repite una variación exacta." if not n_moda else f" Solo {n_moda} repiten una variación exacta."), **T)
    _p(pdf, f"{vol[-1]['clave']} se movió {e(vol[-1], 'desv'):.2f} % al día y {vol[0]['clave']} {e(vol[0], 'desv'):.2f} %, "
            f"{e(vol[-1], 'desv') / e(vol[0], 'desv'):.1f} veces menos. La curtosis es positiva en "
            + (f"los {len(items)}" if k_cur == len(items) else f"{k_cur} de los {len(items)}") +
            f": hubo más días extremos que en una distribución normal. La asimetría es negativa solo en {_junta(neg, 'ninguno')}, donde las caídas "
            "fuertes pesaron más que las subidas.", **T)
    _dispersion(pdf, ML + tw + 4, y, 68, PIE - y - 2, list(enumerate(items)))


# ------------------------------------------------------------------------------ 8. conclusión
def _diferencias(pdf, y, acc, dec):
    """Barras que salen de cero: cuánto arriba o abajo del S&P 500 quedó cada acción, con su decisión a la derecha."""
    fila, x_et, x0, w_dec = 8.2, ML, ML + 18, 30
    w = ANCHO - 18 - w_dec - 8
    m = max(abs(dec[x["clave"]][2]) for x in acc) * 1.3
    cx = x0 + w / 2
    pdf.set_xy(x0, y)
    pdf.set_font("Barlow", "", 7)
    pdf.set_text_color(*GRIS)
    pdf.cell(w / 2 - 2, 3.6, "Abajo del S&P 500", align="R")
    pdf.set_x(cx + 2)
    pdf.cell(w / 2 - 2, 3.6, "Arriba del S&P 500")
    pdf.set_xy(x0 + w + 4, y)
    pdf.cell(w_dec, 3.6, "Decisión")
    y += 5
    for i, it in enumerate(acc):
        d_, c_, dif, b, f = dec[it["clave"]]
        yy = y + i * fila
        pdf.set_xy(x_et, yy)
        pdf.set_font("BarlowC", "B", 11)
        pdf.set_text_color(*NEGRO)
        pdf.cell(16, fila - 1.6, it["clave"])
        largo = dif / m * (w / 2)
        pdf.set_fill_color(*COLORES[i % 5])
        pdf.rect(min(cx, cx + largo), yy + 1.2, abs(largo), fila - 4, "F")
        pdf.set_font("Barlow", "B", 8)
        pdf.set_text_color(*NEGRO)
        if largo >= 0:
            pdf.set_xy(cx + largo + 1.2, yy)
            pdf.cell(20, fila - 1.6, f"{dif:+.2f}")
        else:
            pdf.set_xy(cx + largo - 21.2, yy)
            pdf.cell(20, fila - 1.6, f"{dif:+.2f}", align="R")
        pdf.set_fill_color(*c_)
        pdf.ellipse(x0 + w + 4, yy + (fila - 1.6) / 2 - 1.3, 2.6, 2.6, "F")
        pdf.set_xy(x0 + w + 8, yy)
        pdf.set_font("Barlow", "B", 9)
        pdf.set_text_color(*c_)
        pdf.cell(w_dec - 4, fila - 1.6, d_)
    pdf.set_draw_color(*GRIS)
    pdf.set_line_width(0.3)
    pdf.line(cx, y - 1, cx, y + len(acc) * fila - 1)
    pdf.set_xy(x0, y + len(acc) * fila)
    pdf.set_font("Barlow", "", 7)
    pdf.set_text_color(*GRIS)
    pdf.cell(w, 3.6, "Diferencia entre el rendimiento efectivo de cada acción y el del S&P 500, en puntos porcentuales", align="C")
    return y + len(acc) * fila + 5


def _conclusion(pdf, d, acc, ipc, sp, fichas_):
    dec = {}
    for it in acc:
        f = fichas_[it["clave"]]
        dec[it["clave"]] = (*_decision(it, sp, f), it["efectivo"] - sp["efectivo"], f["betas"].get("S&P 500"), f)
    comprar = [x["clave"] for x in acc if dec[x["clave"]][0] == "Comprar"]
    mantener = [x["clave"] for x in acc if dec[x["clave"]][0] == "Mantener"]
    vender = [x["clave"] for x in acc if dec[x["clave"]][0] == "Vender"]
    titular = ", ".join(t for t in (f"comprar {_junta(comprar)}" if comprar else "", f"mantener {_junta(mantener)}" if mantener else "",
                                    f"vender {_junta(vender)}" if vender else "") if t)
    _pagina(pdf, "Conclusión y toma de decisión", 7, titular[0].upper() + titular[1:])
    NUM = {0: "ninguna", 1: "una", 2: "dos", 3: "tres", 4: "cuatro", 5: "las cinco"}
    arriba = sum(1 for x in acc if x["efectivo"] > max(sp["efectivo"], ipc["efectivo"]))
    abajo = sum(1 for x in acc if x["efectivo"] < min(sp["efectivo"], ipc["efectivo"]))
    _p(pdf, f"En el periodo el S&P 500 rindió {sp['efectivo']:+.2f} % y el IPC {ipc['efectivo']:+.2f} %. Contra esas dos referencias, {NUM[arriba]} de las cinco "
            f"acciones quedaron arriba de ambas y {NUM[abajo]} abajo. La regla de decisión es sencilla: si la acción rindió más que el S&P 500 y su volatilidad "
            "anual es baja o media (menor a 35 %), se compra; si rindió más con volatilidad alta, se mantiene; si quedó debajo del índice, se vende. Se compara "
            "contra el S&P 500 porque las cinco cotizan en dólares.", size=9.4, alto=4.7, esp=3)
    y = _diferencias(pdf, pdf.get_y(), acc, dec)
    pdf.set_y(y + 1)
    beta_max = max(acc, key=lambda x: (dec[x["clave"]][3] or {}).get("beta") or -9)["clave"]
    for i, it in enumerate(acc):
        d_, c_, dif, b, f = dec[it["clave"]]
        if b and b["beta"] > 1.3 and it["clave"] == beta_max:
            com = f"es la más sensible al mercado del grupo, por cada punto que se movió el S&P 500 ella se movió {b['beta']:.2f}"
        elif b and b["beta"] < 0:
            com = f"con beta de {b['beta']:.2f} se movió al revés del índice, por eso amortigua una cartera cargada de tecnología"
        elif b and b["beta"] > 1.3:
            com = f"también amplifica al mercado, con beta de {b['beta']:.2f}"
        elif b and b["beta"] > 0.8:
            com = f"con beta de {b['beta']:.2f} se mueve casi al ritmo del mercado"
        else:
            com = f"con beta de {b['beta']:.2f} su precio dependió más de lo propio que del mercado"
        peor = min(it["ra"])
        fpeor = it["serie"][it["ra"].index(peor) + 1][0]
        y = pdf.get_y()
        pdf.set_xy(ML, y)
        pdf.set_font("BarlowC", "B", 10.5)
        pdf.set_text_color(*COLORES[i % 5])
        pdf.cell(13, 4.5, it["clave"])
        pdf.set_font("Barlow", "", 9)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(ANCHO - 13, 4.5, f"Volatilidad anual {f['nivel']} ({f['vol']:.2f} %); {com}. Su peor día fue el {R.fecha_corta(fpeor)}, con {peor:+.2f} %.",
                       new_x="LMARGIN", new_y="NEXT", align="J")
        pdf.ln(1)
    texto = (f"La cartera se armaría con {_junta(comprar)}, que le ganaron al índice sin una volatilidad alta. " if comprar else "")
    if mantener:
        texto += f"{_junta(mantener)} se mantendría como posición secundaria, el rendimiento está pero viene con oscilaciones grandes. "
    peores = sorted(acc, key=lambda x: -x["stats"]["desv"])[:len(vender)]
    extra = " y además fueron las más volátiles del grupo" if {x["clave"] for x in peores} == set(vender) else ""
    texto += f"{_junta(vender)} se venderían: quedaron debajo del índice{extra}."
    y = pdf.get_y() + 3.4
    pdf.set_xy(ML + 6, y)
    pdf.set_font("Barlow", "B", 7.8)
    pdf.set_text_color(*GUINDA)
    pdf.cell(ANCHO - 6, 4, "DECISIÓN FINAL", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.8)
    pdf.set_x(ML + 6)
    pdf.set_font("BarlowC", "B", 14)
    pdf.set_text_color(*GUINDA)
    pdf.multi_cell(ANCHO - 6, 6.4, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(*GUINDA)
    pdf.rect(ML, y, 1.6, pdf.get_y() - y, "F")
    pdf.ln(2.6)
    _p(pdf, f"Aun así, el ejercicio tiene límites, son {acc[0]['stats']['n']} días de un solo periodo y la estadística describe lo que ya pasó. Para invertir "
            "habría que repetirlo en otros periodos, revisar los estados financieros completos y considerar el tipo de cambio, que para un inversionista "
            "mexicano cambia el resultado de cualquier acción comprada en dólares. Fuentes: Yahoo Finance y Securities and Exchange Commission (EDGAR).",
       size=8.6, alto=4.3, color=GRIS, esp=0)


# ------------------------------------------------------------------------------ armado
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
        if pdf.get_y() > PIE + 0.5:
            pdf.desbordes.append((nombre, round(pdf.get_y(), 1)))
    if pdf.desbordes:
        print("[AVISO] apartados que no caben en su hoja:", pdf.desbordes)
    return bytes(pdf.output()), reg


def trabajo(d):
    """Documento completo en dos pasadas, para que el índice traiga las páginas correctas."""
    _, reg = _armar(d, {})
    return _armar(d, reg)[0]
