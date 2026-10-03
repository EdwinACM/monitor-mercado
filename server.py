"""Monitor de Mercado — consulta de datos y análisis.

Consulta Yahoo Finance (acciones BMV) y Banco de México (subastas de deuda).
En producción lo usan las funciones de Vercel (api/*.py); en la Mac puede correr
como servidor local (solo 127.0.0.1) con:  python server.py
"""
import io
import json
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

import analisis
import diario
import reportes
import truststore
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

truststore.inject_into_ssl()  # usa los certificados de macOS/Windows (redes con proxy)

PORT = 8765
TZ = ZoneInfo("America/Mexico_City")
STATIC = Path(__file__).parent / "static"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) MonitorMercado/1.0"}

ACCIONES = {
    "WALMEX.MX": "Walmart de México",
    "AMXB.MX": "América Móvil",
    "KOFUBL.MX": "Coca-Cola FEMSA",
    "KIMBERA.MX": "Kimberly-Clark de México",
    "OMAB.MX": "Grupo Aeroportuario Centro Norte",
}

# (cuadro Banxico, sección, renglón buscado, emisor, unidad, tipo)
DEUDA = {
    "CETES 28 días": ("CF107", "Cetes a 28 días", "Tasa de rendimiento", "Gobierno Federal", "% anual", "tasa"),
    "BONDES F 2 años": ("CF107", "Bondes F a 2 años", "Precio Promedio", "Gobierno Federal", "$ por título de $100", "precio"),
    "UDIBONOS 10 años": ("CF107", "Udibonos a 10 años", "Tasa de rendimiento real", "Gobierno Federal", "% real anual", "tasa"),
    "BPAG28 3 años": ("CF115", "BPAG28", "Sobretasa", "IPAB", "puntos % sobre referencia", "tasa"),
    "BONOS M 10 años": ("CF107", "Bonos a tasa fija a 10 años", "Tasa de rendimiento", "Gobierno Federal", "% anual", "tasa"),
}

_cache, _lock = {}, threading.Lock()


def cached(key, ttl, fn):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _lock:
        _cache[key] = (time.time(), val)
    return val


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def mercado_abierto(now=None):
    # La BMV sigue el horario de Nueva York (9:30–16:00 ET): 7:30–14:00 u 8:30–15:00 en CDMX según el horario de verano de EE. UU.
    ny = (now or datetime.now(TZ)).astimezone(ZoneInfo("America/New_York"))
    return ny.weekday() < 5 and (9, 30) <= (ny.hour, ny.minute) < (16, 0)


# ---------------- Yahoo Finance ----------------
def yahoo_chart(ticker, **params):
    q = urllib.parse.urlencode(params)
    last = None
    for host in ("query1", "query2"):
        try:
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?{q}"
            return json.loads(http_get(url, 30))["chart"]["result"][0]
        except Exception as e:  # reintenta con el otro host
            last = e
    raise last


def historico(ticker, desde):
    p1 = int(datetime.combine(desde, datetime.min.time(), TZ).timestamp())
    r = yahoo_chart(ticker, period1=p1, period2=int(time.time()) + 3600, interval="1d")
    q, meta = r["indicators"]["quote"][0], r["meta"]
    filas = []
    for i, ts in enumerate(r.get("timestamp") or []):
        if q["close"][i] is None:
            continue
        filas.append({
            "fecha": datetime.fromtimestamp(ts, TZ).date().isoformat(),
            "apertura": q["open"][i], "maximo": q["high"][i], "minimo": q["low"][i],
            "cierre": q["close"][i], "volumen": q["volume"][i] or 0,
        })
    precio = meta.get("regularMarketPrice")
    hora = meta.get("regularMarketTime")
    if filas and precio is not None and hora:
        hoy = datetime.fromtimestamp(hora, TZ).date().isoformat()
        if filas[-1]["fecha"] == hoy:
            filas[-1]["cierre"] = precio
    for i, f in enumerate(filas):
        prev = filas[i - 1]["cierre"] if i else None
        f["var"] = f["cierre"] - prev if prev else None
        f["var_pct"] = f["cierre"] / prev - 1 if prev else None
        f["var_acum_pct"] = f["cierre"] / filas[0]["cierre"] - 1
    return {
        "ticker": ticker,
        "nombre": ACCIONES.get(ticker, meta.get("longName") or meta.get("shortName") or ticker),
        "moneda": meta.get("currency"),
        "precio": precio,
        "hora": datetime.fromtimestamp(hora, TZ).isoformat() if hora else None,
        "historico": filas,
    }


