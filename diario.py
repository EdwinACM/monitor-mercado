"""Construye el registro de análisis de un día (decisiones, porqué y qué pasó después)."""
import analisis


def preparar(hist):
    """Indicadores sobre todo el historial; son causales, así que valen para cualquier día."""
    out = {}
    for t, rows in hist.items():
        c = [r["cierre"] for r in rows]
        out[t] = (c, analisis.indicadores(c))
    return out


def registro_dia(fecha, hist, deu, nombres):
    emisoras = []
    for t, rows in hist.items():
        k = next((i for i, r in enumerate(rows) if r["fecha"] == fecha), None)
        if k is None or k < 30:
            continue
        nombre = nombres.get(t, t)
        d = analisis.analizar_serie(nombre, rows[:k + 1], None, con_serie=False, con_backtest=False)
        emisoras.append({
            "ticker": t.replace(".MX", ""), "nombre": nombre, "cierre": d["cierre"], "var": d["var"], "var_pct": d["var_pct"],
            "ret5": d["ret5"], "ret20": d["ret20"], "rsi": d["rsi"], "macd_hist": d["macd_hist"], "pctb": d["pctb"],
            "tendencia": d["tendencia"]["etiqueta"], "pendiente": d["tendencia"]["pendiente"], "r2": d["tendencia"]["r2"],
            "vol_anual": d["stats"]["vol_anual"], "max_drawdown": d["stats"]["max_drawdown"],
            "score": d["score"], "veredicto": d["veredicto"], "decision": d["decision"], "confianza": d["confianza"],
            "veredicto_ant": d["veredicto_ant"], "cambio": d["cambio"], "por_que": d["por_que"], "accion": d["accion"],
            "componentes": [[c["criterio"], c["puntos"]] for c in d["componentes"]], "texto": d["texto"],
            "ret_5": None, "ret_10": None, "acierto": None,
        })
    if not emisoras:
        return None
    instrumentos = []
    for s in deu:
        a = analisis.analizar_deuda(s, hasta=fecha)
        instrumentos.append({k: a.get(k) for k in ("nombre", "emisor", "fecha", "valor", "var_pb", "z", "pendiente", "tendencia",
                                                     "senal", "decision", "por_que", "texto")})
    return {"fecha": fecha, "mercado": analisis.resumen_mercado(emisoras), "emisoras": emisoras, "deuda": instrumentos}


def completar(registros, hist):
    """Agrega a cada decisión qué pasó 5 y 10 sesiones después (cuando ya hay datos)."""
    for reg in registros:
        for e in reg["emisoras"]:
            rows = hist.get(e["ticker"] + ".MX")
            if not rows:
                continue
            k = next((i for i, r in enumerate(rows) if r["fecha"] == reg["fecha"]), None)
            if k is None:
                continue
            fwd = lambda h: round((rows[k + h]["cierre"] / rows[k]["cierre"] - 1) * 100, 2) if k + h < len(rows) else None
            e["ret_5"], e["ret_10"] = fwd(5), fwd(10)
            r5, v = e["ret_5"], e["veredicto"]
            e["acierto"] = None if r5 is None else (r5 > 0 if "COMPRA" in v else r5 < 0 if "VENT" in v or v == "VENDER" else abs(r5) <= 2)
    return registros
