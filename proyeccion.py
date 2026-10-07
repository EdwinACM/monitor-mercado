"""Proyecciones y medidas estadísticas de finanzas (solo biblioteca estándar).

Las proyecciones NO son pronósticos de lo que «va a pasar»: son rangos de probabilidad. El precio futuro se modela con
rendimientos logarítmicos normales cuya volatilidad se estima con un promedio móvil exponencial (EWMA, λ = 0.94, método
RiskMetrics), que da más peso a lo ocurrido recientemente. Cada rango se contrasta con lo que habría pasado en las últimas
250 sesiones (cobertura) para que se vea qué tan confiable es.
"""
import bisect
import math
from statistics import mean, pstdev

import analisis as A

LAMBDA = 0.94
HORIZONTES = (5, 20, 60)
Z68, Z95 = 1.0, 1.959964
DIAS_ANIO = 252


def _logret(c):
    return [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]


def sigmas_ewma(lr, lam=LAMBDA):
    """Volatilidad diaria estimada al cierre de cada sesión (sin usar datos posteriores)."""
    base = lr[:20] if len(lr) >= 20 else lr
    s2 = sum(x * x for x in base) / max(1, len(base))
    out = []
    for x in lr:
        s2 = lam * s2 + (1 - lam) * x * x
        out.append(math.sqrt(s2))
    return out


def _cobertura(c, sig, h, n=250):
    """Qué porcentaje de las veces el precio real cayó dentro del rango proyectado (últimas n sesiones)."""
    d68 = d95 = tot = 0
    fin = len(c) - 1 - h
    for t in range(max(30, fin - n + 1), fin + 1):
        s = sig[t - 1]  # sigma estimada con datos hasta t
        if not s:
            continue
        z = math.log(c[t + h] / c[t]) / (s * math.sqrt(h))
        tot += 1
        d68 += abs(z) <= Z68
        d95 += abs(z) <= Z95
    if not tot:
        return None
    return {"n": tot, "p68": round(100 * d68 / tot, 2), "p95": round(100 * d95 / tot, 2)}


def proyectar(c, maximo=60):
    """Rangos de precio a 5, 20 y 60 sesiones, abanico diario y cobertura histórica del método."""
    if len(c) < 60:
        return None
    lr = _logret(c)
    sig = sigmas_ewma(lr)
    sd = sig[-1]
    c0 = c[-1]
    slope, r2 = A._linreg([math.log(x) for x in c[-30:]])
    rango = lambda h, z: (c0 * math.exp(-0.5 * sd * sd * h - z * sd * math.sqrt(h)), c0 * math.exp(-0.5 * sd * sd * h + z * sd * math.sqrt(h)))
    tend = lambda h: c0 * math.exp(slope * r2 * h)
    hs = []
    for h in HORIZONTES:
        b68, b95 = rango(h, Z68), rango(h, Z95)
        hs.append({"h": h, "esperado": round(c0, 2), "mediana": round(c0 * math.exp(-0.5 * sd * sd * h), 2),
                   "b68": [round(b68[0], 2), round(b68[1], 2)], "b95": [round(b95[0], 2), round(b95[1], 2)],
                   "tendencia": round(tend(h), 2), "sigma_h": round(sd * math.sqrt(h) * 100, 2),
                   "cobertura": _cobertura(c, sig, h) if h <= 20 else None})
    ab = {"h": list(range(1, maximo + 1)), "mediana": [], "lo68": [], "hi68": [], "lo95": [], "hi95": [], "tendencia": []}
    for h in ab["h"]:
        ab["mediana"].append(round(c0 * math.exp(-0.5 * sd * sd * h), 2))
        a, b = rango(h, Z68)
        ab["lo68"].append(round(a, 2))
        ab["hi68"].append(round(b, 2))
        a, b = rango(h, Z95)
        ab["lo95"].append(round(a, 2))
        ab["hi95"].append(round(b, 2))
        ab["tendencia"].append(round(tend(h), 2))
    return {"base": round(c0, 2), "sigma_diaria": round(sd * 100, 2), "sigma_anual": round(sd * math.sqrt(DIAS_ANIO) * 100, 2),
            "pendiente_tendencia": round(slope * 100, 3), "r2_tendencia": round(r2, 2), "horizontes": hs, "abanico": ab,
            "texto": (f"Con la volatilidad reciente ({sd * math.sqrt(DIAS_ANIO) * 100:.2f}% anual), el precio de {c0:,.2f} podría estar entre "
                      f"{hs[0]['b95'][0]:,.2f} y {hs[0]['b95'][1]:,.2f} dentro de 5 sesiones, y entre {hs[1]['b95'][0]:,.2f} y {hs[1]['b95'][1]:,.2f} dentro de 20, "
                      f"con 95% de probabilidad. Es un rango de probabilidad, no un pronóstico del precio.")}