def intradia(ticker):
    r = yahoo_chart(ticker, range="1d", interval="5m")
    q = r["indicators"]["quote"][0]
    return [
        {"hora": datetime.fromtimestamp(ts, TZ).strftime("%H:%M"), "precio": q["close"][i]}
        for i, ts in enumerate(r.get("timestamp") or []) if q["close"][i] is not None
    ]


# ---------------- Banco de México ----------------
def banxico_cuadro(cuadro, desde, hasta):
    ms = lambda d: int(datetime.combine(d, datetime.min.time(), TZ).timestamp() * 1000)
    url = ("https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?"
           f"sector=22&accion=consultarCuadro&idCuadro={cuadro}&locale=es&formatoXLS.x=1"
           f"&fechaInicio={ms(desde)}&fechaFin={ms(hasta)}")
    raw = http_get(url, 120)
    if not raw.startswith(b"PK"):
        raise RuntimeError(f"Banxico no devolvió el cuadro {cuadro}")
    ws = load_workbook(io.BytesIO(raw)).active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    fila_fechas = next(r for r in rows if any(isinstance(v, str) and v.count("/") == 2 and len(v) == 10 for v in r[2:]))
    fechas = [datetime.strptime(v, "%d/%m/%Y").date().isoformat() if isinstance(v, str) and v.count("/") == 2 else None
              for v in fila_fechas]
    return fechas, rows


def serie_deuda(nombre, desde, hasta, cuadros):
    cuadro, seccion, renglon, emisor, unidad, tipo = DEUDA[nombre]
    fechas, rows = cuadros[cuadro]
    actual, datos = None, []
    for r in rows:
        label = (r[1] or "") if len(r) > 1 else ""
        if "●" in label:
            actual = label.split("●")[-1].strip()
        elif actual and actual.startswith(seccion) and renglon.lower() in label.lower():
            datos = [{"fecha": fechas[j], "valor": float(v)} for j, v in enumerate(r)
                     if j >= 2 and fechas[j] and isinstance(v, (int, float))]
            break
    for i, d in enumerate(datos):
        prev = datos[i - 1]["valor"] if i else None
        d["var"] = d["valor"] - prev if prev is not None else None
        d["var_pb"] = (d["valor"] - prev) * 100 if prev is not None and tipo == "tasa" else None
        d["var_pct"] = d["valor"] / prev - 1 if prev else None
    return {"nombre": nombre, "emisor": emisor, "unidad": unidad, "tipo": tipo, "datos": datos}


def deuda(desde):
    hasta = datetime.now(TZ).date()

    def cargar():
        cuadros = {c: banxico_cuadro(c, desde, hasta) for c in {v[0] for v in DEUDA.values()}}
        return [serie_deuda(n, desde, hasta, cuadros) for n in DEUDA]

    # las subastas son semanales: basta refrescar cada 3 h
    return cached(("deuda", desde, hasta), 3 * 3600, cargar)


def acciones(tickers, desde):
    ttl = 60 if mercado_abierto() else 15 * 60

    def uno(t):
        try:
            return cached(("acc", t, desde), ttl, lambda: historico(t, desde))
        except Exception as e:
            return {"ticker": t, "nombre": ACCIONES.get(t, t), "error": str(e), "historico": []}

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(uno, tickers))


def validar_desde(accs, desde):
    """La fecha inicial debe ser anterior al último cierre disponible; si no, el periodo queda vacío."""
    ult = max((a["historico"][-1]["fecha"] for a in accs if a.get("historico")), default=None)
    if ult and desde.isoformat() >= ult:
        raise ValueError(f"La fecha inicial ({desde.isoformat()}) debe ser anterior al último cierre ({ult}). Elige una fecha más antigua.")


def ventana_historial():
    """Historial largo (≈14 meses) para que las medias y el backtest tengan datos."""
    return date.today() - timedelta(days=420)


def cotizacion(t):
    """Último precio y puntos del día (5 min) de una emisora."""
    r = yahoo_chart(t, range="1d", interval="5m")
    m, q = r["meta"], r["indicators"]["quote"][0]
    precio, previo = m.get("regularMarketPrice"), m.get("chartPreviousClose")
    hora = m.get("regularMarketTime")
    return {
        "ticker": t, "precio": precio, "previo": previo,
        "var": precio - previo if precio is not None and previo else None,
        "var_pct": (precio / previo - 1) * 100 if precio is not None and previo else None,
        "maximo": m.get("regularMarketDayHigh"), "minimo": m.get("regularMarketDayLow"),
        "volumen": m.get("regularMarketVolume"),
        "hora": datetime.fromtimestamp(hora, TZ).isoformat() if hora else None,
        "puntos": [round(x, 2) for x in (q.get("close") or []) if x is not None],
    }


