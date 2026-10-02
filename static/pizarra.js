"use strict";
/* Pizarra — interfaz. Los cálculos viven en el servidor (analisis.py); aquí solo se muestran. */
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
const fhumana = s => { const [y, m, d] = ymd(s); return `${DIAS[new Date(y, m - 1, d).getDay()]} ${d} de ${MESES[m - 1]}`; };
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const alpha = (hex, a) => { const n = parseInt(hex.replace("#", ""), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
const serie = i => css("--s" + (i % 8 + 1));
const ICON = (id, c = "ic") => `<svg class="${c}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
const SIG = { "COMPRA FUERTE": ["buy", "up", "Compra fuerte"], COMPRAR: ["buy", "up", "Comprar"], MANTENER: ["hold", "flat", "Mantener"],
  VENDER: ["sell", "down", "Vender"], "VENTA FUERTE": ["sell", "down", "Venta fuerte"], ESPERAR: ["wait", "wait", "Esperar"], "SIN DATOS": ["hold", "flat", "Sin datos"] };
const sig = v => { const [k, i, t] = SIG[v] || SIG.MANTENER; return `<span class="sig ${k}">${ICON(i)}${t}</span>`; };
const sigK = v => (SIG[v] || SIG.MANTENER)[0];

const VISTAS = [["mercado", "Mercado", "board"], ["comparar", "Comparar", "compare"], ["deuda", "Deuda", "debt"], ["simulacion", "Simulación", "sim"], ["archivo", "Archivo", "archive"]];
const RANGOS = [["hoy", "Hoy"], ["21", "1M"], ["63", "3M"], ["126", "6M"], ["0", "Periodo"]];
const S = { vista: "mercado", data: null, sel: null, selD: 0, rango: "63", cmp: null, hist: null, sim: null, quotes: {}, shown: {}, intra: null,
  auto: store.get("auto", true), tData: 0, tQuote: 0, busy: false, selCmp: new Set(), fechaDia: null, charts: {} };

/* ---------------------------------------------------------------- utilidades */
async function api(path) {
  const r = await fetch(path, { cache: "no-store" });
  let j;
  try { j = await r.json(); } catch { throw new Error("El servidor no respondió con datos válidos"); }
  if (!r.ok || j.error) throw new Error(j.error || r.statusText);
  return j;
}
const showErr = m => { const e = $("#err"); e.textContent = m || ""; e.hidden = !m; };
const desde = () => $("#desde").value;
function abiertoNY() {
  const p = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", weekday: "short", hour: "numeric", minute: "numeric", hourCycle: "h23" }).formatToParts(new Date());
  const g = k => p.find(x => x.type === k).value, m = +g("hour") * 60 + +g("minute");
  return !["Sat", "Sun"].includes(g("weekday")) && m >= 570 && m < 960;
}

/* ------------------------------------------------------------------- gráficas */
const crosshair = { id: "crosshair", afterDatasetsDraw(ch) {
  const a = ch.tooltip?._active; if (!a?.length) return;
  const { ctx, chartArea: { top, bottom } } = ch, x = a[0].element.x;
  ctx.save(); ctx.strokeStyle = css("--rule-strong"); ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke(); ctx.restore();
} };
const endLabels = { id: "endLabels", afterDatasetsDraw(ch, _, o) {
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
  items.forEach(it => { ctx.fillStyle = it.color; ctx.fillRect(it.x + 5, it.y - 4, 8, 8); ctx.fillStyle = css("--ink-2"); ctx.fillText(it.text, it.x + 18, it.y); });
  ctx.restore();
} };
const refLine = { id: "refLine", afterDatasetsDraw(ch, _, o) {
  if (o?.valor == null) return;
  const y = ch.scales.y.getPixelForValue(o.valor), { ctx, chartArea: { left, right } } = ch;
  ctx.save(); ctx.strokeStyle = css("--muted"); ctx.lineWidth = 1; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke(); ctx.restore();
} };
Chart.register(crosshair, endLabels, refLine);

function mk(id, cfg) { S.charts[id]?.destroy(); S.charts[id] = new Chart(document.getElementById(id), cfg); return S.charts[id]; }
function opts({ fy = v => fmt(v), ftip, min, max, step, right = 8, extra, title } = {}) {
  const o = {
    responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false }, layout: { padding: { right } },
    plugins: { legend: { display: false }, endLabels: { on: false }, refLine: {},
      tooltip: { backgroundColor: css("--surface"), titleColor: css("--muted"), bodyColor: css("--ink"), borderColor: css("--rule-strong"), borderWidth: 1,
        padding: 10, boxPadding: 4, usePointStyle: true, titleFont: { family: css("--f-ui"), size: 12 }, bodyFont: { family: css("--f-num"), size: 14, weight: "600" },
        filter: it => it.dataset.tip !== false, callbacks: { label: c => ` ${c.dataset.label}: ${(ftip || fy)(c.parsed.y)}`, title: title } },
      ...(extra || {}) },
    scales: {
      x: { grid: { display: false }, border: { color: css("--rule-strong") }, ticks: { color: css("--muted"), maxTicksLimit: 6, maxRotation: 0, font: { family: css("--f-num"), size: 12 } } },
      y: { min, max, grid: { color: css("--rule") }, border: { display: false }, ticks: { color: css("--muted"), callback: fy, stepSize: step, font: { family: css("--f-num"), size: 12 } } },
    },
  };
  return o;
}
const linea = (label, data, color, o = {}) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: o.w ?? 2, pointRadius: o.pr ?? 0,
  pointHoverRadius: 4, tension: .12, spanGaps: true, fill: false, ...o });
const hexOf = v => { const c = css(v); return c.startsWith("#") ? c : "#888888"; };

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
    if (S.vista === "archivo") { await cargarHistorial(); renderArchivo(); return; }
    if (!S.data) return;
    if (S.vista === "mercado") renderMercado();
    else if (S.vista === "comparar") { await cargarComparar(); renderComparar(); }
    else if (S.vista === "deuda") renderDeuda();
    else if (S.vista === "simulacion") await renderSimulacion();
  } catch (e) { showErr(`No se pudo mostrar esta sección. ${e.message}. Intenta actualizar de nuevo.`); }
}

/* ----------------------------------------------------------------------- datos */
async function cargar(fresco) {
  const d = await api(`/api/analisis?desde=${desde()}${fresco ? "&fresco=1" : ""}`);
  S.data = d; S.tData = Date.now();
  const tks = d.acciones.map(a => a.ticker);
  if (!S.sel || !tks.includes(S.sel)) S.sel = tks[0];
  if (!S.selCmp.size) tks.forEach(t => S.selCmp.add(t));
}
async function actualizar(fresco = true) {
  if (S.busy) return;
  S.busy = true; $("#refresh").classList.add("spin");
  try { S.cmp = null; S.hist = null; S.sim = null; await cargar(fresco); await pollQuotes(true); await render(); showErr(""); }
  catch (e) { showErr(`No se pudo actualizar. Revisa tu conexión e intenta de nuevo (${e.message}).`); }
  S.busy = false; $("#refresh").classList.remove("spin"); estadoLive();
}

/* ---------------------------------------------------------------------- tablero */
function spark(vals, up) {
  const w = 92, h = 28, mn = Math.min(...vals), mx = Math.max(...vals), r = mx - mn || 1;
  const pts = vals.map((v, i) => `${(i / (vals.length - 1) * w).toFixed(1)},${(h - 2 - (v - mn) / r * (h - 4)).toFixed(1)}`);
  const c = up ? "var(--up-b)" : "var(--down-b)", last = pts.at(-1).split(",");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts.join(" ")}" fill="none" stroke="${c}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${last[0]}" cy="${last[1]}" r="2.6" fill="${c}"/></svg>`;
}
const visto = {};
const entra = v => visto[v] ? "" : (visto[v] = "enter");
function precioVivo(a) { const q = S.quotes[a.ticker]; return q && q.precio != null ? q.precio : a.cierre; }
function cambioVivo(a) { const p = precioVivo(a); return [p - a.previo, (p / a.previo - 1) * 100]; }

function renderMercado() {
  const d = S.data, ok = d.acciones.find(a => !a.error);
  $("#titulo").textContent = abiertoNY() ? "Sesión en curso" : ok ? `Cierre del ${fhumana(ok.fecha)}` : "Mercado";
  $("#lectura").textContent = d.mercado.texto;
  $("#board").innerHTML = `<thead><tr><th>Emisora</th><th>Último</th><th class="c-chg">Cambio</th><th>%</th><th class="c-spark">30 sesiones</th><th class="c-sig">Señal</th></tr></thead><tbody class="${entra("mercado")}">` +
    d.acciones.map((a, i) => {
      if (a.error) return `<tr><td colspan="6" class="flat">${esc(tk(a.ticker))}: sin datos (${esc(a.error)})</td></tr>`;
      const [v, p] = cambioVivo(a), s30 = a.serie.cierre.slice(-30);
      return `<tr tabindex="0" data-t="${a.ticker}" aria-selected="${a.ticker === S.sel}" style="--i:${i}">
        <td><div class="who"><span class="sw" style="--c:${serie(i)}"></span><div><div class="tk">${tk(a.ticker)}</div><div class="nm">${esc(a.nombre)}</div><div class="m-only">${sig(a.veredicto)}</div></div></div></td>
        <td><span class="px num" data-px>${fmt(precioVivo(a))}</span></td>
        <td class="c-chg"><span class="chg num ${cls(v)}" data-chg>${sg(v)}${fmt(Math.abs(v))}</span></td>
        <td><span class="chg num ${cls(p)}" data-pct style="display:inline-flex;align-items:center;gap:4px">${ICON(v > 0 ? "up" : v < 0 ? "down" : "flat")}${Math.abs(p).toFixed(2)}%</span></td>
        <td class="c-spark">${spark(s30, s30.at(-1) >= s30[0])}</td>
        <td class="c-sig">${sig(a.veredicto)}</td></tr>`; }).join("") + "</tbody>";
  $$("#board tbody tr[data-t]").forEach(tr => {
    tr.onclick = () => seleccionar(tr.dataset.t, true);
    tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); seleccionar(tr.dataset.t, true); } };
    const a = d.acciones.find(x => x.ticker === tr.dataset.t), old = S.shown[a.ticker], nw = precioVivo(a);
    if (old != null && old !== nw) flip(tr.querySelector("[data-px]"), nw > old);
    S.shown[a.ticker] = nw;
  });
  pieTablero();
  renderAlertas();
  cargarCambios();
  renderDetalle();
}
function pieTablero() {
  $("#boardFoot").innerHTML = `<span>Yahoo Finance · precios en pesos mexicanos</span><span id="updTxt">${textoActualizado()}</span>`;
}
function textoActualizado() {
  if (!S.tData) return "";
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
  $$("#board tbody tr").forEach(tr => tr.setAttribute("aria-selected", tr.dataset.t === t));
  renderDetalle();
  if (scroll && innerWidth < 980) $("#detalle").scrollIntoView({ behavior: "smooth", block: "start" });
}

