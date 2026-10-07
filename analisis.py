"""Estadística, indicadores técnicos y señales (solo biblioteca estándar).

Todo es determinista y explicable: la decisión se compone de nueve señales técnicas cuyos pesos se recalculan cada día
(ver modelo.py) y se describe en español. Es una herramienta educativa; no
constituye asesoría financiera.
"""
import bisect
import math
from statistics import mean, pstdev, stdev

DIAS_ANIO = 252
HORIZONTE = 5  # sesiones hacia adelante para evaluar la señal


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


def veredicto(score):
    return ("COMPRA FUERTE" if score >= 45 else "COMPRAR" if score >= 20
            else "VENTA FUERTE" if score <= -45 else "VENDER" if score <= -20 else "MANTENER")


DECISION = {"COMPRA FUERTE": "Comprar (señal fuerte)", "COMPRAR": "Comprar", "MANTENER": "Mantener",
            "VENDER": "Vender", "VENTA FUERTE": "Vender (señal fuerte)"}
ACCION = {
    "COMPRA FUERTE": "Si no tenías la acción, era un buen momento para entrar; si ya la tenías, mantener o aumentar la posición.",
    "COMPRAR": "Si no tenías la acción, considerar entrar; si ya la tenías, mantenerla.",
    "MANTENER": "No operar: no hay ventaja clara. Si tenías la acción, conservarla; si no, esperar una señal más definida.",
    "VENDER": "Si tenías la acción, considerar salir o reducir; si no la tenías, no entrar todavía.",
    "VENTA FUERTE": "Si tenías la acción, era momento de salir; si no la tenías, no entrar.",
}


def razonar(veredicto_, score, comp, anterior=None):
    """Explica en español por qué se tomó la decisión: criterios que empujan a favor o en contra."""
    if score >= 20:
        por_que = [f"El puntaje total fue {score:+d} de ±100: supera el umbral de +20, por eso la decisión es comprar."]
    elif score <= -20:
        por_que = [f"El puntaje total fue {score:+d} de ±100: cae por debajo del umbral de -20, por eso la decisión es vender."]
    else:
        por_que = [f"El puntaje total fue {score:+d} de ±100: queda entre -20 y +20, sin ventaja clara, por eso la decisión es mantener."]
    for c in sorted(comp, key=lambda x: -abs(x["puntos"])):
        if c["puntos"]:
            lado = "a favor de comprar" if c["puntos"] > 0 else "a favor de vender"
            por_que.append(f"{c['criterio']} ({c['puntos']:+d}, {lado}): {c['detalle']}.")
    neutros = [c["criterio"] for c in comp if not c["puntos"]]
    if neutros:
        por_que.append("Sin aporte hoy: " + ", ".join(neutros) + ".")
    if anterior and anterior != veredicto_:
        por_que.append(f"Cambio de señal: el día anterior era {DECISION.get(anterior, anterior).lower()}.")
    return por_que


def confianza(score, comp):
    """Qué tan de acuerdo están entre sí las señales que sí aportaron puntos."""
    activos = [x["puntos"] for x in comp if x["puntos"]]
    if len(activos) < 3:
        return "Baja"
    acuerdo = sum(1 for p in activos if (p > 0) == (score > 0)) / len(activos)
    return "Alta" if acuerdo >= 0.8 else "Media" if acuerdo >= 0.6 else "Baja"


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
        "vol_anual": round(sd * math.sqrt(DIAS_ANIO) * 100, 2) if sd else None,
        "ratio_rend_riesgo": round(mean(w) / sd * math.sqrt(DIAS_ANIO), 2) if sd else None,
        "max_drawdown": round(dd * 100, 2),
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
        partes.append(f"En 5 sesiones acumula {d['ret5']:+.2f}% y en 20 sesiones {d['ret20']:+.2f}%.")
    if t["pendiente"] is not None:
        partes.append(f"Tendencia {t['etiqueta']} (pendiente {t['pendiente']:+.2f}%/día, R² {t['r2']:.2f}).")
    if d.get("rsi") is not None:
        zona = "sobreventa" if d["rsi"] < 30 else "sobrecompra" if d["rsi"] > 70 else "zona neutral"
        partes.append(f"RSI {d['rsi']:.2f} ({zona}).")
    s = d["stats"]
    if s["vol_anual"] is not None:
        partes.append(f"Volatilidad anualizada {s['vol_anual']:.2f}%; caída máxima reciente {s['max_drawdown']:.2f}%.")
    if s["vol_relativo"] is not None and (s["vol_relativo"] > 1.5 or s["vol_relativo"] < 0.6):
        partes.append(f"Volumen {s['vol_relativo']:.2f}× su promedio de 20 sesiones.")
    partes.append(f"Señal técnica: {d['veredicto']} (puntaje {d['score']:+d}/100, confianza {d['confianza'].lower()}).")
    return " ".join(partes)


