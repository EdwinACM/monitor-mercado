"use strict";
/* Alzea · interfaz. Los cálculos viven en el servidor (analisis.py, contexto.py); aquí solo se muestran. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sin almacenamiento */ } },
};
const MINUS = "−";
const fmt = (n, d = 2) => (n == null || Number.isNaN(n)) ? "—" : n.toLocaleString("es-MX", { minimumFractionDigits: d, maximumFractionDigits: d }).replace("-", MINUS);
const sg = n => n > 0 ? "+" : n < 0 ? MINUS : "";
const pct = (n, d = 2) => n == null ? "—" : sg(n) + Math.abs(n).toFixed(d) + "%";
const cls = n => n == null || Math.abs(n) < 1e-9 ? "flat" : n > 0 ? "up" : "down";
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const tk = t => t.replace(".MX", "");
const ymd = s => s.split("-").map(Number);
const flarga = s => { const [y, m, d] = ymd(s); return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}/${y}`; };
const fcorta = s => { const [, m, d] = ymd(s); return `${d} ${MESES[m - 1].slice(0, 3)}`; };
const fmes = s => { const [y, m] = ymd(s); return `${MESES[m - 1]} de ${y}`; };
const fhumana = s => { const [y, m, d] = ymd(s); return `${DIAS[new Date(y, m - 1, d).getDay()]} ${d} de ${MESES[m - 1]}`; };
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const alpha = (hex, a) => { const n = parseInt(hex.replace("#", ""), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
const hexOf = v => { const c = css(v); return c.startsWith("#") ? c : "#888888"; };
const serie = i => css("--s" + (i % 5 + 1));
const ICON = (id, c = "ic") => `<svg class="${c}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
const money = (v, m) => (m === "USD" ? "US$" : "$") + fmt(v);
const SIG = { "COMPRA FUERTE": ["buy", "up", "Compra fuerte"], COMPRAR: ["buy", "up", "Comprar"], MANTENER: ["hold", "flat", "Mantener"],
  VENDER: ["sell", "down", "Vender"], "VENTA FUERTE": ["sell", "down", "Venta fuerte"], ESPERAR: ["wait", "wait", "Esperar"], INFORMATIVO: ["hold", "info", "Informativo"], "SIN DATOS": ["hold", "flat", "Sin datos"] };
const sig = v => { const [k, i, t] = SIG[v] || SIG.MANTENER; return `<span class="sig ${k}">${ICON(i)}${t}</span>`; };
const sigK = v => (SIG[v] || SIG.MANTENER)[0];
const sigT = v => (SIG[v] || SIG.MANTENER)[2];

/* ------------------------------------------------------------------- estado */
const INICIO = "2026-03-01"; // el periodo de consulta nunca empieza antes
const hoyMX = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Mexico_City" });
const VISTAS = [["mercado", "Mercado", "board"], ["entorno", "Entorno", "globe"], ["deuda", "Deuda", "debt"], ["comparar", "Comparar", "compare"], ["informe", "Informe", "report"]];
const RANGOS = [["hoy", "Hoy"], ["21", "1M"], ["63", "3M"], ["126", "6M"], ["0", "Periodo"]];
const S = { vista: "mercado", periodo: null, data: null, ctx: null, guia: null, sel: null, selD: 0, rango: "0", filtro: "todas", moneda: "mxn", modoC: "comparar",
  cmp: null, sim: null, arch: null, quotes: {}, shown: {}, auto: store.get("auto", true), tData: 0, tQuote: 0, busy: false, selCmp: new Set(), fechaDia: null, dia: null, charts: {} };

function ajustar(p) {
  const hoy = hoyMX();
  return { desde: p.desde < INICIO ? INICIO : p.desde > hoy ? hoy : p.desde, hasta: p.hasta > hoy ? hoy : p.hasta < INICIO ? INICIO : p.hasta };
}
function periodoGuardado() {
  try { const p = JSON.parse(sessionStorage.getItem("periodo")); if (p?.desde && p?.hasta) return ajustar(p); } catch { /* sin almacenamiento */ }
  return { desde: INICIO, hasta: hoyMX() };
}
const qsP = () => `desde=${S.periodo.desde}&hasta=${S.periodo.hasta}`;
const vivo = () => !!S.data?.periodo?.vivo;

/* ---------------------------------------------------------------- utilidades */
async function api(path) {
  const r = await fetch(path, { cache: "no-store" });
  if (r.headers.get("X-Desde-Cache")) marcarSinConexion(+r.headers.get("X-Guardado") || 0);
  else if (S.sinConexion && r.ok) { S.sinConexion = false; avisoConexion(); }
  let j;
  try { j = await r.json(); } catch { throw new Error("El servidor no respondió con datos válidos"); }
  if (!r.ok || j.error) throw new Error(j.error || r.statusText);
  return j;
}
function marcarSinConexion(t) {
  S.sinConexion = true; S.guardado = Math.max(S.guardado || 0, t || 0);
  avisoConexion();
}
function avisoConexion() {
  const el = $("#offline"); if (!el) return;
  el.hidden = !S.sinConexion && navigator.onLine;
  if (!el.hidden) {
    const g = S.guardado ? ` Última actualización guardada: ${new Date(S.guardado).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" })}.` : "";
    el.textContent = `Sin conexión a internet. Se muestran los últimos datos guardados en este dispositivo.${g}`;
  }
}
const showErr = m => { const e = $("#err"); e.textContent = m || ""; e.hidden = !m; };
function relojNY() {
  const p = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", weekday: "short", hour: "numeric", minute: "numeric", hourCycle: "h23" }).formatToParts(new Date());
  const g = k => p.find(x => x.type === k).value;
  return { finde: ["Sat", "Sun"].includes(g("weekday")), min: +g("hour") * 60 + +g("minute") };
}
// La BMV, el Nasdaq y la NYSE operan lunes a viernes de 9:30 a 16:00 (hora de Nueva York). En días festivos el reloj diría «abierta»,
// así que además se exige que haya cotizaciones recientes (o que apenas haya abierto la sesión). Ningún botón cambia este estado.
function abiertoNY() { const r = relojNY(); return !r.finde && r.min >= 570 && r.min < 960; }
function abierto() {
  if (!abiertoNY()) return false;
  const t = Math.max(0, ...Object.values(S.quotes).map(q => q.hora ? Date.parse(q.hora) : 0));
  return !t || Date.now() - t < 40 * 60000 || relojNY().min - 570 < 30;
}
async function descargar(url, btn) {
  btn.setAttribute("aria-busy", "true");
  const txt = btn.innerHTML; btn.innerHTML = `${ICON("refresh")}Generando…`;
  try {
    const r = await fetch(url + (url.includes('?') ? '&' : '?') + 'fresco=1&t=' + Date.now());
    if (!r.ok) { let m = r.statusText; try { m = (await r.json()).error || m; } catch { /* no es json */ } throw new Error(m); }
    const nombre = /filename="([^"]+)"/.exec(r.headers.get("Content-Disposition") || "")?.[1] || "reporte";
    const u = URL.createObjectURL(await r.blob());
    Object.assign(document.createElement("a"), { href: u, download: nombre }).click();
    setTimeout(() => URL.revokeObjectURL(u), 3000);
    showErr("");
  } catch (e) { showErr(navigator.onLine ? `No se pudo generar el archivo. ${e.message}. Intenta de nuevo en unos segundos.` : "Sin conexión: este archivo no está guardado en el dispositivo. Descárgalo cuando tengas internet o usa «Guardar para ver sin internet»."); }
  btn.removeAttribute("aria-busy"); btn.innerHTML = txt;
}
function ligarDescargas(raiz) {
  $$("[data-dl]", raiz).forEach(b => b.onclick = e => { e.preventDefault(); descargar(b.dataset.dl, b); });
}
const dlBtn = (url, etq, solid) => `<a class="btn ${solid ? "solid" : ""}" href="${url}" data-dl="${url}">${ICON("download")}${etq}</a>`;

/* ------------------------------------------------------------------- gráficas */
const crosshair = { id: "crosshair", afterDatasetsDraw(ch) {
  const a = ch.tooltip?._active; if (!a?.length) return;
  const { ctx, chartArea: { top, bottom } } = ch, x = a[0].element.x;
  ctx.save(); ctx.strokeStyle = css("--rule-strong"); ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke(); ctx.restore();
} };
const endLabels = { id: "endLabels",
  beforeLayout(ch, _, o) {
    if (!o?.on) return;
    const c = ch.ctx; c.save(); c.font = `600 12px ${css("--f-num")}`;
    const w = Math.max(0, ...ch.data.datasets.filter(d => d.endLabel).map(d => c.measureText(d.endLabel).width));
    c.restore();
    const lim = Math.round(ch.width * 0.34);  // en pantallas angostas las etiquetas no pueden comerse la gráfica
    ch.options.layout.padding.right = Math.min(Math.ceil(w) + 26, lim);
  },
  afterDatasetsDraw(ch, _, o) {
  if (!o?.on) return;
  const { ctx } = ch, items = [];
  ch.data.datasets.forEach((ds, i) => {
    if (!ds.endLabel || ch.getDatasetMeta(i).hidden) return;
    const pts = ch.getDatasetMeta(i).data; let k = pts.length - 1;
    while (k >= 0 && ds.data[k] == null) k--;
    if (k >= 0) items.push({ y: pts[k].y, x: pts[k].x, text: ds.endLabel, color: ds.borderColor });
  });
  items.sort((a, b) => a.y - b.y);
  for (let i = 1; i < items.length; i++) if (items[i].y - items[i - 1].y < 15) items[i].y = items[i - 1].y + 15;
  ctx.save(); ctx.font = `600 12px ${css("--f-num")}`; ctx.textBaseline = "middle";
  items.forEach(it => { ctx.fillStyle = it.color; ctx.fillRect(it.x + 5, it.y - 4, 8, 8); ctx.fillStyle = css("--ink-2"); ctx.fillText(it.text, it.x + 18, it.y, Math.max(20, ch.width - it.x - 20)); });
  ctx.restore();
} };
const refLine = { id: "refLine", afterDatasetsDraw(ch, _, o) {
  if (o?.valor == null) return;
  const y = ch.scales.y.getPixelForValue(o.valor), { ctx, chartArea: { left, right } } = ch;
  ctx.save(); ctx.strokeStyle = css("--muted"); ctx.lineWidth = 1; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke(); ctx.restore();
} };
Chart.register(crosshair, endLabels, refLine);

function mk(id, cfg) { S.charts[id]?.destroy(); const c = document.getElementById(id); if (!c) return null; S.charts[id] = new Chart(c, cfg); return S.charts[id]; }
function opts({ fy = v => fmt(v), ftip, min, max, step, right = 8, extra, title } = {}) {
  return {
    responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false }, layout: { padding: { right } },
    plugins: { legend: { display: false }, endLabels: { on: false }, refLine: {},
      tooltip: { backgroundColor: css("--surface"), titleColor: css("--muted"), bodyColor: css("--ink"), borderColor: css("--rule-strong"), borderWidth: 1,
        padding: 10, boxPadding: 4, usePointStyle: true, titleFont: { family: css("--f-ui"), size: 12 }, bodyFont: { family: css("--f-num"), size: 14, weight: "600" },
        filter: it => it.dataset.tip !== false, callbacks: { label: c => ` ${c.dataset.label}: ${(ftip || fy)(c.parsed.y)}`, title: title } },
      ...(extra || {}) },
    scales: {
      x: { grid: { display: false }, border: { color: css("--rule-strong") }, ticks: { color: css("--muted"), maxTicksLimit: innerWidth < 600 ? 4 : 7, maxRotation: 0, autoSkip: true, font: { family: css("--f-num"), size: innerWidth < 600 ? 11 : 12 } } },
      y: { min, max, grid: { color: css("--rule") }, border: { display: false }, ticks: { color: css("--muted"), callback: fy, stepSize: step, maxTicksLimit: 6, font: { family: css("--f-num"), size: innerWidth < 600 ? 11 : 12 } } },
    },
  };
}
const linea = (label, data, color, o = {}) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: o.w ?? 2, pointRadius: o.pr ?? 0,
  pointHoverRadius: 4, tension: .12, spanGaps: true, fill: false, ...o });
function alinear(lista, base100) {
  const fechas = [...new Set(lista.flatMap(s => s.datos.map(x => x[0])))].sort();
  return { fechas, valores: lista.map(s => { const m = new Map(s.datos); let ult = null, base = null;
    return fechas.map(f => { if (m.has(f)) ult = m.get(f); if (ult == null) return null; if (base == null) base = ult; return base100 ? ult / base * 100 : ult; }); }) };
}