/* --------------------------------------------------------------------- detalle */
async function renderDetalle() {
  const d = S.data, a = d.acciones.find(x => x.ticker === S.sel && !x.error) || d.acciones.find(x => !x.error);
  if (!a) return;
  $("#detalle").hidden = false;
  const idx = d.acciones.findIndex(x => x.ticker === a.ticker);
  $("#dNombre").textContent = `${a.nombre} (${tk(a.ticker)})`;
  $("#rango").innerHTML = RANGOS.map(([v, t]) => `<button data-r="${v}" aria-pressed="${S.rango === v}">${t}</button>`).join("");
  $$("#rango button").forEach(b => b.onclick = () => { S.rango = b.dataset.r; renderDetalle(); });

  const k = sigK(a.veredicto);
  $("#senal").innerHTML = `<div class="word ${k}">${(SIG[a.veredicto] || SIG.MANTENER)[2]}</div>
    <p class="meta">Puntaje <b class="num">${sg(a.score)}${Math.abs(a.score)}</b> de ±100 · confianza ${a.confianza.toLowerCase()} · tendencia ${a.tendencia.etiqueta}</p>
    <div class="gauge"><i style="left:${Math.max(0, Math.min(100, (a.score + 100) / 2))}%"></i></div>
    <div class="gauge-l"><span>Vender</span><span>Mantener</span><span>Comprar</span></div>
    <table class="crit"><tbody>` + a.componentes.map(c => { const w = Math.abs(c.puntos) / c.max * 50;
      return `<tr><td><b>${esc(c.criterio)}</b><span>${esc(c.detalle)}</span><span class="pbar"><i style="left:${c.puntos >= 0 ? 50 : 50 - w}%;width:${w}%;background:var(${c.puntos === 0 ? "--rule-strong" : c.puntos > 0 ? "--up" : "--down"})"></i></span></td><td class="pts ${cls(c.puntos)}">${sg(c.puntos)}${Math.abs(c.puntos)}</td></tr>`; }).join("") + `</tbody></table>`;

  const s = a.stats, row = (l, v, c) => `<div><dt>${l}</dt><dd class="${c || ""}">${v}</dd></div>`;
  $("#stats").innerHTML = [
    row("Rendimiento 5 sesiones", pct(a.ret5), cls(a.ret5)), row("Rendimiento 20 sesiones", pct(a.ret20), cls(a.ret20)),
    row("Rendimiento del periodo", pct(a.ret_periodo), cls(a.ret_periodo)), row("RSI (14)", a.rsi == null ? "—" : a.rsi.toFixed(2)),
    row("Volatilidad anual", s.vol_anual == null ? "—" : s.vol_anual.toFixed(2) + "%"), row("Caída máxima (120 ses.)", pct(s.max_drawdown), "down"),
    row("Soporte (20 ses.)", fmt(s.soporte)), row("Resistencia (20 ses.)", fmt(s.resistencia)),
    row("Rendimiento / riesgo", s.ratio_rend_riesgo == null ? "—" : fmt(s.ratio_rend_riesgo), cls(s.ratio_rend_riesgo)), row("Z del precio vs. media 20", sg(s.z_precio) + Math.abs(s.z_precio).toFixed(2)),
    row("Tendencia 30 ses.", a.tendencia.pendiente == null ? "—" : pct(a.tendencia.pendiente, 2) + "/día", cls(a.tendencia.pendiente)), row("Volumen vs. promedio", s.vol_relativo == null ? "—" : s.vol_relativo.toFixed(2) + "×")].join("");
  $("#texto").innerHTML = `<div class="decision ${sigK(a.veredicto)}">${esc(a.decision)}</div>
    <p>${esc(a.texto)}</p><p class="que"><b>Por qué:</b></p><ul>${a.por_que.map(p => `<li>${esc(p)}</li>`).join("")}</ul>
    <p class="que"><b>Qué hacer:</b> ${esc(a.accion)}</p>` + (a.cambio ? `<p class="que"><b>Cambio de decisión:</b> ayer era ${esc((SIG[a.veredicto_ant] || SIG.MANTENER)[2].toLowerCase())}, hoy es ${esc(a.decision.toLowerCase())}.</p>` : "");
  $("#descDia").innerHTML = ["pdf:PDF", "xlsx:Excel"].map(x => { const [f, t] = x.split(":");
    return `<a class="btn" href="/api/dia?fecha=${a.fecha}&formato=${f}" download>${ICON("download")}Descargar análisis del ${flarga(a.fecha)} (${t})</a>`; }).join("") +
    `<p class="note" style="flex-basis:100%">Incluye las 5 emisoras y la deuda: decisión, por qué y qué hacer, con lo que pasó después cuando ya hay datos.</p>`;
  const b = a.backtest, fila = (t, n, ac, r, ok, bueno) => `<tr><td>${t}</td><td>${n}</td><td class="${ok ? "up" : "down"}">${n < 8 ? "—" : fmt(ac) + "%"}</td><td class="${cls(r)}">${n < 8 ? "—" : pct(r)}</td><td>${n < 8 ? "pocos casos" : bueno}</td></tr>`;
  const okC = b.aciertos_compra >= 55 && b.rend_medio_compra > b.base_rend_medio, okV = b.aciertos_venta >= 55 && b.rend_medio_venta < b.base_rend_medio;
  $("#bt").innerHTML = `<div class="scrollx"><table class="tbl"><thead><tr><th>Señal</th><th>Casos</th><th>Aciertos</th><th>Rend. a ${b.horizonte} ses.</th><th>Lectura</th></tr></thead><tbody>` +
    fila("Compra", b.n_compra, b.aciertos_compra, b.rend_medio_compra, okC, okC ? "respaldada" : "sin respaldo") + fila("Venta", b.n_venta, b.aciertos_venta, b.rend_medio_venta, okV, okV ? "respaldada" : "sin respaldo") +
    `</tbody></table></div><p class="note" style="margin-top:10px">Rendimiento medio de todas las sesiones: ${pct(b.base_rend_medio)}. Prueba dentro de la misma muestra (${b.muestra} sesiones): sirve para calibrar la confianza, no la garantiza.</p>`;
  await graficaPrecio(a);
}

