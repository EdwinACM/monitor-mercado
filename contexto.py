"""Entorno global del periodo: tipo de cambio, tasas, mercados de EE. UU. y cómo se relacionan con los instrumentos.

Los datos son los de fuentes.py (oficiales donde existen). Las lecturas se redactan solo con esas cifras;
las explicaciones generales de «cómo afecta» están en glosario.py.
"""
import bisect
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from statistics import StatisticsError, correlation, mean, pvariance

import fuentes
import glosario
import server as S

# id, grupo, unidad, tipo ("nivel" cambia en %, "tasa" cambia en puntos base), decimales, fuente
DEFS = [
    ("fx", "México y el dólar", "MXN por USD", "nivel", 2, "banxico"),
    ("tasa_obj", "México y el dólar", "% anual", "tasa", 2, "banxico"),
    ("tiie28", "México y el dólar", "% anual", "tasa", 2, "banxico"),
    ("infl_mx", "México y el dólar", "% anual", "tasa", 2, "banxico"),
    ("ipc", "México y el dólar", "puntos", "nivel", 2, "yahoo"),
    ("dxy", "México y el dólar", "puntos", "nivel", 2, "yahoo"),
    ("effr", "Estados Unidos", "% anual", "tasa", 2, "nyfed"),
    ("ust3m", "Estados Unidos", "% anual", "tasa", 2, "tesoro"),
    ("ust2y", "Estados Unidos", "% anual", "tasa", 2, "tesoro"),
    ("ust10y", "Estados Unidos", "% anual", "tasa", 2, "tesoro"),
    ("ust30y", "Estados Unidos", "% anual", "tasa", 2, "tesoro"),
    ("infl_us", "Estados Unidos", "% anual", "tasa", 2, "bls"),
    ("sp500", "Estados Unidos", "puntos", "nivel", 2, "yahoo"),
    ("nasdaq", "Estados Unidos", "puntos", "nivel", 2, "yahoo"),
    ("dow", "Estados Unidos", "puntos", "nivel", 2, "yahoo"),
    ("vix", "Estados Unidos", "puntos", "nivel", 2, "cboe"),
    ("stoxx", "Otros mercados", "puntos", "nivel", 2, "yahoo"),
    ("nikkei", "Otros mercados", "puntos", "nivel", 2, "yahoo"),
    ("ftse", "Otros mercados", "puntos", "nivel", 2, "yahoo"),
    ("shanghai", "Otros mercados", "puntos", "nivel", 2, "yahoo"),
]
YAHOO = {"sp500": "^GSPC", "nasdaq": "^IXIC", "dow": "^DJI", "dxy": "DX-Y.NYB", "ipc": "^MXX",
         "stoxx": "^STOXX50E", "nikkei": "^N225", "ftse": "^FTSE", "shanghai": "000001.SS"}
MENSUALES = {"infl_mx", "infl_us"}


# ----------------------------------------------------------------------- carga
def _cargar(hasta):
    d0 = S.INICIO - timedelta(days=15)
    res, err = {}, {}

    def tarea(clave, fn):
        try:
            return clave, fn(), None
        except Exception as e:  # una fuente caída no tumba el informe
            return clave, None, f"{type(e).__name__}: {e}"

    def banxico():
        out = {}
        for k, fn in (("fx", lambda: fuentes.fx_fix(d0, hasta)), ("fxc", lambda: fuentes.fx_cierre(d0, hasta)),
                      ("tasa_obj", lambda: fuentes.tasa_objetivo(d0, hasta)), ("tiie28", lambda: fuentes.tiie28(d0, hasta)),
                      ("infl_mx", lambda: fuentes.inflacion_mx(S.INICIO, hasta))):
            out[k] = tarea(k, fn)
        return out

    trabajos = [("banxico", banxico), ("tesoro", lambda: fuentes.tesoro(d0, hasta)), ("effr", lambda: fuentes.effr(d0, hasta)),
                ("infl_us", lambda: fuentes.inflacion_us(S.INICIO, hasta)), ("vix", lambda: fuentes.vix(d0, hasta))]
    trabajos += [(k, (lambda t=t: fuentes.yahoo_cierres(t, d0))) for k, t in YAHOO.items()]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for clave, val, e in ex.map(lambda t: tarea(*t), trabajos):
            if clave == "banxico":
                for k, (_, v, ee) in val.items():
                    (err if ee else res).__setitem__(k, ee or v)
            elif e:
                err[clave] = e
            elif clave == "tesoro":
                for plazo, k in (("3 Mo", "ust3m"), ("2 Yr", "ust2y"), ("10 Yr", "ust10y"), ("30 Yr", "ust30y")):
                    res[k] = val[plazo]
            elif clave == "effr":
                res["effr"], res["_rango_fed"] = val
            else:
                res[clave] = val
    return res, err


