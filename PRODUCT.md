# Product

<!-- impeccable:product-schema 1 -->

## Platform

web (instalable, con modo sin internet)

## Users
Edwin Cruz, estudiante del Seminario de Titulación 2026 (Escuela Superior de Economía, IPN; tesina «Comportamiento Fintech México 2021-2026»), y su asesor y profesores, que revisan el trabajo. Lo consultan en celular (iOS y Android) y en computadora con la misma frecuencia: revisión rápida en el día y análisis más largo al preparar la tesina o una exposición.

## Product Purpose
Seguir 10 acciones (5 de la Bolsa Mexicana de Valores y 5 de EE. UU.: Apple, Microsoft, Nvidia, Tesla y Coca-Cola) y 7 instrumentos de deuda (CETES, Bonos M, Udibonos, Bondes F, BPAG28, papel comercial y certificados bursátiles). Mostrar precio, variación, tendencia, estadística de riesgo y proyecciones; explicar qué es cada instrumento y cómo lo afectan el dólar, las tasas y los mercados del exterior, sobre todo el de EE. UU., con fuentes oficiales; proponer una decisión (comprar, mantener o vender) con su justificación y respaldo estadístico; y entregar informes por periodo y por día en PDF y Excel. Éxito: que el asesor entienda la lectura del mercado en segundos y que cada cifra sea trazable a su fuente.

## Regla del periodo
Toda consulta empieza el 1 de marzo de 2026 o después; no existen datos ni informes anteriores. La fecha se valida en la interfaz y en el servidor.

## Positioning
Un panel académico con rigor: cada decisión se descompone en señales con puntos y pesos que se recalculan cada día solo con información ya conocida, se contrasta con lo que pasó después (aciertos medidos día por día, hoy cerca de 50 %, sin prometer más) y se acompaña de riesgos, proyecciones con su cobertura histórica y medidas de finanzas (VaR, Sharpe, Sortino, alfa y beta, duración, diversificación).

## Operating Context
- **Oficiales:** Banco de México (SIE: tipo de cambio FIX y de cierre, tasa objetivo, TIIE, inflación, subastas, papel comercial y certificados), Departamento del Tesoro de EE. UU., Reserva Federal de Nueva York (EFFR), BLS (inflación) y Cboe (VIX).
- **Referencia, no oficial:** precios de acciones e índices de Yahoo Finance (posible retraso de 15 a 20 minutos). FRED no está disponible desde el servidor.
- Alojado gratis en Vercel (plan Hobby: una sola función `/api`) con código en GitHub; sin servidor propio ni costo.
- Idioma: español de México. Herramienta educativa: las decisiones no son asesoría financiera y así debe decirse.

## Capabilities and Constraints
- Todo gratuito; nada corriendo en la computadora del usuario.
- Actualización automática mientras la bolsa está abierta, botón manual y uso sin internet con los últimos datos guardados.
- Informes generados al momento con los datos más recientes: PDF y Excel por periodo y por día, con una ficha u hoja por emisora e instrumento.
- Sin emojis; íconos en SVG. Dos decimales en todas las cifras medidas.
- Formato institucional del IPN en interfaz y reportes (ver `DESIGN.md`).

## Brand Commitments
Formato IPN: guinda #750946, negro #231F20, gris #636569 y blanco, con escudos del IPN y de la ESE. Sube y baja usan verde y rojo funcionales (no son colores del IPN). El nombre de la app no se escribe en el encabezado; solo el logo.