def _respaldo_texto(v, r):
    """Evidencia estadística de la decisión: qué pasó a 5 sesiones tras señales del mismo tipo (dentro de la muestra de calibración)."""
    if not r or not r["n"]:
        return "Aún no hay sesiones suficientes para respaldar estadísticamente esta decisión."
    marco = f"entre el {r['desde'][8:]}/{r['desde'][5:7]}/{r['desde'][:4]} y el {r['hasta'][8:]}/{r['hasta'][5:7]}/{r['hasta'][:4]} ({r['n']:,} observaciones de las 10 emisoras)"
    if "COMPRA" in v and r["compra"]["n"]:
        c = r["compra"]
        return (f"{marco.capitalize()[:1] + marco[1:]}, cuando el puntaje era de comprar el precio subió a 5 sesiones el {c['sube']:.2f}% de las veces "
                f"(frente a {r['base_sube']:.2f}% en cualquier sesión) con un rendimiento medio de {c['media']:+.2f}%.")
    if v in ("VENDER", "VENTA FUERTE") and r["venta"]["n"]:
        c = r["venta"]
        return (f"{marco.capitalize()[:1] + marco[1:]}, cuando el puntaje era de vender el precio bajó a 5 sesiones el {c['baja']:.2f}% de las veces "
                f"(frente a {100 - r['base_sube']:.2f}% en cualquier sesión) con un rendimiento medio de {c['media']:+.2f}%.")
    c = r["mantener"]
    return (f"{marco.capitalize()[:1] + marco[1:]}, cuando no había señal clara el precio se movió 2% o menos en solo {c['quieto']:.2f}% de los casos: "
            "mantener significa que no hay ventaja estadística, no que se espere que el precio quede quieto.")


def _riesgos(d, r):
    """Qué podría hacer fallar la decisión."""
    out = []
    s = d["stats"]
    sem = (s["vol_anual"] or 0) / math.sqrt(DIAS_ANIO / 5)
    if "COMPRA" in d["veredicto"]:
        out.append(f"Si el precio cierra por debajo del soporte de 20 sesiones ({s['soporte']:.2f}), la señal de compra pierde validez.")
    elif d["veredicto"] in ("VENDER", "VENTA FUERTE"):
        out.append(f"Si el precio cierra por encima de la resistencia de 20 sesiones ({s['resistencia']:.2f}), la señal de venta pierde validez.")
    if sem:
        out.append(f"La oscilación típica de una semana es de ±{sem:.2f}%, normalmente mayor que la ventaja estadística de la señal: es normal que se equivoque con frecuencia.")
    if r and r["compra"]["sube"] and "COMPRA" in d["veredicto"] and r["compra"]["sube"] < 60:
        out.append(f"Aun en el respaldo histórico la compra acertó {r['compra']['sube']:.2f}% de las veces: no es una señal segura.")
    out.append("Noticias, resultados de la empresa o cambios de tasas pueden cambiar el precio sin que lo anticipen los indicadores técnicos.")
    return out