def series(hasta):
    ttl = 15 * 60 if S.mercado_abierto() else 3 * 3600
    return S.cached(("ctx", hasta), ttl, lambda: _cargar(hasta))


# --------------------------------------------------------------------- utilidades
def _valor_en(serie, f):
    """Último valor con fecha <= f (None si no hay)."""
    i = bisect.bisect_right([x[0] for x in serie], f)
    return serie[i - 1] if i else None


def _rend(a, b):
    return (b / a - 1) * 100 if a else None


def _corte(serie, desde, hasta):
    return [(f, v) for f, v in serie if desde <= f <= hasta]


def _resumen(serie, tipo, desde, hasta):
    pts = _corte(serie, desde, hasta)
    if not pts and serie:  # series mensuales: el último dato publicado antes del fin del periodo
        ult = _valor_en(serie, hasta)
        pts = [ult] if ult else []
    if not pts:
        return None
    ini, fin = pts[0], pts[-1]
    cambio = (fin[1] - ini[1]) * 100 if tipo == "tasa" else _rend(ini[1], fin[1])
    return {"ini": {"fecha": ini[0], "valor": ini[1]}, "fin": {"fecha": fin[0], "valor": fin[1]}, "cambio": cambio,
            "cambio_unidad": "pb" if tipo == "tasa" else "%", "serie": [[f, round(v, 4)] for f, v in pts]}


def _f(x, d=2):
    return f"{x:,.{d}f}"


def _sg(x, d=2, suf=""):
    return f"{'+' if x > 0 else '−' if x < 0 else ''}{abs(x):,.{d}f}{suf}"


def _fecha(f):
    y, m, d = f.split("-")
    return f"{d}/{m}/{y}"


def _mes(f):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    y, m, _ = f.split("-")
    return f"{meses[int(m) - 1]} de {y}"


# ------------------------------------------------------------------ sensibilidades
def _retornos(cierres):
    return [(cierres[i][0], cierres[i][1] / cierres[i - 1][1] - 1) for i in range(1, len(cierres))]


def sensibilidades(hist, serie_sp, serie_fx, serie_ipc, desde, hasta):
    """Correlación y beta diaria de cada acción frente al S&P 500, correlación con el dólar y (acciones de México) con el IPC."""
    sp = dict(_corte(serie_sp, desde, hasta))
    fx = serie_fx
    ipc = dict(_corte(serie_ipc, desde, hasta)) if serie_ipc else {}
    out = []
    for t, rows in hist.items():
        cierres = [(r["fecha"], r["cierre"]) for r in rows if desde <= r["fecha"] <= hasta]
        cierres_sp = [(f, c) for f, c in cierres if f in sp]
        if len(cierres_sp) < 20:
            continue
        r_acc = [(cierres_sp[i][0], cierres_sp[i][1] / cierres_sp[i - 1][1] - 1) for i in range(1, len(cierres_sp))]
        r_sp = [sp[cierres_sp[i][0]] / sp[cierres_sp[i - 1][0]] - 1 for i in range(1, len(cierres_sp))]
        x = [v for _, v in r_acc]
        try:
            c_sp = correlation(x, r_sp)
            beta = (sum((a - mean(r_sp)) * (b - mean(x)) for a, b in zip(r_sp, x)) / len(x)) / pvariance(r_sp)
        except (StatisticsError, ZeroDivisionError):
            c_sp = beta = None
        c_fx = None
        fxp = [(cierres_sp[i][0], _valor_en(fx, cierres_sp[i][0])) for i in range(len(cierres_sp))]
        if all(p[1] for p in fxp):
            r_fx = [fxp[i][1][1] / fxp[i - 1][1][1] - 1 for i in range(1, len(fxp))]
            try:
                c_fx = correlation(x, r_fx)
            except StatisticsError:
                c_fx = None
        c_ipc = None
        if S.META[t]["pais"] == "México" and ipc:
            cc = [(f, c) for f, c in cierres if f in ipc]
            if len(cc) >= 20:
                try:
                    c_ipc = correlation([cc[i][1] / cc[i - 1][1] - 1 for i in range(1, len(cc))],
                                        [ipc[cc[i][0]] / ipc[cc[i - 1][0]] - 1 for i in range(1, len(cc))])
                except StatisticsError:
                    c_ipc = None
        out.append({"ticker": t, "nombre": S.ACCIONES[t], "pais": S.META[t]["pais"], "moneda": S.META[t]["moneda"], "n": len(x),
                    "corr_sp500": c_sp, "beta_sp500": beta, "corr_dolar": c_fx, "corr_ipc": c_ipc})
    return out