async function graficaPrecio(a) {
  const ink = css("--ink"), medias = $("#chkMedias").checked, bandas = $("#chkBandas").checked, sr = a.serie;
  if (S.rango === "hoy") {
    $("#chkMedias").disabled = $("#chkBandas").disabled = true;
    try { S.intra = await api(`/api/intradia?ticker=${encodeURIComponent(a.ticker)}`); } catch (e) { S.intra = []; showErr("No se pudo traer la gráfica del día. Intenta de nuevo en unos segundos."); }
    const L = S.intra.map(r => r.hora), v = S.intra.map(r => r.precio);
    const o = opts({ fy: n => fmt(n), ftip: n => "$" + fmt(n), extra: { refLine: { valor: a.previo } } });
    mk("chPrecio", { type: "line", data: { labels: L, datasets: [linea("Precio", v, ink, { w: 2 })] }, options: o });
    $("#legPrecio").innerHTML = `<span style="--c:${ink}"><i></i>Precio cada 5 minutos</span><span style="--c:${css("--muted")}"><i class="d"></i>Cierre anterior ($${fmt(a.previo)})</span>`;
  } else {
    $("#chkMedias").disabled = $("#chkBandas").disabled = false;
    const n = +S.rango, ini = n ? Math.max(0, sr.fechas.length - n) : 0, sl = arr => arr.slice(ini), L = sl(sr.fechas), ds = [];
    if (bandas) {
      ds.push({ label: "Banda sup.", data: sl(sr.bb_up), borderColor: alpha(hexOf("--ink-2"), .35), borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: alpha(hexOf("--ink"), .06), tip: false });
      ds.push({ label: "Banda inf.", data: sl(sr.bb_low), borderColor: alpha(hexOf("--ink-2"), .35), borderWidth: 1, pointRadius: 0, fill: false, tip: false });
    }
    ds.push(linea("Cierre", sl(sr.cierre), ink, { w: 2.2, endLabel: "Cierre" }));
    if (medias) { ds.push(linea("Media 20", sl(sr.sma20), css("--amber-ink"), { w: 1.6, borderDash: [6, 4], endLabel: "Media 20" }));
      ds.push(linea("Media 50", sl(sr.sma50), css("--muted"), { w: 1.6, borderDash: [2, 3], endLabel: "Media 50" })); }
    const o = opts({ ftip: v => "$" + fmt(v), right: 76, extra: { endLabels: { on: true } }, title: it => flarga(L[it[0].dataIndex]) });
    mk("chPrecio", { type: "line", data: { labels: L.map(fcorta), datasets: ds }, options: o });
    $("#legPrecio").innerHTML = `<span style="--c:${ink}"><i></i>Cierre</span>` + (medias ? `<span style="--c:${css("--amber-ink")}"><i class="d"></i>Media de 20 sesiones</span><span style="--c:${css("--muted")}"><i class="t"></i>Media de 50</span>` : "") + (bandas ? `<span style="--c:${ink}"><i class="f"></i>Bollinger (20, 2σ)</span>` : "");
    const orsi = opts({ fy: v => fmt(v), ftip: v => v?.toFixed(2), min: 0, max: 100, step: 25, title: it => flarga(L[it[0].dataIndex]) });
    mk("chRsi", { type: "line", data: { labels: L.map(fcorta), datasets: [linea("RSI", sl(sr.rsi), ink, { w: 1.8 }),
      linea("70", L.map(() => 70), css("--down"), { w: 1, borderDash: [4, 4], tip: false }), linea("30", L.map(() => 30), css("--up"), { w: 1, borderDash: [4, 4], tip: false })] }, options: orsi });
    const h = sl(sr.hist), om = opts({ fy: v => fmt(v, 1), ftip: v => fmt(v, 3), title: it => flarga(L[it[0].dataIndex]) });
    mk("chMacd", { type: "bar", data: { labels: L.map(fcorta), datasets: [
      { type: "bar", label: "Histograma", data: h, backgroundColor: h.map(v => alpha(v >= 0 ? hexOf("--up") : hexOf("--down"), .55)), borderWidth: 0, barPercentage: 1, categoryPercentage: 1 },
      linea("MACD", sl(sr.macd), ink, { type: "line", w: 1.6 }), linea("Señal", sl(sr.macd_signal), css("--amber-ink"), { type: "line", w: 1.3, borderDash: [4, 3] })] }, options: om });
  }
}
/* --------------------------------------------------------------------- comparar */
async function cargarComparar() {
  const tks = [...S.selCmp], clave = tks.join(",") + desde();
  if (S.cmp?.clave === clave || tks.length < 2) return;
  S.cmp = { ...(await api(`/api/comparar?desde=${desde()}&tickers=${tks.join(",")}`)), clave };
}
function renderComparar() {
  const d = S.data;
  $("#chips").innerHTML = d.acciones.map((x, i) => `<button class="chip" style="--c:${serie(i)}" data-t="${x.ticker}" aria-pressed="${S.selCmp.has(x.ticker)}"><i></i>${tk(x.ticker)}</button>`).join("");
  $$("#chips .chip").forEach(b => b.onclick = () => {
    const t = b.dataset.t;
    if (S.selCmp.has(t)) { if (S.selCmp.size <= 2) return; S.selCmp.delete(t); } else S.selCmp.add(t);
    render();
  });
  const c = S.cmp; if (!c || !c.fechas.length) return;
  const nom = t => d.acciones.find(a => a.ticker === t)?.nombre || t, colr = t => serie(d.acciones.findIndex(a => a.ticker === t));
  const L = c.fechas, tks = Object.keys(c.base100);
  const o = opts({ fy: v => fmt(v), ftip: v => fmt(v), right: 128, extra: { endLabels: { on: true }, refLine: { valor: 100 } }, title: it => flarga(L[it[0].dataIndex]) });
  mk("chComparar", { type: "line", data: { labels: L.map(fcorta), datasets: tks.map(t => linea(tk(t), c.base100[t], colr(t), { w: 2.2, endLabel: `${tk(t)} ${fmt(c.base100[t].at(-1))}` })) }, options: o });
  $("#legComparar").innerHTML = tks.map(t => `<span style="--c:${colr(t)}"><i class="sq"></i>${esc(nom(t))}</span>`).join("");

  const fa = $("#fechaA"), fb = $("#fechaB");
  fa.min = fb.min = L[0]; fa.max = fb.max = L.at(-1);
  if (!fa.value || fa.value < L[0] || fa.value > L.at(-1)) fa.value = L[0];
  if (!fb.value || fb.value < L[0] || fb.value > L.at(-1)) fb.value = L.at(-1);
  const pos = f => { let k = -1; L.forEach((x, i) => { if (x <= f) k = i; }); return k; };
  const tabla = () => {
    const ia = pos(fa.value), ib = pos(fb.value);
    if (ia < 0 || ib < 0) { $("#tblConsulta").innerHTML = "<tbody><tr><td>Elige fechas dentro del periodo.</td></tr></tbody>"; return; }
    const filas = tks.map(t => { const a = c.cierres[t][ia], b = c.cierres[t][ib]; return { t, a, b, dv: b - a, dp: (b / a - 1) * 100 }; });
    const mejor = Math.max(...filas.map(f => f.dp));
    $("#tblConsulta").innerHTML = `<thead><tr><th>Emisora</th><th>${fcorta(L[ia])}</th><th>${fcorta(L[ib])}</th><th>Cambio</th></tr></thead><tbody>` +
      filas.map(f => `<tr><td><b>${tk(f.t)}</b>${f.dp === mejor ? ' <span class="note">mejor</span>' : ""}</td><td>$${fmt(f.a)}</td><td>$${fmt(f.b)}</td><td class="${cls(f.dp)}"><b>${pct(f.dp)}</b><small>${sg(f.dv)}${fmt(Math.abs(f.dv))}</small></td></tr>`).join("") + "</tbody>";
  };
  fa.onchange = fb.onchange = tabla; tabla();
  $$("#atajos button").forEach(b => b.onclick = () => { const u = L.length - 1; fb.value = L[u]; fa.value = b.dataset.a === "ini" ? L[0] : L[Math.max(0, u - (b.dataset.a === "sem" ? 5 : 21))]; tabla(); });

  $("#tblRanking").innerHTML = `<thead><tr><th>Emisora</th><th>Rend.</th><th>Vol.</th><th>R/R</th><th>Caída</th><th>Días al alza</th></tr></thead><tbody>` +
    [...c.ranking].sort((a, b) => b.ret - a.ret).map(r => `<tr><td><b>${tk(r.ticker)}</b></td><td class="${cls(r.ret)}"><b>${pct(r.ret)}</b></td><td>${fmt(r.vol_anual)}%</td><td>${r.ratio == null ? "—" : fmt(r.ratio)}</td><td class="down">${pct(r.max_drawdown)}</td><td>${fmt(r.dias_alza)}%</td></tr>`).join("") + "</tbody>";
  const m = c.corr.matriz, n = c.corr.tickers.length, g = $("#heat");
  g.style.gridTemplateColumns = `auto repeat(${n},minmax(0,1fr))`;
  g.innerHTML = `<div class="h"></div>` + c.corr.tickers.map(t => `<div class="h">${tk(t)}</div>`).join("") +
    m.map((row, i) => `<div class="h" style="text-align:right">${tk(c.corr.tickers[i])}</div>` + row.map(v => { const w = Math.round(Math.abs(v) * 80), base = v >= 0 ? "--s1" : "--s8";
      return `<div style="background:color-mix(in srgb,var(${base}) ${w}%,var(--surface));color:${w > 50 ? "#fff" : "var(--ink)"}">${fmt(v)}</div>`; }).join("")).join("");
  $("#tblCierres").innerHTML = `<thead><tr><th>Fecha</th>${tks.map(t => `<th>${tk(t)}</th>`).join("")}</tr></thead><tbody>` +
    L.map((f, i) => `<tr><td>${flarga(f)}</td>` + tks.map(t => { const v = c.cierres[t][i], p = i ? (v / c.cierres[t][i - 1] - 1) * 100 : null;
      return `<td>${fmt(v)}${p == null ? "" : `<small class="${cls(p)}">${pct(p)}</small>`}</td>`; }).join("") + "</tr>").reverse().join("") + "</tbody>";
}

