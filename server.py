"""Monitor de Mercado — servidor local.

Consulta Yahoo Finance (acciones BMV) y Banco de México (subastas de deuda)
y sirve un tablero web en http://localhost:8765 que se actualiza solo.

Uso:  python server.py   (o doble clic en iniciar.command)
"""
import io
import json
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

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
    out = []
    for t in tickers:
        try:
            out.append(cached(("acc", t, desde), ttl, lambda t=t: historico(t, desde)))
        except Exception as e:
            out.append({"ticker": t, "nombre": ACCIONES.get(t, t), "error": str(e), "historico": []})
    return out


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


def ip_local():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", PORT))
    print(f"Monitor de mercado en http://localhost:{port}  (Ctrl+C para detener)")
    if ip := ip_local():
        print(f"Desde tu celular (misma red Wi-Fi): http://{ip}:{port}")
    # 0.0.0.0 = acepta conexiones de otros dispositivos de la red (celular)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
