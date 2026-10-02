# Monitor de Mercado

Tablero web con 5 acciones de la BMV y 5 instrumentos de deuda. Los datos se consultan al abrir la página y cada vez que tocas **Actualizar**.

## Verla en el celular (Android o iPhone)
La app vive en Vercel y se publica desde el repositorio `github.com/EdwinACM/monitor-mercado`.

Primera vez (una sola vez):
1. Entra a https://vercel.com/new y elige **Continue with GitHub**.
2. Importa el repositorio **monitor-mercado** → **Deploy** (no cambies ninguna opción).
3. Vercel te da una dirección tipo `monitor-mercado-xxxx.vercel.app`. Ábrela en el celular.
4. Para tenerla como app: iPhone (Safari) → Compartir → **Agregar a pantalla de inicio**; Android (Chrome) → ⋮ → **Agregar a la pantalla principal**.

Cada `git push` a `main` vuelve a publicar la app sola.

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