def cotizaciones(tickers):
    def uno(t):
        try:
            return cached(("cot", t), 20, lambda: cotizacion(t))
        except Exception as e:
            return {"ticker": t, "error": str(e)}

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(uno, tickers))


def analisis_completo(tickers, desde):
    """Señales, estadística y series para la pantalla (todo calculado en el servidor)."""
    accs = acciones(tickers, ventana_historial())
    validar_desde(accs, desde)
    items = []
    for a in accs:
        if a.get("error") or len(a["historico"]) < 30:
            items.append({"ticker": a["ticker"], "nombre": a["nombre"], "error": a.get("error") or "Historial insuficiente"})
            continue
        d = analisis.analizar_serie(a["nombre"], a["historico"], desde.isoformat())
        d.update(ticker=a["ticker"], nombre=a["nombre"], precio=a.get("precio"), hora=a.get("hora"))
        items.append(d)
    ok = [x for x in items if "error" not in x]
    deu = []
    for s in deuda(date.today() - timedelta(days=300)):
        d = analisis.analizar_deuda(s)
        d["datos"] = [x for x in s["datos"] if x["fecha"] >= desde.isoformat()]
        deu.append(d)
    return {"ahora": datetime.now(TZ).isoformat(), "mercado_abierto": mercado_abierto(),
            "mercado": analisis.resumen_mercado(ok), "acciones": items, "deuda": deu}


def dia(fecha_iso):
    """Registro de un día: decisiones, porqué y qué pasó después (para descargar en PDF, Excel o Markdown)."""
    hist = {a["ticker"]: a["historico"] for a in acciones(list(ACCIONES), ventana_historial()) if a["historico"]}
    deu = deuda(date.today() - timedelta(days=300))
    reg = diario.registro_dia(fecha_iso, hist, deu, ACCIONES)
    if not reg:
        raise ValueError("No hubo sesión de la BMV en esa fecha o no hay historial suficiente")
    return diario.completar([reg], hist)[0]


def simulacion(desde):
    accs = acciones(list(ACCIONES), ventana_historial())
    validar_desde(accs, desde)
    hist = {a["ticker"]: a["historico"] for a in accs if a["historico"]}
    return analisis.simular(hist, desde.isoformat())


def comparacion(tickers, desde):
    accs = acciones(tickers, ventana_historial())
    validar_desde(accs, desde)
    hist = {a["ticker"]: a["historico"] for a in accs if not a.get("error") and a["historico"]}
    return analisis.comparar(hist, desde.isoformat())