def analizar_serie(nombre, rows, desde_vista=None, con_serie=True, con_backtest=True, modelo=None, ticker=None):
    """Analiza la última sesión de `rows` (lista de dicts con fecha/cierre/volumen).

    `modelo` (modelo.Modelo) reúne a todas las emisoras para calibrar los pesos; si no se da, se calibra solo con esta serie."""
    import modelo as _m
    ticker = ticker or nombre
    modelo = modelo or _m.Modelo({ticker: rows})
    c = [r["cierre"] for r in rows]
    vol = [r.get("volumen") or 0 for r in rows]
    i = len(c) - 1
    ind = indicadores(c)
    fecha = rows[i]["fecha"]
    score, comp = modelo.evaluar(ticker, fecha)
    var_pct = (c[i] / c[i - 1] - 1) * 100 if i else 0.0
    ini = next((k for k, r in enumerate(rows) if desde_vista and r["fecha"] >= desde_vista), 0)
    d = {
        "fecha": rows[i]["fecha"], "cierre": round(c[i], 2), "previo": round(c[i - 1], 2) if i else None,
        "var": round(c[i] - c[i - 1], 2) if i else 0.0, "var_pct": round(var_pct, 2),
        "ret5": round((c[i] / c[i - 5] - 1) * 100, 2) if i >= 5 else None,
        "ret20": round((c[i] / c[i - 20] - 1) * 100, 2) if i >= 20 else None,
        "ret_periodo": round((c[i] / c[ini] - 1) * 100, 2),
        "rsi": round(ind["rsi"][i], 2) if ind["rsi"][i] is not None else None,
        "macd_hist": round(ind["hist"][i], 3) if ind["hist"][i] is not None else None,
        "pctb": round(ind["pctb"][i], 2) if ind["pctb"][i] is not None else None,
        "score": score, "veredicto": veredicto(score), "confianza": confianza(score, comp),
        "componentes": comp, "tendencia": _tendencia(c, i), "stats": estadisticas(i, c, vol),
    }
    if i >= 1:
        sc_ant, _ = modelo.evaluar(ticker, rows[i - 1]["fecha"])
        d["veredicto_ant"] = veredicto(sc_ant)
    else:
        d["veredicto_ant"] = None
    d["cambio"] = d["veredicto_ant"] is not None and d["veredicto_ant"] != d["veredicto"]
    d["decision"] = DECISION[d["veredicto"]]
    d["calibracion"] = modelo.calibracion(fecha)
    resp = modelo.respaldo(fecha)
    d["respaldo"] = _respaldo_texto(d["veredicto"], resp)
    d["riesgos"] = _riesgos(d, resp)
    d["por_que"] = razonar(d["veredicto"], score, comp, d["veredicto_ant"])
    cal = d["calibracion"]
    if cal:
        d["por_que"].insert(1, f"Cómo se calcula: nueve señales técnicas se combinan con pesos recalculados hoy según cuánto anticiparon el rendimiento a 5 sesiones de las 10 emisoras en las últimas {cal['sesiones']} sesiones; el puntaje se escala para que +20 y −20 marquen las señales poco habituales.")
    d["accion"] = ACCION[d["veredicto"]]
    d["texto"] = _texto(nombre, d)
    if con_backtest:
        d["backtest"] = modelo.backtest(ticker, fecha) or {"horizonte": 5, "muestra": 0, "base_rend_medio": None, "n_compra": 0, "aciertos_compra": None,
                                                           "rend_medio_compra": None, "n_venta": 0, "aciertos_venta": None, "rend_medio_venta": None}
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
        k = "COMPRAR" if "COMPRA" in x["veredicto"] else "VENDER" if x["veredicto"] in ("VENDER", "VENTA FUERTE") else "MANTENER"
        cuenta[k] = cuenta.get(k, 0) + 1
    prom = mean(x["score"] for x in items)
    sesgo = "positivo" if prom >= 10 else "negativo" if prom <= -10 else "neutral"
    ver = lambda n, s, p: f"{n} {s if n == 1 else p}"
    texto = (f"De {len(items)} emisoras, {ver(len(suben), 'subió', 'subieron')} y {ver(len(bajan), 'bajó', 'bajaron')}. "
             f"Mejor: {mejor['nombre']} ({mejor['var_pct']:+.2f}%); peor: {peor['nombre']} ({peor['var_pct']:+.2f}%). "
             f"Decisiones: {cuenta.get('COMPRAR', 0)} de comprar, {cuenta.get('MANTENER', 0)} de mantener, "
             f"{cuenta.get('VENDER', 0)} de vender (puntaje promedio {prom:+.2f}, sesgo {sesgo}).")
    out = {"texto": texto, "suben": len(suben), "bajan": len(bajan), "puntaje_promedio": round(prom, 2),
           "sesgo": sesgo, "senales": cuenta}
    if all(x.get("ret_periodo") is not None for x in items):  # texto del periodo consultado (rendimiento en la moneda de cada emisora)
        pos = [x for x in items if x["ret_periodo"] > 0]
        mj = max(items, key=lambda x: x["ret_periodo"])
        pr = min(items, key=lambda x: x["ret_periodo"])
        out["texto_periodo"] = (f"En el periodo, {len(pos)} de {len(items)} emisoras tuvieron rendimiento positivo en su moneda. "
                                f"Mejor: {mj['nombre']} ({mj['ret_periodo']:+.2f}%); peor: {pr['nombre']} ({pr['ret_periodo']:+.2f}%). "
                                f"Al último cierre: {cuenta.get('COMPRAR', 0)} decisiones de comprar, {cuenta.get('MANTENER', 0)} de mantener y {cuenta.get('VENDER', 0)} de vender.")
    return out


