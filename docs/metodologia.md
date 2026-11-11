# Metodología

Este documento explica cómo calcula Alzea sus decisiones, proyecciones y medidas de riesgo. El código está en `modelo.py`, `analisis.py` y `proyeccion.py`.

## Decisión de comprar, mantener o vender

### Señales

Cada sesión, cada emisora recibe nueve señales técnicas. Todas son positivas cuando favorecen comprar.

- Reversión semanal, a partir del rendimiento de cinco sesiones.
- Reversión de un día.
- RSI de 14 sesiones (sobrecompra y sobreventa).
- Posición en las bandas de Bollinger.
- Momentum de 20, 60 y 120 sesiones.
- Tendencia frente a la media de 50 sesiones.
- Histograma MACD.

### Pesos que se recalculan cada día

No todas las señales funcionan en todos los periodos. En algunos los precios se revierten en una semana y en otros siguen la tendencia. Por eso el peso de cada señal se calcula con la correlación que tuvo en las últimas 250 sesiones de las 10 emisoras en conjunto, frente al rendimiento que ocurrió cinco sesiones después.

Se usan solo observaciones cuyo resultado ya se conocía ese día. Se deja un margen de siete sesiones para que el resultado a cinco sesiones ya sea conocido en todos los mercados. Una señal solo cuenta si su correlación es de al menos 0.03 y, si funcionó al revés, se invierte. Se necesitan al menos 100 sesiones para calibrar y 120 sesiones previas para calcular las señales.

### Puntaje

Las señales se combinan con esos pesos y el resultado se escala con su desviación estándar reciente. El puntaje va de menos 100 a 100.

- Desde 20: comprar. Desde 45: comprar con señal fuerte.
- Entre menos 20 y 20: mantener.
- Desde menos 20: vender. Desde menos 45: vender con señal fuerte.

El 20 equivale a unas 0.6 desviaciones por encima de lo normal y el 45 a unas 1.35. Si ninguna señal tuvo poder predictivo reciente, el puntaje es 0 y la decisión es mantener.

Cada decisión muestra el puntaje contra el umbral, cada señal con su valor y su correlación, el respaldo estadístico (qué pasó tras señales parecidas) y qué podría hacerla fallar.

### Cómo se mide el acierto

Se evalúa día por día, sin ver el futuro, a cinco sesiones. Comprar acierta si el precio subió, vender si bajó, y mantener si el precio se movió 2% o menos. La sección Informe muestra la cifra al día. En deuda se compara el rendimiento de la última subasta con el promedio de las últimas 12 (puntaje z) y su pendiente.

## Proyecciones

- **Precio a 5, 20 y 60 sesiones.** Rangos de 68% y 95% con rendimientos logarítmicos normales. La volatilidad se estima con un promedio móvil exponencial (EWMA, factor 0.94, método RiskMetrics) que da más peso a lo reciente. Cada rango se contrasta con cuántas veces contuvo el precio real en las últimas 250 sesiones, y esa cobertura se muestra al lado.
- **Próxima subasta de deuda.** Recta ajustada a las últimas 12 cifras con intervalo de predicción de 95%.

Las proyecciones son rangos de probabilidad, no pronósticos de lo que va a pasar.

## Medidas de riesgo y rendimiento

- Volatilidad, caída máxima, VaR y CVaR al 95%, mejor y peor día, soporte y resistencia.
- Razones de Sharpe y Sortino, alfa y beta (CAPM) frente al S&P 500 o al IPC, R², asimetría y VaR a 20 sesiones.
- Duración modificada de la deuda: CETES con su plazo, Bonos M y Udibonos como bono a la par con cupón semestral, y Bondes y BPAG con 28 días por ser de tasa flotante.
- Portafolio: volatilidad del equiponderado frente al de mínima varianza (sin ventas en corto) y razón de diversificación.

## Estado de la bolsa y actualización

El indicador de bolsa abierta o cerrada se calcula con el reloj y el horario real de la BMV y de Nueva York. Con la bolsa abierta la app se actualiza sola (precios cada 20 segundos y decisiones cada 5 minutos). Cerrada, revisa cada 15 minutos. Las consultas de periodos pasados no se actualizan en vivo.

## Informes

En la sección Informe hay PDF y Excel del periodo elegido y de cualquier día.

- El PDF incluye resumen, entorno global, tablero de cierres y decisiones, una ficha por emisora e instrumento, portafolio, aciertos, simulación, anexo y fuentes.
- El Excel tiene una hoja por emisora e instrumento, una columna que explica qué significa cada medida y una hoja con índice.

## Análisis diario

`python analisis_diario.py --desde 2026-03-02` guarda en `static/data/` el análisis del día en JSON, en CSV y en Markdown. La acción de GitHub lo ejecuta cada día hábil y Vercel republica la app con los archivos nuevos.
