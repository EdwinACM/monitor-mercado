# Monitor de Mercado

Tablero web con 5 acciones de la BMV y 5 instrumentos de deuda. Los datos se consultan al abrir la página y cada vez que tocas **Actualizar**.

## Verla en el celular (Android o iPhone)
Dirección pública: **https://monitor-mercado-alpha.vercel.app**

Ábrela en el navegador del celular. Para tenerla como app:
- iPhone (Safari): Compartir → **Agregar a pantalla de inicio**.
- Android (Chrome): menú ⋮ → **Agregar a la pantalla principal**.

La app corre en Vercel (nube): no necesita que la Mac esté encendida. Cada `git push` a `main` del repositorio `github.com/EdwinACM/monitor-mercado` la vuelve a publicar sola.

## Verla en la Mac (opcional)
No hace falta: la app vive en la nube. Si quieres probar cambios, `iniciar.command` abre `http://localhost:8765` (solo tu equipo) y se cierra con Ctrl+C.

## Qué hace la app
| Pestaña | Contenido |
|---|---|
| **Panel** | Lectura del día, termómetro técnico del mercado, tarjetas con precio, variación, señal y mini-gráfica. |
| **Análisis** | Por emisora: señal (comprar / mantener / vender) con su desglose por criterio, indicadores estadísticos, gráfica con medias móviles y bandas de Bollinger, RSI, MACD, prueba histórica de la señal y el análisis del día (descargable en .md). |
| **Comparar** | Rendimiento base 100, consulta de cierres por fecha (A vs. B), ranking, correlación y tabla de cierres lado a lado. |
| **Deuda** | Rendimiento por subasta con promedio móvil, z-score, tendencia y señal. |
| **Historial** | Análisis diarios guardados (mapa de señales, consulta por día, descarga en Excel / CSV / JSON). |

- **En vivo**: consulta precios cada 30 s mientras la BMV está abierta (Yahoo puede tener retraso de 15–20 min).
- **Actualizar**: vuelve a consultar Yahoo Finance y Banxico.

## Cómo se calcula la señal (educativa, no es asesoría financiera)
Seis criterios con puntos (máx. ±100): tendencia por medias móviles (±20), MACD (±15), RSI (±20), bandas de Bollinger (±15), momentum a 20 sesiones (±10) y regresión lineal de 30 sesiones (±15, solo si R² ≥ 0.5).
Puntaje ≥ +45 compra fuerte · ≥ +20 comprar · entre −20 y +20 mantener · ≤ −20 vender · ≤ −45 venta fuerte.
La app muestra también una prueba histórica (¿qué pasó 10 sesiones después de cada señal?) para calibrar cuánto confiar en ella.
Deuda: compara el rendimiento de la última subasta con el promedio de las últimas 12 (z-score) y su pendiente.

## Análisis diario guardado
`analisis_diario.py` guarda cada día en `static/data/`: `analisis_diario.json`, `analisis_acciones.csv`, `analisis_deuda.csv`, `analisis_diario.xlsx` y `diario/AAAA-MM-DD.md`.
**Guardado automático (pendiente de activar):** el proceso `.github/workflows/analisis-diario.yml` ejecutaría esto cada día hábil a las 16:00 (CDMX), guardaría los archivos en el repositorio y Vercel republicaría la app. Para activarlo, GitHub exige el permiso `workflow`: ejecutar `gh auth refresh -h github.com -s workflow`, autorizar en el navegador y luego `git add .github && git commit -m "Activar análisis diario" && git push`.
Mientras tanto el archivo trae el historial completo hasta el 2 de octubre de 2026; para agregar días: `python analisis_diario.py`, luego `git add static/data && git commit && git push`.
Manual: `python analisis_diario.py` (agrega los días que falten) o `python analisis_diario.py --desde 2026-03-02` (reconstruye).

## De dónde salen los datos
| Dato | Fuente | Cuándo cambia |
|---|---|---|
| Acciones (cierre, apertura, máx., mín., volumen, intradía 5 min) | Yahoo Finance | Durante la sesión de la BMV (retraso aprox. 15–20 min) |
| CETES 28 d, Bondes F 2a, Udibonos 10a, Bonos M 10a | Banxico SIE, cuadro CF107 | Subasta semanal |
| BPAG28 (IPAB) | Banxico SIE, cuadro CF115 | Subasta semanal |

## Funciones
- **Actualizar**: vuelve a consultar Yahoo y Banxico en ese momento.
- **Desde**: cambia el inicio del periodo; el final siempre es hoy.
- **Agregar**: cualquier emisora (p. ej. `BIMBOA`, `GFNORTEO`); se agrega `.MX` sola.
- **Excel**: descarga el periodo (resumen + una hoja por instrumento).

## Archivos
- `server.py`: consulta las fuentes. Emisoras y bonos por defecto: `ACCIONES` y `DEUDA` al inicio.
- `analisis.py`: indicadores, estadística, señales, comparación y análisis de deuda (solo biblioteca estándar).
- `analisis_diario.py`: genera los archivos de análisis diario.
- `api/*.py`: funciones de Vercel (`/api/analisis`, `/api/comparar`, `/api/cotizaciones`, …).
- `static/`: la interfaz (`index.html`, `app.css`, `app.js`) y `data/` con el archivo diario.
