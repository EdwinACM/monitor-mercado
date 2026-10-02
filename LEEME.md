# Monitor de Mercado

Tablero local que muestra 5 acciones de la BMV y 5 instrumentos de deuda, siempre actualizados hasta el día en curso.

## Cómo abrirlo
Doble clic en **`iniciar.command`**. La primera vez instala lo necesario (aprox. 30 s), luego abre `http://localhost:8765`.
Para cerrarlo, cierra la ventana de Terminal (o Ctrl+C).

> Si macOS dice que no puede abrirlo: clic derecho → Abrir → Abrir.

## Verla desde el celular
1. Abre la app en la Mac con `iniciar.command` y deja la ventana de Terminal abierta.
2. El celular debe estar en la **misma red Wi-Fi** que la Mac.
3. En la Terminal aparece la línea `Desde tu celular (misma red Wi-Fi): http://10.0.0.X:8765`; abre esa dirección en Safari o Chrome del celular.
4. Para tenerla como app: en Safari, Compartir → **Agregar a pantalla de inicio**.

Si la Mac duerme o cambias de red, la dirección deja de responder (la IP puede cambiar; vuelve a verla en la Terminal).

## De dónde salen los datos
| Dato | Fuente | Frecuencia |
|---|---|---|
| Acciones (cierre, apertura, máx., mín., volumen, intradía 5 min) | Yahoo Finance | Cada minuto con la BMV abierta (retraso aprox. 15–20 min) |
| CETES 28 d, Bondes F 2a, Udibonos 10a, Bonos M 10a | Banxico SIE, cuadro CF107 | Subasta semanal (martes, resultados publicados el mismo día) |
| BPAG28 (IPAB) | Banxico SIE, cuadro CF115 | Subasta semanal |

## Funciones
- La fecha "hasta" siempre es hoy; cambia "Desde" para otro periodo.
- **Auto**: refresca cada minuto con el mercado abierto y cada 15 min con el mercado cerrado.
- **Agregar**: escribe cualquier emisora (p. ej. `BIMBOA`, `GFNORTEO`, `CEMEXCPO`); se agrega `.MX` sola.
- **Excel**: descarga el periodo completo (resumen + una hoja por instrumento).

## Archivos
- `server.py`: servidor (Python), consulta las fuentes y guarda caché.
- `static/index.html`: tablero (Chart.js).
- Para cambiar las emisoras o los bonos por defecto, edita `ACCIONES` y `DEUDA` al inicio de `server.py`.