/* ------------------------------------------------------------------ navegación */
function renderNav() {
  $("#nav").innerHTML = VISTAS.map(([id, t, ic]) => `<a href="#${id}" data-v="${id}">${ICON(ic)}${t}</a>`).join("");
}
function setVista(v) {
  if (!VISTAS.some(x => x[0] === v)) v = "mercado";
  S.vista = v;
  $$("#nav a").forEach(a => { if (a.dataset.v === v) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  $$(".view").forEach(x => x.hidden = x.id !== "v-" + v);
  window.scrollTo({ top: 0 });
  render();
}
async function render() {
  try {
    showErr("");
    if (!S.data) return;
    ({ mercado: renderMercado, entorno: renderEntorno, deuda: renderDeuda, comparar: renderComparar, informe: renderInforme })[S.vista]();
  } catch (e) { showErr(`No se pudo mostrar esta sección. ${e.message}. Intenta actualizar de nuevo.`); }
}
function armar(id, html) {
  const el = $("#v-" + id);
  if (!el.dataset.listo) { el.innerHTML = html; el.dataset.listo = "1"; }
  return el;
}

/* ----------------------------------------------------------------- periodo */
function renderPeriodo() {
  const hoy = hoyMX(), p = S.periodo, [yh, mh] = ymd(hoy);
  const meses = [];
  for (let m = 3; m <= (yh === 2026 ? mh : 12); m++) {
    const ini = `2026-${String(m).padStart(2, "0")}-01`, fin = `2026-${String(m).padStart(2, "0")}-${new Date(2026, m, 0).getDate()}`;
    meses.push({ etq: MESES[m - 1].slice(0, 3), largo: MESES[m - 1], ini, fin: fin > hoy ? hoy : fin });
  }
  const dias = n => { const d = new Date(hoy + "T12:00:00"); d.setDate(d.getDate() - n + 1); const s = d.toLocaleDateString("en-CA"); return s < INICIO ? INICIO : s; };
  const chips = [{ etq: "Todo", largo: "Todo el periodo desde el 1 de marzo", ini: INICIO, fin: hoy }, { etq: "7 días", largo: "Últimos 7 días", ini: dias(7), fin: hoy },
    { etq: "30 días", largo: "Últimos 30 días", ini: dias(30), fin: hoy }, ...meses];
  $("#periodo").innerHTML = `<div class="periodo-in"><span class="tit">Periodo de consulta</span>
    <label>Desde <input type="date" id="pDesde" min="${INICIO}" max="${hoy}" value="${p.desde}"></label>
    <label>Hasta <input type="date" id="pHasta" min="${INICIO}" max="${hoy}" value="${p.hasta}"></label>
    <div class="pchips" role="group" aria-label="Periodos rápidos">${chips.map((c, i) => `<button class="pchip" data-i="${i}" title="${esc(c.largo)}" aria-pressed="${c.ini === p.desde && c.fin === p.hasta}">${esc(c.etq)}</button>`).join("")}</div>
    <p class="nota">Las consultas siempre inician el 1 de marzo de 2026 o después; no hay datos ni informes anteriores a esa fecha.</p></div>`;
  $$("#periodo .pchip").forEach(b => b.onclick = () => setPeriodo(chips[+b.dataset.i].ini, chips[+b.dataset.i].fin));
  const cambio = () => setPeriodo($("#pDesde").value || INICIO, $("#pHasta").value || hoy);
  $("#pDesde").onchange = $("#pHasta").onchange = cambio;
}
function setPeriodo(d, h) {
  const aj = ajustar({ desde: d, hasta: h });
  if (aj.desde >= aj.hasta) { showErr("El periodo debe tener al menos dos días: «Desde» tiene que ser anterior a «Hasta» y no antes del 1 de marzo de 2026."); renderPeriodo(); return; }
  S.periodo = aj;
  try { sessionStorage.setItem("periodo", JSON.stringify(aj)); } catch { /* sin almacenamiento */ }
  renderPeriodo();
  S.cmp = S.sim = S.arch = S.ctx = S.dia = null;
  actualizar(false);
}

/* ----------------------------------------------------------------------- datos */
async function cargar(fresco) {
  const d = await api(`/api/analisis?${qsP()}&tickers=${(S.tickers || []).join(",")}${fresco ? "&fresco=1" : ""}`);
  S.data = d; S.tData = Date.now();
  const tks = d.acciones.map(a => a.ticker);
  if (!S.sel || !tks.includes(S.sel)) S.sel = tks[0];
  if (!S.selCmp.size) ["AAPL", "NVDA", "WALMEX.MX", "AMXB.MX", "KO"].filter(t => tks.includes(t)).forEach(t => S.selCmp.add(t));
}
async function cargarCtx() {
  if (S.ctx) return S.ctx;
  const clave = qsP();
  try { const c = await api(`/api/contexto?${clave}`); if (clave === qsP()) { S.ctx = c; } }
  catch (e) { S.ctxError = e.message; }
  renderCinta();
  if (S.data && (S.vista === "entorno" || S.vista === "mercado" || S.vista === "deuda")) render();
  return S.ctx;
}
async function cargarGuia() {
  if (!S.guia) S.guia = await api("/api/guia");
  return S.guia;
}
async function actualizar(fresco = true) {
  if (S.busy) return;
  S.busy = true; $("#refresh").classList.add("spin");
  try {
    S.cmp = S.sim = S.arch = null;
    if (fresco) S.ctx = null;
    await cargar(fresco);
    if (vivo()) await pollQuotes(true).catch(() => {});
    S.busy = false;
    await render(); showErr("");
    cargarCtx();
  } catch (e) { showErr(`No se pudo actualizar. ${e.message}`); }
  S.busy = false; $("#refresh").classList.remove("spin"); estadoLive();
}

/* ------------------------------------------------------------ cinta de indicadores */
const CINTA = [["fx", "USD/MXN FIX"], ["sp500", "S&P 500"], ["nasdaq", "Nasdaq"], ["ipc", "IPC México"], ["dxy", "Dólar DXY"], ["ust10y", "Tesoro 10 a."], ["effr", "Fed (EFFR)"], ["tasa_obj", "Banxico"], ["vix", "VIX"]];
function renderCinta() {
  const el = $("#cinta");
  if (!S.ctx) { el.innerHTML = `<div class="carga">${S.ctxError ? "No se pudo cargar el entorno global: " + esc(S.ctxError) : "Cargando indicadores del entorno global…"}</div>`; return; }
  const d = Object.fromEntries(S.ctx.indicadores.map(x => [x.id, x]));
  el.innerHTML = `<div class="cinta-in">` + CINTA.filter(([id]) => d[id]).map(([id, etq]) => {
    const x = d[id], s = x.serie, v1 = s.at(-1)[1], v0 = s.length > 1 ? s.at(-2)[1] : v1;
    const c = x.tipo === "tasa" ? (v1 - v0) * 100 : (v0 ? (v1 / v0 - 1) * 100 : 0), u = x.tipo === "tasa" ? " pb" : "%";
    return `<a class="ci" href="#entorno" title="${esc(x.nombre)} al ${flarga(s.at(-1)[0])}"><div class="l">${esc(etq)}</div><div class="v num">${fmt(v1)}</div><div class="c num ${cls(c)}">${sg(c)}${Math.abs(c).toFixed(2)}${u}</div></a>`; }).join("") + `</div>`;
}

/* ------------------------------------------------------------------- mercado */
const MERCADO_HTML = `
  <div class="head"><h1 id="mTitulo">Mercado</h1><p class="sub" id="mSub"></p><div class="lectura prose" id="mLectura"></div></div>
  <div id="alertas" aria-live="polite"></div>
  <div class="filtro"><div class="seg" id="mFiltro" role="group" aria-label="Mercado a mostrar"></div><span class="note" id="mNota"></span></div>
  <div class="board"><table id="board" aria-label="Cotizaciones de acciones"></table><div class="board-foot" id="boardFoot"></div></div>
  <div class="detail" id="detalle" hidden>
    <div class="detail-head"><h2 id="dNombre"></h2>
      <div class="tools"><div class="seg" id="rango" role="group" aria-label="Rango de la gráfica"></div>
        <label class="tgl"><input type="checkbox" id="chkMedias" checked> Medias móviles</label><label class="tgl"><input type="checkbox" id="chkBandas"> Bandas de Bollinger</label></div></div>
    <div class="cols"><div><div class="legend" id="legPrecio"></div><div class="chartbox"><canvas id="chPrecio" role="img" aria-label="Gráfica de precio de cierre"></canvas></div></div><aside class="verdict" id="senal"></aside></div>
    <div class="split"><section class="sec"><h2>Qué es</h2><div id="queEs"></div></section><section class="sec"><h2>Estadística del periodo</h2><dl class="dl" id="stats"></dl></section></div>
    <div class="split"><section class="sec"><h2>Decisión del día y por qué</h2><div class="prose" id="texto"></div><div class="row-btns" id="descDia"></div></section>
      <section class="sec"><h2>Relación con EE. UU. y el dólar</h2><div id="mxVista"></div></section></div>
    <section class="sec"><h2>Proyección de precio</h2><p class="intro" id="proyTexto"></p><div class="legend" id="legProy"></div><div class="chartbox md"><canvas id="chProy" role="img" aria-label="Rango proyectado del precio"></canvas></div>
      <div class="scrollx"><table class="tbl" id="tblProy"></table></div><p class="note" id="proyNota" style="margin-top:8px"></p></section>
    <div class="split"><section class="sec"><h2>RSI y MACD</h2><div class="chartbox sm"><canvas id="chRsi" role="img" aria-label="RSI de 14 sesiones"></canvas></div><div class="chartbox sm" style="margin-top:12px"><canvas id="chMacd" role="img" aria-label="MACD"></canvas></div></section>
      <section class="sec"><h2>Prueba histórica de la señal</h2><div id="bt"></div></section></div>
    <section class="sec"><h2>Últimos cambios de decisión</h2><div id="histCambios"><p class="note">Cargando…</p></div></section>
  </div>`;

const visto = {};
const entra = v => visto[v] ? "" : (visto[v] = "enter");
function precioVivo(a) { const q = vivo() && S.quotes[a.ticker]; return q && q.precio != null ? q.precio : a.cierre; }
function cambioVivo(a) { const p = precioVivo(a); return [p - a.previo, (p / a.previo - 1) * 100]; }
function spark(vals, up) {
  const w = 92, h = 28, mn = Math.min(...vals), mx = Math.max(...vals), r = mx - mn || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1) * w).toFixed(1)},${(h - 2 - (v - mn) / r * (h - 4)).toFixed(1)}`);
  const c = up ? "var(--up-b)" : "var(--down-b)", last = pts.at(-1).split(",");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts.join(" ")}" fill="none" stroke="${c}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${last[0]}" cy="${last[1]}" r="2.6" fill="${c}"/></svg>`;
}
function filaAccion(a, i) {
  if (a.error) return `<tr><td colspan="7" class="flat">${esc(tk(a.ticker))}: sin datos (${esc(a.error)})</td></tr>`;
  const [v, p] = cambioVivo(a), s30 = a.serie.cierre.slice(-30);
  return `<tr tabindex="0" data-t="${a.ticker}" aria-selected="${a.ticker === S.sel}" style="--i:${i}">
    <td><div><div class="tk">${tk(a.ticker)}<span class="mk">${esc(a.mercado)}</span></div><div class="nm">${esc(a.nombre)}</div><div class="m-only">${sig(a.veredicto)}</div></div></td>
    <td><span class="px num" data-px>${fmt(precioVivo(a))}</span><span class="mon">${a.moneda}</span></td>
    <td class="c-chg"><span class="chg num ${cls(v)}" data-chg>${sg(v)}${fmt(Math.abs(v))}</span></td>
    <td><span class="chg num ${cls(p)}" data-pct style="display:inline-flex;align-items:center;gap:4px">${ICON(v > 0 ? "up" : v < 0 ? "down" : "flat")}${Math.abs(p).toFixed(2)}%</span></td>
    <td class="c-per"><span class="chg num ${cls(a.ret_periodo)}">${pct(a.ret_periodo)}</span></td>
    <td class="c-spark">${spark(s30, s30.at(-1) >= s30[0])}</td>
    <td class="c-sig">${sig(a.veredicto)}</td></tr>`;
}
function renderMercado() {
  armar("mercado", MERCADO_HTML);
  const d = S.data, ok = d.acciones.find(a => !a.error), hist = !vivo();
  $("#mTitulo").textContent = !hist && abierto() ? "Sesión en curso" : ok ? `Cierre del ${fhumana(ok.fecha)}` : "Mercado";
  $("#mSub").textContent = `Periodo del ${flarga(S.periodo.desde)} al ${flarga(S.periodo.hasta)}${hist ? " · consulta histórica, sin actualización en vivo" : ""}`;
  $("#mLectura").innerHTML = `<p>${esc(d.mercado.texto_periodo || "")}</p><p>${esc(d.mercado.texto)}</p>`;
  const filtros = [["todas", "Todas"], ["mx", "México · BMV"], ["us", "EE. UU. · Nasdaq y NYSE"]];
  $("#mFiltro").innerHTML = filtros.map(([k, t]) => `<button data-f="${k}" aria-pressed="${S.filtro === k}">${t}</button>`).join("");
  $$("#mFiltro button").forEach(b => b.onclick = () => { S.filtro = b.dataset.f; renderMercado(); });
  $("#mNota").textContent = "Precios en la moneda de cada mercado: pesos (MXN) o dólares (USD). «Periodo» es el rendimiento en esa moneda.";
  const lista = d.acciones.filter(a => S.filtro === "todas" || (S.filtro === "mx" ? a.pais === "México" : a.pais && a.pais !== "México"));
  let cuerpo = "", grupo = null;
  lista.forEach((a, i) => {
    if (S.filtro === "todas" && !a.error) { const g = a.pais === "México" ? "México · Bolsa Mexicana de Valores · pesos" : "Estados Unidos · Nasdaq y NYSE · dólares";
      if (g !== grupo) { grupo = g; cuerpo += `<tr class="grupo"><th colspan="7" scope="colgroup">${g}</th></tr>`; } }
    cuerpo += filaAccion(a, i);
  });
  $("#board").innerHTML = `<thead><tr><th>Emisora</th><th>Último</th><th class="c-chg">Cambio</th><th>Día</th><th class="c-per">Periodo</th><th class="c-spark">30 sesiones</th><th class="c-sig">Decisión</th></tr></thead><tbody class="${entra("mercado")}">${cuerpo}</tbody>`;
  $$("#board tbody tr[data-t]").forEach(tr => {
    tr.onclick = () => seleccionar(tr.dataset.t, true);
    tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); seleccionar(tr.dataset.t, true); } };
    const a = d.acciones.find(x => x.ticker === tr.dataset.t), old = S.shown[a.ticker], nw = precioVivo(a);
    if (old != null && old !== nw) flip(tr.querySelector("[data-px]"), nw > old);
    S.shown[a.ticker] = nw;
  });
  pieCotizaciones();
  if (vivo()) renderAlertas(); else $("#alertas").innerHTML = "";
  renderDetalle();
}
function pieCotizaciones() {
  $("#boardFoot").innerHTML = `<span>Precios: Yahoo Finance (referencia, con posible retraso de 15 a 20 minutos)</span><span id="updTxt">${textoActualizado()}</span>`;
}
function textoActualizado() {
  if (!S.tData) return "";
  if (!vivo()) return "Consulta histórica";
  const q = S.tQuote ? Math.max(S.tQuote, S.tData) : S.tData, s = Math.round((Date.now() - q) / 1000);
  return s < 5 ? "Actualizado ahora" : s < 60 ? `Actualizado hace ${s} s` : `Actualizado hace ${Math.round(s / 60)} min`;
}
function flip(el, sube) {
  if (!el) return;
  el.classList.remove("flip"); void el.offsetWidth; el.classList.add("flip");
  const td = el.closest("td"); td.classList.remove("tick-up", "tick-down"); void td.offsetWidth; td.classList.add(sube ? "tick-up" : "tick-down");
}
function seleccionar(t, scroll) {
  S.sel = t;
  $$("#board tbody tr[data-t]").forEach(tr => tr.setAttribute("aria-selected", tr.dataset.t === t));
  renderDetalle();
  if (scroll && innerWidth < 980) $("#detalle").scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --------------------------------------------------------------------- detalle */
async function renderDetalle() {
  const d = S.data, a = d.acciones.find(x => x.ticker === S.sel && !x.error) || d.acciones.find(x => !x.error);
  if (!a) return;
  $("#detalle").hidden = false;
  $("#dNombre").textContent = `${a.nombre} (${tk(a.ticker)}) · ${a.mercado} · ${a.moneda}`;
  $("#chkMedias").onchange = $("#chkBandas").onchange = () => graficaPrecio(a);
  $("#rango").innerHTML = RANGOS.map(([v, t]) => `<button data-r="${v}" aria-pressed="${S.rango === v}" ${v === "hoy" && !vivo() ? "disabled" : ""}>${t}</button>`).join("");
  $$("#rango button").forEach(b => b.onclick = () => { S.rango = b.dataset.r; renderDetalle(); });
  if (S.rango === "hoy" && !vivo()) S.rango = "0";

  $("#senal").innerHTML = `<div class="word ${sigK(a.veredicto)}">${sigT(a.veredicto)}</div>
    <p class="meta">Puntaje <b class="num">${sg(a.score)}${Math.abs(a.score)}</b> de ±100 · confianza ${a.confianza.toLowerCase()} · tendencia ${a.tendencia.etiqueta}</p>
    <div class="gauge"><i style="left:${Math.max(0, Math.min(100, (a.score + 100) / 2))}%"></i></div>
    <div class="gauge-l"><span>Vender</span><span>Mantener</span><span>Comprar</span></div>
    <table class="crit"><tbody>` + a.componentes.map(c => { const w = Math.abs(c.puntos) / c.max * 50;
      return `<tr><td><b>${esc(c.criterio)}</b><span>${esc(c.detalle)}</span><span class="pbar"><i style="left:${c.puntos >= 0 ? 50 : 50 - w}%;width:${w}%;background:var(${c.puntos === 0 ? "--rule-strong" : c.puntos > 0 ? "--up" : "--down"})"></i></span></td><td class="pts ${cls(c.puntos)}">${sg(c.puntos)}${Math.abs(c.puntos)}</td></tr>`; }).join("") + `</tbody></table>`;

  const s = a.stats, row = (l, v, c) => `<div><dt>${l}</dt><dd class="${c || ""}">${v}</dd></div>`;
  $("#stats").innerHTML = [
    row("Rendimiento del periodo", pct(a.ret_periodo), cls(a.ret_periodo)), row("Rendimiento 20 sesiones", pct(a.ret20), cls(a.ret20)),
    row("Rendimiento 5 sesiones", pct(a.ret5), cls(a.ret5)), row("RSI (14)", a.rsi == null ? "—" : a.rsi.toFixed(2)),
    row("Volatilidad anual", s.vol_anual == null ? "—" : s.vol_anual.toFixed(2) + "%"), row("Caída máxima (120 ses.)", pct(s.max_drawdown), "down"),
    row("Soporte (20 ses.)", fmt(s.soporte)), row("Resistencia (20 ses.)", fmt(s.resistencia)),
    row("Rendimiento / riesgo", s.ratio_rend_riesgo == null ? "—" : fmt(s.ratio_rend_riesgo), cls(s.ratio_rend_riesgo)), row("Z del precio vs. media 20", sg(s.z_precio) + Math.abs(s.z_precio).toFixed(2)),
    row("Tendencia 30 ses.", a.tendencia.pendiente == null ? "—" : pct(a.tendencia.pendiente, 2) + "/día", cls(a.tendencia.pendiente)), row("Volumen vs. promedio", s.vol_relativo == null ? "—" : s.vol_relativo.toFixed(2) + "×")].join("");
  $("#texto").innerHTML = `<div class="decision ${sigK(a.veredicto)}" style="font:700 22px/1.2 var(--f-num);margin-bottom:8px">${esc(a.decision)}</div>
    <p>${esc(a.texto)}</p><p><b>Por qué:</b></p><ul>${a.por_que.map(p => `<li>${esc(p)}</li>`).join("")}</ul>
    <p><b>Respaldo estadístico:</b> ${esc(a.respaldo)}</p>
    <p><b>Qué hacer:</b> ${esc(a.accion)}</p>
    <p><b>Qué podría hacer fallar la decisión:</b></p><ul>${a.riesgos.map(p => `<li>${esc(p)}</li>`).join("")}</ul>` + (a.cambio ? `<p><b>Cambio de decisión:</b> antes era ${esc(sigT(a.veredicto_ant).toLowerCase())}, ahora es ${esc(a.decision.toLowerCase())}.</p>` : "");
  $("#descDia").innerHTML = dlBtn(`/api/dia?fecha=${a.fecha}&formato=pdf`, `PDF del ${flarga(a.fecha)}`) + dlBtn(`/api/dia?fecha=${a.fecha}&formato=xlsx`, "Excel del día") +
    `<p class="note" style="flex-basis:100%">Incluye todas las emisoras y la deuda: decisión, por qué, qué hacer, lo que pasó después y el entorno del día.</p>`;
  ligarDescargas($("#descDia"));
  const b = a.backtest, fila = (t, n, ac, r, ok, bueno) => `<tr><td>${t}</td><td>${n}</td><td class="${ok ? "up" : "down"}">${n < 8 ? "—" : fmt(ac) + "%"}</td><td class="${cls(r)}">${n < 8 ? "—" : pct(r)}</td><td>${n < 8 ? "pocos casos" : bueno}</td></tr>`;
  const okC = b.aciertos_compra >= 55 && b.rend_medio_compra > b.base_rend_medio, okV = b.aciertos_venta >= 55 && b.rend_medio_venta < b.base_rend_medio;
  $("#bt").innerHTML = `<div class="scrollx"><table class="tbl"><thead><tr><th>Señal</th><th>Casos</th><th>Aciertos</th><th>Rend. a ${b.horizonte} ses.</th><th>Lectura</th></tr></thead><tbody>` +
    fila("Compra", b.n_compra, b.aciertos_compra, b.rend_medio_compra, okC, okC ? "respaldada" : "sin respaldo") + fila("Venta", b.n_venta, b.aciertos_venta, b.rend_medio_venta, okV, okV ? "respaldada" : "sin respaldo") +
    `</tbody></table></div><p class="note" style="margin-top:10px">Rendimiento medio de todas las sesiones: ${pct(b.base_rend_medio)}. Es una prueba dentro de la muestra de calibración (${b.muestra} sesiones de esta emisora): sirve para dimensionar la confianza, no la garantiza.</p>`;
  mxVista(a);
  proyeccion(a);
  queEs(a);
  cargarCambios();
  await graficaPrecio(a);
}
function proyeccion(a) {
  const p = a.proyeccion, mn = a.moneda;
  if (!p) { $("#proyTexto").textContent = "No hay historial suficiente para proyectar."; return; }
  const H = Math.min(60, a.serie.fechas.length), ab = p.abanico, col = hexOf("--line");
  const hist = a.serie.cierre.slice(-H), n = ab.h.length, nul = k => Array(k).fill(null);
  const proj = arr => [...nul(H - 1), hist[H - 1], ...arr];
  const L = [...a.serie.fechas.slice(-H).map(fcorta), ...ab.h.map(h => `+${h}`)];
  const brand = hexOf("--brand-text");
  mk("chProy", { type: "line", data: { labels: L, datasets: [
    { label: "Banda 95 % alta", data: proj(ab.hi95), borderColor: "transparent", backgroundColor: alpha(brand, .10), pointRadius: 0, fill: "+1", tip: false },
    { label: "Banda 95 % baja", data: proj(ab.lo95), borderColor: "transparent", pointRadius: 0, fill: false, tip: false },
    { label: "Banda 68 % alta", data: proj(ab.hi68), borderColor: "transparent", backgroundColor: alpha(brand, .18), pointRadius: 0, fill: "+1", tip: false },
    { label: "Banda 68 % baja", data: proj(ab.lo68), borderColor: "transparent", pointRadius: 0, fill: false, tip: false },
    linea("Cierre", [...hist, ...nul(n)], col, { w: 2.3 }),
    linea("Mediana proyectada", proj(ab.mediana), css("--ink"), { w: 1.6, borderDash: [6, 4] }),
    linea("Si continúa la tendencia", proj(ab.tendencia), css("--s2"), { w: 1.6, borderDash: [2, 3] })] },
    options: opts({ ftip: v => money(v, mn), right: 12, title: it => it[0].label.startsWith("+") ? `Dentro de ${it[0].label.slice(1)} sesiones` : it[0].label }) });
  $("#legProy").innerHTML = `<span style="--c:${col}"><i></i>Cierre de las últimas ${H} sesiones</span><span style="--c:${css("--ink")}"><i class="d"></i>Mediana proyectada</span><span style="--c:${css("--s2")}"><i class="t"></i>Si continúa la tendencia</span>
    <span style="--c:${brand}"><i class="f"></i>Rango de 68 % y de 95 %</span>`;
  $("#proyTexto").textContent = p.texto;
  $("#tblProy").innerHTML = `<thead><tr><th>Horizonte</th><th>Rango con 68 %</th><th>Rango con 95 %</th><th>Si continúa la tendencia</th><th>Acierto histórico del rango de 95 %</th></tr></thead><tbody>` +
    p.horizontes.map(h => `<tr><td>${h.h} sesiones</td><td>${money(h.b68[0], mn)} a ${money(h.b68[1], mn)}</td><td>${money(h.b95[0], mn)} a ${money(h.b95[1], mn)}</td><td>${money(h.tendencia, mn)}</td><td>${h.cobertura ? fmt(h.cobertura.p95) + " % de " + h.cobertura.n + " sesiones" : "—"}</td></tr>`).join("") + "</tbody>";
  $("#proyNota").textContent = `Volatilidad diaria reciente: ${fmt(p.sigma_diaria)} % (${fmt(p.sigma_anual)} % anual), estimada con un promedio móvil exponencial que pesa más lo reciente. El rango de 95 % debería contener el precio real 95 de cada 100 veces; la última columna muestra cuántas veces lo hizo en las últimas 250 sesiones. La línea de tendencia extiende la recta de las últimas 30 sesiones, ponderada por su ajuste (R² ${fmt(p.r2_tendencia)}). Son rangos de probabilidad, no un pronóstico.`;
}
async function queEs(a) {
  try {
    const g = (await cargarGuia()).acciones.find(x => x.ticker === a.ticker);
    if (!g || S.sel !== a.ticker && S.sel !== undefined && !S.data.acciones.find(x => x.ticker === S.sel)) return;
    $("#queEs").innerHTML = `<div class="prose"><p>${esc(g.que_es)}</p><p><b>Qué la mueve.</b> ${esc(g.que_la_mueve)}</p></div>` +
      (g.fuente ? `<p class="note" style="margin-top:8px">Fuente oficial: <a class="fuente" href="${esc(g.fuente.url)}" target="_blank" rel="noopener">${esc(g.fuente.nombre)}</a></p>` : "");
  } catch { $("#queEs").innerHTML = '<p class="note">No se pudo cargar la descripción.</p>'; }
}
function mxVista(a) {
  const el = $("#mxVista");
  if (!S.ctx) { el.innerHTML = `<p class="cargando">${S.ctxError ? "No se pudo cargar el entorno: " + esc(S.ctxError) : "Calculando con datos de Banxico y de EE. UU."}</p>`; return; }
  const s = S.ctx.sensibilidades.find(x => x.ticker === a.ticker), e = S.ctx.efecto_cambiario.find(x => x.ticker === a.ticker);
  const row = (l, v, c) => `<div><dt>${l}</dt><dd class="${c || ""}">${v}</dd></div>`;
  let h = "";
  if (s) h += `<dl class="dl">${row("Correlación con el S&P 500", fmt(s.corr_sp500))}${row("Beta frente al S&P 500", fmt(s.beta_sp500))}${row("Correlación con el dólar", fmt(s.corr_dolar))}${s.corr_ipc != null ? row("Correlación con el IPC", fmt(s.corr_ipc)) : ""}</dl>`;
  if (e) h += `<p class="h3" style="margin-top:14px">Visto desde México</p><dl class="dl">${row("Rendimiento en dólares", pct(e.ret_usd), cls(e.ret_usd))}${row("Variación del dólar", pct(e.ret_dolar), cls(e.ret_dolar))}${row("Rendimiento en pesos", pct(e.ret_pesos), cls(e.ret_pesos))}</dl>
    <p class="note" style="margin-top:8px">El tipo de cambio es el de cierre de Banxico. Un peso más débil suma al rendimiento de una acción en dólares; uno más fuerte lo resta.</p>`;
  const rm = S.ctx.riesgo_mercado?.find(x => x.ticker === a.ticker);
  if (rm) h += `<p class="h3" style="margin-top:14px">Rendimiento ajustado por riesgo</p><dl class="dl">${row("Razón de Sharpe", fmt(rm.sharpe))}${row("Razón de Sortino", fmt(rm.sortino))}${row("Alfa anual frente al " + rm.indice, pct(rm.alfa_anual), cls(rm.alfa_anual))}${row("Beta frente al " + rm.indice, fmt(rm.beta))}${row("R² del modelo", fmt(rm.r2))}${row("Asimetría", fmt(rm.asimetria))}${row("Pérdida probable a 20 sesiones (VaR 95 %)", fmt(rm.var20) + " %")}</dl>
    <p class="note" style="margin-top:8px">Sharpe: rendimiento por encima de la ${esc(rm.tasa_libre_nombre)} (${fmt(rm.tasa_libre)} % anual) por unidad de riesgo; Sortino solo penaliza las caídas. Alfa: rendimiento anual que no explica el índice (modelo CAPM). R²: qué parte de los movimientos explica el índice. Asimetría negativa: las caídas fuertes pesan más que las alzas. Calculado con ${rm.n} sesiones del periodo.</p>`;
  h += `<p class="note" style="margin-top:10px">Correlación y beta de los rendimientos diarios del periodo (${s ? s.n : "—"} sesiones). Un valor alto indica que se mueven juntos; no prueba que uno cause al otro.</p>`;
  el.innerHTML = h;
}
async function graficaPrecio(a) {
  const col = hexOf("--line"), medias = $("#chkMedias").checked, bandas = $("#chkBandas").checked, sr = a.serie, mn = a.moneda;
  if (S.rango === "hoy") {
    $("#chkMedias").disabled = $("#chkBandas").disabled = true;
    let intra = [];
    try { intra = await api(`/api/intradia?ticker=${encodeURIComponent(a.ticker)}`); } catch { showErr("No se pudo traer la gráfica del día. Intenta de nuevo en unos segundos."); }
    const L = intra.map(r => r.hora), v = intra.map(r => r.precio);
    mk("chPrecio", { type: "line", data: { labels: L, datasets: [linea("Precio", v, col, { w: 2 })] }, options: opts({ fy: n => fmt(n), ftip: n => money(n, mn), extra: { refLine: { valor: a.previo } } }) });
    $("#legPrecio").innerHTML = `<span style="--c:${col}"><i></i>Precio cada 5 minutos</span><span style="--c:${css("--muted")}"><i class="d"></i>Cierre anterior (${money(a.previo, mn)})</span>`;
    return;
  }
  $("#chkMedias").disabled = $("#chkBandas").disabled = false;
  const n = +S.rango, ini = n ? Math.max(0, sr.fechas.length - n) : 0, sl = arr => arr.slice(ini), L = sl(sr.fechas), ds = [];
  if (bandas) {
    ds.push({ label: "Banda sup.", data: sl(sr.bb_up), borderColor: alpha(hexOf("--ink-2"), .35), borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: alpha(hexOf("--brand-text"), .07), tip: false });
    ds.push({ label: "Banda inf.", data: sl(sr.bb_low), borderColor: alpha(hexOf("--ink-2"), .35), borderWidth: 1, pointRadius: 0, fill: false, tip: false });
  }
  ds.push(linea("Cierre", sl(sr.cierre), col, { w: 2.4, endLabel: "Cierre" }));
  if (medias) { ds.push(linea("Media 20", sl(sr.sma20), css("--ink"), { w: 1.5, borderDash: [6, 4], endLabel: "Media 20" }));
    ds.push(linea("Media 50", sl(sr.sma50), css("--muted"), { w: 1.6, borderDash: [2, 3], endLabel: "Media 50" })); }
  mk("chPrecio", { type: "line", data: { labels: L.map(fcorta), datasets: ds }, options: opts({ ftip: v => money(v, mn), right: 76, extra: { endLabels: { on: true } }, title: it => flarga(L[it[0].dataIndex]) }) });
  $("#legPrecio").innerHTML = `<span style="--c:${col}"><i></i>Cierre (${mn})</span>` + (medias ? `<span style="--c:${css("--ink")}"><i class="d"></i>Media de 20 sesiones</span><span style="--c:${css("--muted")}"><i class="t"></i>Media de 50</span>` : "") + (bandas ? `<span style="--c:${col}"><i class="f"></i>Bollinger (20, 2σ)</span>` : "");
  mk("chRsi", { type: "line", data: { labels: L.map(fcorta), datasets: [linea("RSI", sl(sr.rsi), col, { w: 1.8 }),
    linea("70", L.map(() => 70), css("--down"), { w: 1, borderDash: [4, 4], tip: false }), linea("30", L.map(() => 30), css("--up"), { w: 1, borderDash: [4, 4], tip: false })] },
    options: opts({ fy: v => fmt(v), ftip: v => v?.toFixed(2), min: 0, max: 100, step: 25, title: it => flarga(L[it[0].dataIndex]) }) });
  const h = sl(sr.hist);
  mk("chMacd", { type: "bar", data: { labels: L.map(fcorta), datasets: [
    { type: "bar", label: "Histograma", data: h, backgroundColor: h.map(v => alpha(v >= 0 ? hexOf("--up") : hexOf("--down"), .55)), borderWidth: 0, barPercentage: 1, categoryPercentage: 1 },
    linea("MACD", sl(sr.macd), col, { type: "line", w: 1.6 }), linea("Señal", sl(sr.macd_signal), css("--ink"), { type: "line", w: 1.3, borderDash: [4, 3] })] },
    options: opts({ fy: v => fmt(v, 1), ftip: v => fmt(v, 3), title: it => flarga(L[it[0].dataIndex]) }) });
}
async function cargarCambios() {
  try {
    const A = await cargarArchivo();
    $("#histCambios").innerHTML = A.cambios.length ? A.cambios.slice(0, 10).map(c => `<div class="cambio"><span class="f">${flarga(c.fecha)}</span><span class="t">${esc(c.ticker)}</span>
      <span class="flecha">${esc(c.de ? sigT(c.de) : "Sin dato previo")} ${ICON("chevron")} ${sig(c.a)}</span></div>`).join("") : '<p class="note">No hubo cambios de decisión en el periodo.</p>';
  } catch { $("#histCambios").innerHTML = '<p class="note">No se pudo cargar el historial de decisiones.</p>'; }
}
async function cargarArchivo() {
  if (!S.arch) { const clave = qsP(); const a = await api(`/api/archivo?${clave}`); if (clave !== qsP()) return a; S.arch = a; }
  return S.arch;
}

/* ---------------------------------------------------- alertas de cambio de decisión */
const VISTOS_INICIO = store.get("vistos", null);
function renderAlertas() {
  const cambios = S.data.acciones.filter(a => !a.error && a.cambio);
  const vistos = VISTOS_INICIO;
  const hoy = Object.fromEntries(S.data.acciones.filter(a => !a.error).map(a => [a.ticker, a.veredicto]));
  const desdeVisita = vistos ? S.data.acciones.filter(a => !a.error && vistos[a.ticker] && vistos[a.ticker] !== a.veredicto) : [];
  store.set("vistos", hoy);
  let html = "";
  if (cambios.length) html += `<div class="alerta">${ICON("wait")}<div><b>Cambió la decisión en la última sesión</b><p>${cambios.map(a => `<b>${tk(a.ticker)}</b>: de ${esc(sigT(a.veredicto_ant).toLowerCase())} a ${esc(a.decision.toLowerCase())}`).join("; ")}.</p></div></div>`;
  if (desdeVisita.length) html += `<div class="alerta">${ICON("wait")}<div><b>Desde tu última visita</b><p>${desdeVisita.map(a => `<b>${tk(a.ticker)}</b>: de ${sigT(vistos[a.ticker]).toLowerCase()} a ${sigT(a.veredicto).toLowerCase()}`).join("; ")}.</p></div></div>`;
  $("#alertas").innerHTML = html;
}

/* -------------------------------------------------------------------- entorno */
const ENTORNO_HTML = `
  <div class="head"><h1>Entorno global</h1><p class="sub" id="eSub"></p><p class="intro" style="margin-top:10px">Cómo se mueven el dólar, las tasas y las bolsas de EE. UU. y del mundo, y qué relación tienen con las acciones y la deuda que sigues aquí. Las cifras vienen de fuentes oficiales (Banco de México, Departamento del Tesoro de EE. UU., Reserva Federal de Nueva York, BLS y Cboe); los índices bursátiles son de referencia.</p></div>
  <section class="sec"><h2>Lectura del periodo</h2><div class="prose" id="eLectura"><p class="cargando">Consultando fuentes oficiales…</p></div></section>
  <section class="sec"><h2>Tipo de cambio: pesos por dólar (FIX de Banxico)</h2><div class="legend" id="legFx"></div><div class="chartbox md"><canvas id="chFx" role="img" aria-label="Tipo de cambio FIX"></canvas></div></section>
  <section class="sec"><h2>Bolsas del mundo, base 100 al inicio del periodo</h2><div class="legend" id="legBolsas"></div><div class="chartbox"><canvas id="chBolsas" role="img" aria-label="Bolsas del mundo"></canvas></div></section>
  <section class="sec"><h2>Tasas de interés: México y EE. UU.</h2><div class="legend" id="legTasas"></div><div class="chartbox md"><canvas id="chTasas" role="img" aria-label="Tasas de interés"></canvas></div></section>
  <section class="sec"><h2>Indicadores del periodo y fuentes</h2><div class="scrollx" id="eTabla"></div><p class="note" style="margin-top:8px">«Oficial» significa que la publica la propia institución. «Referencia» son datos de mercado de Yahoo Finance, que no es una fuente oficial. Las tasas cambian en puntos base (pb): 100 pb = 1 punto porcentual.</p></section>
  <section class="sec"><h2>Diferenciales de tasas</h2><div id="eDifs"></div></section>
  <section class="sec"><h2>Qué tan ligados están tus instrumentos a EE. UU. y al dólar</h2><div class="scrollx" id="eSens"></div><div id="eEfecto"></div></section>
  <section class="sec"><h2>Qué es cada cosa</h2><div id="eGuia"><p class="cargando">Cargando…</p></div></section>
  <section class="sec"><h2>Fuentes oficiales</h2><div id="eFuentes"></div></section>`;

function renderEntorno() {
  armar("entorno", ENTORNO_HTML);
  $("#eSub").textContent = `Periodo del ${flarga(S.periodo.desde)} al ${flarga(S.periodo.hasta)}`;
  renderGuia();
  if (!S.ctx) { if (S.ctxError) $("#eLectura").innerHTML = `<p class="err">No se pudo cargar el entorno global: ${esc(S.ctxError)}</p>`; cargarCtx(); return; }
  const c = S.ctx, d = Object.fromEntries(c.indicadores.map(x => [x.id, x]));
  $("#eLectura").innerHTML = c.lectura.map(p => `<p>${esc(p)}</p>`).join("");
  if (Object.keys(c.errores || {}).length) $("#eLectura").innerHTML += `<p class="note">Algunas fuentes no respondieron y se omitieron: ${Object.entries(c.errores).map(([k, v]) => esc(k)).join(", ")}.</p>`;
  // tipo de cambio
  if (d.fx) {
    mk("chFx", { type: "line", data: { labels: d.fx.serie.map(x => fcorta(x[0])), datasets: [linea("FIX", d.fx.serie.map(x => x[1]), hexOf("--line"), { w: 2.2, endLabel: `FIX ${fmt(d.fx.fin.valor)}` })] },
      options: opts({ ftip: v => "$" + fmt(v), right: 84, extra: { endLabels: { on: true } }, title: it => flarga(d.fx.serie[it[0].dataIndex][0]) }) });
    $("#legFx").innerHTML = `<span style="--c:${hexOf("--line")}"><i></i>Pesos por dólar. Si sube, el peso se deprecia</span>`;
  }
  // bolsas base 100
  const bol = [["sp500", "S&P 500"], ["nasdaq", "Nasdaq"], ["ipc", "IPC México"], ["stoxx", "Euro Stoxx 50"], ["nikkei", "Nikkei 225"]].filter(([k]) => d[k]);
  if (bol.length) {
    const al = alinear(bol.map(([k]) => ({ datos: d[k].serie })), true);
    mk("chBolsas", { type: "line", data: { labels: al.fechas.map(fcorta), datasets: bol.map(([k, n], i) => linea(n, al.valores[i], serie(i), { w: 2.1, endLabel: `${n} ${fmt(al.valores[i].at(-1))}` })) },
      options: opts({ ftip: v => fmt(v), right: 128, extra: { endLabels: { on: true }, refLine: { valor: 100 } }, title: it => flarga(al.fechas[it[0].dataIndex]) }) });
    $("#legBolsas").innerHTML = bol.map(([, n], i) => `<span style="--c:${serie(i)}"><i class="sq"></i>${esc(n)}</span>`).join("");
  }
  // tasas
  const tas = [["tasa_obj", "Banxico (objetivo)"], ["effr", "Fed (EFFR)"], ["ust10y", "Tesoro 10 años"], ["ust2y", "Tesoro 2 años"]].filter(([k]) => d[k]);
  if (tas.length) {
    const al = alinear(tas.map(([k]) => ({ datos: d[k].serie })), false);
    mk("chTasas", { type: "line", data: { labels: al.fechas.map(fcorta), datasets: tas.map(([k, n], i) => linea(n, al.valores[i], serie(i), { w: 2.1, endLabel: `${n} ${fmt(al.valores[i].at(-1))}%` })) },
      options: opts({ fy: v => fmt(v) + "%", ftip: v => fmt(v) + "%", right: 150, extra: { endLabels: { on: true } }, title: it => flarga(al.fechas[it[0].dataIndex]) }) });
    $("#legTasas").innerHTML = tas.map(([, n], i) => `<span style="--c:${serie(i)}"><i class="sq"></i>${esc(n)}</span>`).join("");
  }
  // tabla de indicadores agrupada
  let h = `<table class="tbl"><thead><tr><th>Indicador</th><th>Inicio</th><th>Fin</th><th>Cambio</th><th class="l">Fuente</th></tr></thead><tbody>`;
  let grupo = "";
  c.indicadores.forEach(x => {
    if (x.grupo !== grupo) { grupo = x.grupo; h += `<tr><td colspan="5" class="l" style="background:var(--brand-suave);font-weight:700;color:var(--brand-text)">${esc(grupo)}</td></tr>`; }
    const f = x.fuente, u = x.cambio_unidad === "pb" ? " pb" : "%";
    h += `<tr><td><b>${esc(x.nombre)}</b><small>${x.mensual ? "mensual · último dato " + fmes(x.fin.fecha) : "al " + flarga(x.fin.fecha)}</small></td><td>${fmt(x.ini.valor)}<small>${flarga(x.ini.fecha)}</small></td><td>${fmt(x.fin.valor)}</td>
      <td class="${cls(x.cambio)}"><b>${sg(x.cambio)}${fmt(Math.abs(x.cambio))}${u}</b></td><td class="l"><span class="ofi ${f.oficial ? "si" : "no"}">${f.oficial ? "Oficial" : "Referencia"}</span> <a class="fuente" href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.nombre.split(" · ")[0])}</a></td></tr>`;
  });
  $("#eTabla").innerHTML = h + "</tbody></table>";
  $("#eDifs").innerHTML = c.diferenciales.length ? c.diferenciales.map(x => `<div class="cambio" style="display:block"><b>${esc(x.nombre)}:</b> <span class="num ${cls(x.pb)}"><b>${sg(x.pb)}${fmt(Math.abs(x.pb))} pb</b></span> <span class="note">(${esc(x.detalle)})</span><p class="note" style="margin-top:2px">${esc(x.lectura)}</p></div>`).join("") : '<p class="note">No hay datos suficientes en el periodo.</p>';
  $("#eSens").innerHTML = c.sensibilidades.length ? `<table class="tbl"><thead><tr><th>Emisora</th><th>País</th><th>Sesiones</th><th>Corr. S&amp;P 500</th><th>Beta S&amp;P 500</th><th>Corr. dólar</th><th>Corr. IPC</th></tr></thead><tbody>` +
    c.sensibilidades.map(s => `<tr><td><b>${esc(s.nombre)}</b></td><td>${esc(s.pais)}</td><td>${s.n}</td><td>${fmt(s.corr_sp500)}</td><td>${fmt(s.beta_sp500)}</td><td>${fmt(s.corr_dolar)}</td><td>${s.corr_ipc == null ? "—" : fmt(s.corr_ipc)}</td></tr>`).join("") + "</tbody></table>" : "";
  $("#eEfecto").innerHTML = (c.efecto_cambiario.length ? `<h3 class="h3">Acciones de EE. UU. vistas desde México</h3><div class="scrollx"><table class="tbl"><thead><tr><th>Acción</th><th>Rend. en dólares</th><th>Variación del dólar</th><th>Rend. en pesos</th></tr></thead><tbody>` +
    c.efecto_cambiario.map(e => `<tr><td><b>${esc(e.nombre)}</b></td><td class="${cls(e.ret_usd)}">${pct(e.ret_usd)}</td><td class="${cls(e.ret_dolar)}">${pct(e.ret_dolar)}</td><td class="${cls(e.ret_pesos)}"><b>${pct(e.ret_pesos)}</b></td></tr>`).join("") + "</tbody></table></div>" : "") +
    `<p class="note" style="margin-top:10px">La correlación (de −1 a +1) mide si los rendimientos diarios se mueven juntos; la beta, cuánto se mueve la acción por cada 1 % del S&amp;P 500. La correlación con el dólar usa el tipo de cambio de cierre de Banxico: si es negativa, la acción tiende a subir cuando el peso se aprecia. Ninguna prueba que un mercado cause al otro.</p>`;
  $("#eFuentes").innerHTML = c.fuentes.map(f => `<p style="margin:6px 0"><span class="ofi ${f.oficial ? "si" : "no"}">${f.oficial ? "Oficial" : "Referencia"}</span> <a class="fuente" href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.nombre)}</a></p>`).join("") +
    `<p class="note" style="margin-top:8px">Para las empresas: reportes oficiales en SEC EDGAR (EE. UU.) y en la Bolsa Mexicana de Valores y la CNBV (México).</p>`;
}
async function renderGuia() {
  const el = $("#eGuia"); if (!el) return;
  try {
    const g = await cargarGuia();
    const ac = x => `<details class="acc"><summary>${ICON("chevron")}${esc(x.nombre)}<span class="sub">${esc(x.ticker ? tk(x.ticker) + " · " + x.mercado : x.codigo)}</span></summary><div class="cuerpo"><p>${esc(x.que_es)}</p><p><b>${x.que_la_mueve ? "Qué la mueve." : "Qué lo mueve."}</b> ${esc(x.que_la_mueve || x.que_lo_mueve)}</p>${x.fuente ? `<p class="note">Fuente oficial: <a class="fuente" href="${esc(x.fuente.url)}" target="_blank" rel="noopener">${esc(x.fuente.nombre)}</a></p>` : ""}</div></details>`;
    const ind = x => `<details class="acc"><summary>${ICON("chevron")}${esc(x.nombre)}</summary><div class="cuerpo"><p>${esc(x.que_es)}</p><p><b>Cómo se relaciona con tus instrumentos.</b> ${esc(x.como_afecta)}</p></div></details>`;
    el.innerHTML = `<h3 class="h3">Acciones</h3>${g.acciones.map(ac).join("")}<h3 class="h3" style="margin-top:22px">Deuda gubernamental y privada</h3>${g.deuda.map(ac).join("")}<h3 class="h3" style="margin-top:22px">Indicadores del entorno</h3>${g.indicadores.map(ind).join("")}`;
  } catch { el.innerHTML = '<p class="note">No se pudo cargar la guía.</p>'; }
}

/* ------------------------------------------------------------------------ deuda */
const DEUDA_HTML = `
  <div class="head"><h1>Deuda</h1><p class="sub" id="dSub"></p><p class="intro" style="margin-top:10px">Instrumentos del Gobierno Federal (CETES, Bonos M, Udibonos, Bondes F), del IPAB (BPAG28) y del mercado privado (papel comercial y certificados bursátiles). Cada cifra es la de la última subasta o colocación semanal que publica Banxico; el rendimiento se compara con el promedio de las últimas 12.</p></div>
  <div class="board"><table id="boardDeuda" aria-label="Instrumentos de deuda"></table><div class="board-foot" id="footDeuda"></div></div>
  <div class="detail" id="detalleDeuda" hidden>
    <div class="detail-head"><h2 id="deuNombre"></h2></div>
    <div class="cols"><div><div class="legend" id="legDeuda"></div><div class="chartbox md"><canvas id="chDeuda" role="img" aria-label="Rendimiento por semana o subasta"></canvas></div></div><aside class="verdict" id="deuLectura"></aside></div>
    <div class="split"><section class="sec"><h2>Qué es</h2><div id="deuQue"></div></section><section class="sec"><h2>Resultados semana a semana</h2><div class="scroll"><table class="tbl" id="tblDeuda"></table></div></section></div>
    <section class="sec" id="deuProy" hidden><h2>Proyección y sensibilidad a la tasa</h2><div class="prose" id="deuProyT"></div></section>
    <section class="sec" id="deuPriv" hidden><h2>Papel comercial y certificados bursátiles por mes</h2><div class="scrollx" id="deuPrivT"></div></section>
  </div>
  <p class="aviso">Si las tasas suben, el precio de los bonos ya emitidos baja. La decisión es un apoyo educativo y no constituye asesoría financiera.</p>`;
const valDeuda = x => x.valor == null ? "—" : x.tipo === "precio" ? "$" + fmt(x.valor, 5) : x.tipo === "monto" ? "$" + fmt(x.valor / 1000) + " mdp" : fmt(x.valor) + (x.unidad.startsWith("%") ? "%" : " pp");
function renderDeuda() {
  armar("deuda", DEUDA_HTML);
  const d = S.data, ok = d.deuda.find(x => x.fecha);
  $("#dSub").textContent = `Periodo del ${flarga(S.periodo.desde)} al ${flarga(S.periodo.hasta)}`;
  $("#boardDeuda").innerHTML = `<thead><tr><th>Instrumento</th><th>Última cifra</th><th class="c-chg">Cambio</th><th class="c-z">Z</th><th class="c-trend">Tendencia</th><th class="c-sig">Decisión</th></tr></thead><tbody class="${entra("deuda")}">` +
    d.deuda.map((x, i) => `<tr tabindex="0" data-d="${i}" aria-selected="${i === S.selD}" style="--i:${i}">
      <td><div><div class="tk">${esc(x.codigo)}</div><div class="nm">${esc(x.emisor)}</div><div class="m-only">${sig(x.senal)}</div></div></td>
      <td><span class="px num">${valDeuda(x)}</span></td>
      <td class="c-chg"><span class="chg num ${cls(x.var_pb ?? x.var)}">${x.var_pb != null ? sg(x.var_pb) + Math.abs(x.var_pb).toFixed(2) + " pb" : x.var != null ? sg(x.var) + Math.abs(x.var).toFixed(5) : "—"}</span></td>
      <td class="c-z"><span class="chg num flat">${x.z != null ? sg(x.z) + Math.abs(x.z).toFixed(2) : "—"}</span></td>
      <td class="c-trend"><span class="flat">${esc(x.tendencia)}</span></td>
      <td class="c-sig">${sig(x.senal)}</td></tr>`).join("") + "</tbody>";
  $("#footDeuda").innerHTML = `<span>Banco de México · cuadros CF107, CF115 y CF133 del SIE</span><span>${ok ? "Última cifra del " + flarga(ok.fecha) : ""}</span>`;
  $$("#boardDeuda tbody tr").forEach(tr => {
    const go = () => { S.selD = +tr.dataset.d; renderDeuda(); if (innerWidth < 980) $("#detalleDeuda").scrollIntoView({ behavior: "smooth" }); };
    tr.onclick = go; tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } };
  });
  const x = d.deuda[S.selD]; if (!x) return;
  $("#detalleDeuda").hidden = false;
  const tipo = x.tipo, col = hexOf("--line"), v = x.datos.map(r => tipo === "monto" ? r.valor / 1000 : r.valor);
  const ma = v.map((_, i) => i >= 3 ? v.slice(i - 3, i + 1).reduce((p, q) => p + q, 0) / 4 : null);
  const etq = tipo === "tasa" ? "Rendimiento" : tipo === "precio" ? "Precio" : "Colocado (millones de pesos)";
  const fy = n => tipo === "precio" ? n.toFixed(3) : fmt(n), ft = n => tipo === "tasa" ? fmt(n) + (x.unidad.startsWith("%") ? "%" : " pp") : tipo === "precio" ? "$" + n.toFixed(5) : "$" + fmt(n) + " mdp";
  $("#deuNombre").textContent = `${x.nombre} · ${x.emisor}`;
  $("#legDeuda").innerHTML = `<span style="--c:${col}"><i></i>${etq} cada semana (${esc(x.unidad)})</span><span style="--c:${css("--ink")}"><i class="d"></i>Promedio móvil de 4 semanas</span>`;
  mk("chDeuda", { type: tipo === "monto" ? "bar" : "line", data: { labels: x.datos.map(r => fcorta(r.fecha)), datasets: tipo === "monto"
      ? [{ type: "bar", label: etq, data: v, backgroundColor: alpha(hexOf("--line"), .75), borderWidth: 0 }]
      : [linea(etq, v, col, { w: 2.2, pr: 3, endLabel: valDeuda(x) }), linea("Promedio móvil", ma, css("--ink"), { w: 1.5, borderDash: [6, 4] })] },
    options: opts({ fy, ftip: ft, right: tipo === "monto" ? 8 : 78, extra: tipo === "monto" ? {} : { endLabels: { on: true } }, title: it => flarga(x.datos[it[0].dataIndex].fecha) }) });
  $("#deuLectura").innerHTML = `<div class="word ${sigK(x.senal)}">${esc(x.decision)}</div>
    <p class="meta">${esc(x.texto)}</p>
    <p class="note" style="margin-top:14px">${tipo === "monto" ? "Este instrumento se sigue por volumen colocado, no por rendimiento." : `Z: desviaciones estándar frente al promedio de las últimas 12 subastas. Pendiente: regresión de las últimas 8 (${x.pendiente != null ? sg(x.pendiente) + Math.abs(x.pendiente).toFixed(2) + (tipo === "tasa" ? " pb" : " $") + " por subasta" : "sin datos"}).`}</p>
    <ul class="prose" style="margin-top:10px;padding-left:18px">${(x.por_que || []).map(p => `<li>${esc(p)}</li>`).join("")}</ul>`;
  const ex = x.extras || [], tasa = tipo === "tasa";
  $("#tblDeuda").innerHTML = `<thead><tr><th>Fecha</th><th>${tasa ? "Tasa" : tipo === "precio" ? "Precio" : "Colocado (miles de pesos)"}</th>${tasa ? "<th>Cambio (pb)</th>" : ""}${ex.map(e => `<th>${esc(e)}</th>`).join("")}</tr></thead><tbody>` +
    [...x.datos].reverse().map(r => `<tr><td>${flarga(r.fecha)}</td><td><b>${tipo === "precio" ? fmt(r.valor, 5) : fmt(r.valor)}</b></td>${tasa ? `<td class="${cls(r.var_pb)}">${r.var_pb == null ? "—" : sg(r.var_pb) + Math.abs(r.var_pb).toFixed(2)}</td>` : ""}${ex.map(e => `<td>${r.extra?.[e] == null ? "—" : fmt(r.extra[e])}</td>`).join("")}</tr>`).join("") + "</tbody>";
  cargarGuia().then(g => { const q = g.deuda.find(z => z.nombre === x.nombre); if (q && S.data.deuda[S.selD]?.nombre === x.nombre)
    $("#deuQue").innerHTML = `<div class="prose"><p>${esc(q.que_es)}</p><p><b>Qué lo mueve.</b> ${esc(q.que_lo_mueve)}</p></div>` + (q.fuente ? `<p class="note" style="margin-top:8px">Fuente oficial: <a class="fuente" href="${esc(q.fuente.url)}" target="_blank" rel="noopener">${esc(q.fuente.nombre)}</a></p>` : ""); }).catch(() => {});
  const pr = x.proyeccion, se = x.sensibilidad;
  $("#deuProy").hidden = !pr && !se;
  $("#deuProyT").innerHTML = (pr ? `<p>Con una recta ajustada a las últimas ${pr.n} cifras (error típico ${fmt(pr.error_tipico)} puntos), el rendimiento de la próxima subasta podría estar entre <b>${fmt(pr.proyecciones[0].bajo)} %</b> y <b>${fmt(pr.proyecciones[0].alto)} %</b> (centro ${fmt(pr.proyecciones[0].centro)} %), y dentro de 4 subastas entre <b>${fmt(pr.proyecciones[1].bajo)} %</b> y <b>${fmt(pr.proyecciones[1].alto)} %</b>, con 95 % de probabilidad bajo el supuesto de que la tendencia reciente continúe. No es un pronóstico: las decisiones de Banxico y la inflación pueden cambiarla.</p>` : "") + (se ? `<p>${esc(se.texto)}</p>` : "");
  const priv = x.nombre === "PAPEL COMERCIAL" || x.nombre === "CERTIFICADOS BURSÁTILES";
  $("#deuPriv").hidden = !priv;
  if (priv) {
    if (!S.ctx) { $("#deuPrivT").innerHTML = '<p class="cargando">Consultando a Banxico…</p>'; }
    else $("#deuPrivT").innerHTML = S.ctx.privados.length ? `<table class="tbl"><thead><tr><th>Mes</th><th>Tasa CB corto plazo</th><th>Tasa CB mediano plazo</th><th>Colocado corto plazo (mdp)</th><th>Colocado papel comercial (mdp)</th><th>Colocado mediano y largo (mdp)</th></tr></thead><tbody>` +
      S.ctx.privados.map(m => `<tr><td>${fmes(m.mes)}</td><td>${fmt(m.tasa_cb_cp)}%</td><td>${fmt(m.tasa_cb_mp)}%</td><td>${fmt((m.col_cp || 0) / 1e3)}</td><td>${fmt((m.col_pc || 0) / 1e3)}</td><td>${fmt((m.col_mlp || 0) / 1e3)}</td></tr>`).join("") +
      `</tbody></table><p class="note" style="margin-top:8px">Banxico, cuadros CF302 y CF304. mdp = millones de pesos. Una tasa de 0.00 significa que no hubo colocaciones de ese instrumento en el mes.</p>` : '<p class="note">Sin datos mensuales en el periodo.</p>';
  }
}