/* ------------------------------------------------------------------------ deuda */
const valDeuda = x => x.valor == null ? "—" : x.tipo === "precio" ? "$" + fmt(x.valor, 5) : fmt(x.valor) + (x.unidad.startsWith("%") ? "%" : " pp");
function renderDeuda() {
  const d = S.data, ok = d.deuda.find(x => x.fecha);
  $("#boardDeuda").innerHTML = `<thead><tr><th>Instrumento</th><th>Último</th><th class="c-chg">Cambio</th><th class="c-z">Z</th><th class="c-trend">Tendencia</th><th class="c-sig">Señal</th></tr></thead><tbody class="${entra("deuda")}">` +
    d.deuda.map((x, i) => `<tr tabindex="0" data-d="${i}" aria-selected="${i === S.selD}" style="--i:${i}">
      <td><div class="who"><span class="sw" style="--c:${serie(i)}"></span><div><div class="tk">${esc(x.nombre)}</div><div class="nm">${esc(x.emisor)}</div><div class="m-only">${sig(x.senal)}</div></div></div></td>
      <td><span class="px num">${valDeuda(x)}</span></td>
      <td class="c-chg"><span class="chg num ${cls(x.var_pb ?? x.var)}">${x.var_pb != null ? sg(x.var_pb) + Math.abs(x.var_pb).toFixed(2) + " pb" : x.var != null ? sg(x.var) + Math.abs(x.var).toFixed(5) : "—"}</span></td>
      <td class="c-z"><span class="chg num flat">${x.z != null ? sg(x.z) + Math.abs(x.z).toFixed(2) : "—"}</span></td>
      <td class="c-trend"><span class="flat">${esc(x.tendencia)}</span></td>
      <td class="c-sig">${sig(x.senal)}</td></tr>`).join("") + "</tbody>";
  $("#footDeuda").innerHTML = `<span>Banco de México · subastas semanales (cuadros CF107 y CF115)</span><span>${ok ? "Última subasta " + fhumana(ok.fecha) : ""}</span>`;
  $$("#boardDeuda tbody tr").forEach(tr => {
    const go = () => { S.selD = +tr.dataset.d; renderDeuda(); if (innerWidth < 980) $("#detalleDeuda").scrollIntoView({ behavior: "smooth" }); };
    tr.onclick = go; tr.onkeydown = e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } };
  });
  const x = d.deuda[S.selD]; if (!x) return;
  $("#detalleDeuda").hidden = false;
  const es = x.tipo === "tasa", col = css("--ink"), v = x.datos.map(r => r.valor);
  const ma = v.map((_, i) => i >= 3 ? v.slice(i - 3, i + 1).reduce((p, q) => p + q, 0) / 4 : null);
  $("#deuNombre").textContent = `${x.nombre} · ${x.emisor}`;
  $("#legDeuda").innerHTML = `<span style="--c:${col}"><i></i>${es ? "Rendimiento" : "Precio"} en cada subasta (${esc(x.unidad)})</span><span style="--c:${css("--amber-ink")}"><i class="d"></i>Promedio móvil de 4 subastas</span>`;
  const o = opts({ fy: n => es ? n.toFixed(2) : n.toFixed(3), ftip: n => es ? n.toFixed(2) + (x.unidad.startsWith("%") ? "%" : " pp") : "$" + n.toFixed(5), right: 78, extra: { endLabels: { on: true } }, title: it => flarga(x.datos[it[0].dataIndex].fecha) });
  mk("chDeuda", { type: "line", data: { labels: x.datos.map(r => fcorta(r.fecha)), datasets: [
    linea(es ? "Rendimiento" : "Precio", v, col, { w: 2.2, pr: 3, endLabel: valDeuda(x) }), linea("Promedio móvil", ma, css("--amber-ink"), { w: 1.6, borderDash: [6, 4] })] }, options: o });
  $("#deuLectura").innerHTML = `<div class="word ${sigK(x.senal)}">${(SIG[x.senal] || SIG.MANTENER)[2]}</div>
    <p class="meta">${esc(x.texto)}</p>
    <p class="note" style="margin-top:14px">Z: desviaciones estándar frente al promedio de las últimas 12 subastas. Pendiente: regresión de las últimas 8 subastas (${x.pendiente != null ? sg(x.pendiente) + Math.abs(x.pendiente).toFixed(2) + (es ? " pb" : " $") + " por subasta" : "sin datos"}).</p>`;
  $("#tblDeuda").innerHTML = `<thead><tr><th>Subasta</th><th>${es ? "Tasa" : "Precio"}</th><th>${es ? "Cambio (pb)" : "Cambio"}</th></tr></thead><tbody>` +
    [...x.datos].reverse().map(r => `<tr><td>${flarga(r.fecha)}</td><td><b>${es ? fmt(r.valor) : fmt(r.valor, 5)}</b></td><td class="${cls(es ? r.var_pb : r.var)}">${es ? (r.var_pb == null ? "—" : sg(r.var_pb) + Math.abs(r.var_pb).toFixed(2)) : (r.var == null ? "—" : sg(r.var) + Math.abs(r.var).toFixed(5))}</td></tr>`).join("") + "</tbody>";
}

