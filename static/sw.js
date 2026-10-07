/* Uso sin internet: guarda la aplicación y cada respuesta de datos que se consulta; sin conexión se muestra lo último guardado. */
const VERSION = "v1";
const APP = `app-${VERSION}`, DATOS = `datos-${VERSION}`;
const PRECARGA = ["/", "/static/alzea.css", "/static/alzea.js", "/static/vendor/chart.umd.min.js", "/static/manifest.webmanifest", "/static/icon.svg", "/static/icon-180.png", "/static/icon-512.png",
  "/static/marca/ipn-escudo-blanco.png", "/static/marca/ese-escudo.png", "/static/marca/marca.svg",
  "/static/fonts/Barlow-Regular.ttf", "/static/fonts/Barlow-Medium.ttf", "/static/fonts/Barlow-SemiBold.ttf", "/static/fonts/Barlow-Bold.ttf", "/static/fonts/Barlow-Italic.ttf", "/static/fonts/BarlowSemiCondensed-Bold.ttf"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(APP).then(c => Promise.allSettled(PRECARGA.map(u => c.add(new Request(u, { cache: "reload" }))))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => ![APP, DATOS].includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// la clave de caché ignora parámetros que solo sirven para pedir datos frescos
function clave(url) {
  const u = new URL(url);
  ["fresco", "t"].forEach(p => u.searchParams.delete(p));
  return u.pathname + (u.searchParams.toString() ? "?" + u.searchParams.toString() : "");
}
async function conMarca(resp, extra) {
  const h = new Headers(resp.headers);
  Object.entries(extra).forEach(([k, v]) => h.set(k, v));
  return new Response(await resp.blob(), { status: resp.status, statusText: resp.statusText, headers: h });
}

self.addEventListener("fetch", e => {
  const r = e.request;
  if (r.method !== "GET") return;
  const url = new URL(r.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) {
    e.respondWith((async () => {
      const cache = await caches.open(DATOS), k = clave(r.url);
      try {
        const resp = await fetch(r);
        if (resp.ok) await cache.put(k, await conMarca(resp.clone(), { "X-Guardado": String(Date.now()) }));
        return resp;
      } catch {
        const g = await cache.match(k);
        if (g) return conMarca(g, { "X-Desde-Cache": "1" });
        return new Response(JSON.stringify({ error: "Sin conexión y sin datos guardados de esta consulta. Conéctate una vez para guardarla." }), { status: 503, headers: { "Content-Type": "application/json; charset=utf-8" } });
      }
    })());
    return;
  }
  // aplicación: primero la red (siempre la versión más nueva) y, sin internet, lo guardado
  e.respondWith((async () => {
    const cache = await caches.open(APP), k = url.pathname === "/" || url.pathname === "/index.html" ? "/" : url.pathname;
    try {
      const resp = await fetch(r);
      if (resp.ok) cache.put(k, resp.clone());
      return resp;
    } catch {
      return (await cache.match(k)) || (r.mode === "navigate" ? await cache.match("/") : undefined) || Response.error();
    }
  })());
});
