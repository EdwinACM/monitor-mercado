# Monitor de Mercado

Tablero web con 5 acciones de la BMV y 5 instrumentos de deuda. Los datos se consultan al abrir la página y cada vez que tocas **Actualizar**.

## Verla en el celular (Android o iPhone)
Dirección pública: **https://monitor-mercado-alpha.vercel.app**

Ábrela en el navegador del celular. Para tenerla como app:
- iPhone (Safari): Compartir → **Agregar a pantalla de inicio**.
- Android (Chrome): menú ⋮ → **Agregar a la pantalla principal**.

La app corre en Vercel (nube): no necesita que la Mac esté encendida. Cada `git push` a `main` del repositorio `github.com/EdwinACM/monitor-mercado` la vuelve a publicar sola.

## Verla en la Mac (sin internet público)
Doble clic en `iniciar.command` → abre `http://localhost:8765`.

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
- `server.py`: consulta las fuentes (lo usan la Mac y Vercel). Emisoras y bonos por defecto: `ACCIONES` y `DEUDA` al inicio.
- `api/*.py`: funciones de Vercel que reutilizan `server.py`.
- `static/index.html`: el tablero.
