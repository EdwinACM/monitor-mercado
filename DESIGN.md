# Design — Pizarra

Modo: Operate. Escena: un estudiante o su asesor revisan el mercado en el celular o en un escritorio con luz de día; la lectura rápida de cifras manda.

## Mundo
La pizarra de una bolsa: una sola superficie oscura (el tablero) con las cotizaciones en filas fijas y columnas de cifras, sobre una página clara donde viven las gráficas y el análisis. Cuando cambia un precio, el dígito gira como una ficha de pizarra mecánica. No hay mosaicos de tarjetas: el tablero y las secciones separadas por filetes hacen la estructura.

## Color (estrategia: Restringida)
| Rol | Claro | Oscuro (preferencia del sistema) |
|---|---|---|
| Papel | #F3F4F1 | #0E1114 |
| Superficie | #FFFFFF | #161B20 |
| Tinta / tinta 2 / apagado | #14181C / #4A545E / #5F6A75 | #EEF1F3 / #B5BEC6 / #8A949D |
| Filete | #D9DCD6 | #262D34 |
| Tablero | #15191D (filas #1C2227, línea #2B333B) | #1D242A |
| Acento ámbar (riel, punto en vivo, logo) | #F2A900 | #F2A900 |
| Ámbar para texto | #8A5F00 | #F2B93B |
| Sube / baja (papel) | #0B7A55 / #C62828 | #3DDC97 / #FF7A70 |
| Sube / baja (tablero) | #3DDC97 / #FF7A70 | igual |

Series de comparación (validadas con el validador de dataviz): azul #2A78D6, naranja #EB6834, aguamarina #1BAF7A, amarillo #EDA100, magenta #E87BA4 (oscuro: #3987E5, #D95926, #199E70, #C98500, #D55181). Cada emisora conserva su color en todas las vistas. Contraste bajo en tres series claras: siempre con etiquetas directas, leyenda y tabla.

El ámbar se usa pocas veces por pantalla: riel del tablero, indicador en vivo, marca. Sube/baja nunca se comunican solo con color: siempre flecha dibujada y signo.

## Tipografía
Barlow (UI y texto) y Barlow Semi Condensed (cifras del tablero y títulos de columna). Cifras tabulares. Cuerpo 15/1.5, tablero 28–32 px, títulos de sección 18 px semibold, sin sobretítulos ni numeración.

## Forma
Radios 12 px (tablero), controles 8 px. Un solo recurso de elevación: el contraste entre tablero y papel; sin sombras decorativas. Íconos dibujados en SVG, trazo 1.75, nunca glifos Unicode ni emojis.

## Movimiento
Un momento firmado: las filas del tablero se acomodan en cascada al cargar y cada cifra que cambia gira (rotateX, 450 ms, ease-out exponencial) con un destello breve de sube/baja. Respeta prefers-reduced-motion.

## Marca
Nombre: Pizarra. Marca: ficha de pizarra partida por una ranura horizontal, con una línea ámbar ascendente que cruza la ranura y dos pernos de bisagra.
