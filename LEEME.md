# Alzea · Mercados, deuda y entorno global

Seminario de Titulación 2026 · Escuela Superior de Economía · Instituto Politécnico Nacional.

App web con 10 acciones (BMV, Nasdaq y NYSE) y 7 instrumentos de deuda: precio, estadística de riesgo, **decisión de comprar, mantener o vender con su justificación y respaldo estadístico**, proyecciones, entorno global con fuentes oficiales, comparación, simulación e informes en PDF y Excel por periodo.

**Dirección pública:** https://monitor-mercado-alpha.vercel.app (Vercel, gratis; código en `github.com/EdwinACM/monitor-mercado`; cada `git push` a `main` la publica de nuevo en 1 o 2 minutos).

## Qué incluye
- **Acciones (10):** Walmart de México, América Móvil, Coca-Cola FEMSA, Kimberly-Clark de México, OMA, Apple, Microsoft, Nvidia, Tesla y Coca-Cola (KO).
- **Deuda (7):** CETES 28 días, Bonos M 10 años, Udibonos 10 años, Bondes F 2 años, BPAG28 3 años, papel comercial y certificados bursátiles.
- **Periodo:** toda consulta empieza el 1 de marzo de 2026 o después (chips por mes, últimos 7 y 30 días, o fechas libres).

## Secciones
| Sección | Contenido |
|---|---|
| **Mercado** | Cotizaciones por mercado y, al elegir una fila: gráfica con medias móviles y bandas de Bollinger, decisión con su porqué, respaldo estadístico y riesgos, qué es la emisora, estadística de riesgo, proyección de precio, relación con EE. UU. y el dólar, RSI y MACD, prueba histórica y cambios de decisión. |
| **Entorno** | Dólar (FIX), bolsas del mundo, tasas de México y EE. UU., inflación, VIX, diferenciales, sensibilidad de cada acción al S&P 500 y al dólar, y guía de qué es cada cosa, con la fuente (oficial o de referencia). |
| **Deuda** | Rendimiento por subasta, qué es cada instrumento, proyección de la próxima tasa, sensibilidad del precio a las tasas (duración) y detalle mensual de papel comercial y certificados. |
| **Comparar** | Rendimiento base 100, cierres en dos fechas, ranking, correlación, portafolio equiponderado y de mínima varianza, y simulación (acciones de EE. UU. en pesos con el tipo de cambio de Banxico). |
| **Informe** | Tabla en vivo, descargas, aciertos de las decisiones, mapa de decisiones por día y análisis de cualquier día. |

## Informes
En **Informe** hay PDF y Excel del periodo elegido y de cualquier día. Se generan al momento con los datos más recientes y llevan formato IPN.
- **PDF:** resumen, entorno global, tablero de cierres y decisiones, una ficha por emisora e instrumento (cierre, gráfica, estadística, proyección, justificación), portafolio, aciertos, simulación, anexo y fuentes.
- **Excel:** una hoja por emisora e instrumento, columna «Qué significa» en cada medida, hoja «Léeme» con índice y cifras con dos decimales.
- Nombres: `Informe_de_mercados_AAAA-MM-DD_a_AAAA-MM-DD.pdf` y `Analisis_del_dia_AAAA-MM-DD.xlsx`.

## Sin internet
La app guarda en el dispositivo sus pantallas, tipografías y cada consulta que haces. Sin conexión muestra lo último guardado con un aviso. En **Informe**, «Guardar para ver sin internet» guarda de una vez todas las secciones del periodo y los informes. Un PDF o Excel solo se abre sin conexión si ya lo descargaste o guardaste.

## Cómo se decide (educativo, no es asesoría financiera)
Nueve señales técnicas: reversión semanal y de un día, RSI, bandas de Bollinger, momentum de 20, 60 y 120 sesiones, tendencia frente a la media de 50 sesiones y MACD. **El peso de cada señal se recalcula todos los días** con la correlación que tuvo, en las últimas 250 sesiones de las 10 emisoras, con el rendimiento a 5 sesiones; solo usa resultados ya conocidos ese día, y si una señal funcionó al revés se invierte. El puntaje va de −100 a +100: desde +20 comprar (desde +45, señal fuerte), entre −20 y +20 mantener, desde −20 vender (desde −45, señal fuerte).
Cada decisión muestra el puntaje contra el umbral, cada señal con su valor y correlación, el **respaldo estadístico** (qué pasó tras señales parecidas) y **qué podría hacerla fallar**.
**Aciertos medidos día por día desde el 1 de marzo (1,475 decisiones, sin ver el futuro): 49.9 %** (vender 57.1 %, comprar 50.7 %, mantener 45.7 %, señales fuertes 58.5 %). Es una ventaja pequeña: úsalo como método explicable y no como promesa de rendimiento.
Acierto a 5 sesiones: comprar acierta si el precio subió; vender, si bajó; mantener, si se movió 2.00 % o menos. En deuda se compara el rendimiento de la última subasta con el promedio de las últimas 12 (puntaje z) y su pendiente.

