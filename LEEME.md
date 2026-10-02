# Pizarra · Bolsa y deuda de México

Tablero web con 5 acciones de la BMV y 5 instrumentos de deuda gubernamental: precio, variación, tendencia, estadística, señal técnica, comparación de cierres y un análisis archivado por día.

**Dirección pública:** https://monitor-mercado-alpha.vercel.app (alojada en Vercel, gratis; el código está en `github.com/EdwinACM/monitor-mercado` y cada `git push` a `main` la vuelve a publicar).

## Verla en el celular
Abre la dirección en Safari o Chrome. Para tenerla como app: iPhone, Compartir y «Agregar a pantalla de inicio»; Android, menú del navegador y «Agregar a la pantalla principal».

## Secciones
| Sección | Contenido |
|---|---|
| **Mercado** | Tablero de cotizaciones (los dígitos giran cuando un precio cambia). Al elegir una fila: gráfica con medias móviles y bandas de Bollinger (o el día en intervalos de 5 min), señal con el desglose por criterio, estadística, RSI y MACD, análisis del día y prueba histórica de la señal. |
| **Comparar** | Rendimiento base 100, cierres en dos fechas, ranking, correlación y tabla de cierres lado a lado. |
| **Deuda** | Tablero de instrumentos, rendimiento por subasta con promedio móvil y lectura. |
| **Archivo** | Mapa de señales por día, consulta de cualquier día y descarga en Excel, CSV o JSON. |

## Actualización automática
La app se actualiza sola mientras la BMV está abierta: precios cada 20 segundos y señales cada 2 minutos. Con la bolsa cerrada revisa cada 15 minutos. El botón «En vivo» pausa o reanuda; el botón de flechas actualiza de inmediato. Los precios vienen de Yahoo Finance y pueden tener un retraso de 15 a 20 minutos; la deuda solo cambia cuando hay subasta semanal (Banxico).

## Cómo se calcula la señal (educativa, no es asesoría financiera)
Seis criterios con puntos (máx. ±100): tendencia por medias móviles (±20), MACD (±15), RSI (±20), bandas de Bollinger (±15), momentum a 20 sesiones (±10) y regresión lineal de 30 sesiones (±15, solo si R² ≥ 0.5).
Puntaje ≥ +45 compra fuerte · ≥ +20 comprar · entre −20 y +20 mantener · ≤ −20 vender · ≤ −45 venta fuerte.
La prueba histórica muestra qué pasó 10 sesiones después de cada señal para calibrar la confianza.
Deuda: compara el rendimiento de la última subasta con el promedio de las últimas 12 (puntaje z) y su pendiente.

## Análisis diario guardado
`analisis_diario.py` guarda cada día en `static/data/`: `analisis_diario.json`, `analisis_acciones.csv`, `analisis_deuda.csv`, `analisis_diario.xlsx` y `diario/AAAA-MM-DD.md`.
**Guardado automático (pendiente de activar):** el proceso `.github/workflows/analisis-diario.yml` lo ejecutaría cada día hábil a las 16:00 (CDMX) y Vercel republicaría la app. GitHub exige el permiso `workflow`: ejecutar `gh auth refresh -h github.com -s workflow`, autorizar en el navegador y luego `git add .github && git commit -m "Activar análisis diario" && git push`.
Mientras tanto el archivo trae el historial hasta el 2 de octubre de 2026; para agregar días: `python analisis_diario.py`, luego `git add static/data && git commit && git push`.

## Archivos
- `server.py`: consulta las fuentes. Emisoras y bonos por defecto: `ACCIONES` y `DEUDA` al inicio.
- `analisis.py`: indicadores, estadística, señales, comparación y análisis de deuda (solo biblioteca estándar).
- `analisis_diario.py`: genera los archivos de análisis diario.
- `api/*.py`: funciones de Vercel (`/api/analisis`, `/api/comparar`, `/api/cotizaciones`, …).
- `static/`: interfaz (`index.html`, `pizarra.css`, `pizarra.js`), logo (`icon.svg`, `icon-180.png`, `icon-512.png`) y `data/`.
- `PRODUCT.md` y `DESIGN.md`: contexto del producto y decisiones de diseño (paleta, tipografía, logo).
- Opcional en la Mac: `iniciar.command` abre una copia local en `http://localhost:8765` (solo tu equipo); se cierra con Ctrl+C.
