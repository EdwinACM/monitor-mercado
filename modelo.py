"""Modelo de decisión con pesos que se recalculan cada día (validación hacia adelante).

Idea. Cada sesión, cada emisora recibe nueve «señales» técnicas (rebote semanal, RSI, bandas de Bollinger, momentum, tendencia, MACD...).
No todas funcionan siempre: en algunos periodos los precios se revierten en una semana y en otros siguen la tendencia.
Por eso el peso de cada señal se calcula con la correlación que tuvo, en las últimas 250 sesiones de las 10 emisoras en conjunto,
con el rendimiento que ocurrió 5 sesiones después. Solo se usan observaciones cuyo resultado ya se conocía ese día: nunca se mira el futuro.

Puntaje. Se combinan las señales con esos pesos y el resultado se escala con su desviación estándar reciente:
+20 ≈ 0.6 desviaciones por encima de lo normal (compra), −20 (venta); ±45 ≈ 1.35 desviaciones (señal fuerte).
Si ninguna señal tuvo poder predictivo reciente, el puntaje es 0 y la decisión es mantener.
"""
import bisect
import math

import analisis as A

HORIZ = 5            # sesiones hacia adelante que se intentan anticipar
VENTANA = 250        # sesiones de calibración
MIN_VENTANA = 100    # mínimo de sesiones para calibrar
IC_MIN = 0.03        # correlación mínima para que una señal cuente
REZAGO = 7           # sesiones de margen para que el resultado a 5 sesiones ya sea conocido en todos los mercados
ARRANQUE = 120       # sesiones previas necesarias para calcular las señales
ESCALA = 100 / 3

CRITERIOS = [
    ("rev5", "Reversión semanal (rebote tras caídas)"),
    ("rev1", "Reversión de un día"),
    ("rsi", "Sobrecompra / sobreventa (RSI)"),
    ("bb", "Posición en las bandas de Bollinger"),
    ("m20", "Momentum de 20 sesiones"),
    ("m60", "Momentum de 60 sesiones"),
    ("m120", "Momentum de 120 sesiones"),
    ("t50", "Tendencia frente a su media de 50 sesiones"),
    ("macd", "Impulso (MACD)"),
]
K = len(CRITERIOS)
TRI = [(a, b) for a in range(K) for b in range(a, K)]
IDX_TRI = {p: i for i, p in enumerate(TRI)}
M = 1 + K + 1 + 1 + K + len(TRI)  # n, sx, sy, syy, sxy, sxx


def _detalle(k, raw):
    if k == "rev5":
        return f"Rendimiento a 5 sesiones: {raw['ret5']:+.2f}%"
    if k == "rev1":
        return f"Variación de la última sesión: {raw['ret1']:+.2f}%"
    if k == "rsi":
        zona = "sobreventa" if raw["rsi"] < 30 else "sobrecompra" if raw["rsi"] > 70 else "zona neutral"
        return f"RSI de 14 sesiones: {raw['rsi']:.2f} ({zona})"
    if k == "bb":
        return f"Posición en las bandas de Bollinger: {raw['pctb'] * 100:.0f} % (0 % es la banda inferior; 100 %, la superior)"
    if k in ("m20", "m60", "m120"):
        return f"Rendimiento a {k[1:]} sesiones: {raw['r' + k[1:]]:+.2f}%"
    if k == "t50":
        return f"Precio {raw['dist50']:+.2f}% respecto a su media de 50 sesiones"
    return f"Histograma MACD {'positivo' if raw['macd'] > 0 else 'negativo'}"


def _features(c, ind):
    """Por sesión: (vector de señales, datos crudos). Todas las señales son positivas cuando favorecen comprar."""
    n = len(c)
    lr = [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, n)]
    s1, s2 = [0.0], [0.0]
    for v in lr:
        s1.append(s1[-1] + v)
        s2.append(s2[-1] + v * v)
    out = [None] * n
    for i in range(ARRANQUE, n):
        v60 = (s2[i + 1] - s2[i - 59]) / 60 - ((s1[i + 1] - s1[i - 59]) / 60) ** 2
        sd = math.sqrt(v60) if v60 > 0 else 0
        if sd == 0 or ind["rsi"][i] is None or ind["pctb"][i] is None or ind["sma50"][i] is None or ind["hist"][i] is None:
            continue
        L = lambda d: math.log(c[i] / c[i - d])
        x = [-L(5) / (sd * math.sqrt(5)), -lr[i] / sd, (50 - ind["rsi"][i]) / 10, 0.5 - ind["pctb"][i],
             L(20) / (sd * math.sqrt(20)), L(60) / (sd * math.sqrt(60)), L(120) / (sd * math.sqrt(120)),
             math.log(c[i] / ind["sma50"][i]) / sd / 10, ind["hist"][i] / c[i] / sd]
        raw = {"ret5": (c[i] / c[i - 5] - 1) * 100, "ret1": (c[i] / c[i - 1] - 1) * 100, "rsi": ind["rsi"][i], "pctb": ind["pctb"][i],
               "r20": (c[i] / c[i - 20] - 1) * 100, "r60": (c[i] / c[i - 60] - 1) * 100, "r120": (c[i] / c[i - 120] - 1) * 100,
               "dist50": (c[i] / ind["sma50"][i] - 1) * 100, "macd": ind["hist"][i]}
        out[i] = (x, raw)
    return out


