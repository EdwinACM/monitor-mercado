"""Actualiza static/data/fichas.json con datos reales de cada empresa tomados de la SEC (EDGAR).

    python actualizar_fichas.py

Para las cinco empresas de EE. UU. (Apple, Microsoft, Nvidia, Tesla y Coca-Cola) y las tres mexicanas que reportan a la SEC
(América Móvil, Coca-Cola FEMSA y OMA) guarda: acciones en circulación, emitidas y autorizadas, valor par, y cifras financieras
anuales (ingresos, utilidad neta, activos, pasivos, capital, utilidad por acción, flujo de operación y dividendo por acción).
Walmart de México y Kimberly-Clark de México no reportan a la SEC: sus cifras vienen de su reporte anual (ver fichas.py).
Lo ejecuta el flujo de GitHub cada día hábil, antes del análisis diario.
"""
import json
import re
from datetime import date, datetime
from pathlib import Path

import server

OUT = server.STATIC / "data" / "fichas.json"
SEC = {"AAPL": "0000320193", "MSFT": "0000789019", "NVDA": "0001045810", "TSLA": "0001318605", "KO": "0000021344",
       "AMXB.MX": "0001129137", "KOFUBL.MX": "0000910631", "OMAB.MX": "0001378239"}
UA = {"User-Agent": "AlzeaResearch/1.0 (educational project)"}

# etiqueta -> etiquetas XBRL posibles, en orden de preferencia (nombre de espacio, nombre de concepto)
CIFRAS = {
    "ingresos": [("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"), ("us-gaap", "Revenues"), ("us-gaap", "SalesRevenueNet"), ("ifrs-full", "Revenue")],
    "utilidad_neta": [("us-gaap", "NetIncomeLoss"), ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"), ("ifrs-full", "ProfitLoss")],
    "activos": [("us-gaap", "Assets"), ("ifrs-full", "Assets")],
    "pasivos": [("us-gaap", "Liabilities"), ("ifrs-full", "Liabilities")],
    "capital": [("us-gaap", "StockholdersEquity"), ("ifrs-full", "EquityAttributableToOwnersOfParent"), ("ifrs-full", "Equity")],
    "utilidad_por_accion": [("us-gaap", "EarningsPerShareDiluted"), ("ifrs-full", "DilutedEarningsLossPerShare"), ("ifrs-full", "BasicEarningsLossPerShare")],
    "flujo_operacion": [("us-gaap", "NetCashProvidedByUsedInOperatingActivities"), ("ifrs-full", "CashFlowsFromUsedInOperatingActivities")],
    "dividendo_por_accion": [("us-gaap", "CommonStockDividendsPerShareDeclared"), ("us-gaap", "CommonStockDividendsPerShareCashPaid")],
}
ACCION = {"emitidas": ("us-gaap", "CommonStockSharesIssued"), "autorizadas": ("us-gaap", "CommonStockSharesAuthorized"), "valor_par": ("us-gaap", "CommonStockParOrStatedValuePerShare")}


def _get(url):
    import urllib.request
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=90).read()


def _anuales(facts, ns, tag):
    """Valores de periodos de ~12 meses de formularios anuales (10-K, 20-F, 40-F), sin repetir periodos; el más reciente primero."""
    d = facts.get(ns, {}).get(tag)
    if not d:
        return []
    unidad = next((u for u in ("MXN", "USD") if u in d["units"]), None) or next((u for u in d["units"] if u.endswith("/shares")), next(iter(d["units"])))
    if "MXN/shares" in d["units"] and unidad != "MXN":
        unidad = "MXN/shares"
    salida = {}
    for r in d["units"][unidad]:
        if r.get("form") not in ("10-K", "20-F", "40-F", "10-K/A", "20-F/A"):
            continue
        fin = r["end"]
        if "start" in r:
            dias = (date.fromisoformat(fin) - date.fromisoformat(r["start"])).days
            if not 340 <= dias <= 380:
                continue
        salida[fin] = (r["val"], unidad, r.get("form"), r.get("filed"))
    return [(f, *salida[f]) for f in sorted(salida, reverse=True)]


def _ultimo(facts, ns, tag, max_dias=500):
    d = facts.get(ns, {}).get(tag)
    if not d:
        return None
    unidad = next(iter(d["units"]))
    pts = sorted(d["units"][unidad], key=lambda r: (r["end"], r.get("filed", "")))
    if not pts:
        return None
    r = pts[-1]
    if (date.today() - date.fromisoformat(r["end"])).days > max_dias:
        return None
    return {"valor": r["val"], "fecha": r["end"], "formulario": r.get("form"), "presentado": r.get("filed")}


def empresa(t, cik):
    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json"))
    facts = json.loads(_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"))["facts"]
    rec = sub["filings"]["recent"]
    anual = next((k for k, f in enumerate(rec["form"]) if f in ("10-K", "20-F")), None)
    ultimo = next((k for k, f in enumerate(rec["form"]) if f in ("10-K", "10-Q", "20-F", "6-K")), None)
    docs = {}
    for nombre, k in (("anual", anual), ("ultimo", ultimo)):
        if k is not None:
            acc = rec["accessionNumber"][k].replace("-", "")
            docs[nombre] = {"formulario": rec["form"][k], "presentado": rec["filingDate"][k],
                            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{rec['primaryDocument'][k]}"}
    out = {"nombre": sub["name"], "cik": cik, "estado_constitucion": sub.get("stateOfIncorporation"), "ejercicio_fiscal_termina": sub.get("fiscalYearEnd"),
           "documentos": docs, "acciones": {}, "cifras": {}}
    s = _ultimo(facts, "dei", "EntityCommonStockSharesOutstanding")
    if s:
        out["acciones"]["circulacion"] = s
    for k, (ns, tag) in ACCION.items():
        u = _ultimo(facts, ns, tag, 700 if k == "valor_par" else 500)
        if u:
            out["acciones"][k] = u
    for k, cands in CIFRAS.items():
        mejor = None
        for ns, tag in cands:  # de las etiquetas posibles se usa la que trae el periodo más reciente
            v = _anuales(facts, ns, tag)
            if v and (mejor is None or v[0][0] > mejor[0][0]):
                mejor = v
        if mejor:
            out["cifras"][k] = [{"fin": f, "valor": val, "unidad": un, "formulario": fm, "presentado": pr} for f, val, un, fm, pr in mejor[:3]]
    # una cifra cuyo último periodo es mucho más viejo que el resto (etiqueta que la empresa dejó de usar) se descarta
    if out["cifras"]:
        ult = max(v[0]["fin"] for v in out["cifras"].values())
        out["cifras"] = {k: v for k, v in out["cifras"].items() if (date.fromisoformat(ult) - date.fromisoformat(v[0]["fin"])).days <= 200}
    return out


def main():
    previo = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    datos = dict(previo.get("empresas", {}))
    errores = {}
    for t, cik in SEC.items():
        try:
            datos[t] = empresa(t, cik)
            print(f"[OK] {t}: {len(datos[t]['cifras'])} cifras, acciones {list(datos[t]['acciones'])}")
        except Exception as e:
            errores[t] = f"{type(e).__name__}: {e}"
            print(f"[ERROR] {t}: {errores[t]}")
    if not any(t in datos for t in SEC):
        raise SystemExit("[ERROR] La SEC no respondió; no se modificó ningún archivo.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"actualizado": datetime.now(server.TZ).isoformat(), "fuente": "SEC EDGAR (data.sec.gov)", "errores": errores, "empresas": datos},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] fichas.json actualizado ({len(datos)} empresas).")


if __name__ == "__main__":
    main()