/* --------------------------------------------------------------------- comparar */
const COMPARAR_HTML = `
  <div class="head"><h1>Comparar</h1><p class="sub" id="cSub"></p></div>
  <div class="sub-nav"><div class="seg" id="cModo" role="group" aria-label="Qué mostrar"><button data-m="comparar">Comparación de cierres</button><button data-m="simular">Simulación</button></div>
    <div class="seg" id="cMoneda" role="group" aria-label="Moneda de las acciones de EE. UU."><button data-c="mxn">En pesos</button><button data-c="original">Moneda original</button></div>
    <span class="note" id="cNota"></span></div>
  <div id="cComparar">
    <div class="chips" id="chips" role="group" aria-label="Emisoras a comparar (de 2 a 5)"></div>
    <div class="legend" id="legComparar"></div>
    <div class="chartbox"><canvas id="chComparar" role="img" aria-label="Comparación de rendimiento acumulado"></canvas></div>
    <div class="split"><section class="sec"><h2>Cierres en dos fechas</h2>
        <div class="consulta"><label>De <input type="date" id="fechaA"></label><label>A <input type="date" id="fechaB"></label>
          <div class="seg" id="atajos"><button data-a="ini">Periodo</button><button data-a="sem">1 semana</button><button data-a="mes">1 mes</button></div></div>
        <div class="scrollx"><table class="tbl" id="tblConsulta"></table></div><p class="note" style="margin-top:8px">Si la fecha no fue día hábil se usa el cierre anterior. Los cierres se muestran en la moneda elegida arriba.</p></section>
      <section class="sec"><h2>Ranking del periodo</h2><div class="scrollx"><table class="tbl" id="tblRanking"></table></div></section></div>
    <section class="sec"><h2>Portafolio y diversificación</h2><div class="scrollx" id="tblPort"></div><p class="note" id="portNota" style="margin-top:8px"></p></section>
    <div class="split"><section class="sec"><h2>Correlación de rendimientos diarios</h2><div class="heat" id="heat"></div><p class="note" style="margin-top:10px">+1.00 se mueven igual, 0.00 sin relación, −1.00 en sentido contrario. Valores bajos diversifican.</p></section>
      <section class="sec"><h2>Cierres diarios</h2><details class="acc"><summary>${ICON("chevron")}Ver tabla completa</summary><div class="scroll"><table class="tbl" id="tblCierres"></table></div></details></section></div>
  </div>
  <div id="cSim" hidden>
    <p class="intro" id="simTexto">Qué habría pasado si hubieras seguido las decisiones contra comprar y mantener.</p>
    <div class="legend" id="legSim" style="margin-top:12px"></div><div class="chartbox"><canvas id="chSim" role="img" aria-label="Valor del portafolio simulado"></canvas></div>
    <div class="split"><section class="sec"><h2>Resultado del periodo</h2><div class="scrollx"><table class="tbl" id="tblSim"></table></div></section><section class="sec"><h2>Por emisora</h2><div class="scrollx"><table class="tbl" id="tblSimEm"></table></div></section></div>
    <p class="aviso" id="simAviso"></p></div>`;