/* ---------------------------------------------------------------------- archivo */
async function cargarHistorial() {
  if (S.hist) return;
  const r = await fetch("/static/data/analisis_diario.json", { cache: "no-cache" });
  if (!r.ok) throw new Error("Aún no hay análisis guardados");
  S.hist = await r.json();
  S.fechaDia = S.hist.registros.at(-1)?.fecha;
}
const VCLS = { "COMPRA FUERTE": "v-buy2", COMPRAR: "v-buy", MANTENER: "", VENDER: "v-sell", "VENTA FUERTE": "v-sell2" };
function renderArchivo() {
  const h = S.hist; if (!h) return;
  const R = h.registros, a = R[0], z = R.at(-1);
  $("#archResumen").textContent = `${R.length} análisis diarios guardados, del ${fhumana(a.fecha)} al ${fhumana(z.fecha)}.`;
  $("#descargas").innerHTML = [["analisis_diario.xlsx", "Excel"], ["analisis_acciones.csv", "CSV de acciones"], ["analisis_deuda.csv", "CSV de deuda"], ["analisis_diario.json", "JSON"]]
    .map(([f, t]) => `<a class="btn" href="/static/data/${f}" download>${ICON("download")}${t}</a>`).join("");
  $("#legTl").innerHTML = [["v-buy2", "Compra fuerte"], ["v-buy", "Comprar"], ["", "Mantener"], ["v-sell", "Vender"], ["v-sell2", "Venta fuerte"]]
    .map(([c, t]) => `<span><i class="sq ${c}" style="${c ? "" : "background:var(--rule)"}"></i>${t}</span>`).join("");
  const tks = [...new Set(R.flatMap(r => r.emisoras.map(e => e.ticker)))];
  $("#timeline").innerHTML = tks.map(t => `<div class="tl-row"><b>${t}</b><div class="tl-cells">` + R.map(r => { const e = r.emisoras.find(x => x.ticker === t);
    return e ? `<button class="${VCLS[e.veredicto]}" data-f="${r.fecha}" title="${flarga(r.fecha)}: ${e.veredicto.toLowerCase()} (${e.score})" aria-label="${t} ${flarga(r.fecha)} ${e.veredicto.toLowerCase()}" aria-current="${r.fecha === S.fechaDia}"></button>` : `<button disabled></button>`; }).join("") + "</div></div>").join("");
  $("#timeline").scrollLeft = 1e6;
  $$("#timeline button[data-f]").forEach(b => b.onclick = () => { S.fechaDia = b.dataset.f; renderArchivo(); });
  const sel = $("#diaSel"); sel.min = a.fecha; sel.max = z.fecha; sel.value = S.fechaDia;
  sel.onchange = () => { const f = [...R].reverse().find(r => r.fecha <= sel.value); S.fechaDia = (f || a).fecha; renderArchivo(); };
  const ix = R.findIndex(r => r.fecha === S.fechaDia);
  $("#diaPrev").onclick = () => { if (ix > 0) { S.fechaDia = R[ix - 1].fecha; renderArchivo(); } };
  $("#diaNext").onclick = () => { if (ix < R.length - 1) { S.fechaDia = R[ix + 1].fecha; renderArchivo(); } };
  const r = R[ix]; $("#diaTitulo").textContent = fhumana(r.fecha).replace(/^./, c => c.toUpperCase());
  $("#diaDl").innerHTML = ["pdf:PDF", "xlsx:Excel"].map(x => { const [f, t] = x.split(":");
    return `<a class="btn sm" href="/api/dia?fecha=${r.fecha}&formato=${f}" download>${ICON("download")}${t} de este día</a>`; }).join("");
  const ev = R.flatMap(q => q.emisoras).filter(e => e.acierto !== null && e.acierto !== undefined), grupo = k => ev.filter(e => k(e.veredicto));
  const fila = (t, xs) => { const n = xs.length, ok = xs.filter(e => e.acierto).length, med = n ? xs.reduce((s, e) => s + e.ret_5, 0) / n : null;
    return `<tr><td><b>${t}</b></td><td>${n}</td><td>${n ? fmt(100 * ok / n) + "%" : "—"}</td><td class="${cls(med)}">${med == null ? "—" : pct(med)}</td></tr>`; };
  $("#aciertos").innerHTML = `<div class="scrollx"><table class="tbl"><thead><tr><th>Decisión</th><th>Casos evaluados</th><th>Aciertos a 5 sesiones</th><th>Rend. medio a 5 ses.</th></tr></thead><tbody>` +
    fila("Comprar", grupo(v => v.startsWith("COMPR"))) + fila("Mantener", grupo(v => v === "MANTENER")) + fila("Vender", grupo(v => v.startsWith("VEN"))) + fila("Todas", ev) +
    `</tbody></table></div><p class="note" style="margin-top:10px">Comprar acierta si el precio subió a 5 sesiones; vender, si bajó; mantener, si se movió 2.00 % o menos. Un acierto cercano a 50.00 % significa que la decisión no superó al azar en este periodo.</p>`;
  $("#diaDetalle").innerHTML = `<p class="prose">${esc(r.mercado.texto)}</p>
    <div class="scrollx" style="margin-top:14px"><table class="tbl"><thead><tr><th>Emisora</th><th>Cierre</th><th>Var.</th><th>RSI</th><th>Puntaje</th><th>Decisión</th><th>5 ses.</th><th>¿Acertó?</th></tr></thead><tbody>` +
    r.emisoras.map(e => `<tr><td><b>${e.ticker}</b></td><td>$${fmt(e.cierre)}</td><td class="${cls(e.var_pct)}">${pct(e.var_pct)}</td><td>${e.rsi == null ? "—" : fmt(e.rsi)}</td><td>${sg(e.score)}${Math.abs(e.score)}</td><td>${sig(e.veredicto)}</td><td class="${cls(e.ret_5)}">${e.ret_5 == null ? "—" : pct(e.ret_5)}</td><td class="${e.acierto ? "ok" : e.acierto === false ? "no" : ""}">${e.acierto == null ? "por evaluar" : e.acierto ? "Sí" : "No"}</td></tr>`).join("") + `</tbody></table></div>
    <div style="margin-top:18px">` + r.emisoras.map(e => `<div class="day-item"><b>${esc(e.nombre)}</b> ${sig(e.veredicto)}<div class="prose" style="margin-top:6px"><ul>${e.por_que.map(p => `<li>${esc(p)}</li>`).join("")}</ul><p class="que"><b>Qué hacer:</b> ${esc(e.accion)}</p></div></div>`).join("") +
    r.deuda.map(x => `<div class="day-item"><b>${esc(x.nombre)}</b> ${sig(x.senal)}<div class="prose" style="margin-top:6px"><ul>${x.por_que.map(p => `<li>${esc(p)}</li>`).join("")}</ul></div></div>`).join("") + `</div>`;
}

