# Design — Alzea

Modo: Operate. Escena: un estudiante o su asesor revisan el mercado en el celular o en un escritorio con luz de día; la lectura rápida de cifras manda.

## Mundo
Alzea (del verbo «alzar», la subida): un panel con las cotizaciones en filas fijas y columnas de cifras, y una página donde viven las gráficas y el análisis. Cuando cambia un precio, el dígito gira como una ficha mecánica. Sin mosaicos de tarjetas: el panel y las secciones separadas por filetes hacen la estructura.

## Temas (selector en la barra superior; abre en Claro)
| Rol | Claro | Mixto (panel oscuro sobre página clara) | Oscuro |
|---|---|---|---|
| Papel / superficie | #F4F6F8 / #FFFFFF | igual que Claro | #0B0F13 / #141A20 |
| Tinta / tinta 2 / apagado | #0B1117 / #2F3A45 / #4A5663 | igual | #F2F5F7 / #CBD3DA / #A3AFBA |
| Filete / borde de control | #CBD2D9 / #7B8794 | igual | #2B343D / #6B7886 |
| Panel / fila elegida | #FFFFFF / #EAEFF3 | #12171B / #1C242B | #1B2229 / #232C34 |
| Sube / baja (texto) | #00643F / #B3261E | igual | #4BE3A1 / #FF8A80 |
| Sube / baja (en el panel) | #00643F / #B3261E | #4BE3A1 / #FF8A80 | #4BE3A1 / #FF8A80 |
| Ámbar para texto / decorativo | #7A5200 / #F2A900 | igual | #FFC24D / #F2A900 |

Contrastes calculados (WCAG): texto principal ≥ 14.67:1, texto secundario y apagado ≥ 6.80:1, sube/baja ≥ 5.65:1 sobre fondo y panel, bordes de control ≥ 3.38:1. Cero incumplimientos en los tres temas.

Series de comparación (validador dataviz, superficie blanca): azul #1D63C1, naranja #C8480F, verde #0A7F58, ámbar #A86D00, magenta #C23B78 (oscuro: #3987E5, #D95926, #199E70, #C98500, #D55181). Contraste ≥ 3:1 en las cinco; separación para daltonismo en el piso permitido con etiquetas directas y leyenda. Cada emisora conserva su color en todas las vistas. Sube/baja nunca se comunican solo con color: siempre flecha dibujada, signo y texto.

## Tipografía y números
Barlow (UI y texto) y Barlow Semi Condensed (cifras, títulos, marca). Cifras tabulares. Todo valor medido se muestra con dos decimales (precios, porcentajes, RSI, volatilidad, razones, puntos base); solo se dejan enteros los conteos y los puntos de la señal. Los textos corridos van justificados con separación silábica (idioma es).

## Forma y movimiento
Radios 12 px (panel) y 8 px (controles). Un solo recurso de elevación: borde o contraste de superficie; sin sombras decorativas. Íconos dibujados en SVG (trazo 1.75). Un momento firmado: las filas se acomodan en cascada al abrir y cada cifra que cambia gira (rotateX 450 ms, ease-out exponencial). Respeta prefers-reduced-motion.

## Estado de la bolsa
El indicador «Bolsa abierta / cerrada» es de solo lectura: se calcula con el reloj y el horario real de la BMV (lunes a viernes, 9:30 a 16:00 hora de Nueva York) y ningún control lo modifica. La pausa de actualización es un control aparte («Auto»).

## Marca
Nombre: **Alzea**, palabra inventada corta a partir de «alza». No se escribe en la barra superior: ahí va solo el logo (el nombre queda en el título, el ícono de la pantalla de inicio, los reportes y la documentación).
Logo sin letras y en 3D pulido: una esfera de pizarra con brillo y borde de luz, un anillo ámbar inclinado hacia arriba que la rodea y un astro ámbar que sube (la órbita como gráfica; el astro, la cima). Funciona sobre fondo claro y oscuro. Kit en `static/marca/`: marca, marca para fondo oscuro, logo horizontal (claro y fondo oscuro) y logo vertical, con el nombre convertido a trazos desde Barlow Semi Condensed Bold (licencia OFL incluida).