async function renderComparar() {
  armar("comparar", COMPARAR_HTML);
  $("#cSub").textContent = `Periodo del ${flarga(S.periodo.desde)} al ${flarga(S.periodo.hasta)}`;
  $$("#cModo button").forEach(b => { b.setAttribute("aria-pressed", b.dataset.m === S.modoC); b.onclick = () => { S.modoC = b.dataset.m; renderComparar(); }; });
  $$("#cMoneda button").forEach(b => { b.setAttribute("aria-pressed", b.dataset.c === S.moneda); b.onclick = () => { S.moneda = b.dataset.c; S.cmp = S.sim = null; renderComparar(); }; });
  $("#cNota").textContent = S.moneda === "mxn" ? "Las acciones de EE. UU. se convierten a pesos con el tipo de cambio de cierre de Banxico." : "Cada acción en su moneda: el efecto del dólar no se incluye.";
  $("#cComparar").hidden = S.modoC !== "comparar"; $("#cSim").hidden = S.modoC !== "simular";
  try { if (S.modoC === "comparar") { await cargarComparar(); renderChips(); drawComparar(); } else { await cargarSim(); renderChips(true); drawSim(); } }
  catch (e) { showErr(e.message); }
}
function renderChips(oculto) {
  const el = $("#chips"); if (!el) return;
  if (oculto) return;
  const full = S.selCmp.size >= 5;
  el.innerHTML = S.data.acciones.filter(a => !a.error).map(a => `<button class="chip" data-t="${a.ticker}" aria-pressed="${S.selCmp.has(a.ticker)}" ${full && !S.selCmp.has(a.ticker) ? "disabled" : ""} style="--c:${serieDe(a.ticker)}"><i></i>${tk(a.ticker)}</button>`).join("");
  $$("#chips .chip").forEach(b => b.onclick = () => { const t = b.dataset.t;
    if (S.selCmp.has(t)) { if (S.selCmp.size <= 2) return; S.selCmp.delete(t); } else if (S.selCmp.size < 5) S.selCmp.add(t);
    S.cmp = null; renderComparar(); });
}
const serieDe = t => { const i = [...S.selCmp].indexOf(t); return i < 0 ? "var(--rule-strong)" : serie(i); };
async function cargarComparar() {
  if (S.cmp) return;
  const tks = [...S.selCmp], clave = qsP();
  S.cmp = await api(`/api/comparar?${clave}&tickers=${tks.join(",")}&moneda=${S.moneda}`);
}
function drawComparar() {
  const c = S.cmp, d = S.data; if (!c || !c.fechas.length) return;
  const nom = t => d.acciones.find(a => a.ticker === t)?.nombre || t, tks = Object.keys(c.base100), L = c.fechas;
  mk("chComparar", { type: "line", data: { labels: L.map(fcorta), datasets: tks.map((t, i) => linea(tk(t), c.base100[t], serie(i), { w: 2.2, endLabel: `${tk(t)} ${fmt(c.base100[t].at(-1))}` })) },
    options: opts({ fy: v => fmt(v), ftip: v => fmt(v), right: 128, extra: { endLabels: { on: true }, refLine: { valor: 100 } }, title: it => flarga(L[it[0].dataIndex]) }) });
  $("#legComparar").innerHTML = tks.map((t, i) => `<span style="--c:${serie(i)}"><i class="sq"></i>${esc(nom(t))}</span>`).join("") + `<span class="note">Base 100.00 al inicio del periodo.</span>`;
  const fa = $("#fechaA"), fb = $("#fechaB");
  fa.min = fb.min = L[0]; fa.max = fb.max = L.at(-1);
  if (!fa.value || fa.value < L[0] || fa.value > L.at(-1)) fa.value = L[0];
  if (!fb.value || fb.value < L[0] || fb.value > L.at(-1)) fb.value = L.at(-1);
  const pos = f => { let k = -1; L.forEach((x, i) => { if (x <= f) k = i; }); return k; };
  const mon = t => (c.moneda === "pesos" || d.acciones.find(a => a.ticker === t)?.moneda !== "USD") ? "$" : "US$";
  const tabla = () => {
    const ia = pos(fa.value), ib = pos(fb.value);
    if (ia < 0 || ib < 0) { $("#tblConsulta").innerHTML = "<tbody><tr><td>Elige fechas dentro del periodo.</td></tr></tbody>"; return; }
    const filas = tks.map(t => { const a = c.cierres[t][ia], b = c.cierres[t][ib]; return { t, a, b, dv: b - a, dp: (b / a - 1) * 100 }; }), mejor = Math.max(...filas.map(f => f.dp));
    $("#tblConsulta").innerHTML = `<thead><tr><th>Emisora</th><th>${fcorta(L[ia])}</th><th>${fcorta(L[ib])}</th><th>Cambio</th></tr></thead><tbody>` +
      filas.map(f => `<tr><td><b>${tk(f.t)}</b>${f.dp === mejor ? ' <span class="note">mejor</span>' : ""}</td><td>${mon(f.t)}${fmt(f.a)}</td><td>${mon(f.t)}${fmt(f.b)}</td><td class="${cls(f.dp)}"><b>${pct(f.dp)}</b><small>${sg(f.dv)}${fmt(Math.abs(f.dv))}</small></td></tr>`).join("") + "</tbody>";
  };
  fa.onchange = fb.onchange = tabla; tabla();
  $$("#atajos button").forEach(b => b.onclick = () => { const u = L.length - 1; fb.value = L[u]; fa.value = b.dataset.a === "ini" ? L[0] : L[Math.max(0, u - (b.dataset.a === "sem" ? 5 : 21))]; tabla(); });
  $("#tblRanking").innerHTML = `<thead><tr><th>Emisora</th><th>Rend.</th><th>Vol.</th><th>R/R</th><th>Caída</th><th>Días al alza</th></tr></thead><tbody>` +
    [...c.ranking].sort((a, b) => b.ret - a.ret).map(r => `<tr><td><b>${tk(r.ticker)}</b></td><td class="${cls(r.ret)}"><b>${pct(r.ret)}</b></td><td>${fmt(r.vol_anual)}%</td><td>${r.ratio == null ? "—" : fmt(r.ratio)}</td><td class="down">${pct(r.max_drawdown)}</td><td>${fmt(r.dias_alza)}%</td></tr>`).join("") + "</tbody>";
  const po = c.portafolio;
  if (po) {
    $("#tblPort").innerHTML = `<table class="tbl"><thead><tr><th>Emisora</th><th>Peso equiponderado</th><th>Peso de mínima varianza</th></tr></thead><tbody>` +
      po.tickers.map((t, i) => `<tr><td><b>${tk(t)}</b></td><td>${fmt(po.equiponderado.pesos[i])} %</td><td>${fmt(po.min_varianza.pesos[i])} %</td></tr>`).join("") +
      `<tr><td><b>Volatilidad anual</b></td><td>${fmt(po.equiponderado.vol_anual)} %</td><td>${fmt(po.min_varianza.vol_anual)} %</td></tr><tr><td><b>Rendimiento anualizado del periodo</b></td><td>${pct(po.equiponderado.ret_anual)}</td><td>${pct(po.min_varianza.ret_anual)}</td></tr></tbody></table>`;
    $("#portNota").textContent = `La volatilidad promedio de las emisoras por separado es ${fmt(po.vol_individual_promedio)} % y la del portafolio equiponderado ${fmt(po.equiponderado.vol_anual)} %: la razón de diversificación es ${fmt(po.razon_diversificacion)} (más de 1 significa que combinarlas reduce el riesgo). El portafolio de mínima varianza reparte el dinero para tener la menor volatilidad posible sin ventas en corto; usa solo datos pasados y sus pesos cambian con el periodo, así que no garantiza el mismo resultado hacia adelante.`;
  } else $("#tblPort").innerHTML = "<p class='note'>Selecciona al menos dos emisoras.</p>";
  const m = c.corr.matriz, n = c.corr.tickers.length, g = $("#heat");
  g.style.gridTemplateColumns = `auto repeat(${n},minmax(0,1fr))`;
  g.innerHTML = `<div class="h"></div>` + c.corr.tickers.map(t => `<div class="h">${tk(t)}</div>`).join("") +
    m.map((row, i) => `<div class="h" style="text-align:right">${tk(c.corr.tickers[i])}</div>` + row.map(v => { const w = Math.round(Math.abs(v) * 80), base = v >= 0 ? "--brand" : "--down";
      return `<div style="background:color-mix(in srgb,var(${base}) ${w}%,var(--surface));color:${w > 50 ? "#fff" : "var(--ink)"}">${fmt(v)}</div>`; }).join("")).join("");
  $("#tblCierres").innerHTML = `<thead><tr><th>Fecha</th>${tks.map(t => `<th>${tk(t)}</th>`).join("")}</tr></thead><tbody>` +
    L.map((f, i) => `<tr><td>${flarga(f)}</td>` + tks.map(t => { const v = c.cierres[t][i], p = i ? (v / c.cierres[t][i - 1] - 1) * 100 : null;
      return `<td>${fmt(v)}${p == null ? "" : `<small class="${cls(p)}">${pct(p)}</small>`}</td>`; }).join("") + "</tr>").reverse().join("") + "</tbody>";
}
async function cargarSim() {
  if (S.sim) return;
  $("#simTexto").textContent = "Calculando la simulación…";
  S.sim = await api(`/api/simulacion?${qsP()}&moneda=${S.moneda}`);
}
function drawSim() {
  const s = S.sim, m = s.metricas;
  if (!s.fechas.length) { $("#simTexto").textContent = s.error || "No hay datos suficientes."; return; }
  const peso = n => "$" + fmt(n), ink = hexOf("--line"), acc = css("--s2");
  $("#simTexto").textContent = `Con ${peso(s.capital)} repartidos en partes iguales entre las ${s.por_emisora.length} emisoras${s.moneda === "pesos" ? " (las acciones de EE. UU. medidas en pesos)" : " (cada una en su moneda)"}, desde ${fhumana(s.fechas[0])}: seguir las decisiones terminó en ${pct(m.ret_estrategia)} y comprar y mantener en ${pct(m.ret_comprar_mantener)}.`;
  $("#legSim").innerHTML = `<span style="--c:${ink}"><i></i>Siguiendo las decisiones</span><span style="--c:${acc}"><i class="d"></i>Comprar y mantener</span>`;
  mk("chSim", { type: "line", data: { labels: s.fechas.map(fcorta), datasets: [linea("Decisiones", s.estrategia, ink, { w: 2.4 }), linea("Comprar y mantener", s.comprar_mantener, acc, { w: 2, borderDash: [6, 4] })] },
    options: opts({ fy: v => fmt(v), ftip: v => peso(v), right: 8, title: it => flarga(s.fechas[it[0].dataIndex]) }) });
  $("#tblSim").innerHTML = `<thead><tr><th>Medida</th><th>Decisiones</th><th>Comprar y mantener</th></tr></thead><tbody>
    <tr><td>Rendimiento del periodo</td><td class="${cls(m.ret_estrategia)}"><b>${pct(m.ret_estrategia)}</b></td><td class="${cls(m.ret_comprar_mantener)}"><b>${pct(m.ret_comprar_mantener)}</b></td></tr>
    <tr><td>Valor final</td><td>${peso(s.estrategia.at(-1))}</td><td>${peso(s.comprar_mantener.at(-1))}</td></tr>
    <tr><td>Caída máxima</td><td class="down">${pct(m.caida_estrategia)}</td><td class="down">${pct(m.caida_comprar_mantener)}</td></tr>
    <tr><td>Operaciones</td><td>${m.operaciones}</td><td>1 por emisora</td></tr></tbody>`;
  $("#tblSimEm").innerHTML = `<thead><tr><th>Emisora</th><th>Decisiones</th><th>Comprar y mantener</th><th>Operaciones</th><th>Tiempo invertido</th></tr></thead><tbody>` +
    s.por_emisora.map(p => `<tr><td><b>${tk(p.ticker)}</b></td><td class="${cls(p.ret_estrategia)}">${pct(p.ret_estrategia)}</td><td class="${cls(p.ret_comprar_mantener)}">${pct(p.ret_comprar_mantener)}</td><td>${p.operaciones}</td><td>${fmt(p.tiempo_en_mercado)}%</td></tr>`).join("") + "</tbody>";
  $("#simAviso").textContent = `Reglas: se compra cuando el puntaje llega a +20 o más y se sale a efectivo cuando baja a −20 o menos; la decisión de un día se ejecuta al cierre del día siguiente y cada operación paga ${fmt(s.costo_pct)}% de comisión. Es una prueba dentro de la misma muestra, sin impuestos ni deslizamiento, con fines educativos; no constituye asesoría financiera y el resultado pasado no garantiza resultados futuros.`;
}