def efecto_cambiario(hist, serie_fx, desde, hasta):
    """Rendimiento de las acciones de EE. UU. en dólares y en pesos (con el tipo de cambio de cierre de Banxico)."""
    out = []
    for t, rows in hist.items():
        if S.META[t]["moneda"] != "USD":
            continue
        rr = [r for r in rows if desde <= r["fecha"] <= hasta]
        if len(rr) < 2:
            continue
        f0, f1 = rr[0]["fecha"], rr[-1]["fecha"]
        x0, x1 = _valor_en(serie_fx, f0), _valor_en(serie_fx, f1)
        if not x0 or not x1:
            continue
        r_usd = _rend(rr[0]["cierre"], rr[-1]["cierre"])
        r_fx = _rend(x0[1], x1[1])
        out.append({"ticker": t, "nombre": S.ACCIONES[t], "desde": f0, "hasta": f1, "ret_usd": r_usd, "ret_dolar": r_fx,
                    "ret_pesos": ((1 + r_usd / 100) * (1 + r_fx / 100) - 1) * 100})
    return out


# ---------------------------------------------------------------------- diferenciales
def diferenciales(ind, desde, hasta):
    out = []
    try:
        d = {x["id"]: x for x in ind}
        if "tasa_obj" in d and "effr" in d:
            a, b = d["tasa_obj"]["fin"]["valor"], d["effr"]["fin"]["valor"]
            out.append({"nombre": "Tasa objetivo de Banxico menos tasa efectiva de la Fed", "pb": (a - b) * 100,
                        "detalle": f"{_f(a)}% menos {_f(b)}%", "lectura": "Un diferencial amplio suele ayudar a sostener al peso (los inversionistas ganan más por tener pesos)."})
        deu = S.deuda(date.today() - timedelta(days=300))
        bm = next((x for x in deu if x["nombre"] == "BONOS M 10 años"), None)
        ce = next((x for x in deu if x["nombre"] == "CETES 28 días"), None)
        ust = dict(fuentes.tesoro(S.INICIO - timedelta(days=15), hasta)["10 Yr"]) if True else {}
        if bm and bm["datos"]:
            bm_p = [x for x in bm["datos"] if desde <= x["fecha"] <= hasta]
            if bm_p:
                u = bm_p[-1]
                ref = _valor_en(sorted(ust.items()), u["fecha"])
                if ref:
                    out.append({"nombre": "Bono M a 10 años menos Tesoro de EE. UU. a 10 años", "pb": (u["valor"] - ref[1]) * 100,
                                "detalle": f"{_f(u['valor'])}% menos {_f(ref[1])}% (subasta del {_fecha(u['fecha'])})",
                                "lectura": "Es el rendimiento adicional que paga México por prestarle a 10 años frente a EE. UU."})
        if ce and ce["datos"] and "tasa_obj" in d:
            ce_p = [x for x in ce["datos"] if desde <= x["fecha"] <= hasta]
            if ce_p:
                u = ce_p[-1]
                obj = _valor_en(fuentes_serie(d["tasa_obj"]), u["fecha"])
                if obj:
                    out.append({"nombre": "CETES a 28 días menos tasa objetivo de Banxico", "pb": (u["valor"] - obj[1]) * 100,
                                "detalle": f"{_f(u['valor'])}% menos {_f(obj[1])}% (subasta del {_fecha(u['fecha'])})",
                                "lectura": "Si los CETES rinden menos que la tasa objetivo, suele interpretarse como que el mercado espera recortes de tasa."})
    except Exception:
        pass
    return out


def fuentes_serie(ind):
    return [(f, v) for f, v in ind["serie"]]