# ------------------------------------------------------------ riesgo y rendimiento
def _asimetria_curtosis(x):
    n = len(x)
    m = mean(x)
    sd = pstdev(x)
    if n < 8 or not sd:
        return None, None
    return sum(((v - m) / sd) ** 3 for v in x) / n, sum(((v - m) / sd) ** 4 for v in x) / n - 3


def riesgo_mercado(cierres, bench, rf):
    """Medidas de rendimiento ajustado por riesgo de una acción frente a su índice y a la tasa libre de riesgo.

    cierres, bench: [(fecha, valor)] del periodo; rf: [(fecha, % anual)] (CETES/Banxico para pesos, EFFR para dólares)."""
    b = dict(bench)
    pts = [(f, v) for f, v in cierres if f in b]
    if len(pts) < 25:
        return None
    fechas = [f for f, _ in pts]
    r = [pts[i][1] / pts[i - 1][1] - 1 for i in range(1, len(pts))]
    rb = [b[fechas[i]] / b[fechas[i - 1]] - 1 for i in range(1, len(pts))]
    rff, rfv = [x[0] for x in rf], [x[1] for x in rf]
    libre = []
    for i in range(1, len(fechas)):
        k = bisect.bisect_right(rff, fechas[i]) - 1
        libre.append((rfv[k] if k >= 0 else (rfv[0] if rfv else 0)) / 100 / DIAS_ANIO)
    ex = [a - l for a, l in zip(r, libre)]
    exb = [a - l for a, l in zip(rb, libre)]
    mx, mb = mean(ex), mean(exb)
    vb = sum((x - mb) ** 2 for x in exb) / len(exb)
    cov = sum((x - mx) * (y - mb) for x, y in zip(ex, exb)) / len(ex)
    beta = cov / vb if vb else None
    sd = pstdev(ex)
    r2 = (cov * cov / (vb * sd * sd)) if vb and sd else None
    neg = [min(x, 0) for x in ex]
    dd = math.sqrt(sum(x * x for x in neg) / len(neg))
    alfa = (mx - beta * mb) * DIAS_ANIO * 100 if beta is not None else None
    asim, curt = _asimetria_curtosis(r)
    sdr = pstdev(r)
    return {"n": len(r), "beta": beta, "alfa_anual": alfa, "r2": r2,
            "sharpe": mx / sd * math.sqrt(DIAS_ANIO) if sd else None, "sortino": mx / dd * math.sqrt(DIAS_ANIO) if dd else None,
            "asimetria": asim, "curtosis": curt, "var20": 1.645 * sdr * math.sqrt(20) * 100, "tasa_libre": mean(libre) * DIAS_ANIO * 100}


# ----------------------------------------------------------------- portafolio
def _proy_simplex(v):
    """Proyección euclidiana sobre {w >= 0, suma 1}."""
    u = sorted(v, reverse=True)
    css, rho = 0.0, 0
    for i, x in enumerate(u, 1):
        css += x
        if x - (css - 1) / i > 0:
            rho, cs = i, css
    t = (cs - 1) / rho
    return [max(x - t, 0.0) for x in v]


