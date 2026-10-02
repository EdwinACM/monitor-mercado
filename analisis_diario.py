"""Guarda el análisis diario en archivos (static/data/).

    python analisis_diario.py                  # agrega los días hábiles que falten (y refresca el último)
    python analisis_diario.py --desde 2026-03-02   # reconstruye desde esa fecha

Lo ejecuta GitHub Actions cada día hábil después del cierre (ver .github/workflows).
Archivos generados:
    analisis_diario.json    lo lee la pestaña «Historial» de la app
    analisis_acciones.csv   una fila por fecha y emisora
    analisis_deuda.csv      una fila por fecha e instrumento
    analisis_diario.xlsx    las mismas tablas en Excel
    diario/AAAA-MM-DD.md    resumen legible de cada día
"""
import argparse
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

import analisis
import server

OUT = server.STATIC / "data"
INICIO = "2026-03-02"
AVISO = "Herramienta educativa basada en indicadores técnicos; no constituye asesoría financiera."


def registro_dia(fecha, hist, deu):
    emisoras = []
    for t, rows in hist.items():
        k = next((i for i, r in enumerate(rows) if r["fecha"] == fecha), None)
        if k is None or k < 30:
            continue
        nombre = server.ACCIONES.get(t, t)
        d = analisis.analizar_serie(nombre, rows[:k + 1], None, con_serie=False, con_backtest=False)
        emisoras.append({
            "ticker": t.replace(".MX", ""), "nombre": nombre, "cierre": d["cierre"], "var": d["var"], "var_pct": d["var_pct"],
            "ret5": d["ret5"], "ret20": d["ret20"], "rsi": d["rsi"], "macd_hist": d["macd_hist"], "pctb": d["pctb"],
            "tendencia": d["tendencia"]["etiqueta"], "pendiente": d["tendencia"]["pendiente"], "r2": d["tendencia"]["r2"],
            "vol_anual": d["stats"]["vol_anual"], "max_drawdown": d["stats"]["max_drawdown"],
            "score": d["score"], "veredicto": d["veredicto"], "confianza": d["confianza"],
            "componentes": [[c["criterio"], c["puntos"]] for c in d["componentes"]], "texto": d["texto"],
        })
    if not emisoras:
        return None
    resumen = analisis.resumen_mercado(emisoras)
    instrumentos = []
    for s in deu:
        a = analisis.analizar_deuda(s, hasta=fecha)
        instrumentos.append({k: a.get(k) for k in ("nombre", "emisor", "fecha", "valor", "var_pb", "z", "pendiente",
                                                     "tendencia", "senal", "texto")})
    return {"fecha": fecha, "mercado": resumen, "emisoras": emisoras, "deuda": instrumentos}


def escribir_md(reg):
    L = [f"# Análisis del {reg['fecha']}", "", reg["mercado"]["texto"], "",
         "| Emisora | Cierre | Var. % | Tendencia | RSI | Señal | Puntaje | Confianza |", "|---|---:|---:|---|---:|---|---:|---|"]
    for e in reg["emisoras"]:
        L.append(f"| {e['nombre']} | ${e['cierre']:.2f} | {e['var_pct']:+.2f}% | {e['tendencia']} | "
                 f"{'' if e['rsi'] is None else round(e['rsi'])} | **{e['veredicto']}** | {e['score']:+d} | {e['confianza']} |")
    L += ["", "## Detalle por emisora", ""]
    L += [f"- {e['texto']}" for e in reg["emisoras"]]
    L += ["", "## Deuda gubernamental (última subasta conocida)", ""]
    L += [f"- {d['texto']}" for d in reg["deuda"]]
    L += ["", f"_{AVISO}_", ""]
    (OUT / "diario").mkdir(parents=True, exist_ok=True)
    (OUT / "diario" / f"{reg['fecha']}.md").write_text("\n".join(L), encoding="utf-8")


COLS_ACC = ["fecha", "ticker", "nombre", "cierre", "var", "var_pct", "ret5", "ret20", "rsi", "macd_hist", "pctb",
            "tendencia", "pendiente", "r2", "vol_anual", "max_drawdown", "score", "veredicto", "confianza"]
COLS_DEU = ["fecha", "nombre", "emisor", "fecha_subasta", "valor", "var_pb", "z", "pendiente", "tendencia", "senal"]


