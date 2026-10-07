"""Registro de un día: decisión, porqué y qué pasó después; y resumen rápido de un periodo."""
import analisis
import modelo


def registro_dia(fecha, hist, deu, nombres, meta=None):
    """Análisis de una sesión con los datos disponibles hasta esa fecha (sin ver el futuro)."""
    meta = meta or {}
    mod = modelo.obtener(hist)
    emisoras = []
    for t, rows in hist.items():
        k = next((i for i, r in enumerate(rows) if r["fecha"] == fecha), None)
        if k is None or k < 30:
            continue
        nombre = nombres.get(t, t)
        d = analisis.analizar_serie(nombre, rows[:k + 1], None, con_serie=False, con_backtest=False, modelo=mod, ticker=t)
        m = meta.get(t, {})
        emisoras.append({
            "ticker": t.replace(".MX", ""), "yahoo": t, "nombre": nombre, "mercado": m.get("mercado"), "moneda": m.get("moneda"),
            "cierre": d["cierre"], "var": d["var"], "var_pct": d["var_pct"],
            "ret5": d["ret5"], "ret20": d["ret20"], "rsi": d["rsi"], "macd_hist": d["macd_hist"], "pctb": d["pctb"],
            "tendencia": d["tendencia"]["etiqueta"], "pendiente": d["tendencia"]["pendiente"], "r2": d["tendencia"]["r2"],
            "vol_anual": d["stats"]["vol_anual"], "max_drawdown": d["stats"]["max_drawdown"],
            "score": d["score"], "veredicto": d["veredicto"], "decision": d["decision"], "confianza": d["confianza"],
            "veredicto_ant": d["veredicto_ant"], "cambio": d["cambio"], "por_que": d["por_que"], "accion": d["accion"],
            "componentes": [[c["criterio"], c["puntos"]] for c in d["componentes"]], "texto": d["texto"],
            "respaldo": d["respaldo"], "riesgos": d["riesgos"],
            "ret_5": None, "ret_10": None, "acierto": None,
        })
    if not emisoras:
        return None
    instrumentos = []
    for s in deu:
        if s["nombre"].startswith("CETES 91"):
            continue  # serie de referencia (no se muestra)
        a = analisis.analizar_deuda(s, hasta=fecha)
        instrumentos.append({k: a.get(k) for k in ("nombre", "codigo", "emisor", "fecha", "valor", "var_pb", "z", "pendiente", "tendencia",
                                                     "senal", "decision", "por_que", "texto")})
    return {"fecha": fecha, "mercado": analisis.resumen_mercado(emisoras), "emisoras": emisoras, "deuda": instrumentos}


def acierto(veredicto, r5):
    """Comprar acierta si el precio subió a 5 sesiones; vender, si bajó; mantener, si se movió 2 % o menos."""
    if r5 is None:
        return None
    if "COMPRA" in veredicto:
        return r5 > 0
    if veredicto in ("VENDER", "VENTA FUERTE"):
        return r5 < 0
    return abs(r5) <= 2


def completar(registros, hist):
    """Agrega a cada decisión qué pasó 5 y 10 sesiones después (cuando ya hay datos)."""
    for reg in registros:
        for e in reg["emisoras"]:
            rows = hist.get(e["yahoo"])
            if not rows:
                continue
            k = next((i for i, r in enumerate(rows) if r["fecha"] == reg["fecha"]), None)
            if k is None:
                continue
            fwd = lambda h: round((rows[k + h]["cierre"] / rows[k]["cierre"] - 1) * 100, 2) if k + h < len(rows) else None
            e["ret_5"], e["ret_10"] = fwd(5), fwd(10)
            e["acierto"] = acierto(e["veredicto"], e["ret_5"])
    return registros


def resumen_periodo(hist, desde, hasta, meta=None):
    """Decisiones día por día dentro del periodo y su tasa de acierto (cálculo directo, rápido)."""
    meta = meta or {}
    mod = modelo.obtener(hist)
    fechas = sorted({r["fecha"] for rows in hist.values() for r in rows if desde <= r["fecha"] <= hasta})
    cierres = {t: [r["cierre"] for r in rows] for t, rows in hist.items()}
    posiciones = {t: {r["fecha"]: i for i, r in enumerate(rows)} for t, rows in hist.items()}
    dias, prev = [], {}
    for f in fechas:
        es = []
        for t, rows in hist.items():
            k = posiciones[t].get(f)
            if k is None or k < 30:
                continue
            c = cierres[t]
            sc, _ = mod.evaluar(t, f)
            v = analisis.veredicto(sc)
            r5 = round((c[k + 5] / c[k] - 1) * 100, 2) if k + 5 < len(c) else None
            es.append({"t": t.replace(".MX", ""), "y": t, "v": v, "s": sc, "c": 1 if prev.get(t) not in (None, v) else 0,
                       "a": acierto(v, r5), "r5": r5, "cierre": round(c[k], 2)})
            prev[t] = v
        if es:
            dias.append({"fecha": f, "e": es})
    ev = [e for d in dias for e in d["e"] if e["a"] is not None]
    grupos = {"Comprar": lambda v: "COMPRA" in v, "Mantener": lambda v: v == "MANTENER", "Vender": lambda v: v in ("VENDER", "VENTA FUERTE")}
    aciertos = []
    grupos["Señales fuertes"] = lambda v: v in ("COMPRA FUERTE", "VENTA FUERTE")
    for nombre, fn in list(grupos.items()) + [("Todas", lambda v: True)]:
        xs = [e for e in ev if fn(e["v"])]
        aciertos.append({"decision": nombre, "casos": len(xs), "aciertos": sum(1 for e in xs if e["a"]),
                         "pct": round(100 * sum(1 for e in xs if e["a"]) / len(xs), 2) if xs else None,
                         "ret5_medio": round(sum(e["r5"] for e in xs) / len(xs), 2) if xs and nombre != "Señales fuertes" else None})
    cambios = [{"fecha": d["fecha"], "ticker": e["t"], "de": None, "a": e["v"]} for d in dias for e in d["e"] if e["c"]]
    # veredicto anterior para mostrar «de X a Y»
    ult = {}
    for d in dias:
        for e in d["e"]:
            e["ant"] = ult.get(e["y"])
            ult[e["y"]] = e["v"]
    cambios = [{"fecha": d["fecha"], "ticker": e["t"], "de": e["ant"], "a": e["v"]} for d in dias for e in d["e"] if e["c"]]
    return {"periodo": {"desde": desde, "hasta": hasta}, "dias": dias, "aciertos": aciertos, "cambios": cambios[::-1][:30]}