/* ------------------------------------------------------------------------ informe */
const INFORME_HTML = `
  <div class="head"><h1>Informe</h1><p class="sub" id="iSub"></p><p class="intro" style="margin-top:10px">Descarga el informe del periodo que elegiste arriba o el análisis de un día. Todo lleva el formato institucional del IPN e incluye qué es cada instrumento, el entorno global con fuentes oficiales, la decisión de comprar, mantener o vender y por qué.</p></div>
  <section class="sec"><h2>Cierres y decisiones por emisora</h2><div class="scrollx" id="iVivo"></div><p class="note" id="iVivoNota" style="margin-top:8px"></p></section>
  <section class="sec"><h2>Informe del periodo</h2><div class="prose" id="iResumen"></div><div class="dl-grupo" id="iDl"></div></section>
  <section class="sec"><h2>Análisis de un día</h2><div class="daybar"><button class="icon-btn" id="diaPrev" aria-label="Día anterior" style="color:var(--brand-text)"><svg class="ic" style="transform:rotate(180deg)" aria-hidden="true"><use href="#i-chevron"/></svg></button><input type="date" id="diaSel" aria-label="Elegir día"><button class="icon-btn" id="diaNext" aria-label="Día siguiente" style="color:var(--brand-text)"><svg class="ic" aria-hidden="true"><use href="#i-chevron"/></svg></button><span class="dl-grupo" id="diaDl" style="margin:0 0 0 8px"></span></div></section>
  <section class="sec"><h2>¿Acertaron las decisiones?</h2><div id="aciertos"><p class="cargando">Calculando…</p></div></section>
  <section class="sec"><h2>Mapa de decisiones por día</h2><div class="legend" id="legTl"></div><div class="tl" id="timeline"></div></section>
  <section class="sec"><h2 id="diaTitulo">Detalle del día</h2><div id="diaDetalle"><p class="note">Elige un día en el mapa o en el calendario.</p></div></section>
  <section class="sec"><h2>Ver sin internet</h2><p class="intro">Todo lo que consultas se guarda en este dispositivo y puedes verlo sin conexión. Este botón guarda de una vez todas las secciones del periodo elegido y los informes en PDF y Excel.</p>
    <div class="dl-grupo"><button class="btn solid" id="guardarOffline">${ICON("download")}Guardar para ver sin internet</button><span class="note" id="guardarEstado"></span></div></section>
  <section class="sec"><h2>Archivo guardado</h2><p class="intro">El Excel trae una hoja por emisora e instrumento con todas las sesiones desde el 1 de marzo de 2026 y se genera al momento. Los CSV son tablas planas para otros programas.</p><div class="dl-grupo" id="descargas"></div></section>`;