class Modelo:
    def __init__(self, hist):
        self.s = {}
        agreg = {}
        for t, rows in hist.items():
            c = [r["cierre"] for r in rows]
            f = _features(c, A.indicadores(c))
            fechas = [r["fecha"] for r in rows]
            y = [(c[i + HORIZ] / c[i] - 1) * 100 if i + HORIZ < len(c) else None for i in range(len(c))]
            self.s[t] = {"fechas": fechas, "pos": {fe: i for i, fe in enumerate(fechas)}, "f": f, "y": y, "c": c}
            for i, fx in enumerate(f):
                if fx is None or y[i] is None:
                    continue
                v = agreg.setdefault(fechas[i], [0.0] * M)
                x, yy = fx[0], y[i]
                v[0] += 1
                for a in range(K):
                    v[1 + a] += x[a]
                    v[2 + K + 1 + a] += x[a] * yy
                v[1 + K] += yy
                v[2 + K] += yy * yy
                base = 3 + 2 * K
                for p, (a, b) in enumerate(TRI):
                    v[base + p] += x[a] * x[b]
        self.fechas = sorted(agreg)
        self.pref = [[0.0] * M]
        for fe in self.fechas:
            ult, v = self.pref[-1], agreg[fe]
            self.pref.append([a + b for a, b in zip(ult, v)])
        self._pesos = {}
        self._resp = {}

    # ---------------------------------------------------------------- calibración
    def pesos(self, fecha):
        """Pesos vigentes ese día, con observaciones cuyo resultado ya se conocía. None si no hay historial suficiente."""
        if fecha in self._pesos:
            return self._pesos[fecha]
        d = bisect.bisect_right(self.fechas, fecha) - 1
        fin = d - REZAGO
        ini = max(0, fin - VENTANA + 1)
        res = None
        if fin - ini + 1 >= MIN_VENTANA:
            S = [a - b for a, b in zip(self.pref[fin + 1], self.pref[ini])]
            n = S[0]
            if n > 200:
                mu = [S[1 + a] / n for a in range(K)]
                my = S[1 + K] / n
                sy = math.sqrt(max(S[2 + K] / n - my * my, 1e-12))
                base = 3 + 2 * K
                cov = lambda a, b: S[base + IDX_TRI[(min(a, b), max(a, b))]] / n - mu[a] * mu[b]
                s = [math.sqrt(max(cov(a, a), 1e-12)) for a in range(K)]
                ic = [(S[3 + K + a] / n - mu[a] * my) / (s[a] * sy) for a in range(K)]
                w = [x if abs(x) >= IC_MIN else 0.0 for x in ic]
                a_ = [w[k] / s[k] for k in range(K)]
                var = sum(a_[p] * a_[q] * cov(p, q) for p in range(K) for q in range(K))
                res = {"ic": ic, "w": w, "mu": mu, "s": s, "a": a_, "sigma": math.sqrt(var) if var > 1e-12 else 0.0, "n": int(n),
                       "desde": self.fechas[ini], "hasta": self.fechas[fin], "sesiones": fin - ini + 1}
        self._pesos[fecha] = res
        return res

    # ------------------------------------------------------------------ puntaje
    def evaluar(self, t, fecha):
        """(puntaje -100..+100, lista de criterios con puntos y explicación)."""
        s = self.s.get(t)
        i = s["pos"].get(fecha) if s else None
        fx = s["f"][i] if i is not None else None
        p = self.pesos(fecha)
        if fx is None or p is None:
            return 0, [{"criterio": "Historial insuficiente", "puntos": 0, "max": 40,
                        "detalle": "Se necesitan al menos 120 sesiones previas y 100 sesiones de calibración para tomar una decisión"}]
        x, raw = fx
        comp = []
        for k, (clave, nombre) in enumerate(CRITERIOS):
            if p["sigma"] > 0 and p["w"][k]:
                pts = max(-40, min(40, round(ESCALA * p["a"][k] * (x[k] - p["mu"][k]) / p["sigma"])))
            else:
                pts = 0
            if not p["w"][k]:
                nota = f"sin poder predictivo reciente (correlación {p['ic'][k]:+.2f}), no suma"
            elif p["w"][k] > 0:
                nota = f"lectura habitual vigente (correlación reciente {p['ic'][k]:+.2f})"
            else:
                nota = f"lectura invertida: en las últimas sesiones anticipó lo contrario (correlación {p['ic'][k]:+.2f})"
            comp.append({"criterio": nombre, "puntos": int(pts), "max": 40, "detalle": f"{_detalle(clave, raw)}; {nota}",
                         "correlacion": round(p["ic"][k], 3)})
        score = max(-100, min(100, sum(c["puntos"] for c in comp)))
        return int(score), comp

    def calibracion(self, fecha):
        p = self.pesos(fecha)
        if not p:
            return None
        return {"desde": p["desde"], "hasta": p["hasta"], "sesiones": p["sesiones"], "observaciones": p["n"],
                "criterios": [{"criterio": n, "correlacion": round(p["ic"][k], 3), "activo": bool(p["w"][k])} for k, (_, n) in enumerate(CRITERIOS)]}

    # ----------------------------------------------------------------- respaldo
    def respaldo(self, fecha):
        if fecha not in self._resp:
            self._resp[fecha] = self._respaldo(fecha)
        return self._resp[fecha]

    def _respaldo(self, fecha):
        """Qué pasó, dentro de la muestra de calibración y con los pesos de ese día, tras cada tipo de decisión (a 5 sesiones)."""
        p = self.pesos(fecha)
        if not p or p["sigma"] <= 0:
            return None
        compra, venta, mant, todas = [], [], [], []
        for t, s in self.s.items():
            for i, fx in enumerate(s["f"]):
                f = s["fechas"][i]
                if fx is None or s["y"][i] is None or not (p["desde"] <= f <= p["hasta"]):
                    continue
                sc = sum(ESCALA * p["a"][k] * (fx[0][k] - p["mu"][k]) / p["sigma"] for k in range(K) if p["w"][k])
                y = s["y"][i]
                todas.append(y)
                (compra if sc >= 20 else venta if sc <= -20 else mant).append(y)
        pc = lambda xs, fn: round(100 * sum(1 for v in xs if fn(v)) / len(xs), 2) if xs else None
        return {"n": len(todas), "base_sube": pc(todas, lambda v: v > 0),
                "compra": {"n": len(compra), "sube": pc(compra, lambda v: v > 0), "media": round(sum(compra) / len(compra), 2) if compra else None},
                "venta": {"n": len(venta), "baja": pc(venta, lambda v: v < 0), "media": round(sum(venta) / len(venta), 2) if venta else None},
                "mantener": {"n": len(mant), "quieto": pc(mant, lambda v: abs(v) <= 2)},
                "desde": p["desde"], "hasta": p["hasta"]}


    def backtest(self, t, fecha):
        """Resultado a 5 sesiones de las señales de esta emisora (dentro de la muestra de calibración y con los pesos de ese día)."""
        p = self.pesos(fecha)
        s = self.s.get(t)
        if not p or p["sigma"] <= 0 or not s:
            return None
        compra, venta, todas = [], [], []
        for i, fx in enumerate(s["f"]):
            f = s["fechas"][i]
            if fx is None or s["y"][i] is None or not (p["desde"] <= f <= p["hasta"]):
                continue
            sc = sum(ESCALA * p["a"][k] * (fx[0][k] - p["mu"][k]) / p["sigma"] for k in range(K) if p["w"][k])
            y = s["y"][i]
            todas.append(y)
            if sc >= 20:
                compra.append(y)
            elif sc <= -20:
                venta.append(y)
        pc = lambda xs, fn: round(100 * sum(1 for v in xs if fn(v)) / len(xs), 2) if xs else None
        md = lambda xs: round(sum(xs) / len(xs), 2) if xs else None
        return {"horizonte": HORIZ, "muestra": len(todas), "base_rend_medio": md(todas),
                "n_compra": len(compra), "aciertos_compra": pc(compra, lambda v: v > 0), "rend_medio_compra": md(compra),
                "n_venta": len(venta), "aciertos_venta": pc(venta, lambda v: v < 0), "rend_medio_venta": md(venta)}


_cache = {}


def obtener(hist):
    """Modelo para este conjunto de historiales (se reutiliza mientras no cambien)."""
    firma = tuple(sorted((t, rows[-1]["fecha"], len(rows), round(rows[-1]["cierre"], 4)) for t, rows in hist.items() if rows))
    if firma not in _cache:
        _cache.clear()
        _cache[firma] = Modelo({t: rows for t, rows in hist.items() if rows})
    return _cache[firma]