/* ---------------------------------------------------------- actualización automática */
async function pollQuotes(force) {
  if (!S.data) return;
  const q = await api(`/api/cotizaciones?tickers=${S.data.acciones.map(a => a.ticker).join(",")}`);
  S.quotes = Object.fromEntries(q.map(x => [x.ticker, x])); S.tQuote = Date.now();
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
  // El estado de la bolsa depende SOLO del reloj (horario real de la BMV): ningún botón lo modifica.
  const ab = abiertoNY(), m = $("#mkt");
  m.dataset.open = ab;
  $("#mktTxt").innerHTML = `<span class="long">Bolsa </span>${ab ? "abierta" : "cerrada"}`;
  m.title = ab ? "La BMV está operando (lunes a viernes, hora de Nueva York 9:30 a 16:00)" : "La BMV no está operando; se muestra el último cierre";
  const a = $("#auto");
  a.setAttribute("aria-pressed", S.auto);
  a.innerHTML = `${ICON(S.auto ? "pause" : "play")}<span class="t">${S.auto ? "Auto" : "Pausado"}</span>`;
  a.title = S.auto ? "Actualización automática activa. Toca para pausar." : "Actualización en pausa. Toca para reanudar.";
  const u = $("#updTxt"); if (u) u.textContent = textoActualizado() + (S.auto ? "" : " · actualización en pausa");
}
let abiertoAntes = abiertoNY();
async function ciclo() {
  estadoLive();
  if (!S.auto || document.hidden || S.busy || !S.data) return;
  const ab = abiertoNY(), now = Date.now();
  try {
    if (abiertoAntes && !ab) { S.busy = true; await cargar(true); S.busy = false; await pollQuotes(true); render(); }       // cierre de sesión: toma el cierre final
    else if (ab && now - S.tData > 120000) { S.busy = true; await cargar(true); S.busy = false; await pollQuotes(true); render(); } // señales cada 2 min
    else if (ab && now - S.tQuote > 20000) { await pollQuotes(); }                                                           // precios cada 20 s
    else if (!ab && now - S.tData > 900000) { S.busy = true; await cargar(true); S.busy = false; render(); }                  // cerrado: cada 15 min
    showErr("");
  } catch (e) { S.busy = false; showErr(`No se pudo actualizar automáticamente (${e.message}). Se reintentará en unos segundos.`); }
  abiertoAntes = ab;
}