# ---------------- Exportar a Excel ----------------
def excel(tickers, desde):
    G = "6C1D45"
    hdr, hf = PatternFill("solid", fgColor=G), Font(bold=True, color="FFFFFF")
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws.append([f"Monitor de mercado — del {desde:%d/%m/%Y} al {datetime.now(TZ):%d/%m/%Y %H:%M}"])
    ws["A1"].font = Font(bold=True, size=13, color=G)

    def encabezado(sheet, cols):
        sheet.append(cols)
        for c in sheet[sheet.max_row]:
            c.fill, c.font, c.alignment = hdr, hf, Alignment(horizontal="center", wrap_text=True)

    acc = acciones(tickers, desde)
    ws.append([])
    encabezado(ws, ["Acción", "Ticker", "Cierre inicial", "Último", "Var. $", "Var. %"])
    for a in acc:
        h = a["historico"]
        if h:
            ws.append([a["nombre"], a["ticker"], h[0]["cierre"], h[-1]["cierre"],
                       h[-1]["cierre"] - h[0]["cierre"], h[-1]["var_acum_pct"]])
            ws.cell(ws.max_row, 6).number_format = "0.00%"
    deu = deuda(desde)
    ws.append([])
    encabezado(ws, ["Instrumento", "Emisor", "Valor inicial", "Último", "Variación", "Unidad"])
    for d in deu:
        s = d["datos"]
        if s:
            delta = s[-1]["valor"] - s[0]["valor"]
            ws.append([d["nombre"], d["emisor"], s[0]["valor"], s[-1]["valor"],
                       f"{delta * 100:+.0f} pb" if d["tipo"] == "tasa" else round(delta, 5), d["unidad"]])
    for col, w in zip("ABCDEF", (36, 18, 14, 12, 12, 26)):
        ws.column_dimensions[col].width = w

    for a in acc:
        s = wb.create_sheet(a["ticker"].replace(".MX", "")[:31])
        encabezado(s, ["Fecha", "Apertura", "Máximo", "Mínimo", "Cierre", "Volumen", "Var. $", "Var. %", "Var. acum. %"])
        for f in a["historico"]:
            s.append([f["fecha"], f["apertura"], f["maximo"], f["minimo"], f["cierre"], f["volumen"],
                      f["var"], f["var_pct"], f["var_acum_pct"]])
            for j in (8, 9):
                s.cell(s.max_row, j).number_format = "0.00%"
    for d in deu:
        s = wb.create_sheet(d["nombre"][:31])
        encabezado(s, ["Fecha subasta", f"Valor ({d['unidad']})", "Var. (pb)" if d["tipo"] == "tasa" else "Var. $", "Var. %"])
        for f in d["datos"]:
            s.append([f["fecha"], f["valor"], f["var_pb"] if d["tipo"] == "tasa" else f["var"], f["var_pct"]])
            s.cell(s.max_row, 4).number_format = "0.00%"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------- Servidor HTTP ----------------
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

    def translate_path(self, path):  # mismas rutas que en Vercel: /static/app.js
        if path.startswith("/static/"):
            path = path[len("/static"):]
        return super().translate_path(path)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")  # el celular siempre recibe la versión más reciente
        super().end_headers()

    def log_message(self, fmt, *args):
        if "/api/" in (args[0] if args else ""):
            print(f"[{datetime.now(TZ):%H:%M:%S}] {args[0]}")

    def send(self, body, ctype="application/json; charset=utf-8", status=200, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if not u.path.startswith("/api/"):
            return super().do_GET()
        qs = urllib.parse.parse_qs(u.query)
        if "fresco" in qs:  # botón Actualizar: ignora la caché y vuelve a consultar las fuentes
            with _lock:
                _cache.clear()
        try:
            desde = date.fromisoformat(qs.get("desde", ["2026-03-01"])[0])
            tickers = [t.strip().upper() for t in qs.get("tickers", [",".join(ACCIONES)])[0].split(",") if t.strip()]
            if u.path == "/api/estado":
                data = {"ahora": datetime.now(TZ).isoformat(), "mercado_abierto": mercado_abierto(),
                        "acciones": ACCIONES, "deuda": list(DEUDA)}
            elif u.path == "/api/acciones":
                data = acciones(tickers, desde)
            elif u.path == "/api/intradia":
                t = qs["ticker"][0]
                data = cached(("intra", t), 60, lambda: intradia(t))
            elif u.path == "/api/deuda":
                data = deuda(desde)
            elif u.path == "/api/analisis":
                data = analisis_completo(tickers, desde)
            elif u.path == "/api/comparar":
                data = comparacion(tickers, desde)
            elif u.path == "/api/cotizaciones":
                data = cotizaciones(tickers)
            elif u.path == "/api/simulacion":
                data = cached(("sim", desde, date.today()), 120, lambda: simulacion(desde))
            elif u.path == "/api/dia":
                f = qs.get("fecha", [None])[0]
                if not f:
                    raise ValueError("Falta la fecha (AAAA-MM-DD)")
                date.fromisoformat(f)
                reg = cached(("dia", f, date.today()), 120, lambda: dia(f))
                fmt = qs.get("formato", ["json"])[0]
                if fmt == "pdf":
                    return self.send(reportes.pdf_dia(reg), "application/pdf", extra={"Content-Disposition": f'attachment; filename="Alzea_analisis_{f}.pdf"'})
                if fmt == "xlsx":
                    return self.send(reportes.xlsx_dia(reg), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     extra={"Content-Disposition": f'attachment; filename="Alzea_analisis_{f}.xlsx"'})
                if fmt == "md":
                    return self.send(reportes.md_dia(reg).encode(), "text/markdown; charset=utf-8", extra={"Content-Disposition": f'attachment; filename="Alzea_analisis_{f}.md"'})
                data = reg
            elif u.path == "/api/excel":
                name = f"Mercado_{desde:%Y%m%d}_{datetime.now(TZ):%Y%m%d}.xlsx"
                return self.send(excel(tickers, desde),
                                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 extra={"Content-Disposition": f'attachment; filename="{name}"'})
            else:
                return self.send(b'{"error":"ruta no encontrada"}', status=404)
            self.send(json.dumps(data, ensure_ascii=False).encode())
        except Exception as e:
            self.send(json.dumps({"error": str(e)}, ensure_ascii=False).encode(), status=502)


if __name__ == "__main__":
    print(f"Monitor de mercado en http://localhost:{PORT}  (Ctrl+C para detener)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
