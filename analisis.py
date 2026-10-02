"""Estadística, indicadores técnicos y señales (solo biblioteca estándar).

Todo es determinista y explicable: cada señal se compone de seis criterios con
puntos (máx. ±100) y se describe en español. Es una herramienta educativa; no
constituye asesoría financiera.
"""
import math
from statistics import mean, pstdev, stdev

DIAS_ANIO = 252
HORIZONTE = 10  # sesiones hacia adelante para evaluar la señal (backtest)


# ---------------------------------------------------------------- indicadores
def _sma(v, n):
    out, s = [None] * len(v), 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n:
            s -= v[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def _ema(v, n):
    out, k, prev, buf = [None] * len(v), 2 / (n + 1), None, []
    for i, x in enumerate(v):
        if x is None:
            continue
        if prev is None:
            buf.append(x)
            if len(buf) == n:
                prev = sum(buf) / n
                out[i] = prev
        else:
            prev = x * k + prev * (1 - k)
            out[i] = prev
    return out


def _rsi(v, n=14):
    out = [None] * len(v)
    if len(v) <= n:
        return out
    g = [max(v[i] - v[i - 1], 0) for i in range(1, len(v))]
    p = [max(v[i - 1] - v[i], 0) for i in range(1, len(v))]
    ag, ap = sum(g[:n]) / n, sum(p[:n]) / n
    val = lambda a, b: 100.0 if b == 0 else 100 - 100 / (1 + a / b)
    out[n] = val(ag, ap)
    for i in range(n + 1, len(v)):
        ag, ap = (ag * (n - 1) + g[i - 1]) / n, (ap * (n - 1) + p[i - 1]) / n
        out[i] = val(ag, ap)
    return out


def _bollinger(v, n=20, k=2):
    mid = _sma(v, n)
    up, lo, pb = [None] * len(v), [None] * len(v), [None] * len(v)
    for i in range(n - 1, len(v)):
        sd = pstdev(v[i - n + 1:i + 1])
        up[i], lo[i] = mid[i] + k * sd, mid[i] - k * sd
        pb[i] = (v[i] - lo[i]) / (up[i] - lo[i]) if up[i] != lo[i] else 0.5
    return mid, up, lo, pb


def _linreg(y):
    """Pendiente y R² de una regresión lineal simple sobre x = 0..n-1."""
    n = len(y)
    mx, my = (n - 1) / 2, sum(y) / n
    sxx = sum((x - mx) ** 2 for x in range(n))
    sxy = sum((x - mx) * (yy - my) for x, yy in enumerate(y))
    syy = sum((yy - my) ** 2 for yy in y)
    return sxy / sxx, (sxy * sxy / (sxx * syy) if syy > 0 else 0.0)


def indicadores(c):
    e12, e26 = _ema(c, 12), _ema(c, 26)
    macd = [a - b if a is not None and b is not None else None for a, b in zip(e12, e26)]
    sig = _ema(macd, 9)
    hist = [m - s if m is not None and s is not None else None for m, s in zip(macd, sig)]
    mid, up, lo, pb = _bollinger(c)
    return {"sma20": mid, "sma50": _sma(c, 50), "bb_up": up, "bb_low": lo, "pctb": pb,
            "rsi": _rsi(c), "macd": macd, "macd_signal": sig, "hist": hist}


# --------------------------------------------------------------------- señales
def _tope(x, m):
    return max(-m, min(m, x))


def evaluar(i, c, ind):
    """Puntaje (−100..+100) y desglose por criterio en el índice i."""
    comp = []

    s20, s50 = ind["sma20"][i], ind["sma50"][i]
    if s50 is not None:
        pts = (10 if c[i] > s50 else -10) + (10 if s20 > s50 else -10)
        txt = (f"Precio {'sobre' if c[i] > s50 else 'bajo'} su media de 50 sesiones y media de 20 "
               f"{'sobre' if s20 > s50 else 'bajo'} la de 50")
    elif s20 is not None:
        pts, txt = (10 if c[i] > s20 else -10), f"Precio {'sobre' if c[i] > s20 else 'bajo'} su media de 20 sesiones"
    else:
        pts, txt = 0, "Historial insuficiente"
    comp.append({"criterio": "Tendencia (medias móviles)", "puntos": pts, "max": 20, "detalle": txt})

    h = ind["hist"][i]
    if h is not None:
        pts = 8 if h > 0 else -8
        cruce = ""
        hp = ind["hist"][i - 3] if i >= 3 else None
        if hp is not None and hp <= 0 < h:
            pts, cruce = pts + 7, "; cruce alcista reciente"
        elif hp is not None and hp >= 0 > h:
            pts, cruce = pts - 7, "; cruce bajista reciente"
        txt = f"Histograma MACD {'positivo' if h > 0 else 'negativo'}{cruce}"
    else:
        pts, txt = 0, "Historial insuficiente"
    comp.append({"criterio": "Impulso (MACD)", "puntos": pts, "max": 15, "detalle": txt})

    r = ind["rsi"][i]
    if r is not None:
        pts = 20 if r < 30 else 8 if r < 40 else -20 if r > 70 else -8 if r > 60 else 0
        zona = ("sobreventa (posible rebote)" if r < 30 else "cerca de sobreventa" if r < 40
                else "sobrecompra (posible corrección)" if r > 70 else "cerca de sobrecompra" if r > 60 else "zona neutral")
        txt = f"RSI {r:.0f}: {zona}"
    else:
        pts, txt = 0, "Historial insuficiente"
    comp.append({"criterio": "Sobrecompra / sobreventa (RSI)", "puntos": pts, "max": 20, "detalle": txt})

    b = ind["pctb"][i]
    if b is not None:
        pts = 15 if b < 0 else 6 if b < 0.2 else -15 if b > 1 else -6 if b > 0.8 else 0
        txt = ("Precio fuera de la banda inferior" if b < 0 else "Precio cerca de la banda inferior" if b < 0.2
               else "Precio fuera de la banda superior" if b > 1 else "Precio cerca de la banda superior" if b > 0.8
               else "Precio dentro de las bandas de Bollinger")
    else:
        pts, txt = 0, "Historial insuficiente"
    comp.append({"criterio": "Volatilidad (Bollinger)", "puntos": pts, "max": 15, "detalle": txt})

    if i >= 20:
        r20 = c[i] / c[i - 20] - 1
        pts, txt = round(_tope(r20 / 0.05 * 10, 10)), f"Rendimiento a 20 sesiones: {r20 * 100:+.1f}%"
    else:
        pts, txt = 0, "Historial insuficiente"
    comp.append({"criterio": "Momentum (20 sesiones)", "puntos": pts, "max": 10, "detalle": txt})

    if i >= 29:
        sl, r2 = _linreg([math.log(x) for x in c[i - 29:i + 1]])
        if r2 >= 0.5:
            pts = round(15 * _tope(sl / 0.004, 1))
            txt = f"Tendencia estadística {'alcista' if sl > 0 else 'bajista'}: {sl * 100:+.2f}%/día (R² {r2:.2f})"
        else:
            pts, txt = 0, f"Sin tendencia estadística clara (R² {r2:.2f})"
    else:
        pts, txt = 0, "Historial insuficiente"
    comp.append({"criterio": "Regresión lineal (30 sesiones)", "puntos": pts, "max": 15, "detalle": txt})

    return sum(x["puntos"] for x in comp), comp


def veredicto(score):
    return ("COMPRA FUERTE" if score >= 45 else "COMPRAR" if score >= 20
            else "VENTA FUERTE" if score <= -45 else "VENDER" if score <= -20 else "MANTENER")


def confianza(score, comp, i):
    activos = [x["puntos"] for x in comp if x["puntos"]]
    if i < 59 or not activos:
        return "Baja"
    acuerdo = sum(1 for p in activos if (p > 0) == (score > 0)) / len(activos)
    return "Alta" if acuerdo >= 0.8 else "Media" if acuerdo >= 0.6 else "Baja"


def backtest(c, ind, h=HORIZONTE):
    """¿Qué pasó, en este mismo historial, después de cada señal? (dentro de muestra)."""
    compras, ventas, todos = [], [], []
    for i in range(50, len(c) - h):
        s, _ = evaluar(i, c, ind)
        fr = c[i + h] / c[i] - 1
        todos.append(fr)
        if s >= 20:
            compras.append(fr)
        elif s <= -20:
            ventas.append(fr)
    pct = lambda xs, f: round(100 * sum(1 for x in xs if f(x)) / len(xs)) if xs else None
    med = lambda xs: round(mean(xs) * 100, 2) if xs else None
    return {"horizonte": h, "muestra": len(todos), "base_rend_medio": med(todos),
            "n_compra": len(compras), "aciertos_compra": pct(compras, lambda x: x > 0), "rend_medio_compra": med(compras),
            "n_venta": len(ventas), "aciertos_venta": pct(ventas, lambda x: x < 0), "rend_medio_venta": med(ventas)}


# ------------------------------------------------------------------ estadística
def estadisticas(i, c, vol):
    rets = [math.log(c[j] / c[j - 1]) for j in range(1, i + 1)]
    w = rets[-60:]
    sd = pstdev(w) if len(w) >= 5 else None
    pico, dd = c[max(0, i - 119)], 0.0
    for x in c[max(0, i - 119):i + 1]:
        pico = max(pico, x)
        dd = min(dd, x / pico - 1)
    v20 = c[max(0, i - 19):i + 1]
    sd20 = pstdev(v20) if len(v20) >= 5 else 0
    vols = [x for x in vol[max(0, i - 20):i] if x]
    return {
        "vol_anual": round(sd * math.sqrt(DIAS_ANIO) * 100, 1) if sd else None,
        "ratio_rend_riesgo": round(mean(w) / sd * math.sqrt(DIAS_ANIO), 2) if sd else None,
        "max_drawdown": round(dd * 100, 1),
        "soporte": round(min(v20), 2), "resistencia": round(max(v20), 2),
        "z_precio": round((c[i] - mean(v20)) / sd20, 2) if sd20 else 0.0,
        "vol_relativo": round(vol[i] / mean(vols), 2) if vols and vol[i] else None,
    }


def _tendencia(c, i):
    if i < 29:
        return {"etiqueta": "sin datos", "pendiente": None, "r2": None}
    sl, r2 = _linreg([math.log(x) for x in c[i - 29:i + 1]])
    et = "alcista" if sl > 0.001 and r2 >= 0.5 else "bajista" if sl < -0.001 and r2 >= 0.5 else "lateral"
    return {"etiqueta": et, "pendiente": round(sl * 100, 3), "r2": round(r2, 2)}


def _texto(nombre, d):
    t = d["tendencia"]
    partes = [f"{nombre} cerró en ${d['cierre']:.2f}, {'sube' if d['var_pct'] >= 0 else 'baja'} {abs(d['var_pct']):.2f}% vs. la sesión anterior."]
    if d["ret5"] is not None and d["ret20"] is not None:
        partes.append(f"En 5 sesiones acumula {d['ret5']:+.1f}% y en 20 sesiones {d['ret20']:+.1f}%.")
    if t["pendiente"] is not None:
        partes.append(f"Tendencia {t['etiqueta']} (pendiente {t['pendiente']:+.2f}%/día, R² {t['r2']:.2f}).")
    if d.get("rsi") is not None:
        zona = "sobreventa" if d["rsi"] < 30 else "sobrecompra" if d["rsi"] > 70 else "zona neutral"
        partes.append(f"RSI {d['rsi']:.0f} ({zona}).")
    s = d["stats"]
    if s["vol_anual"] is not None:
        partes.append(f"Volatilidad anualizada {s['vol_anual']:.0f}%; caída máxima reciente {s['max_drawdown']:.1f}%.")
    if s["vol_relativo"] is not None and (s["vol_relativo"] > 1.5 or s["vol_relativo"] < 0.6):
        partes.append(f"Volumen {s['vol_relativo']:.1f}× su promedio de 20 sesiones.")
    partes.append(f"Señal técnica: {d['veredicto']} (puntaje {d['score']:+d}/100, confianza {d['confianza'].lower()}).")
    return " ".join(partes)


def analizar_serie(nombre, rows, desde_vista=None, con_serie=True, con_backtest=True):
    """Analiza la última sesión de `rows` (lista de dicts con fecha/cierre/volumen)."""
    c = [r["cierre"] for r in rows]
    vol = [r.get("volumen") or 0 for r in rows]
    i = len(c) - 1
    ind = indicadores(c)
    score, comp = evaluar(i, c, ind)
    var_pct = (c[i] / c[i - 1] - 1) * 100 if i else 0.0
    ini = next((k for k, r in enumerate(rows) if desde_vista and r["fecha"] >= desde_vista), 0)
    d = {
        "fecha": rows[i]["fecha"], "cierre": round(c[i], 2), "previo": round(c[i - 1], 2) if i else None,
        "var": round(c[i] - c[i - 1], 2) if i else 0.0, "var_pct": round(var_pct, 2),
        "ret5": round((c[i] / c[i - 5] - 1) * 100, 2) if i >= 5 else None,
        "ret20": round((c[i] / c[i - 20] - 1) * 100, 2) if i >= 20 else None,
        "ret_periodo": round((c[i] / c[ini] - 1) * 100, 2),
        "rsi": round(ind["rsi"][i], 1) if ind["rsi"][i] is not None else None,
        "macd_hist": round(ind["hist"][i], 3) if ind["hist"][i] is not None else None,
        "pctb": round(ind["pctb"][i], 2) if ind["pctb"][i] is not None else None,
        "score": score, "veredicto": veredicto(score), "confianza": confianza(score, comp, i),
        "componentes": comp, "tendencia": _tendencia(c, i), "stats": estadisticas(i, c, vol),
    }
    d["texto"] = _texto(nombre, d)
    if con_backtest:
        d["backtest"] = backtest(c, ind)
    if con_serie:
        r = lambda arr, k=4: [None if x is None else round(x, k) for x in arr[ini:]]
        d["serie"] = {"fechas": [x["fecha"] for x in rows[ini:]], "cierre": r(c, 2), "volumen": vol[ini:],
                      "sma20": r(ind["sma20"], 2), "sma50": r(ind["sma50"], 2),
                      "bb_up": r(ind["bb_up"], 2), "bb_low": r(ind["bb_low"], 2),
                      "rsi": r(ind["rsi"], 1), "macd": r(ind["macd"]), "macd_signal": r(ind["macd_signal"]),
                      "hist": r(ind["hist"])}
    return d


def resumen_mercado(items):
    """items: lista de dicts con nombre, ticker, var_pct, veredicto, score."""
    if not items:
        return {"texto": "Sin datos.", "suben": 0, "bajan": 0}
    suben = [x for x in items if x["var_pct"] > 0]
    bajan = [x for x in items if x["var_pct"] < 0]
    mejor = max(items, key=lambda x: x["var_pct"])
    peor = min(items, key=lambda x: x["var_pct"])
    cuenta = {}
    for x in items:
        k = "COMPRAR" if "COMPRA" in x["veredicto"] else "VENDER" if "VENTA" in x["veredicto"] else "MANTENER"
        cuenta[k] = cuenta.get(k, 0) + 1
    prom = mean(x["score"] for x in items)
    sesgo = "positivo" if prom >= 10 else "negativo" if prom <= -10 else "neutral"
    texto = (f"De {len(items)} emisoras, {len(suben)} subieron y {len(bajan)} bajaron. "
             f"Mejor: {mejor['nombre']} ({mejor['var_pct']:+.2f}%); peor: {peor['nombre']} ({peor['var_pct']:+.2f}%). "
             f"Señales: {cuenta.get('COMPRAR', 0)} de compra, {cuenta.get('MANTENER', 0)} de mantener, "
             f"{cuenta.get('VENDER', 0)} de venta (puntaje promedio {prom:+.0f}, sesgo {sesgo}).")
    return {"texto": texto, "suben": len(suben), "bajan": len(bajan), "puntaje_promedio": round(prom),
            "sesgo": sesgo, "senales": cuenta}


# ---------------------------------------------------------------- comparación
def comparar(hist, desde):
    """hist: {ticker: [filas]}. Alinea fechas comunes ≥ desde y calcula base 100, correlación y ranking."""
    tks = list(hist)
    conjuntos = [{r["fecha"] for r in rows if r["fecha"] >= desde} for rows in hist.values()]
    fechas = sorted(set.intersection(*conjuntos)) if conjuntos else []
    cierres = {}
    for t in tks:
        m = {r["fecha"]: r["cierre"] for r in hist[t]}
        cierres[t] = [m[f] for f in fechas]
    base = {t: [round(x / v[0] * 100, 2) for x in v] for t, v in cierres.items() if v}
    rets = {t: [v[j] / v[j - 1] - 1 for j in range(1, len(v))] for t, v in cierres.items() if len(v) > 2}

    def pearson(a, b):
        ma, mb = mean(a), mean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return round(num / den, 2) if den else 0.0

    orden = [t for t in tks if t in rets]
    matriz = [[1.0 if a == b else pearson(rets[a], rets[b]) for b in orden] for a in orden]
    ranking = []
    for t in orden:
        v, r = cierres[t], rets[t]
        sd = pstdev(r) if len(r) > 1 else 0
        pico, dd = v[0], 0.0
        for x in v:
            pico = max(pico, x)
            dd = min(dd, x / pico - 1)
        ranking.append({"ticker": t, "ret": round((v[-1] / v[0] - 1) * 100, 2),
                        "vol_anual": round(sd * math.sqrt(DIAS_ANIO) * 100, 1),
                        "ratio": round(mean(r) / sd * math.sqrt(DIAS_ANIO), 2) if sd else None,
                        "max_drawdown": round(dd * 100, 1),
                        "mejor_dia": round(max(r) * 100, 2), "peor_dia": round(min(r) * 100, 2),
                        "dias_alza": round(100 * sum(1 for x in r if x > 0) / len(r))})
    return {"fechas": fechas, "cierres": cierres, "base100": base,
            "corr": {"tickers": orden, "matriz": matriz}, "ranking": ranking}


# ----------------------------------------------------------------------- deuda
def analizar_deuda(d, hasta=None):
    datos = [x for x in d["datos"] if hasta is None or x["fecha"] <= hasta]
    base = {"nombre": d["nombre"], "emisor": d["emisor"], "unidad": d["unidad"], "tipo": d["tipo"]}
    if not datos:
        return {**base, "fecha": None, "valor": None, "senal": "SIN DATOS", "tendencia": "sin datos",
                "texto": f"{d['nombre']}: sin subastas en el periodo."}
    vals = [x["valor"] for x in datos]
    last, prev = vals[-1], (vals[-2] if len(vals) > 1 else None)
    ven = vals[-12:]
    sd = stdev(ven) if len(ven) >= 3 else 0
    z = round((last - mean(ven)) / sd, 2) if sd > 0 else 0.0
    sl = _linreg(vals[-8:])[0] if len(vals) >= 4 else 0.0
    es_tasa = d["tipo"] == "tasa"
    sl_u = sl * 100 if es_tasa else sl  # pb por subasta (tasas) o pesos por subasta (precio)
    umbral = 1.5 if es_tasa else 0.004
    tend = "al alza" if sl_u > umbral else "a la baja" if sl_u < -umbral else "estable"
    var = (last - prev) if prev is not None else None
    var_txt = "" if var is None else (f" ({var * 100:+.0f} pb vs. la subasta previa)" if es_tasa else f" ({var:+.5f} vs. la previa)")
    if len(vals) < 4:
        senal, razon = "MANTENER", "Hay pocas subastas en el periodo para estimar una tendencia confiable."
    elif not es_tasa:
        senal, razon = "MANTENER", "Cotiza cerca de la par: el rendimiento proviene sobre todo del cupón; no hay señal de precio relevante."
    elif z >= 0.75:
        senal, razon = "COMPRAR", "El rendimiento está alto frente a sus últimas subastas: buen momento para fijar tasa."
    elif z <= -0.75:
        senal, razon = "ESPERAR", "El rendimiento está bajo frente a sus últimas subastas: conviene esperar o escalonar compras."
    else:
        senal, razon = "MANTENER", "El rendimiento está en su rango reciente."
    val_txt = f"{last:.2f}%" if es_tasa and d["unidad"].startswith("%") else (f"{last:.2f} pp" if es_tasa else f"${last:.5f}")
    texto = (f"{d['nombre']} ({d['emisor']}): {val_txt}{var_txt}. Tendencia {tend} "
             f"({sl_u:+.1f} {'pb' if es_tasa else '$'}/subasta, z={z:+.1f}). {razon}")
    return {**base, "fecha": datos[-1]["fecha"], "valor": last, "var": None if var is None else round(var, 5),
            "var_pb": round(var * 100, 1) if var is not None and es_tasa else None, "z": z,
            "pendiente": round(sl_u, 2), "tendencia": tend, "senal": senal, "n": len(vals), "texto": texto}