/* -------------------------------------------------------------------- arranque */
function init() {
  renderNav();
  $("#refresh").onclick = () => actualizar(true);
  $("#auto").onclick = () => { S.auto = !S.auto; store.set("auto", S.auto); estadoLive(); if (S.auto) ciclo(); };
  iniciarTema();
  $("#desde").onchange = () => actualizar(false);
  $("#chkMedias").onchange = $("#chkBandas").onchange = () => S.data && renderDetalle();
  addEventListener("hashchange", () => setVista(location.hash.slice(1)));
  document.addEventListener("visibilitychange", () => { if (!document.hidden && S.auto && S.data) { S.tQuote = 0; ciclo(); } });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => S.data && render());
  $("#board").innerHTML = `<tbody>${Array(5).fill('<tr class="skel"><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td><td><div></div></td></tr>').join("")}</tbody>`;
  setVista(location.hash.slice(1));
  cargar(false).then(() => pollQuotes()).then(() => { render(); estadoLive(); })
    .catch(e => showErr(`No se pudo cargar el mercado. Revisa tu conexión y toca actualizar (${e.message}).`));
  setInterval(ciclo, 1000);
}
init();

/* -------------------------------------------------------------------------- tema */
const TEMAS = ["claro", "pizarra", "oscuro"];
function iniciarTema() {
  const actual = () => document.documentElement.dataset.theme;
  const marcar = () => $$("#menuTema button").forEach(b => b.setAttribute("aria-checked", b.dataset.t === actual()));
  marcar();
  $$("#menuTema button").forEach(b => b.onclick = () => {
    const t = TEMAS.includes(b.dataset.t) ? b.dataset.t : "claro";
    document.documentElement.dataset.theme = t; store.set("tema", t); marcar();
    $("#menuTema").open = false;
    const mc = document.querySelector('meta[name="theme-color"]'); if (mc) mc.content = t === "oscuro" ? "#0B0F13" : "#15191D";
    if (S.data) render();
  });
  document.addEventListener("click", e => { const m = $("#menuTema"); if (m.open && !m.contains(e.target)) m.open = false; });
  document.addEventListener("keydown", e => { if (e.key === "Escape") $("#menuTema").open = false; });
}