# ----------------------------------------------------------------------- lectura
def _lectura(ind, difs, sens, efecto, rango):
    d = {x["id"]: x for x in ind}
    ps = []
    try:
        if "fx" in d:
            x = d["fx"]
            c = x["cambio"]
            t = (f"Tipo de cambio. El FIX de Banxico pasó de ${_f(x['ini']['valor'])} el {_fecha(x['ini']['fecha'])} a ${_f(x['fin']['valor'])} el {_fecha(x['fin']['fecha'])} "
                 f"({_sg(c, 2, '%')}): el peso se {'depreció' if c > 0 else 'apreció'} frente al dólar. ")
            if "dxy" in d:
                t += f"En el mismo lapso el índice del dólar (DXY) {'subió' if d['dxy']['cambio'] > 0 else 'bajó'} {_f(abs(d['dxy']['cambio']))}%. "
            t += (f"Para quien compra acciones de EE. UU. con pesos, un peso {'más débil' if c > 0 else 'más fuerte'} "
                  f"{'suma' if c > 0 else 'resta'} aproximadamente {_f(abs(c))} puntos porcentuales al rendimiento que esas acciones tienen en dólares.")
            ps.append(t)
        if "sp500" in d:
            t = (f"Bolsa de EE. UU. El S&P 500 {'avanzó' if d['sp500']['cambio'] > 0 else 'retrocedió'} {_f(abs(d['sp500']['cambio']))}% en el periodo"
                 + (f" y el Nasdaq {'avanzó' if d['nasdaq']['cambio'] > 0 else 'retrocedió'} {_f(abs(d['nasdaq']['cambio']))}%" if "nasdaq" in d else "") + ". ")
            if "ipc" in d:
                t += f"El S&P/BMV IPC {'avanzó' if d['ipc']['cambio'] > 0 else 'retrocedió'} {_f(abs(d['ipc']['cambio']))}% en pesos. "
            if "vix" in d:
                v = d["vix"]["fin"]["valor"]
                t += (f"El VIX cerró en {_f(v)} el {_fecha(d['vix']['fin']['fecha'])}, nivel de {'calma' if v < 20 else 'nerviosismo moderado' if v < 30 else 'estrés'} "
                      "(por debajo de 20 suele haber calma; por arriba de 30, estrés).")
            ps.append(t)
        if "ust10y" in d:
            x = d["ust10y"]
            t = f"Tasas en EE. UU. El Tesoro a 10 años rinde {_f(x['fin']['valor'])}% ({_sg(x['cambio'], 2, ' pb')} desde el inicio del periodo)"
            if "ust2y" in d:
                spread = (x["fin"]["valor"] - d["ust2y"]["fin"]["valor"]) * 100
                t += f" y a 2 años {_f(d['ust2y']['fin']['valor'])}%; la curva entre 10 y 2 años está {'invertida' if spread < 0 else 'con pendiente positiva'} ({_sg(spread, 2, ' pb')})"
            t += ". "
            if "effr" in d:
                t += f"La tasa efectiva de fondos federales es {_f(d['effr']['fin']['valor'])}%"
                if rango and rango[0] is not None:
                    t += f" dentro del rango objetivo de la Fed ({_f(float(rango[0]))}% a {_f(float(rango[1]))}%)"
                t += "."
            ps.append(t)
        if "tasa_obj" in d:
            x = d["tasa_obj"]
            t = (f"Tasas en México. La tasa objetivo de Banxico está en {_f(x['fin']['valor'])}% "
                 f"({'sin cambio' if abs(x['cambio']) < 0.5 else _sg(x['cambio'], 2, ' pb') + ' en el periodo'})")
            if "tiie28" in d:
                t += f" y la TIIE a 28 días en {_f(d['tiie28']['fin']['valor'])}%"
            t += ". "
            if difs:
                t += " ".join(f"{q['nombre']}: {_sg(q['pb'], 2, ' pb')}." for q in difs[:3])
            ps.append(t)
        inf = []
        if "infl_mx" in d:
            inf.append(f"México {_f(d['infl_mx']['fin']['valor'])}% ({_mes(d['infl_mx']['fin']['fecha'])})")
        if "infl_us" in d:
            inf.append(f"EE. UU. {_f(d['infl_us']['fin']['valor'])}% ({_mes(d['infl_us']['fin']['fecha'])})")
        if inf:
            ps.append("Inflación anual. " + "; ".join(inf) + ". Con inflación más alta los bancos centrales tardan más en bajar tasas, lo que sostiene los rendimientos de los bonos y presiona a las acciones.")
        if sens:
            ok = [s for s in sens if s["corr_sp500"] is not None]
            if ok:
                a = max(ok, key=lambda s: s["corr_sp500"])
                b = min(ok, key=lambda s: s["corr_sp500"])
                t = (f"Qué tan ligadas están tus acciones a EE. UU. En el periodo, la más ligada al S&P 500 fue {a['nombre']} (correlación {_f(a['corr_sp500'])}) "
                     f"y la menos ligada {b['nombre']} ({_f(b['corr_sp500'])}). La correlación mide si dos precios se mueven juntos; no prueba que uno cause al otro.")
                ps.append(t)
        if efecto:
            ps.append("Acciones de EE. UU. vistas desde México. " + "; ".join(
                f"{e['nombre']} {_sg(e['ret_usd'], 2, '%')} en dólares y {_sg(e['ret_pesos'], 2, '%')} en pesos" for e in efecto) + ".")
    except Exception as e:  # nunca romper el informe por un texto
        ps.append(f"(No se pudo redactar parte de la lectura: {e})")
    return ps