def filas(registros):
    acc, deu = [], []
    for r in registros:
        for e in r["emisoras"]:
            acc.append({"fecha": r["fecha"], **{k: e[k] for k in COLS_ACC[1:]}})
        for d in r["deuda"]:
            deu.append({"fecha": r["fecha"], "fecha_subasta": d["fecha"], **{k: d.get(k) for k in COLS_DEU if k not in ("fecha", "fecha_subasta")}})
    return acc, deu


def escribir_csv(nombre, cols, filas_):
    with open(OUT / nombre, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(filas_)


def escribir_xlsx(registros, acc, deu):
    G, hf = PatternFill("solid", fgColor="6C1D45"), Font(bold=True, color="FFFFFF")
    verde, rojo = PatternFill("solid", fgColor="D9F2DD"), PatternFill("solid", fgColor="F8D7D3")
    wb = Workbook()

    def hoja(ws, cols, datos, anchos):
        ws.append(cols)
        for c in ws[1]:
            c.fill, c.font, c.alignment = G, hf, Alignment(horizontal="center", wrap_text=True)
        for f in datos:
            ws.append([f.get(c) for c in cols])
        for i, w in enumerate(anchos):
            ws.column_dimensions[chr(65 + i)].width = w
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "Resumen diario"
    hoja(ws, ["fecha", "suben", "bajan", "puntaje_promedio", "sesgo", "texto"],
         [{"fecha": r["fecha"], **{k: r["mercado"].get(k) for k in ("suben", "bajan", "puntaje_promedio", "sesgo", "texto")}}
          for r in registros], [12, 8, 8, 16, 10, 120])
    ws = wb.create_sheet("Acciones")
    hoja(ws, COLS_ACC, acc, [12, 11, 30, 10, 9, 9, 8, 8, 7, 10, 7, 11, 10, 7, 10, 12, 8, 15, 10])
    for fila in ws.iter_rows(min_row=2):
        v = fila[COLS_ACC.index("veredicto")]
        v.fill = verde if "COMPRA" in str(v.value) else rojo if "VENTA" in str(v.value) else PatternFill()
    ws = wb.create_sheet("Deuda")
    hoja(ws, COLS_DEU, deu, [12, 22, 18, 14, 10, 9, 7, 11, 11, 11])
    wb.save(OUT / "analisis_diario.xlsx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", help="reconstruir desde esta fecha (AAAA-MM-DD)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    existente = {}
    ruta = OUT / "analisis_diario.json"
    if ruta.exists() and not args.desde:
        existente = {r["fecha"]: r for r in json.loads(ruta.read_text(encoding="utf-8"))["registros"]}

    accs = server.acciones(list(server.ACCIONES), server.ventana_historial())
    hist = {a["ticker"]: a["historico"] for a in accs if a["historico"]}
    if not hist:
        raise SystemExit("[ERROR] Yahoo Finance no devolvió datos; no se modificó ningún archivo.")
    deu = server.deuda(date.today() - timedelta(days=300))

    habiles = sorted({r["fecha"] for rows in hist.values() for r in rows})
    if args.desde:
        pendientes = [f for f in habiles if f >= args.desde]
    elif existente:
        ultimo = max(existente)
        pendientes = [f for f in habiles if f >= ultimo]  # refresca el último y agrega los que falten
    else:
        pendientes = [f for f in habiles if f >= INICIO]

    nuevos = 0
    for f in pendientes:
        reg = registro_dia(f, hist, deu)
        if reg:
            existente[f] = reg
            nuevos += 1
            escribir_md(reg)
    registros = [existente[k] for k in sorted(existente)]
    ruta.write_text(json.dumps({"actualizado": datetime.now(server.TZ).isoformat(), "aviso": AVISO, "registros": registros},
                               ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    acc, deud = filas(registros)
    escribir_csv("analisis_acciones.csv", COLS_ACC, acc)
    escribir_csv("analisis_deuda.csv", COLS_DEU, deud)
    escribir_xlsx(registros, acc, deud)
    print(f"[OK] {nuevos} día(s) procesados; {len(registros)} en total ({registros[0]['fecha']} → {registros[-1]['fecha']}).")


if __name__ == "__main__":
    main()