/* ---------------------------------------------------- alertas y cambios de decisión */
function renderAlertas() {
  const cambios = S.data.acciones.filter(a => !a.error && a.cambio);
  let vistos = store.get("vistos", null);
  const hoy = Object.fromEntries(S.data.acciones.filter(a => !a.error).map(a => [a.ticker, a.veredicto]));
  const desdeVisita = vistos ? S.data.acciones.filter(a => !a.error && vistos[a.ticker] && vistos[a.ticker] !== a.veredicto) : [];
  store.set("vistos", hoy);
  const lin = a => `<b>${tk(a.ticker)}</b>: de ${esc((SIG[a.veredicto_ant] || SIG.MANTENER)[2].toLowerCase())} a ${esc(a.decision.toLowerCase())}`;
  const nombre = (a, v) => (SIG[v] || SIG.MANTENER)[2].toLowerCase();
  let html = "";
  if (cambios.length) html += `<div class="alerta">${ICON("wait")}<div><b>Cambió la decisión en la última sesión</b><p>${cambios.map(lin).join("; ")}.</p></div></div>`;
  if (desdeVisita.length) html += `<div class="alerta">${ICON("wait")}<div><b>Desde tu última visita</b><p>${desdeVisita.map(a => `<b>${tk(a.ticker)}</b>: de ${nombre(a, vistos[a.ticker])} a ${nombre(a, a.veredicto)}`).join("; ")}.</p></div></div>`;
  $("#alertas").innerHTML = html;
}
async function cargarCambios() {
  try {
    await cargarHistorial();
    const R = S.hist.registros, lista = [];
    for (let i = R.length - 1; i >= 0 && lista.length < 10; i--) for (const e of R[i].emisoras) if (e.cambio) lista.push([R[i].fecha, e]);
    $("#histCambios").innerHTML = lista.length ? lista.map(([f, e]) => `<div class="cambio"><span class="f">${flarga(f)}</span><span class="t">${esc(e.ticker)}</span>
      <span class="flecha">${esc((SIG[e.veredicto_ant] || SIG.MANTENER)[2])} ${ICON("chevron")} ${sig(e.veredicto)}</span></div>`).join("") : '<p class="note">Aún no hay cambios de decisión registrados.</p>';
  } catch { $("#histCambios").innerHTML = '<p class="note">El archivo de decisiones aún no está disponible.</p>'; }
}

/* ------------------------------------------------------------------- simulación */
async function renderSimulacion() {
  if (!S.sim) { $("#simTexto").textContent = "Calculando la simulación…"; S.sim = await api(`/api/simulacion?desde=${desde()}`); }
  const s = S.sim, m = s.metricas;
  if (!s.fechas.length) { $("#simTexto").textContent = s.error || "No hay datos suficientes."; return; }
  const peso = n => "$" + fmt(n), ink = css("--ink"), acc = css("--s2");
  $("#simTexto").textContent = `Con ${peso(s.capital)} repartidos en partes iguales entre las 5 emisoras, desde ${fhumana(s.fechas[0])}: seguir las decisiones de Pizarra terminó en ${pct(m.ret_estrategia)} y comprar y mantener en ${pct(m.ret_comprar_mantener)}.`;
  $("#legSim").innerHTML = `<span style="--c:${ink}"><i></i>Siguiendo las decisiones de Pizarra</span><span style="--c:${acc}"><i class="d"></i>Comprar y mantener</span>`;
  const o = opts({ fy: v => fmt(v, 2), ftip: v => peso(v), right: 8, title: it => flarga(s.fechas[it[0].dataIndex]) });
  mk("chSim", { type: "line", data: { labels: s.fechas.map(fcorta), datasets: [linea("Pizarra", s.estrategia, ink, { w: 2.4 }), linea("Comprar y mantener", s.comprar_mantener, acc, { w: 2, borderDash: [6, 4] })] }, options: o });
  $("#tblSim").innerHTML = `<thead><tr><th>Medida</th><th>Pizarra</th><th>Comprar y mantener</th></tr></thead><tbody>
    <tr><td>Rendimiento del periodo</td><td class="${cls(m.ret_estrategia)}"><b>${pct(m.ret_estrategia)}</b></td><td class="${cls(m.ret_comprar_mantener)}"><b>${pct(m.ret_comprar_mantener)}</b></td></tr>
    <tr><td>Valor final</td><td>${peso(s.estrategia.at(-1))}</td><td>${peso(s.comprar_mantener.at(-1))}</td></tr>
    <tr><td>Caída máxima</td><td class="down">${pct(m.caida_estrategia)}</td><td class="down">${pct(m.caida_comprar_mantener)}</td></tr>
    <tr><td>Operaciones</td><td>${m.operaciones}</td><td>1 por emisora</td></tr></tbody>`;
  $("#tblSimEm").innerHTML = `<thead><tr><th>Emisora</th><th>Pizarra</th><th>Comprar y mantener</th><th>Operaciones</th><th>Tiempo invertido</th></tr></thead><tbody>` +
    s.por_emisora.map(p => `<tr><td><b>${tk(p.ticker)}</b></td><td class="${cls(p.ret_estrategia)}">${pct(p.ret_estrategia)}</td><td class="${cls(p.ret_comprar_mantener)}">${pct(p.ret_comprar_mantener)}</td><td>${p.operaciones}</td><td>${fmt(p.tiempo_en_mercado)}%</td></tr>`).join("") + "</tbody>";
  $("#simAviso").textContent = `Reglas: se compra cuando el puntaje llega a +20 o más y se sale a efectivo cuando baja a -20 o menos; la decisión de un día se ejecuta al cierre del día siguiente y cada operación paga ${fmt(s.costo_pct)}% de comisión. Es una prueba dentro de la misma muestra, sin impuestos ni deslizamiento, con fines educativos; no constituye asesoría financiera y el resultado pasado no garantiza resultados futuros.`;
}