# ------------------------------------------------------------------------ principal
def construir(desde, hasta, acciones_items=None):
    res, err = series(hasta)
    d_iso, h_iso = desde.isoformat(), hasta.isoformat()
    ind = []
    for id_, grupo, unidad, tipo, dec, fuente in DEFS:
        if id_ not in res:
            continue
        r = _resumen(res[id_], tipo, d_iso, h_iso)
        if not r:
            continue
        nombre, que_es, como = glosario.INDICADORES[id_]
        f = {**fuentes.FUENTES[fuente], "id": fuente}
        if fuente == "banxico":
            f["cuadro"] = {"fx": "CF102", "tasa_obj": "CF101", "tiie28": "CF101", "infl_mx": "CP151"}.get(id_)
            f["url"] = fuentes.cuadro_url(f["cuadro"]) if f["cuadro"] else f["url"]
        ind.append({"id": id_, "nombre": nombre, "grupo": grupo, "unidad": unidad, "tipo": tipo, "dec": dec, "fuente": f,
                    "mensual": id_ in MENSUALES, "que_es": que_es, "como_afecta": como, **r})
    hist = S._historiales()
    hist = {t: rows for t, rows in hist.items() if (not acciones_items) or t in {a["ticker"] for a in acciones_items if "error" not in a}}
    sens = sensibilidades(hist, res.get("sp500", []), res.get("fxc", []), res.get("ipc", []), d_iso, h_iso) if res.get("sp500") and res.get("fxc") else []
    efecto = efecto_cambiario(hist, res.get("fxc", []), d_iso, h_iso) if res.get("fxc") else []
    difs = diferenciales(ind, d_iso, h_iso)
    privados = []
    try:
        privados = fuentes.privados_mensual(desde - timedelta(days=31), hasta)
    except Exception as e:
        err["privados"] = f"{type(e).__name__}: {e}"
    usadas = {x["fuente"]["id"]: x["fuente"] for x in ind}
    return {"periodo": {"desde": d_iso, "hasta": h_iso}, "indicadores": ind, "diferenciales": difs, "sensibilidades": sens,
            "efecto_cambiario": efecto, "privados": privados, "lectura": _lectura(ind, difs, sens, efecto, res.get("_rango_fed")),
            "fuentes": list(usadas.values()), "errores": err, "rango_fed": res.get("_rango_fed")}


def entorno_del_dia(fecha_iso):
    """Valor de los indicadores clave al cierre de una fecha y su cambio contra la sesión anterior."""
    res, _ = series(date.today())
    out = []
    for id_ in ("fx", "sp500", "nasdaq", "ust10y", "effr", "tasa_obj", "vix", "dxy"):
        s = res.get(id_)
        if not s:
            continue
        tipo = next(d[3] for d in DEFS if d[0] == id_)
        i = bisect.bisect_right([x[0] for x in s], fecha_iso)
        if i < 2:
            continue
        (f1, v1), (_, v0) = s[i - 1], s[i - 2]
        nombre = glosario.INDICADORES[id_][0]
        out.append({"id": id_, "nombre": nombre, "fecha": f1, "valor": v1, "tipo": tipo,
                    "cambio": (v1 - v0) * 100 if tipo == "tasa" else _rend(v0, v1), "cambio_unidad": "pb" if tipo == "tasa" else "%",
                    "oficial": next(d[5] for d in DEFS if d[0] == id_) != "yahoo"})
    return {"indicadores": out}