async function renderInforme() {
  armar("informe", INFORME_HTML);
  const p = S.periodo;
  $("#iSub").textContent = `Periodo del ${flarga(p.desde)} al ${flarga(p.hasta)}`;
  const ctx = S.ctx, an = S.data;
  $("#iResumen").innerHTML = `<p>${esc(an.mercado.texto_periodo || an.mercado.texto)}</p>` + (ctx ? `<p>${esc(ctx.lectura[0] || "")}</p>` : "");
  pintarVivo();
  $("#guardarOffline").onclick = guardarTodo;
  $("#iDl").innerHTML = dlBtn(`/api/informe?${qsP()}&formato=pdf`, "Informe en PDF", true) + dlBtn(`/api/informe?${qsP()}&formato=xlsx`, "Informe en Excel") +
    `<p class="note" style="flex-basis:100%">Se genera al momento con los datos más recientes; puede tardar unos segundos.</p>`;
  ligarDescargas($("#iDl"));
  $("#descargas").innerHTML = dlBtn(`/api/informe?desde=${INICIO}&hasta=${hoyMX()}&formato=xlsx`, "Excel completo desde el 1 de marzo", true) +
    [["analisis_acciones.csv", "CSV de acciones"], ["analisis_deuda.csv", "CSV de deuda"]].map(([f, t]) => `<a class="btn" href="/static/data/${f}" download>${ICON("download")}${t}</a>`).join("");
  ligarDescargas($("#descargas"));
  try {
    const A = await cargarArchivo();
    if (!S.fechaDia || S.fechaDia < p.desde || S.fechaDia > p.hasta) S.fechaDia = A.dias.at(-1)?.fecha;
    pintarArchivo(A);
    cargarDia(false);
  } catch (e) { $("#aciertos").innerHTML = `<p class="note">No se pudo calcular: ${esc(e.message)}</p>`; }
}
function pintarVivo() {
  const el = $("#iVivo"); if (!el || !S.data) return;
  const acc = S.data.acciones.filter(a => !a.error);
  let h = `<table class="tbl"><thead><tr><th>Emisora</th><th>Moneda</th><th>Cierre inicial</th><th>Precio actual o último cierre</th><th>Cambio del día</th><th>Periodo</th><th>Decisión</th><th>Puntaje</th></tr></thead><tbody>`, g = "";
  acc.forEach(a => {
    const mx = a.pais === "México", t = mx ? "México · BMV" : "EE. UU. · Nasdaq y NYSE";
    if (t !== g) { g = t; h += `<tr><td colspan="8" class="l" style="background:var(--brand-suave);font-weight:700;color:var(--brand-text)">${t}</td></tr>`; }
    const [v, p] = cambioVivo(a);
    h += `<tr><td><b>${esc(a.nombre)}</b></td><td>${a.moneda}</td><td>${money(a.serie.cierre[0], a.moneda)}</td><td><b>${money(precioVivo(a), a.moneda)}</b></td><td class="${cls(v)}">${pct(p)}</td><td class="${cls(a.ret_periodo)}">${pct(a.ret_periodo)}</td><td>${sig(a.veredicto)}</td><td>${sg(a.score)}${Math.abs(a.score)}</td></tr>`;
  });
  el.innerHTML = h + "</tbody></table>";
  $("#iVivoNota").textContent = vivo() ? `Los precios se actualizan solos mientras la bolsa está abierta. Al descargar, el informe se genera de nuevo con los datos del momento (${new Date().toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}).` : "Consulta histórica: cifras al cierre del último día del periodo.";
}
const VCLS = { "COMPRA FUERTE": "v-buy2", COMPRAR: "v-buy", MANTENER: "", VENDER: "v-sell", "VENTA FUERTE": "v-sell2" };
function pintarArchivo(A) {
  $("#aciertos").innerHTML = `<div class="scrollx"><table class="tbl"><thead><tr><th>Decisión</th><th>Casos evaluados</th><th>Aciertos a 5 sesiones</th><th>% de aciertos</th><th>Rend. medio a 5 ses.</th></tr></thead><tbody>` +
    A.aciertos.map(a => `<tr><td><b>${a.decision}</b></td><td>${a.casos}</td><td>${a.aciertos}</td><td>${a.pct == null ? "—" : fmt(a.pct) + "%"}</td><td class="${cls(a.ret5_medio)}">${a.ret5_medio == null ? "—" : pct(a.ret5_medio)}</td></tr>`).join("") +
    `</tbody></table></div><p class="note" style="margin-top:10px">Comprar acierta si el precio subió a 5 sesiones; vender, si bajó; mantener, si se movió 2.00 % o menos. Un porcentaje cercano a 50.00 % significa que la decisión no superó al azar en este periodo. Las decisiones de los últimos 5 días aún no se pueden evaluar.</p>`;
  $("#legTl").innerHTML = [["v-buy2", "Compra fuerte"], ["v-buy", "Comprar"], ["", "Mantener"], ["v-sell", "Vender"], ["v-sell2", "Venta fuerte"]]
    .map(([c, t]) => `<span><i class="sq ${c}" style="${c ? "" : "background:var(--rule-2)"}"></i>${t}</span>`).join("");
  const tks = [...new Set(A.dias.flatMap(d => d.e.map(e => e.t)))];
  $("#timeline").innerHTML = tks.map(t => `<div class="tl-row"><b>${t}</b><div class="tl-cells">` + A.dias.map(d => { const e = d.e.find(x => x.t === t);
    return e ? `<button class="${VCLS[e.v]}" data-f="${d.fecha}" title="${flarga(d.fecha)}: ${sigT(e.v).toLowerCase()} (${e.s})" aria-label="${t} ${flarga(d.fecha)} ${sigT(e.v).toLowerCase()}" aria-current="${d.fecha === S.fechaDia}"></button>` : `<button disabled></button>`; }).join("") + "</div></div>").join("");
  $("#timeline").scrollLeft = 1e6;
  $$("#timeline button[data-f]").forEach(b => b.onclick = () => { S.fechaDia = b.dataset.f; pintarArchivo(A); cargarDia(true); });
  const sel = $("#diaSel"), fechas = A.dias.map(d => d.fecha);
  sel.min = fechas[0]; sel.max = fechas.at(-1); sel.value = S.fechaDia || "";
  sel.onchange = () => { const f = [...fechas].reverse().find(x => x <= sel.value); S.fechaDia = f || fechas[0]; pintarArchivo(A); cargarDia(true); };
  const ix = fechas.indexOf(S.fechaDia);
  $("#diaPrev").onclick = () => { if (ix > 0) { S.fechaDia = fechas[ix - 1]; pintarArchivo(A); cargarDia(true); } };
  $("#diaNext").onclick = () => { if (ix < fechas.length - 1) { S.fechaDia = fechas[ix + 1]; pintarArchivo(A); cargarDia(true); } };
  $("#diaDl").innerHTML = S.fechaDia ? dlBtn(`/api/dia?fecha=${S.fechaDia}&formato=pdf`, `PDF del ${flarga(S.fechaDia)}`) + dlBtn(`/api/dia?fecha=${S.fechaDia}&formato=xlsx`, "Excel del día") : "";
  ligarDescargas($("#diaDl"));
  $("#diaTitulo").textContent = S.fechaDia ? fhumana(S.fechaDia).replace(/^./, c => c.toUpperCase()) : "Detalle del día";
}
async function cargarDia(forzar) {
  const f = S.fechaDia; if (!f) return;
  if (S.dia?.fecha === f && !forzar) return pintarDia(S.dia);
  $("#diaDetalle").innerHTML = '<p class="cargando">Preparando el análisis del día (consulta fuentes oficiales)…</p>';
  try { const r = await api(`/api/dia?fecha=${f}`); if (f !== S.fechaDia) return; S.dia = r; pintarDia(r); }
  catch (e) { $("#diaDetalle").innerHTML = `<p class="note">No se pudo cargar el día: ${esc(e.message)}</p>`; }
}
function pintarDia(r) {
  const ent = (r.entorno?.indicadores || []);
  $("#diaDetalle").innerHTML = `<div class="prose"><p>${esc(r.mercado.texto)}</p></div>` +
    (ent.length ? `<h3 class="h3">Entorno del día</h3><div class="scrollx"><table class="tbl"><thead><tr><th>Indicador</th><th>Valor</th><th>Cambio contra la sesión previa</th><th>Fuente</th></tr></thead><tbody>${ent.map(x => `<tr><td><b>${esc(x.nombre)}</b></td><td>${fmt(x.valor)}</td><td class="${cls(x.cambio)}">${sg(x.cambio)}${fmt(Math.abs(x.cambio))}${x.cambio_unidad === "pb" ? " pb" : "%"}</td><td><span class="ofi ${x.oficial ? "si" : "no"}">${x.oficial ? "Oficial" : "Referencia"}</span></td></tr>`).join("")}</tbody></table></div>` : "") +
    `<h3 class="h3">Decisiones</h3><div class="scrollx"><table class="tbl"><thead><tr><th>Emisora</th><th>Cierre</th><th>Var.</th><th>Puntaje</th><th>Decisión</th><th>5 ses.</th><th>¿Acertó?</th></tr></thead><tbody>` +
    r.emisoras.map(e => `<tr><td><b>${esc(e.ticker)}</b></td><td>${money(e.cierre, e.moneda)}</td><td class="${cls(e.var_pct)}">${pct(e.var_pct)}</td><td>${sg(e.score)}${Math.abs(e.score)}</td><td>${sig(e.veredicto)}</td><td class="${cls(e.ret_5)}">${e.ret_5 == null ? "—" : pct(e.ret_5)}</td><td class="${e.acierto ? "up" : e.acierto === false ? "down" : ""}">${e.acierto == null ? "por evaluar" : e.acierto ? "Sí" : "No"}</td></tr>`).join("") + `</tbody></table></div>` +
    r.emisoras.map(e => `<div class="day-item"><b>${esc(e.nombre)}</b> ${sig(e.veredicto)}<div class="prose" style="margin-top:6px"><ul>${e.por_que.map(p => `<li>${esc(p)}</li>`).join("")}</ul><p><b>Qué hacer:</b> ${esc(e.accion)}</p></div></div>`).join("") +
    r.deuda.map(x => `<div class="day-item"><b>${esc(x.nombre)}</b> ${sig(x.senal)}<div class="prose" style="margin-top:6px"><ul>${x.por_que.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div></div>`).join("");
}