# ---------------------------------------------------------------- comparación
def _fx_en(fx_f, fx_v, f):
    """Tipo de cambio vigente en la fecha f (el último publicado; el primero si f es anterior)."""
    i = bisect.bisect_right(fx_f, f)
    return fx_v[max(i - 1, 0)]


def _cierres_en_pesos(rows, fx):
    """Cierres de una acción en dólares convertidos a pesos con el tipo de cambio de cierre de Banxico."""
    fx_f, fx_v = [x[0] for x in fx], [x[1] for x in fx]
    return [r["cierre"] * _fx_en(fx_f, fx_v, r["fecha"]) for r in rows]


def comparar(hist, desde, hasta, fx=None, meta=None):
    """hist: {ticker: [filas]}. Alinea las fechas comunes del periodo y calcula base 100, correlación y ranking.

    Con `fx` (lista [(fecha, pesos por dólar)]) las acciones de EE. UU. se miden en pesos; sin él, en su moneda."""
    tks = list(hist)
    en_pesos = {t: (fx and meta and meta.get(t, {}).get("moneda") == "USD") for t in tks}
    px = {t: (dict(zip([r["fecha"] for r in hist[t]], _cierres_en_pesos(hist[t], fx))) if en_pesos[t]
              else {r["fecha"]: r["cierre"] for r in hist[t]}) for t in tks}
    conjuntos = [{f for f in px[t] if desde <= f <= hasta} for t in tks]
    fechas = sorted(set.intersection(*conjuntos)) if conjuntos else []
    cierres = {t: [px[t][f] for f in fechas] for t in tks}
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
                        "vol_anual": round(sd * math.sqrt(DIAS_ANIO) * 100, 2),
                        "ratio": round(mean(r) / sd * math.sqrt(DIAS_ANIO), 2) if sd else None,
                        "max_drawdown": round(dd * 100, 2),
                        "mejor_dia": round(max(r) * 100, 2), "peor_dia": round(min(r) * 100, 2),
                        "dias_alza": round(100 * sum(1 for x in r if x > 0) / len(r), 2)})
    return {"fechas": fechas, "cierres": {k: [round(x, 4) for x in v] for k, v in cierres.items()}, "base100": base,
            "moneda": "pesos" if fx else "original", "en_pesos": [t for t in tks if en_pesos[t]],
            "corr": {"tickers": orden, "matriz": matriz}, "ranking": ranking}


