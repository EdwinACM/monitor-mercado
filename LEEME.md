# Atalaya · Bolsa y deuda de México

App web con 5 acciones de la BMV y 5 instrumentos de deuda gubernamental: precio, variación, tendencia, estadística, **decisión de comprar, mantener o vender con su porqué**, comparación de cierres, simulación y un análisis archivado por día.

**Dirección pública:** https://monitor-mercado-alpha.vercel.app (alojada en Vercel, gratis; el código está en `github.com/EdwinACM/monitor-mercado` y cada `git push` a `main` la vuelve a publicar).

## Verla en el celular
Abre la dirección en Safari o Chrome. Para tenerla como app: iPhone, Compartir y «Agregar a pantalla de inicio»; Android, menú del navegador y «Agregar a la pantalla principal».

## Secciones
| Sección | Contenido |
|---|---|
| **Mercado** | Cotizaciones (los dígitos giran cuando un precio cambia), alertas de cambio de decisión y, al elegir una fila: gráfica, decisión del día con su porqué y qué hacer, estadística, RSI y MACD, prueba histórica de la señal y últimos cambios de decisión. |
| **Comparar** | Rendimiento base 100.00, cierres en dos fechas, ranking, correlación y tabla de cierres lado a lado. |
| **Deuda** | Instrumentos, rendimiento por subasta con promedio móvil y lectura. |
| **Simulación** | Qué habría pasado siguiendo las decisiones contra comprar y mantener (con comisión de 0.20 % y ejecución al cierre siguiente). |
| **Archivo** | ¿Acertaron las decisiones?, mapa de decisiones por día y consulta de cualquier día con descarga. |

## Descargar el análisis de un día
En **Mercado** (día más reciente) y en **Archivo** (cualquier día) hay botones **PDF** y **Excel**. Cada reporte trae, para las 5 emisoras y la deuda: la decisión (comprar, mantener o vender), **por qué** (criterios a favor y en contra, con puntos), qué hacer si tenías o no la acción y **qué pasó después** (rendimiento a 5 y 10 sesiones y si acertó). Los textos van justificados y los valores con dos decimales.
Archivo completo en Excel, CSV y JSON desde la sección **Archivo**.

## Temas de color
Botón del sol en la barra superior: **Claro** (abre por defecto), **Mixto** (panel de cotizaciones oscuro sobre página clara) y **Oscuro**. Contrastes verificados con WCAG en los tres (ver `DESIGN.md`).

## Estado de la bolsa y actualización automática
«Bolsa abierta / cerrada» se calcula con el reloj y el horario real de la BMV y **no lo modifica ningún botón**. Con la bolsa abierta la app se actualiza sola (precios cada 20 s, decisiones cada 2 min); cerrada, revisa cada 15 min. El botón **Auto** solo pausa o reanuda esa actualización. Los precios vienen de Yahoo Finance y pueden tener 15 a 20 minutos de retraso; la deuda cambia con la subasta semanal (Banxico).

## Cómo se decide (educativo, no es asesoría financiera)
Seis criterios con puntos (máx. ±100): tendencia por medias móviles (±20), MACD (±15), RSI (±20), bandas de Bollinger (±15), momentum a 20 sesiones (±10) y regresión lineal de 30 sesiones (±15, solo si R² ≥ 0.5).
Puntaje ≥ +20 comprar (≥ +45 señal fuerte) · entre -20 y +20 mantener · ≤ -20 vender (≤ -45 señal fuerte).
Acierto a 5 sesiones: comprar acierta si el precio subió; vender, si bajó; mantener, si se movió 2.00 % o menos.
**Resultado en el historial (2 de marzo al 2 de octubre de 2026, 720 decisiones evaluadas): aciertos de 50.14 %, es decir, sin ventaja clara sobre el azar.** Úsalo así en la tesina: como método explicable y no como promesa de rendimiento.
Deuda: compara el rendimiento de la última subasta con el promedio de las últimas 12 (puntaje z) y su pendiente.

## Análisis diario guardado
`analisis_diario.py` guarda cada día en `static/data/`: `analisis_diario.json`, `analisis_acciones.csv`, `analisis_deuda.csv`, `analisis_diario.xlsx` y `diario/AAAA-MM-DD.md`.
**Guardado automático (pendiente de activar):** el proceso `.github/workflows/analisis-diario.yml` lo ejecutaría cada día hábil a las 16:00 (CDMX) y Vercel republicaría la app. GitHub exige el permiso `workflow`: ejecutar `gh auth refresh -h github.com -s workflow`, autorizar en el navegador y luego `git add .github && git commit -m "Activar análisis diario" && git push`.
Mientras tanto, para agregar días: `python analisis_diario.py`, luego `git add static/data && git commit && git push`. Los reportes PDF y Excel de cualquier día se generan al momento, sin depender de ese proceso.

## Logo
Kit en `static/marca/` (torre isométrica de tres columnas que ascienden con un farol ámbar, sin letras): `marca.svg`, `marca-fondo-oscuro.svg`, `logo-horizontal.svg`, `logo-horizontal-fondo-oscuro.svg` y `logo-vertical.svg` (nombre convertido a trazos desde Barlow Semi Condensed Bold, licencia OFL). Íconos de la app: `static/icon.svg`, `icon-180.png`, `icon-512.png`.

## Archivos
- `server.py`: consulta las fuentes y atiende las rutas `/api/*`.
- `analisis.py`: indicadores, estadística, decisiones y porqué, comparación, deuda y simulación (solo biblioteca estándar).
- `diario.py`: registro de un día con decisión, porqué y resultados posteriores.
- `reportes.py`: PDF, Excel y Markdown del día.
- `analisis_diario.py`: genera los archivos de análisis diario.
- `api/*.py`: funciones de Vercel (`analisis`, `comparar`, `cotizaciones`, `dia`, `simulacion`, …).
- `static/`: interfaz (`index.html`, `atalaya.css`, `atalaya.js`), logo y `data/`.
- `PRODUCT.md` y `DESIGN.md`: contexto del producto y decisiones de diseño.
- Opcional en la Mac: `iniciar.command` abre una copia local en `http://localhost:8765` (solo tu equipo); se cierra con Ctrl+C.
