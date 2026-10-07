"""Fuentes del entorno de mercado.

Oficiales (publicadas por la propia institución):
  Banxico (SIE)  tipo de cambio FIX, tasa objetivo, TIIE, inflación de México (INPC, que Banxico toma del INEGI),
                 papel comercial y certificados bursátiles (cuadros CF102, CF101, CP151, CF133, CF302, CF304).
  Tesoro de EE. UU.        curva de rendimientos diaria (bonos del Tesoro).
  Reserva Federal de NY    tasa efectiva de fondos federales (EFFR) y rango objetivo de la Fed.
  BLS                      índice de precios al consumidor de EE. UU. (inflación).
  Cboe                     índice VIX.
De referencia (no oficiales): Yahoo Finance, para índices bursátiles y el índice del dólar.

Cada función devuelve listas [(fecha_iso, valor)] ordenadas por fecha.
"""
import csv
import io
import json
from datetime import date, datetime, timedelta

import server as S

FUENTES = {
    "banxico": {"nombre": "Banco de México · Sistema de Información Económica (SIE)",
                "url": "https://www.banxico.org.mx/SieInternet/", "oficial": True},
    "tesoro": {"nombre": "Departamento del Tesoro de EE. UU. · Daily Treasury Par Yield Curve Rates",
               "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve",
               "oficial": True},
    "nyfed": {"nombre": "Reserva Federal de Nueva York · Tasa efectiva de fondos federales (EFFR)",
              "url": "https://www.newyorkfed.org/markets/reference-rates/effr", "oficial": True},
    "bls": {"nombre": "Oficina de Estadísticas Laborales de EE. UU. (BLS) · Índice de precios al consumidor",
            "url": "https://www.bls.gov/cpi/", "oficial": True},
    "cboe": {"nombre": "Cboe Global Markets · Índice de volatilidad VIX",
             "url": "https://www.cboe.com/tradable_products/vix/vix_historical_data/", "oficial": True},
    "yahoo": {"nombre": "Yahoo Finance · datos de mercado (referencia, no oficial)",
              "url": "https://finance.yahoo.com/", "oficial": False},
}


def cuadro_url(c):
    return f"https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?sector=22&accion=consultarCuadro&idCuadro={c}&locale=es"


def _norm(t):
    """Etiqueta del SIE sin acentos, viñetas ni espacios especiales."""
    import re
    return " ".join(re.sub(r"[^a-z0-9% ]+", " ", S.sin_acentos(t)).split())


def _fila(rows, contiene, ocurrencia=0, despues=None):
    """Índice del renglón cuya etiqueta contiene `contiene` (sin acentos ni mayúsculas); opcionalmente después de `despues`."""
    n, ini = -1, 0
    if despues:
        ini = next((i for i, r in enumerate(rows) if len(r) > 1 and r[1] and S.sin_acentos(despues) in S.sin_acentos(r[1])), 0) + 1
    for i in range(ini, len(rows)):
        r = rows[i]
        if len(r) > 1 and r[1] and S.sin_acentos(contiene) in S.sin_acentos(r[1]) and any(isinstance(v, (int, float)) for v in r[2:]):
            n += 1
            if n == ocurrencia:
                return i
    return None


def _serie_fila(fechas, rows, i):
    if i is None:
        return []
    return sorted((fechas[j], float(v)) for j, v in enumerate(rows[i]) if j >= 2 and fechas[j] and isinstance(v, (int, float)))


def _banxico(cuadro, desde, hasta, contiene, ocurrencia=0, despues=None):
    fechas, rows = S.banxico_cuadro(cuadro, desde, hasta)
    return _serie_fila(fechas, rows, _fila(rows, contiene, ocurrencia, despues))


# ---------------------------------------------------------------- Banxico
def fx_fix(desde, hasta):
    """Tipo de cambio FIX (pesos por dólar), determinado cada día hábil por Banxico."""
    return _banxico("CF102", desde, hasta, "serie histórica")


def fx_cierre(desde, hasta):
    """Tipo de cambio de cierre de jornada (Banxico): se alinea mejor con el cierre de las bolsas."""
    return S.cached(("fxc", desde, hasta), 3 * 3600, lambda: _banxico("CF102", desde, hasta, "Cierre de Jornada"))


def tasa_objetivo(desde, hasta):
    return _banxico("CF101", desde, hasta, "Tasa objetivo")


def tiie28(desde, hasta):
    return _banxico("CF101", desde, hasta, "TIIE a 28")


def inflacion_mx(desde, hasta):
    """Inflación anual del INPC (mensual). El INEGI la calcula; Banxico la publica en el SIE."""
    ini = date(desde.year - 1, 12, 1) if desde.month < 3 else date(desde.year, 1, 1)
    return [(f, v) for f, v in _banxico("CP151", ini, hasta, "Inflación anual") if f <= hasta.isoformat()]