## Proyecciones y estadística
- **Proyección de precio** a 5, 20 y 60 sesiones: rangos de 68 % y 95 % con volatilidad EWMA (factor 0.94) y escenario de tendencia; se contrasta con cuántas veces el rango contuvo el precio real en las últimas 250 sesiones.
- **Riesgo:** volatilidad, caída máxima, VaR y CVaR al 95 %, mejor y peor día, soporte y resistencia.
- **Rendimiento ajustado por riesgo:** razones de Sharpe y Sortino, alfa y beta (CAPM) frente al S&P 500 o al IPC, R², asimetría y VaR a 20 sesiones.
- **Deuda:** proyección de la próxima subasta (recta con intervalo de predicción de 95 %) y duración modificada.
- **Portafolio:** volatilidad del portafolio equiponderado frente al de mínima varianza y razón de diversificación.
Todo son rangos de probabilidad, no pronósticos.

## Estado de la bolsa y actualización
«Bolsa abierta / cerrada» se calcula con el reloj y el horario real de la BMV y de Nueva York y no lo modifica ningún botón. Con la bolsa abierta la app se actualiza sola (precios cada 20 s, decisiones cada 5 min); cerrada, revisa cada 15 min. El botón **Auto** solo pausa o reanuda la actualización. Las consultas de periodos pasados no se actualizan en vivo.

## Fuentes
Oficiales: Banco de México (SIE), Departamento del Tesoro de EE. UU., Reserva Federal de Nueva York, BLS y Cboe; reportes de empresas en SEC EDGAR y la BMV. Referencia (no oficial): Yahoo Finance para precios de acciones e índices.

## Análisis diario guardado
`python analisis_diario.py --desde 2026-03-02` guarda en `static/data/`: `analisis_diario.json` (lo lee la sección Informe), `analisis_acciones.csv`, `analisis_deuda.csv` (encabezados legibles) y `diario/AAAA-MM-DD.md`.
Automático: `.github/workflows/analisis-diario.yml` lo ejecuta cada día hábil a las 16:00 (CDMX) y Vercel republica la app. Subir ese archivo requiere el permiso `workflow` de GitHub: `gh auth refresh -h github.com -s workflow`, autorizar en el navegador y `git add .github && git commit -m "Activar análisis diario" && git push`.

## Seguridad
La app solo muestra datos públicos y no tiene cuentas. Todo parámetro se valida (fechas, claves de emisoras); los servidores a los que consulta están fijos; los errores no exponen detalles internos; hay cabeceras `Content-Security-Policy`, `X-Frame-Options`, `nosniff` y `Referrer-Policy`. Auditoría con la skill `security-review`: sin hallazgos graves.

## Archivos
- `server.py`: consulta las fuentes y atiende las rutas `/api/*`.
- `analisis.py`: indicadores, estadística, decisiones, comparación, deuda y simulación.
- `modelo.py`: modelo de decisión con pesos diarios (validación hacia adelante).
- `proyeccion.py`: proyecciones, Sharpe, Sortino, CAPM, portafolio y duración.
- `contexto.py` y `fuentes.py`: entorno global con fuentes oficiales; `glosario.py`: qué es cada cosa.
- `diario.py`, `reportes.py` y `excel.py`: registro diario, PDF y Excel.
- `analisis_diario.py`: archivos de análisis diario.
- `api/index.py`: única función de Vercel (el plan Hobby permite 12).
- `static/`: interfaz (`index.html`, `alzea.css`, `alzea.js`), `sw.js` (uso sin internet), `fonts/`, `vendor/`, `marca/` y `data/`.
- `PRODUCT.md` y `DESIGN.md`: contexto del producto y decisiones de diseño.
- Opcional en la Mac: `iniciar.command` abre una copia local en `http://localhost:8765`.