/* ---------------------------------------------------------- actualización automática */
async function pollQuotes() {
  if (!S.data || !vivo()) return;
  const q = await api(`/api/cotizaciones?tickers=${S.data.acciones.map(a => a.ticker).join(",")}`);
  S.quotes = Object.fromEntries(q.map(x => [x.ticker, x])); S.tQuote = Date.now();
  if (S.vista === "informe") pintarVivo();
  if (S.vista !== "mercado") return;
  $$("#board tbody tr[data-t]").forEach(tr => {
    const a = S.data.acciones.find(x => x.ticker === tr.dataset.t); if (!a || a.error) return;
    const nw = precioVivo(a), old = S.shown[a.ticker], [v, p] = cambioVivo(a);
    tr.querySelector("[data-px]").textContent = fmt(nw);
    if (old != null && old !== nw) flip(tr.querySelector("[data-px]"), nw > old);
    S.shown[a.ticker] = nw;
    const c = tr.querySelector("[data-chg]"); c.className = `chg num ${cls(v)}`; c.textContent = sg(v) + fmt(Math.abs(v));
    const pc = tr.querySelector("[data-pct]"); pc.className = `chg num ${cls(p)}`; pc.innerHTML = `${ICON(v > 0 ? "up" : v < 0 ? "down" : "flat")}${Math.abs(p).toFixed(2)}%`;
  });
  if (S.rango === "hoy") { const a = S.data.acciones.find(x => x.ticker === S.sel); if (a && !a.error) await graficaPrecio(a); }
}
function estadoLive() {
  // El estado de la bolsa depende SOLO del reloj (horario real de la BMV, el Nasdaq y la NYSE): ningún botón lo modifica.
  const ab = abierto(), m = $("#mkt");
  m.dataset.open = ab;
  $("#mktTxt").innerHTML = `<span class="largo">Bolsa </span>${ab ? "abierta" : "cerrada"}`;
  m.title = ab ? "Los mercados operan (lunes a viernes, hora de Nueva York 9:30 a 16:00)" : "Los mercados no están operando; se muestra el último cierre";
  const a = $("#auto"), hist = S.data && !vivo();
  a.setAttribute("aria-pressed", S.auto && !hist); a.disabled = !!hist;
  a.innerHTML = `${ICON(S.auto && !hist ? "pause" : "play")}<span class="t">${hist ? "Histórico" : S.auto ? "Auto" : "Pausado"}</span>`;
  a.title = hist ? "Consulta de un periodo pasado: no se actualiza en vivo" : S.auto ? "Actualización automática activa. Toca para pausar." : "Actualización en pausa. Toca para reanudar.";
  const u = $("#updTxt"); if (u) u.textContent = (navigator.onLine ? "" : "Sin conexión · ") + textoActualizado() + (S.auto || hist ? "" : " · actualización en pausa");
}
let abiertoAntes = abierto();
async function ciclo() {
  estadoLive();
  if (!S.auto || document.hidden || S.busy || !S.data || !vivo() || !navigator.onLine) return;
  const ab = abierto(), now = Date.now();
  try {
    if (abiertoAntes && !ab) { S.busy = true; await cargar(true); S.busy = false; await pollQuotes(); render(); }
    else if (ab && now - S.tData > 300000) { S.busy = true; await cargar(true); S.busy = false; await pollQuotes(); render(); }
    else if (ab && now - S.tQuote > 20000) { await pollQuotes(); }
    else if (!ab && now - S.tData > 900000) { S.busy = true; await cargar(true); S.busy = false; render(); }
    S.fallos = 0; showErr("");
  } catch (e) {
    S.busy = false; S.fallos = (S.fallos || 0) + 1; S.tQuote = Date.now(); S.tData = Date.now() - 60000;
    if (S.fallos >= 3) showErr("La actualización automática no pudo conectarse con el servidor. Se sigue reintentando; revisa tu conexión.");
  }
  abiertoAntes = ab;
}