def privados_mensual(desde, hasta):
    """Papel comercial y certificados bursátiles: tasas (CF302) y colocaciones (CF304), por mes."""
    f2, r2 = S.banxico_cuadro("CF302", desde, hasta)
    f4, r4 = S.banxico_cuadro("CF304", desde, hasta)
    i_pc = _fila(r2, "Papel Comercial")
    i_cbcp = _fila(r2, "Certificados Bursatiles", 0)
    i_cbmp = _fila(r2, "Colocados en pesos", 0, despues="Certificados Bursátiles")
    i_cbmp_h = None
    # el «Colocados en pesos» posterior al encabezado «Certificados Bursátiles» de mediano plazo
    for i, r in enumerate(r2):
        if len(r) > 1 and r[1] and _norm(r[1]).startswith("certificados bursatiles") and not any(isinstance(v, (int, float)) for v in r[2:]):
            i_cbmp_h = i
    if i_cbmp_h is not None:
        i_cbmp = next((i for i in range(i_cbmp_h + 1, len(r2)) if r2[i][1] and "colocados en pesos" in _norm(r2[i][1])), None)
    s = {
        "tasa_pc": dict(_serie_fila(f2, r2, i_pc)),
        "tasa_cb_cp": dict(_serie_fila(f2, r2, i_cbcp)),
        "tasa_cb_mp": dict(_serie_fila(f2, r2, i_cbmp)),
        "col_cp": dict(_serie_fila(f4, r4, _fila(r4, "Corto Plazo"))),
        "col_pc": dict(_serie_fila(f4, r4, _fila(r4, "Papel comercial"))),
        "col_cb_cp": dict(_serie_fila(f4, r4, _fila(r4, "Certificados bursatiles"))),
        "col_mlp": dict(_serie_fila(f4, r4, _fila(r4, "Mediano y Largo Plazo"))),
    }
    meses = sorted(set().union(*[set(v) for v in s.values()]))
    return [{"mes": m, **{k: v.get(m) for k, v in s.items()}} for m in meses if desde.isoformat()[:7] <= m[:7] <= hasta.isoformat()[:7]]


# ----------------------------------------------------- Tesoro de EE. UU.
def tesoro(desde, hasta):
    """{plazo: [(fecha, rendimiento %)]} con la curva diaria del Tesoro (3 meses, 2, 10 y 30 años)."""
    def cargar():
        out = {"3 Mo": [], "2 Yr": [], "10 Yr": [], "30 Yr": []}
        for año in range(desde.year, hasta.year + 1):
            url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
                   f"{año}/all?type=daily_treasury_yield_curve&field_tdr_date_value={año}&page&_format=csv")
            for r in csv.DictReader(io.StringIO(S.http_get(url, 40).decode("utf-8-sig"))):
                f = datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat()
                for k in out:
                    if r.get(k) not in (None, ""):
                        out[k].append((f, float(r[k])))
        return {k: sorted(v) for k, v in out.items()}
    return S.cached(("ust", desde.year, hasta.year, hasta), 3600, cargar)


# ------------------------------------------------ Reserva Federal de NY
def effr(desde, hasta):
    """([(fecha, tasa efectiva %)], rango objetivo vigente (inferior, superior))."""
    def cargar():
        url = ("https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?"
               f"startDate={desde.isoformat()}&endDate={hasta.isoformat()}")
        filas = json.loads(S.http_get(url, 40))["refRates"]
        serie = sorted((r["effectiveDate"], float(r["percentRate"])) for r in filas)
        ult = max(filas, key=lambda r: r["effectiveDate"])
        return serie, (ult.get("targetRateFrom"), ult.get("targetRateTo"))
    return S.cached(("effr", desde, hasta), 3600, cargar)


# ------------------------------------------------------------------- BLS
def inflacion_us(desde, hasta):
    """Inflación anual de EE. UU. (IPC-U, todas las partidas), mensual."""
    def cargar():
        url = ("https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0?"
               f"startyear={desde.year - 1}&endyear={hasta.year}")
        datos = json.loads(S.http_get(url, 40))["Results"]["series"][0]["data"]
        idx = {}
        for d in datos:  # algunos meses vienen sin dato ("-"), por ejemplo cuando hubo cierre del gobierno
            try:
                if d["period"].startswith("M") and d["period"] != "M13":
                    idx[(int(d["year"]), int(d["period"][1:]))] = float(d["value"])
            except ValueError:
                continue
        out = []
        for (a, m), v in sorted(idx.items()):
            if (a - 1, m) in idx:
                out.append((date(a, m, 1).isoformat(), (v / idx[(a - 1, m)] - 1) * 100))
        return out
    return S.cached(("bls", desde.year, hasta.year), 6 * 3600, cargar)


# ------------------------------------------------------------------ Cboe
def vix(desde, hasta):
    def cargar():
        txt = S.http_get("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv", 40).decode("utf-8-sig")
        out = []
        for r in csv.DictReader(io.StringIO(txt)):
            try:
                f = datetime.strptime(r["DATE"], "%m/%d/%Y").date().isoformat()
            except (KeyError, ValueError):
                continue
            if f >= (desde - timedelta(days=10)).isoformat():
                out.append((f, float(r["CLOSE"])))
        return sorted(out)
    return S.cached(("vix", desde), 3 * 3600, cargar)


# ----------------------------------------------------- Yahoo (referencia)
def yahoo_cierres(ticker, desde):
    def cargar():
        p1 = int(datetime.combine(desde - timedelta(days=12), datetime.min.time(), S.TZ).timestamp())
        r = S.yahoo_chart(ticker, period1=p1, period2=int(datetime.now().timestamp()) + 3600, interval="1d")
        q = r["indicators"]["quote"][0]["close"]
        return sorted((datetime.fromtimestamp(t, S.TZ).date().isoformat(), float(c)) for t, c in zip(r.get("timestamp") or [], q) if c is not None)
    return S.cached(("yc", ticker, desde), 15 * 60, cargar)
