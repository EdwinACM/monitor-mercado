# Seguridad

## Cómo reportar un problema

Si encuentras una vulnerabilidad, repórtala de forma privada desde la pestaña Security de este repositorio, con la opción "Report a vulnerability". Por favor no abras un issue público con los detalles.

Incluye qué ruta o archivo afecta, cómo reproducirlo y qué impacto crees que tiene. Es un proyecto personal y académico, así que la respuesta puede tardar unos días.

## Alcance

La app solo muestra datos públicos, no tiene cuentas de usuario ni guarda información personal. Lo que importa es:

- Que ninguna entrada permita ejecutar código, leer archivos o hacer que el servidor consulte direcciones distintas de las fuentes fijas.
- Que las cabeceras de seguridad y la política de contenido se mantengan.
- Que no se publiquen llaves, contraseñas ni datos personales en el repositorio.

## Medidas que ya existen

- Los parámetros de fechas, emisoras y moneda se validan contra valores permitidos.
- El servidor solo consulta fuentes fijas y solo por https.
- Los errores no exponen detalles internos.
- La política de contenido no permite scripts en línea salvo uno autorizado por su huella (hash), y las pruebas verifican que la huella coincida.
- Dependabot revisa las dependencias y las acciones de GitHub cada semana, y las acciones están fijadas a un commit.
- El análisis de secretos y la protección contra subir llaves están activos en GitHub.
