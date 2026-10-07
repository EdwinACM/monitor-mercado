# Design — Alzea

Modo: Operate. Escena: un estudiante o su asesor revisan el mercado en el celular o en un escritorio con luz de día; la lectura rápida de cifras manda.

## Identidad institucional (IPN)
La interfaz y los reportes siguen el Manual de Identidad Gráfica del IPN: la paleta oficial tiene solo cuatro colores y la app no introduce otros para estructura o marca.

| Color | HEX | Uso |
|---|---|---|
| Guinda | #750946 | Barra superior, títulos, filetes, botones primarios, línea principal de las gráficas |
| Guinda oscuro (derivado) | #4F0630 | Franja institucional, pie, fondos muy oscuros |
| Guinda suave (derivado) | #F7ECF1 | Filas alternas, encabezados de tabla, chips activos |
| Negro | #231F20 | Texto |
| Gris | #636569 | Texto secundario |
| Blanco | #FFFFFF | Superficies y texto sobre guinda |

El ámbar de la versión anterior se eliminó porque no pertenece a la paleta del IPN. **Sube y baja (verde #00643F y rojo #B3261E) no son colores del IPN: son colores funcionales** que sirven para leer ganancias y pérdidas, y siempre van acompañados de flecha, signo y texto. Las decisiones usan además verde/rojo suave en celdas de Excel.

La barra superior lleva el escudo del IPN (blanco sobre guinda) y el logo de la app; el nombre «Alzea» no se escribe ahí. Franja superior: «Instituto Politécnico Nacional · Escuela Superior de Economía · Seminario de Titulación 2026». El pie lleva los escudos del IPN y de la ESE y las fuentes de los datos.

## Temas (selector en la barra superior; abre en Claro)
| Rol | Claro | Mixto (panel oscuro sobre página clara) | Oscuro |
|---|---|---|---|
| Papel / superficie | #F7F6F5 / #FFFFFF | igual que Claro | #141112 / #1E1A1B |
| Tinta / tinta 2 / apagado | #231F20 / #3D393A / #636569 | igual | #F4F1F2 / #D5D0D2 / #B0AAAD |
| Filete / borde de control | #E8E9EA / #8C8E92 | igual | #322C2E / #7A7376 |
| Texto de marca | #750946 | igual | #E9B1CD |
| Panel / fila elegida | #FFFFFF / #F7ECF1 | #231F20 / #352B30 | #1E1A1B / #2B1621 |
| Sube / baja | #00643F / #B3261E | panel: #4BE3A1 / #FF8A80 | #4BE3A1 / #FF8A80 |

Contrastes calculados (WCAG 2.x): texto principal ≥ 15.10:1, texto secundario ≥ 5.41:1, texto guinda sobre blanco 11.15:1, sube/baja ≥ 5.67:1 sobre superficie y fila suave, en el tema Mixto ≥ 7.14:1 sobre el panel, en Oscuro ≥ 7.55:1; bordes de control ≥ 3.28:1. Cero incumplimientos en los tres temas.

Series de gráficas (validador dataviz): azul #1D63C1, naranja #C8480F, verde #0A7F58, ámbar #A86D00 y magenta #C23B78 (oscuro: #3987E5, #D95926, #199E70, #C98500, #D55181). El guinda no pasa las pruebas de separación para series categóricas, por eso solo se usa como línea principal de una gráfica de una sola serie. Contraste ≥ 3:1 en las cinco; la separación para daltonismo queda en el piso permitido y se compensa con etiquetas directas, leyenda y tabla. Cada emisora conserva su color en todas las vistas.

## Tipografía y números
Barlow (UI y texto) y Barlow Semi Condensed (cifras, títulos). Se sirven desde la propia app (`static/fonts`) para que funcionen sin internet; los reportes PDF incrustan las mismas fuentes. Cifras tabulares. Todo valor medido se muestra con dos decimales (precios, porcentajes, RSI, volatilidad, razones, puntos base); solo son enteros los conteos y los puntos de la señal. Los textos van justificados con separación silábica (es) y en forma de frase (primera letra en mayúscula).

## Gráficas
Chart.js local (`static/vendor`). Se ajustan al ancho de su contenedor con altura proporcional (`clamp`), etiquetas directas al final de cada línea con ancho calculado, retícula tenue, cruz con tooltip y rangos de proyección como bandas sombreadas. Cada gráfica tiene alternativa en tabla.

## Forma y movimiento
Radios 12 px (panel) y 8 px (controles). Un solo recurso de elevación: borde o contraste de superficie; sin sombras decorativas. Íconos en SVG (trazo 1.75). Un momento firmado: las filas se acomodan en cascada al abrir y cada cifra que cambia gira (rotateX 450 ms). Respeta prefers-reduced-motion. En pantallas ≤ 900 px la navegación pasa a una barra inferior.

## Estado de la bolsa
«Bolsa abierta / cerrada» es de solo lectura: se calcula con el reloj y el horario de la BMV y de Nueva York (lunes a viernes, 9:30 a 16:00 hora de Nueva York) y ningún control lo modifica. La pausa de actualización es un control aparte («Auto»). Sin internet aparece un aviso con la hora de lo último guardado.

## Reportes (PDF y Excel)
- **PDF:** portada con banda guinda, escudo IPN en blanco y escudo ESE; títulos Barlow Semi Condensed; tablas con encabezado guinda y filas alternas guinda suave; una ficha por emisora e instrumento con tarjetas de cifras, gráfica dibujada en vectores, estadística, proyección y justificación; pie «Herramienta educativa · no constituye asesoría financiera».
- **Excel:** una hoja por emisora e instrumento; encabezados guinda con texto blanco, columna «Qué significa» en cada medida, formatos de número con dos decimales, gráfica de cierres y hoja «Léeme» con índice enlazado.
- Nombres de archivo normales: `Informe_de_mercados_2026-03-01_a_2026-10-07.pdf`, `Analisis_del_dia_2026-10-06.xlsx`.
