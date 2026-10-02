"use strict";
/* Monitor de Mercado — interfaz. Los cálculos viven en el servidor (analisis.py); aquí solo se muestra. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sin almacenamiento */ } },
};
const fmt = (n, d = 2) => (n == null || Number.isNaN(n)) ? "—" : n.toLocaleString("es-MX", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (n, d = 2) => n == null ? "—" : (n > 0 ? "+" : "") + n.toFixed(d) + "%";
const sgn = n => n > 0 ? "up" : n < 0 ? "down" : "flat";
const arrow = n => n > 0 ? "▲" : n < 0 ? "▼" : "●";
const fcorta = s => { const [, m, d] = s.split("-"); return `${+d} ${MESES[+m - 1]}`; };
const flarga = s => { const [y, m, d] = s.split("-"); return `${d}/${m}/${y}`; };
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const alpha = (hex, a) => { const n = parseInt(hex.replace("#", ""), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`; };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const serie = i => css("--s" + (i % 8 + 1));
const tk = t => t.replace(".MX", "");

const ICONOS = {
  panel: '<path d="M4 5h7v7H4zM13 5h7v4h-7zM13 11h7v8h-7zM4 14h7v5H4z"/>',
  analisis: '<path d="M3 17l5-6 4 4 8-9"/><path d="M3 21h18"/>',
  comparar: '<path d="M3 8l5 4 5-6 8 5"/><path d="M3 18l5-3 5 2 8-5"/>',
  deuda: '<path d="M4 20h16M6 20V10M12 20V6M18 20v-8"/><path d="M4 8l8-4 8 4"/>',
  historial: '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
};
const TABS = [["panel", "Panel"], ["analisis", "Análisis"], ["comparar", "Comparar"], ["deuda", "Deuda"], ["historial", "Historial"]];

const S = { data: null, cmp: null, hist: null, sel: null, selCmp: new Set(), selD: 0, tab: "panel", rango: 0,
  vivo: store.get("vivo", false), quotes: {}, nTick: 0, charts: {}, fechaDia: null };

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
const sigClase = v => v?.startsWith("VEN") ? "sell" : v?.startsWith("COMPR") ? "buy" : v === "ESPERAR" ? "wait" : "hold";
const SIG_ICO = { "COMPRA FUERTE": "▲▲", COMPRAR: "▲", MANTENER: "●", VENDER: "▼", "VENTA FUERTE": "▼▼", ESPERAR: "◔", "SIN DATOS": "–" };
const chip = (v, lg) => `<span class="chip ${sigClase(v)}${lg ? " lg" : ""}"><span aria-hidden="true">${SIG_ICO[v] || "●"}</span>${esc(v)}</span>`;
const pinLeft = s => `${Math.max(0, Math.min(100, (s + 100) / 2))}%`;

/* ------------------------------------------------------------------- gráficas */
const crosshair = { id: "crosshair", afterDatasetsDraw(ch) {
  const a = ch.tooltip?._active; if (!a?.length) return;
  const { ctx, chartArea: { top, bottom } } = ch, x = a[0].element.x;
  ctx.save(); ctx.strokeStyle = css("--axis"); ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke(); ctx.restore();
} };
const endLabels = { id: "endLabels", afterDatasetsDraw(ch, _, o) {
  if (!o?.on) return;
  const { ctx, chartArea } = ch, items = [];
  ch.data.datasets.forEach((ds, i) => {
    if (!ds.endLabel || ch.getDatasetMeta(i).hidden) return;
    const pts = ch.getDatasetMeta(i).data; let k = pts.length - 1;
    while (k >= 0 && ds.data[k] == null) k--;
    if (k >= 0) items.push({ y: pts[k].y, x: pts[k].x, text: ds.endLabel, color: ds.borderColor });
  });
  items.sort((a, b) => a.y - b.y);
  for (let i = 1; i < items.length; i++) if (items[i].y - items[i - 1].y < 15) items[i].y = items[i - 1].y + 15;
  ctx.save(); ctx.font = `600 11px ${css("--f-mono")}`; ctx.textBaseline = "middle";
  items.forEach(it => { ctx.fillStyle = it.color; ctx.beginPath(); ctx.arc(it.x + 7, it.y, 3.5, 0, 7); ctx.fill();
    ctx.fillStyle = css("--ink-2"); ctx.fillText(it.text, it.x + 15, it.y); });
  ctx.restore();
} };
const baseline = { id: "baseline", afterDatasetsDraw(ch, _, o) {
  if (o?.valor == null) return;
  const y = ch.scales.y.getPixelForValue(o.valor), { ctx, chartArea: { left, right } } = ch;
  ctx.save(); ctx.strokeStyle = css("--ink-2"); ctx.lineWidth = 1; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke(); ctx.restore();
} };
Chart.register(crosshair, endLabels, baseline);

function mk(id, cfg) {
  S.charts[id]?.destroy();
  const el = document.getElementById(id) || id;
  S.charts[id] = new Chart(el, cfg);
  return S.charts[id];
}
function opts({ fy = v => fmt(v), ftip, min, max, step, right = 8, labels, extra } = {}) {
  return {
    responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
    layout: { padding: { right } },
    plugins: { legend: { display: false }, endLabels: { on: false }, baseline: {},
      tooltip: { backgroundColor: css("--surface"), titleColor: css("--ink-2"), bodyColor: css("--ink"), borderColor: css("--line"), borderWidth: 1,
        padding: 10, boxPadding: 4, usePointStyle: true, titleFont: { family: css("--f-mono"), size: 11 }, bodyFont: { family: css("--f-ui"), size: 12 },
        filter: it => it.dataset.tip !== false, callbacks: { label: c => ` ${c.dataset.label}: ${(ftip || fy)(c.parsed.y)}` } },
      ...(extra || {}) },
    scales: {
      x: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--muted"), maxTicksLimit: 6, maxRotation: 0, font: { family: css("--f-mono"), size: 10 } } },
      y: { min, max, grid: { color: css("--grid") }, border: { display: false }, ticks: { color: css("--muted"), callback: fy, stepSize: step, font: { family: css("--f-mono"), size: 10 } } },
    },
  };
}
const linea = (label, data, color, o = {}) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: o.w ?? 2, pointRadius: o.pr ?? 0,
  pointHoverRadius: 4, tension: .15, spanGaps: true, fill: false, ...o });

/* ------------------------------------------------------------------ navegación */
function renderTabs() {
  $("#tabs").innerHTML = TABS.map(([id, t]) => `<button class="tab" role="tab" data-tab="${id}" aria-selected="false"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONOS[id]}</svg>${t}</button>`).join("");
  $$(".tab").forEach(b => b.onclick = () => mostrar(b.dataset.tab));
}
async function mostrar(tab) {
  S.tab = tab; location.hash = tab;
  $$(".tab").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  $$(".view").forEach(v => v.hidden = v.id !== "v-" + tab);
  window.scrollTo({ top: 0 });
  try { await dibujar(); } catch (e) { showErr(e.message); }
}
async function dibujar() {
  showErr("");
  if (S.tab === "comparar") await cargarComparar();
  if (S.tab === "historial") await cargarHistorial();
  if (!S.data) return;
  ({ panel: renderPanel, analisis: renderAnalisis, comparar: renderComparar, deuda: renderDeuda, historial: renderHistorial })[S.tab]();
}

/* ----------------------------------------------------------------------- datos */
async function cargar(fresco) {
  const d = await api(`/api/analisis?desde=${desde()}${fresco ? "&fresco=1" : ""}`);
  S.data = d;
  const tks = d.acciones.map(a => a.ticker);
  if (!S.sel || !tks.includes(S.sel)) S.sel = tks[0];
  if (!S.selCmp.size) tks.forEach(t => S.selCmp.add(t));
  $("#hasta").textContent = new Date(d.ahora).toLocaleDateString("es-MX", { timeZone: "America/Mexico_City" });
  $("#ult").textContent = "Actualizado " + new Date().toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
  renderEstado();
}
function renderEstado() {
  const ab = abiertoNY(), a = S.data?.acciones.find(x => !x.error);
  $("#estado").className = "pill" + (ab ? " abierto" : "");
  $("#estadoTxt").textContent = ab ? "BMV abierta" : "BMV cerrada" + (a ? " · cierre " + fcorta(a.fecha) : "");
  $("#vivoNota").textContent = S.vivo ? (ab ? "En vivo · se consulta cada 30 s (posible retraso de Yahoo)" : "Bolsa cerrada · se revisará cada 5 min") : "";
}
async function actualizar(fresco = true) {
  const b = $("#btnAct"); b.disabled = true; b.textContent = "Actualizando…"; showErr("");
  try {
    S.cmp = null; S.hist = null;
    await cargar(fresco);
    await dibujar();
  } catch (e) { showErr("No se pudo actualizar: " + e.message); }
  b.disabled = false; b.textContent = "Actualizar";
}

/* ------------------------------------------------------------------------ panel */
function renderPanel() {
  const d = S.data, m = d.mercado, ok = d.acciones.filter(a => !a.error);
  $("#heroTexto").textContent = m.texto;
  const s = m.senales || {};
  $("#heroStats").innerHTML = [["suben", m.suben, "up"], ["bajan", m.bajan, "down"], ["señales de compra", s.COMPRAR || 0, "up"], ["mantener", s.MANTENER || 0, "flat"], ["señales de venta", s.VENDER || 0, "down"]]
    .map(([l, v, c]) => `<div class="stat"><div class="v ${c}">${v}</div><div class="l">${l}</div></div>`).join("");
  $("#meter .pin").style.left = pinLeft(m.puntaje_promedio || 0);
  $("#meterTxt").textContent = `Puntaje promedio ${m.puntaje_promedio >= 0 ? "+" : ""}${m.puntaje_promedio ?? 0}: sesgo ${m.sesgo}. Combina tendencia, impulso, RSI, Bollinger, momentum y regresión de ${ok.length} emisoras.`;
  S.charts.sparks?.forEach(c => c.destroy());
  $("#cards").innerHTML = d.acciones.map((a, i) => a.error
    ? `<div class="card stock" style="--c:${serie(i)}"><div class="tk">${tk(a.ticker)}</div><p class="note">Sin datos: ${esc(a.error)}</p></div>`
    : `<button class="card stock" data-t="${a.ticker}" style="--c:var(--s${i % 8 + 1});--i:${i}" aria-label="Analizar ${esc(a.nombre)}">
        <div class="r1"><span class="tk">${tk(a.ticker)}</span>${chip(a.veredicto)}</div>
        <div class="nm">${esc(a.nombre)}</div>
        <div class="px" data-px>$${fmt(a.cierre)}</div>
        <div class="dv"><span data-dv class="${sgn(a.var)}">${arrow(a.var)} ${fmt(Math.abs(a.var))} (${pct(a.var_pct)})</span><span class="flat">20 ses. ${pct(a.ret20, 1)}</span></div>
        <canvas aria-hidden="true"></canvas>
        <div class="sc"><span>Puntaje ${a.score > 0 ? "+" : ""}${a.score}</span><span>${a.tendencia.etiqueta}</span></div></button>`).join("");
  S.charts.sparks = $$("#cards .stock").map((el, i) => { const a = d.acciones.find(x => x.ticker === el.dataset.t);
    const v = a.serie.cierre.slice(-40); const c = el.querySelector("canvas");
    return new Chart(c, { type: "line", data: { labels: v.map((_, k) => k), datasets: [{ data: v, borderColor: v.at(-1) >= v[0] ? css("--up") : css("--down"), borderWidth: 1.7, pointRadius: 0, tension: .25 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, events: [], plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { display: false }, y: { display: false } } } }); });
  $$("#cards .stock[data-t]").forEach(el => el.onclick = () => { S.sel = el.dataset.t; mostrar("analisis"); });
  $("#cardsDeuda").innerHTML = d.deuda.map(tarjetaDeuda).join("");
  $$("#cardsDeuda .stock").forEach(el => el.onclick = () => { S.selD = +el.dataset.d; mostrar("deuda"); });
  aplicarCotizaciones(false);
}
const valDeuda = x => x.valor == null ? "—" : x.tipo === "precio" ? "$" + fmt(x.valor, 5) : fmt(x.valor) + (x.unidad.startsWith("%") ? "%" : " pp");
function tarjetaDeuda(x, i) {
  const v = x.var_pb != null ? `${arrow(x.var_pb)} ${Math.abs(x.var_pb).toFixed(0)} pb` : (x.var != null ? `${arrow(x.var)} ${Math.abs(x.var).toFixed(5)}` : "—");
  return `<button class="card stock" data-d="${i}" style="--c:var(--s${i % 8 + 1});--i:${i}" aria-label="Ver ${esc(x.nombre)}">
    <div class="r1"><span class="tk">${esc(x.nombre.split(" ").slice(0, 2).join(" "))}</span>${chip(x.senal)}</div>
    <div class="nm">${esc(x.emisor)} · ${esc(x.nombre)}</div>
    <div class="px">${valDeuda(x)}</div>
    <div class="dv"><span class="${sgn(x.var_pb ?? x.var)}">${v} vs. previa</span></div>
    <div class="sc"><span>z ${x.z != null ? (x.z > 0 ? "+" : "") + x.z : "—"}</span><span>tendencia ${esc(x.tendencia)}</span></div></button>`;
}

/* --------------------------------------------------------------------- en vivo */
function aplicarCotizaciones(flash = true) {
  $$("#cards .stock[data-t]").forEach(el => {
    const q = S.quotes[el.dataset.t], a = S.data.acciones.find(x => x.ticker === el.dataset.t);
    if (!q || q.error || q.precio == null || !a) return;
    const v = q.precio - a.previo, p = (q.precio / a.previo - 1) * 100;
    const px = el.querySelector("[data-px]"), prev = px.dataset.v ? +px.dataset.v : null;
    px.textContent = "$" + fmt(q.precio); px.dataset.v = q.precio;
    const dv = el.querySelector("[data-dv]"); dv.className = sgn(v); dv.textContent = `${arrow(v)} ${fmt(Math.abs(v))} (${pct(p)})`;
    if (flash && prev != null && prev !== q.precio) { px.classList.remove("flash-up", "flash-down"); void px.offsetWidth; px.classList.add(q.precio > prev ? "flash-up" : "flash-down"); }
  });
}
async function tickVivo() {
  clearTimeout(S.tv);
  if (!S.vivo) return;
  const ab = abiertoNY();
  if (!document.hidden && S.data) {
    try {
      const qs = await api(`/api/cotizaciones?tickers=${S.data.acciones.map(a => a.ticker).join(",")}`);
      S.quotes = Object.fromEntries(qs.map(q => [q.ticker, q]));
      aplicarCotizaciones(ab);
      if (ab && ++S.nTick % 10 === 0) { await cargar(true); S.tab === "panel" ? renderPanel() : S.tab === "analisis" && renderAnalisis(); }
      $("#ult").textContent = "Cotizado " + new Date().toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch (e) { showErr("En vivo: " + e.message); }
  }
  renderEstado();
  S.tv = setTimeout(tickVivo, ab ? 30000 : 300000);
}
function setVivo(on) {
  S.vivo = on; store.set("vivo", on);
  $("#btnVivo").setAttribute("aria-pressed", on);
  renderEstado();
  if (on) tickVivo(); else clearTimeout(S.tv);
}

/* --------------------------------------------------------------------- análisis */
function renderAnalisis() {
  const d = S.data, a = d.acciones.find(x => x.ticker === S.sel && !x.error) || d.acciones.find(x => !x.error);
  if (!a) return;
  const idx = d.acciones.findIndex(x => x.ticker === a.ticker), col = serie(idx);
  $("#selAnalisis").innerHTML = d.acciones.map((x, i) => `<button class="sel" style="--c:${serie(i)}" data-t="${x.ticker}" aria-pressed="${x.ticker === a.ticker}"><i></i>${tk(x.ticker)}</button>`).join("");
  $$("#selAnalisis .sel").forEach(b => b.onclick = () => { S.sel = b.dataset.t; renderAnalisis(); });
  const k = sigClase(a.veredicto);
  $("#veredicto").innerHTML = `<p class="kicker">${esc(a.nombre)} · ${tk(a.ticker)} · ${flarga(a.fecha)}</p>
    <div class="big ${k}">${esc(a.veredicto)}</div>
    <p class="meta">Puntaje <b class="num">${a.score > 0 ? "+" : ""}${a.score}</b> de ±100 · confianza <b>${a.confianza.toLowerCase()}</b> · tendencia <b>${a.tendencia.etiqueta}</b></p>
    <div class="meter"><span class="pin" style="left:${pinLeft(a.score)}"></span></div>
    <div class="meter-l"><span>Vender</span><span>Mantener</span><span>Comprar</span></div>
    <p class="note" style="margin-top:12px">Señal técnica educativa, no asesoría financiera. Cada criterio suma o resta puntos; los umbrales son ±20 (comprar / vender) y ±45 (señal fuerte).</p>`;
  $("#comp").innerHTML = a.componentes.map(c => { const w = Math.abs(c.puntos) / c.max * 50, pos = c.puntos >= 0;
    return `<div class="row"><div class="nm">${esc(c.criterio)}</div><div class="bar"><i style="left:${pos ? 50 : 50 - w}%;width:${w}%;background:var(${c.puntos === 0 ? "--axis" : pos ? "--up" : "--down"})"></i></div><div class="pt ${sgn(c.puntos)}">${c.puntos > 0 ? "+" : ""}${c.puntos}</div><div class="dt">${esc(c.detalle)}</div></div>`; }).join("");
  const s = a.stats, kp = (l, v, sub, c) => `<div class="kpi"><div class="l">${l}</div><div class="v ${c || ""}">${v}</div><div class="s">${sub || "&nbsp;"}</div></div>`;
  $("#kpis").innerHTML = [
    kp("Cierre", "$" + fmt(a.cierre), `${arrow(a.var)} ${fmt(Math.abs(a.var))} (${pct(a.var_pct)})`, sgn(a.var)),
    kp("5 sesiones", pct(a.ret5, 1), "", sgn(a.ret5)), kp("20 sesiones", pct(a.ret20, 1), "", sgn(a.ret20)), kp("Periodo", pct(a.ret_periodo, 1), "desde " + flarga(desde()), sgn(a.ret_periodo)),
    kp("RSI (14)", a.rsi == null ? "—" : a.rsi.toFixed(0), a.rsi < 30 ? "sobreventa" : a.rsi > 70 ? "sobrecompra" : "zona neutral"),
    kp("Volatilidad anual", s.vol_anual == null ? "—" : s.vol_anual.toFixed(1) + "%", "desv. estándar × √252"),
    kp("Caída máxima", pct(s.max_drawdown, 1), "últimas 120 sesiones", "down"),
    kp("Soporte / resistencia", `${fmt(s.soporte)} · ${fmt(s.resistencia)}`, "mín. y máx. de 20 sesiones"),
    kp("Rend. / riesgo", s.ratio_rend_riesgo == null ? "—" : s.ratio_rend_riesgo.toFixed(2), "anualizado, sin tasa libre", sgn(s.ratio_rend_riesgo)),
    kp("Z del precio", (s.z_precio > 0 ? "+" : "") + s.z_precio, "desviaciones vs. media de 20"),
    kp("Tendencia 30 ses.", a.tendencia.pendiente == null ? "—" : pct(a.tendencia.pendiente, 2) + "/día", "R² " + (a.tendencia.r2 ?? "—"), sgn(a.tendencia.pendiente)),
    kp("Volumen relativo", s.vol_relativo == null ? "—" : s.vol_relativo.toFixed(1) + "×", "vs. promedio de 20"),
  ].join("");
  $("#tituloGrafica").textContent = `${a.nombre}`;
  graficaPrecio(a, col);
  $("#textoDia").innerHTML = `<p>${esc(a.texto)}</p>`;
  const b = a.backtest, n = b.muestra;
  const fila = (t, nn, ac, r, ok) => nn < 8 ? `<p class="note">${t}: pocas señales (${nn}) para evaluar.</p>` :
    `<div style="margin-bottom:14px"><div style="display:flex;justify-content:space-between;font-weight:600"><span>${t} <span class="note">(${nn} casos)</span></span><span class="num ${ok ? "up" : "down"}">${ac}% de aciertos</span></div>
     <div class="bar" style="margin:8px 0 4px"><i style="left:0;width:${ac}%;background:var(${ok ? "--up" : "--down"})"></i></div>
     <p class="note">A ${b.horizonte} sesiones el rendimiento medio fue <b class="num">${pct(r)}</b> (todas las sesiones: ${pct(b.base_rend_medio)}). ${ok ? "Evidencia a favor en este historial." : "Sin evidencia a favor: tómala con cautela."}</p></div>`;
  $("#backtest").innerHTML = fila("Señales de compra", b.n_compra, b.aciertos_compra, b.rend_medio_compra, b.aciertos_compra >= 55 && b.rend_medio_compra > b.base_rend_medio) +
    fila("Señales de venta", b.n_venta, b.aciertos_venta, b.rend_medio_venta, b.aciertos_venta >= 55 && b.rend_medio_venta < b.base_rend_medio) +
    `<p class="note">Prueba sobre ${n} sesiones del mismo historial (dentro de muestra): calibra la confianza, no la garantiza.</p>`;
  $("#btnMd").onclick = () => descargarMd(a);
}
function graficaPrecio(a, col) {
  const sr = a.serie, n = S.rango, ini = n ? Math.max(0, sr.fechas.length - n) : 0, sl = arr => arr.slice(ini);
  const L = sl(sr.fechas), medias = $("#chkMedias").checked, bandas = $("#chkBandas").checked, ds = [];
  if (bandas) {
    ds.push({ label: "Banda sup.", data: sl(sr.bb_up), borderColor: alpha(css("--ink-2").replace(/^#?/, "#"), .35), borderWidth: 1, pointRadius: 0, fill: "+1", backgroundColor: alpha(col, .10), tip: false });
    ds.push({ label: "Banda inf.", data: sl(sr.bb_low), borderColor: alpha(css("--ink-2").replace(/^#?/, "#"), .35), borderWidth: 1, pointRadius: 0, fill: false, tip: false });
  }
  ds.push(linea("Cierre", sl(sr.cierre), col, { w: 2.2, endLabel: "Cierre" }));
  if (medias) { ds.push(linea("Media 20", sl(sr.sma20), css("--ink-2"), { w: 1.4, borderDash: [6, 4], endLabel: "SMA20" }));
    ds.push(linea("Media 50", sl(sr.sma50), css("--muted"), { w: 1.6, borderDash: [2, 3], endLabel: "SMA50" })); }
  const o = opts({ fy: v => fmt(v), ftip: v => "$" + fmt(v), right: 64, extra: { endLabels: { on: true } } });
  o.plugins.tooltip.callbacks.title = it => flarga(L[it[0].dataIndex]);
  mk("chPrecio", { type: "line", data: { labels: L.map(fcorta), datasets: ds }, options: o });
  $("#legAnalisis").innerHTML = `<span style="--c:${col}"><i></i>Cierre</span>` + (medias ? `<span style="--c:${css("--ink-2")}"><i class="d"></i>Media 20</span><span style="--c:${css("--muted")}"><i class="t"></i>Media 50</span>` : "") + (bandas ? `<span style="--c:${col}"><i class="f"></i>Bollinger (20, 2σ)</span>` : "");
  const lo = css("--grid");
  const orsi = opts({ fy: v => v, ftip: v => v?.toFixed(0), min: 0, max: 100, step: 20 });
  orsi.plugins.tooltip.callbacks.title = it => flarga(L[it[0].dataIndex]);
  mk("chRsi", { type: "line", data: { labels: L.map(fcorta), datasets: [linea("RSI", sl(sr.rsi), col, { w: 1.8 }),
    linea("70", L.map(() => 70), css("--down"), { w: 1, borderDash: [4, 4], tip: false }), linea("30", L.map(() => 30), css("--up"), { w: 1, borderDash: [4, 4], tip: false })] }, options: orsi });
  const h = sl(sr.hist), om = opts({ fy: v => fmt(v, 2), ftip: v => fmt(v, 3) });
  om.plugins.tooltip.callbacks.title = it => flarga(L[it[0].dataIndex]);
  mk("chMacd", { type: "bar", data: { labels: L.map(fcorta), datasets: [
    { type: "bar", label: "Histograma", data: h, backgroundColor: h.map(v => alpha(v >= 0 ? hexOf("--up") : hexOf("--down"), .55)), borderWidth: 0, barPercentage: 1, categoryPercentage: 1 },
    linea("MACD", sl(sr.macd), col, { type: "line", w: 1.6 }), linea("Señal", sl(sr.macd_signal), css("--ink-2"), { type: "line", w: 1.2, borderDash: [4, 3] })] }, options: om });
}
const hexOf = v => { const c = css(v); return c.startsWith("#") ? c : "#888888"; };
function descargarMd(a) {
  const L = [`# ${a.nombre} (${tk(a.ticker)}) — análisis del ${a.fecha}`, "", a.texto, "", `## Señal: ${a.veredicto} (puntaje ${a.score}/100, confianza ${a.confianza})`, "",
    "| Criterio | Puntos | Detalle |", "|---|---:|---|", ...a.componentes.map(c => `| ${c.criterio} | ${c.puntos} | ${c.detalle} |`), "",
    "## Estadística", "", `- Volatilidad anual: ${a.stats.vol_anual}%`, `- Caída máxima (120 ses.): ${a.stats.max_drawdown}%`, `- Soporte/resistencia (20 ses.): ${a.stats.soporte} / ${a.stats.resistencia}`,
    `- Rendimiento/riesgo anualizado: ${a.stats.ratio_rend_riesgo}`, "", "_Herramienta educativa; no constituye asesoría financiera._", ""];
  const url = URL.createObjectURL(new Blob([L.join("\n")], { type: "text/markdown;charset=utf-8" }));
  Object.assign(document.createElement("a"), { href: url, download: `analisis_${tk(a.ticker)}_${a.fecha}.md` }).click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/* --------------------------------------------------------------------- comparar */
async function cargarComparar() {
  if (!S.data) await cargar(false);
  const tks = [...S.selCmp];
  const clave = tks.join(",") + desde();
  if (S.cmp?.clave === clave) return;
  if (tks.length < 2) return;
  S.cmp = { ...(await api(`/api/comparar?desde=${desde()}&tickers=${tks.join(",")}`)), clave };
}
function renderComparar() {
  const d = S.data;
  $("#selComparar").innerHTML = d.acciones.map((x, i) => `<button class="sel" style="--c:${serie(i)}" data-t="${x.ticker}" aria-pressed="${S.selCmp.has(x.ticker)}"><i></i>${tk(x.ticker)}</button>`).join("");
  $$("#selComparar .sel").forEach(b => b.onclick = async () => {
    const t = b.dataset.t;
    if (S.selCmp.has(t)) { if (S.selCmp.size <= 2) return; S.selCmp.delete(t); } else S.selCmp.add(t);
    try { await cargarComparar(); renderComparar(); } catch (e) { showErr(e.message); }
  });
  const c = S.cmp; if (!c || !c.fechas.length) return;
  const nom = t => d.acciones.find(a => a.ticker === t)?.nombre || t, colr = t => serie(d.acciones.findIndex(a => a.ticker === t));
  const L = c.fechas, tks = Object.keys(c.base100);
  const o = opts({ fy: v => v.toFixed(0), ftip: v => v.toFixed(1), right: 104, extra: { endLabels: { on: true }, baseline: { valor: 100 } } });
  o.plugins.tooltip.callbacks.title = it => flarga(L[it[0].dataIndex]);
  mk("chComparar", { type: "line", data: { labels: L.map(fcorta), datasets: tks.map(t => linea(tk(t), c.base100[t], colr(t), { w: 2, endLabel: `${tk(t)} ${c.base100[t].at(-1).toFixed(0)}` })) }, options: o });
  $("#legComparar").innerHTML = tks.map(t => `<span style="--c:${colr(t)}"><i></i>${esc(nom(t))}</span>`).join("");

  // consulta de cierres por fecha
  const fa = $("#fechaA"), fb = $("#fechaB");
  fa.min = fb.min = L[0]; fa.max = fb.max = L.at(-1);
  if (!fa.value || fa.value < L[0] || fa.value > L.at(-1)) fa.value = L[0];
  if (!fb.value || fb.value < L[0] || fb.value > L.at(-1)) fb.value = L.at(-1);
  const pos = f => { let k = -1; L.forEach((x, i) => { if (x <= f) k = i; }); return k; };
  const tabla = () => {
    const ia = pos(fa.value), ib = pos(fb.value);
    if (ia < 0 || ib < 0) { $("#tblConsulta").innerHTML = "<tr><td>Elige fechas dentro del periodo.</td></tr>"; return; }
    const filas = tks.map(t => { const a = c.cierres[t][ia], b = c.cierres[t][ib]; return { t, a, b, dv: b - a, dp: (b / a - 1) * 100 }; });
    const mejor = Math.max(...filas.map(f => f.dp)), peor = Math.min(...filas.map(f => f.dp));
    $("#tblConsulta").innerHTML = `<thead><tr><th>Emisora</th><th>${fcorta(L[ia])}</th><th>${fcorta(L[ib])}</th><th>Cambio $</th><th>Cambio %</th><th></th></tr></thead><tbody>` +
      filas.map(f => `<tr><td><b>${tk(f.t)}</b> <small class="note">${esc(nom(f.t))}</small></td><td>$${fmt(f.a)}</td><td>$${fmt(f.b)}</td><td class="${sgn(f.dv)}">${arrow(f.dv)} ${fmt(Math.abs(f.dv))}</td><td class="${sgn(f.dp)}"><b>${pct(f.dp)}</b></td><td>${f.dp === mejor ? "★ mejor" : f.dp === peor ? "peor" : ""}</td></tr>`).join("") + "</tbody>";
  };
  fa.onchange = fb.onchange = tabla; tabla();
  $$("#atajos button").forEach(b => b.onclick = () => { const u = L.length - 1;
    fb.value = L[u]; fa.value = b.dataset.a === "ini" ? L[0] : L[Math.max(0, u - (b.dataset.a === "sem" ? 5 : 21))]; tabla(); });

  $("#tblRanking").innerHTML = `<thead><tr><th>#</th><th>Emisora</th><th>Rend.</th><th>Vol.</th><th>R/R</th><th>Caída máx.</th><th>Días ↑</th></tr></thead><tbody>` +
    [...c.ranking].sort((a, b) => b.ret - a.ret).map((r, i) => `<tr><td>${i + 1}</td><td><b>${tk(r.ticker)}</b></td><td class="${sgn(r.ret)}"><b>${pct(r.ret, 1)}</b></td><td>${r.vol_anual.toFixed(0)}%</td><td>${r.ratio ?? "—"}</td><td class="down">${r.max_drawdown.toFixed(1)}%</td><td>${r.dias_alza}%</td></tr>`).join("") + "</tbody>";
  const m = c.corr.matriz, n = c.corr.tickers.length, g = $("#heat");
  g.style.gridTemplateColumns = `auto repeat(${n},minmax(0,1fr))`;
  g.innerHTML = `<div class="h"></div>` + c.corr.tickers.map(t => `<div class="h">${tk(t)}</div>`).join("") +
    m.map((row, i) => `<div class="h" style="text-align:right">${tk(c.corr.tickers[i])}</div>` + row.map(v => {
      const base = v >= 0 ? "--s1" : "--s8", w = Math.round(Math.abs(v) * 75);
      return `<div style="background:color-mix(in srgb,var(${base}) ${w}%,var(--surface-2));color:${w > 45 ? "#fff" : "var(--ink)"}">${v.toFixed(2)}</div>`; }).join("")).join("");
  const filasC = L.map((f, i) => `<tr><td>${flarga(f)}</td>` + tks.map(t => { const v = c.cierres[t][i], p = i ? (v / c.cierres[t][i - 1] - 1) * 100 : null;
    return `<td>${fmt(v)}${p == null ? "" : `<small class="${sgn(p)}">${pct(p)}</small>`}</td>`; }).join("") + "</tr>");
  $("#tblCierres").innerHTML = `<thead><tr><th>Fecha</th>${tks.map(t => `<th>${tk(t)}</th>`).join("")}</tr></thead><tbody>${filasC.reverse().join("")}</tbody>`;
}

/* ------------------------------------------------------------------------ deuda */
function renderDeuda() {
  const d = S.data;
  $("#cardsDeuda2").innerHTML = d.deuda.map(tarjetaDeuda).join("");
  $$("#cardsDeuda2 .stock").forEach(el => el.onclick = () => { S.selD = +el.dataset.d; renderDeuda(); });
  const x = d.deuda[S.selD]; if (!x) return;
  const es = x.tipo === "tasa", col = serie(S.selD), v = x.datos.map(r => r.valor);
  const ma = v.map((_, i) => i >= 3 ? v.slice(i - 3, i + 1).reduce((a, b) => a + b, 0) / 4 : null);
  $("#deuKicker").textContent = `${x.emisor} · ${x.unidad}`;
  $("#deuTitulo").textContent = x.nombre;
  $("#legDeuda").innerHTML = `<span style="--c:${col}"><i></i>${es ? "Rendimiento" : "Precio"} en cada subasta</span><span style="--c:${css("--ink-2")}"><i class="d"></i>Promedio móvil (4 subastas)</span>`;
  const o = opts({ fy: n => es ? n.toFixed(2) : n.toFixed(3), ftip: n => es ? n.toFixed(2) + (x.unidad.startsWith("%") ? "%" : " pp") : "$" + n.toFixed(5), right: 72, extra: { endLabels: { on: true } } });
  o.plugins.tooltip.callbacks.title = it => flarga(x.datos[it[0].dataIndex].fecha);
  mk("chDeuda", { type: "line", data: { labels: x.datos.map(r => fcorta(r.fecha)), datasets: [
    linea(es ? "Rendimiento" : "Precio", v, col, { w: 2.2, pr: 3, endLabel: valDeuda(x) }), linea("Prom. móvil", ma, css("--ink-2"), { w: 1.4, borderDash: [6, 4] })] }, options: o });
  $("#deuLectura").innerHTML = `${chip(x.senal, true)}<p class="prose" style="margin-top:12px"><span>${esc(x.texto)}</span></p>
    <p class="note" style="margin-top:12px">Z: cuántas desviaciones estándar está el dato frente al promedio de las últimas 12 subastas. Pendiente: regresión lineal de las últimas 8 subastas. Si las tasas suben, el precio de los bonos ya emitidos baja.</p>`;
  $("#tblDeuda").innerHTML = `<thead><tr><th>Fecha subasta</th><th>${es ? "Tasa" : "Precio"}</th><th>${es ? "Cambio (pb)" : "Cambio $"}</th></tr></thead><tbody>` +
    [...x.datos].reverse().map(r => `<tr><td>${flarga(r.fecha)}</td><td><b>${es ? fmt(r.valor) : fmt(r.valor, 5)}</b></td><td class="${sgn(es ? r.var_pb : r.var)}">${es ? (r.var_pb == null ? "—" : (r.var_pb > 0 ? "+" : "") + r.var_pb.toFixed(0)) : (r.var == null ? "—" : (r.var > 0 ? "+" : "") + r.var.toFixed(5))}</td></tr>`).join("") + "</tbody>";
}

/* --------------------------------------------------------------------- historial */
async function cargarHistorial() {
  if (S.hist) return;
  const r = await fetch("/static/data/analisis_diario.json", { cache: "no-cache" });
  if (!r.ok) throw new Error("Aún no hay análisis guardados.");
  S.hist = await r.json();
  S.fechaDia = S.hist.registros.at(-1)?.fecha;
}
const VCLS = { "COMPRA FUERTE": "v-buy2", COMPRAR: "v-buy", MANTENER: "v-hold", VENDER: "v-sell", "VENTA FUERTE": "v-sell2" };
function renderHistorial() {
  const h = S.hist; if (!h) return;
  const R = h.registros, a = R[0], z = R.at(-1);
  $("#histResumen").textContent = `${R.length} análisis diarios guardados, del ${flarga(a.fecha)} al ${flarga(z.fecha)}. Último: ${z.mercado.texto}`;
  const base = "/static/data/";
  $("#descargas").innerHTML = [["analisis_diario.xlsx", "Excel completo"], ["analisis_acciones.csv", "CSV acciones"], ["analisis_deuda.csv", "CSV deuda"], ["analisis_diario.json", "JSON"]]
    .map(([f, t]) => `<a class="btn" href="${base}${f}" download>${t}</a>`).join("");
  $("#legTl").innerHTML = Object.entries(VCLS).map(([k, c]) => `<span style="display:inline-flex;gap:6px;align-items:center"><i class="${c}" style="width:12px;height:12px;border-radius:3px;display:inline-block"></i>${k.toLowerCase()}</span>`).join("");
  const tks = [...new Set(R.flatMap(r => r.emisoras.map(e => e.ticker)))];
  $("#timeline").innerHTML = tks.map(t => `<div class="tl-row"><b>${t}</b><div class="tl-cells">` + R.map(r => { const e = r.emisoras.find(x => x.ticker === t);
    return e ? `<button class="${VCLS[e.veredicto]}" data-f="${r.fecha}" title="${flarga(r.fecha)} · ${e.veredicto} (${e.score})" aria-label="${t} ${r.fecha} ${e.veredicto}" aria-current="${r.fecha === S.fechaDia}"></button>` : `<button disabled style="background:transparent"></button>`; }).join("") + "</div></div>").join("") +
    `<div class="tl-row"><b></b><div class="note" style="width:${R.length * 11}px;display:flex;justify-content:space-between"><span>${fcorta(a.fecha)}</span><span>${fcorta(z.fecha)}</span></div></div>`;
  $("#timeline").scrollLeft = 1e6;
  $$("#timeline button[data-f]").forEach(b => b.onclick = () => { S.fechaDia = b.dataset.f; renderHistorial(); });
  const sel = $("#diaSel"); sel.min = a.fecha; sel.max = z.fecha; sel.value = S.fechaDia;
  sel.onchange = () => { const f = [...R].reverse().find(r => r.fecha <= sel.value); S.fechaDia = (f || a).fecha; renderHistorial(); };
  const ix = R.findIndex(r => r.fecha === S.fechaDia);
  $("#diaPrev").onclick = () => { if (ix > 0) { S.fechaDia = R[ix - 1].fecha; renderHistorial(); } };
  $("#diaNext").onclick = () => { if (ix < R.length - 1) { S.fechaDia = R[ix + 1].fecha; renderHistorial(); } };
  const r = R[ix]; $("#diaTitulo").textContent = flarga(r.fecha);
  $("#diaDetalle").innerHTML = `<p class="prose"><span>${esc(r.mercado.texto)}</span></p>
    <div class="tablewrap" style="margin-top:14px;max-height:none"><table><thead><tr><th>Emisora</th><th>Cierre</th><th>Var. %</th><th>Tendencia</th><th>RSI</th><th>Señal</th><th>Puntaje</th></tr></thead><tbody>` +
    r.emisoras.map(e => `<tr><td><b>${e.ticker}</b></td><td>$${fmt(e.cierre)}</td><td class="${sgn(e.var_pct)}">${pct(e.var_pct)}</td><td>${e.tendencia}</td><td>${e.rsi == null ? "—" : Math.round(e.rsi)}</td><td>${chip(e.veredicto)}</td><td>${e.score > 0 ? "+" : ""}${e.score}</td></tr>`).join("") + `</tbody></table></div>` +
    `<div style="margin-top:14px">` + r.emisoras.map(e => `<div class="day-item"><div class="t">${esc(e.nombre)}</div><p class="note" style="font-size:13.5px">${esc(e.texto)}</p></div>`).join("") + `</div>` +
    `<p class="kicker" style="margin-top:16px">Deuda gubernamental</p>` + r.deuda.map(x => `<div class="day-item"><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span class="t" style="margin:0">${esc(x.nombre)}</span>${chip(x.senal)}</div><p class="note" style="font-size:13.5px;margin-top:4px">${esc(x.texto)}</p></div>`).join("");
}

/* -------------------------------------------------------------------- arranque */
function tema() {
  const act = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const sig = act === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = sig; store.set("tema", sig);
  if (S.data) dibujar();
}
function init() {
  const t = store.get("tema", null); if (t) document.documentElement.dataset.theme = t;
  renderTabs();
  const hash = location.hash.slice(1);
  const inicial = TABS.some(([id]) => id === hash) ? hash : "panel";
  $("#btnAct").onclick = () => actualizar(true);
  $("#btnTema").onclick = tema;
  $("#btnVivo").onclick = () => setVivo(!S.vivo);
  $("#desde").onchange = () => actualizar(false);
  $$("#rango button").forEach(b => b.onclick = () => { S.rango = +b.dataset.r; $$("#rango button").forEach(x => x.setAttribute("aria-pressed", x === b)); if (S.data) renderAnalisis(); });
  $("#chkMedias").onchange = $("#chkBandas").onchange = () => S.data && renderAnalisis();
  addEventListener("hashchange", () => { const h = location.hash.slice(1); if (TABS.some(([id]) => id === h) && h !== S.tab) mostrar(h); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && S.vivo) tickVivo(); });
  setInterval(renderEstado, 60000);
  $("#cards").innerHTML = Array(5).fill('<div class="skeleton"></div>').join("");
  mostrar(inicial).then(async () => {
    try { if (!S.data) { await cargar(false); await dibujar(); } } catch (e) { showErr("No se pudo cargar: " + e.message); }
    $("#btnVivo").setAttribute("aria-pressed", S.vivo);
    if (S.vivo) tickVivo();
  });
}
init();