# ----------------------------------------------------------------------- deuda
def analizar_deuda(d, hasta=None, desde=None):
    datos = [x for x in d["datos"] if hasta is None or x["fecha"] <= hasta]
    base = {"nombre": d["nombre"], "codigo": d.get("codigo", d["nombre"]), "emisor": d["emisor"], "unidad": d["unidad"], "tipo": d["tipo"],
            "extras": d.get("extras", [])}
    if not datos:
        return {**base, "fecha": None, "valor": None, "senal": "SIN DATOS", "tendencia": "sin datos",
                "decision": "Sin datos", "por_que": ["No hubo subastas del instrumento en el periodo."],
                "texto": f"{d['nombre']}: sin subastas en el periodo."}
    if d["tipo"] == "monto":
        return _deuda_monto(d, base, datos, desde)
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
    var_txt = "" if var is None else (f" ({var * 100:+.2f} pb vs. la subasta previa)" if es_tasa else f" ({var:+.5f} vs. la previa)")
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
             f"({sl_u:+.2f} {'pb' if es_tasa else '$'}/subasta, z={z:+.2f}). {razon}")
    decision = {"COMPRAR": "Comprar (fijar tasa)", "ESPERAR": "Esperar", "MANTENER": "Mantener"}.get(senal, senal.title())
    por_que = [f"El rendimiento de la última subasta fue {val_txt}{var_txt}.",
               f"Frente al promedio de las últimas 12 subastas su puntaje z es {z:+.2f}.",
               f"La tendencia es {tend} ({sl_u:+.2f} {'pb' if es_tasa else '$'} por subasta).", razon]
    return {**base, "fecha": datos[-1]["fecha"], "valor": last, "var": None if var is None else round(var, 5),
            "decision": decision, "por_que": por_que,
            "var_pb": round(var * 100, 2) if var is not None and es_tasa else None, "z": z,
            "pendiente": round(sl_u, 2), "tendencia": tend, "senal": senal, "n": len(vals), "texto": texto}


def _deuda_monto(d, base, datos, desde):
    """Instrumentos que se siguen por volumen colocado (no por tasa), como el papel comercial."""
    per = [x for x in datos if desde is None or x["fecha"] >= desde] or datos
    total = sum(x["valor"] for x in per) / 1000  # miles de pesos -> millones de pesos
    con = sum(1 for x in per if x["valor"] > 0)
    ult = per[-1]
    saldo = next((x["extra"].get(e) for x in [ult] for e in x["extra"] if e.startswith("Saldo")), None)
    saldo_txt = "" if saldo is None else f" El saldo vigente al {ult['fecha'][8:]}/{ult['fecha'][5:7]}/{ult['fecha'][:4]} es de ${saldo / 1000:,.2f} millones de pesos."
    if total == 0:
        texto = (f"{d['nombre']}: en las {len(per)} semanas del periodo no se registraron colocaciones.{saldo_txt} "
                 "Banxico agrupa este instrumento con los certificados bursátiles de corto plazo en sus indicadores semanales de valores privados.")
    else:
        texto = (f"{d['nombre']}: en las {len(per)} semanas del periodo se colocaron ${total:,.2f} millones de pesos "
                 f"({con} semanas con colocaciones; en la última semana ${ult['valor'] / 1000:,.2f} millones).{saldo_txt}")
    por_que = ["Este instrumento se sigue por volumen colocado, no por rendimiento: no genera señal de compra o venta.", texto]
    return {**base, "fecha": ult["fecha"], "valor": ult["valor"], "var": None, "var_pb": None, "z": None, "pendiente": None,
            "tendencia": "sin colocaciones" if total == 0 else "con colocaciones", "senal": "INFORMATIVO",
            "decision": "Solo informativo", "por_que": por_que, "n": len(per), "texto": texto,
            "total_periodo_millones": round(total, 2), "semanas_con_colocacion": con}