/* -------------------------------------------------------------------------- tema */
const TEMAS = ["claro", "mixto", "oscuro"];
function iniciarTema() {
  const actual = () => document.documentElement.dataset.theme;
  const marcar = () => $$("#menuTema button").forEach(b => b.setAttribute("aria-checked", b.dataset.t === actual()));
  marcar();
  $$("#menuTema button").forEach(b => b.onclick = () => {
    const t = TEMAS.includes(b.dataset.t) ? b.dataset.t : "claro";
    document.documentElement.dataset.theme = t; store.set("tema", t); marcar();
    $("#menuTema").open = false;
    if (S.data) render();
  });
  document.addEventListener("click", e => { const m = $("#menuTema"); if (m.open && !m.contains(e.target)) m.open = false; });
  document.addEventListener("keydown", e => { if (e.key === "Escape") $("#menuTema").open = false; });
}

/* ---------------------------------------------------------------- sin internet */
async function guardarTodo() {
  const b = $("#guardarOffline"), est = $("#guardarEstado");
  if (!navigator.onLine) { est.textContent = "Necesitas conexión para guardar los datos."; return; }
  b.setAttribute("aria-busy", "true");
  const q = qsP(), tks = [...S.selCmp].join(","), f = S.fechaDia || S.data?.acciones.find(a => !a.error)?.fecha;
  const tareas = [["Mercado", `/api/analisis?${q}&tickers=${(S.tickers || []).join(",")}`], ["Entorno global", `/api/contexto?${q}`], ["Guía", "/api/guia"], ["Decisiones por día", `/api/archivo?${q}`],
    ["Comparación", `/api/comparar?${q}&tickers=${tks}&moneda=${S.moneda}`], ["Simulación", `/api/simulacion?${q}&moneda=${S.moneda}`], ["Estado", "/api/estado"],
    ["Informe en PDF", `/api/informe?${q}&formato=pdf`], ["Informe en Excel", `/api/informe?${q}&formato=xlsx`]];
  if (f) tareas.push([`Día ${flarga(f)}`, `/api/dia?fecha=${f}`], ["PDF del día", `/api/dia?fecha=${f}&formato=pdf`], ["Excel del día", `/api/dia?fecha=${f}&formato=xlsx`]);
  let ok = 0, fallas = [];
  for (const [n, u] of tareas) {
    est.textContent = `Guardando ${n}… (${ok + fallas.length + 1} de ${tareas.length})`;
    try { const r = await fetch(u, { cache: "no-store" }); if (!r.ok) throw new Error(r.statusText); await r.blob(); ok++; } catch { fallas.push(n); }
  }
  b.removeAttribute("aria-busy");
  est.textContent = fallas.length ? `Se guardaron ${ok} de ${tareas.length}. No se pudo guardar: ${fallas.join(", ")}.` : `Listo: ${ok} consultas guardadas. Ya puedes verlas sin internet.`;
  S.guardado = Date.now();
}
function iniciarSinConexion() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/static/sw.js", { scope: "/" }).catch(() => {});
  addEventListener("offline", () => { S.sinConexion = true; avisoConexion(); estadoLive(); });
  addEventListener("online", () => { S.sinConexion = false; avisoConexion(); estadoLive(); if (S.data) actualizar(true); });
  avisoConexion();
}

/* -------------------------------------------------------------------- arranque */
function init() {
  S.periodo = periodoGuardado();
  S.tickers = [];
  renderNav(); renderPeriodo(); renderCinta(); iniciarTema(); iniciarSinConexion();
  $("#refresh").onclick = () => actualizar(true);
  $("#auto").onclick = () => { S.auto = !S.auto; store.set("auto", S.auto); estadoLive(); if (S.auto) ciclo(); };
  addEventListener("hashchange", () => setVista(location.hash.slice(1)));
  document.addEventListener("visibilitychange", () => { if (!document.hidden && S.auto && S.data) { S.tQuote = 0; ciclo(); } });
  setVista(location.hash.slice(1));
  armar("mercado", MERCADO_HTML);
  $("#board").innerHTML = `<tbody>${Array(6).fill('<tr class="skel"><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td></tr>').join("")}</tbody>`;
  api("/api/estado").then(e => { S.tickers = Object.keys(e.acciones); }).catch(() => {}).finally(() => actualizar(false));
  setInterval(ciclo, 1000);
}
init();