def portafolio(rets):
    """rets: {ticker: [rendimientos diarios alineados]}. Equiponderado frente al de mínima varianza (sin ventas en corto)."""
    tks = list(rets)
    n = len(tks)
    if n < 2 or len(rets[tks[0]]) < 20:
        return None
    T = len(rets[tks[0]])
    mu = [mean(rets[t]) for t in tks]
    cov = [[sum((rets[a][i] - mu[x]) * (rets[b][i] - mu[y]) for i in range(T)) / T for y, b in enumerate(tks)] for x, a in enumerate(tks)]
    vol = lambda w: math.sqrt(max(sum(w[i] * w[j] * cov[i][j] for i in range(n) for j in range(n)), 0)) * math.sqrt(DIAS_ANIO) * 100
    ret = lambda w: sum(w[i] * mu[i] for i in range(n)) * DIAS_ANIO * 100
    ew = [1 / n] * n
    w = ew[:]
    paso = 1 / (2 * max(max(cov[i][i] for i in range(n)), 1e-12) * n)
    for _ in range(3000):
        g = [2 * sum(cov[i][j] * w[j] for j in range(n)) for i in range(n)]
        w = _proy_simplex([w[i] - paso * g[i] for i in range(n)])
    individual = [math.sqrt(cov[i][i]) * math.sqrt(DIAS_ANIO) * 100 for i in range(n)]
    v_ew = vol(ew)
    return {"tickers": tks, "equiponderado": {"pesos": [round(x * 100, 2) for x in ew], "vol_anual": round(v_ew, 2), "ret_anual": round(ret(ew), 2)},
            "min_varianza": {"pesos": [round(x * 100, 2) for x in w], "vol_anual": round(vol(w), 2), "ret_anual": round(ret(w), 2)},
            "vol_individual_promedio": round(sum(individual) / n, 2), "razon_diversificacion": round((sum(individual) / n) / v_ew, 2) if v_ew else None}


# --------------------------------------------------------------------- deuda
def duracion(nombre, valor):
    """Duración modificada aproximada (años): cuánto cambia el precio por cada 1 punto porcentual de cambio en la tasa."""
    if valor is None:
        return None
    n = nombre.upper()
    if n.startswith("CETES"):
        dias = int("".join(ch for ch in n.split()[1] if ch.isdigit()) or 28)
        return dias / 360 / (1 + valor / 100 * dias / 360)
    if n.startswith("BONOS M") or n.startswith("UDIBONOS"):
        anios = int("".join(ch for ch in n.split()[2] if ch.isdigit()) or 10)
        y = valor / 100
        return (1 - (1 + y / 2) ** (-2 * anios)) / y if y > 0 else None  # bono a la par con cupón semestral
    if n.startswith("BONDES") or n.startswith("BPAG"):
        return 28 / 360  # tasa flotante: se ajusta cada 28 días
    return None


def proyectar_deuda(valores, pasos=(1, 4), ventana=12):
    """Rango del próximo rendimiento con una recta ajustada a las últimas `ventana` cifras (intervalo de predicción de 95 %)."""
    y = valores[-ventana:]
    n = len(y)
    if n < 6:
        return None
    x = list(range(n))
    mx, my = (n - 1) / 2, mean(y)
    sxx = sum((i - mx) ** 2 for i in x)
    b = sum((i - mx) * (v - my) for i, v in zip(x, y)) / sxx
    a = my - b * mx
    res = [v - (a + b * i) for i, v in zip(x, y)]
    s = math.sqrt(sum(e * e for e in res) / (n - 2))
    tcrit = {6: 2.776, 7: 2.571, 8: 2.447, 9: 2.365, 10: 2.306, 11: 2.262, 12: 2.228}.get(n, 2.228)
    out = []
    for h in pasos:
        t = n - 1 + h
        c = a + b * t
        m = tcrit * s * math.sqrt(1 + 1 / n + (t - mx) ** 2 / sxx)
        out.append({"pasos": h, "centro": round(c, 2), "bajo": round(c - m, 2), "alto": round(c + m, 2)})
    return {"pendiente": round(b, 4), "error_tipico": round(s, 4), "n": n, "proyecciones": out}