# ------------------------------------------------------------------- simulación
def simular(hist, desde, hasta, capital=100000.0, costo=0.002, fx=None, meta=None):
    """Qué habría pasado siguiendo las señales (comprar cuando puntaje >= 20, salir a efectivo cuando <= -20).

    La señal calculada al cierre del día j se ejecuta al cierre del día j+1 (sin ver el futuro) y cada
    operación paga `costo` (0.20 % por defecto). Se compara contra comprar y mantener en partes iguales.
    Con `fx`, las acciones de EE. UU. generan su señal con su precio en dólares pero ganan o pierden en pesos."""
    import modelo as _m
    mod = _m.obtener(hist)
    tks = list(hist)
    conj = [{r["fecha"] for r in rows if desde <= r["fecha"] <= hasta} for rows in hist.values()]
    fechas = sorted(set.intersection(*conj)) if conj else []
    if len(fechas) < 3:
        return {"fechas": [], "error": "El periodo es demasiado corto para simular (se necesitan al menos 3 sesiones)."}
    parte = capital / len(tks)
    estrategia = [0.0] * len(fechas)
    comprarmant = [0.0] * len(fechas)
    por = []
    for t in tks:
        rows = hist[t]
        c = [r["cierre"] for r in rows]
        usd = bool(fx and meta and meta.get(t, {}).get("moneda") == "USD")
        cp = _cierres_en_pesos(rows, fx) if usd else c  # precios con los que se gana o se pierde
        pos_idx = {r["fecha"]: k for k, r in enumerate(rows)}
        valor, pos, pend, ops, dias_pos = parte, 0, 0, 0, 0
        serie_v = [valor]
        for j in range(1, len(fechas)):
            k, kp = pos_idx[fechas[j]], pos_idx[fechas[j - 1]]
            if pos:
                valor *= cp[k] / cp[kp]
                dias_pos += 1
            if pend != pos:                      # ejecución de la decisión del día anterior
                valor *= (1 - costo)
                pos, ops = pend, ops + 1
            sc, _ = mod.evaluar(t, fechas[j])    # decisión de hoy, se ejecuta al cierre de mañana
            pend = 1 if sc >= 20 else 0 if sc <= -20 else pend
            serie_v.append(valor)
        k0, kn = pos_idx[fechas[0]], pos_idx[fechas[-1]]
        bh = [parte * cp[pos_idx[f]] / cp[k0] for f in fechas]
        for j in range(len(fechas)):
            estrategia[j] += serie_v[j]
            comprarmant[j] += bh[j]
        por.append({"ticker": t, "ret_estrategia": round((serie_v[-1] / parte - 1) * 100, 2),
                    "ret_comprar_mantener": round((cp[kn] / cp[k0] - 1) * 100, 2), "operaciones": ops,
                    "tiempo_en_mercado": round(100 * dias_pos / (len(fechas) - 1), 2), "en_pesos": usd})

    def dd(v):
        pico, m = v[0], 0.0
        for x in v:
            pico = max(pico, x)
            m = min(m, x / pico - 1)
        return round(m * 100, 2)

    return {"fechas": fechas, "capital": capital, "costo_pct": round(costo * 100, 2), "moneda": "pesos" if fx else "original",
            "estrategia": [round(x, 2) for x in estrategia], "comprar_mantener": [round(x, 2) for x in comprarmant],
            "metricas": {"ret_estrategia": round((estrategia[-1] / capital - 1) * 100, 2),
                         "ret_comprar_mantener": round((comprarmant[-1] / capital - 1) * 100, 2),
                         "caida_estrategia": dd(estrategia), "caida_comprar_mantener": dd(comprarmant),
                         "operaciones": sum(p["operaciones"] for p in por)},
            "por_emisora": por}
