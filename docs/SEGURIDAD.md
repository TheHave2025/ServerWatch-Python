# Seguridad y privacidad de ServerWatch-Python v2.0

## Qué datos procesa

- Porcentaje de CPU, RAM, disco, carga, memoria total, contadores de red, uptime, hostname y principales procesos.
- Estados `systemd` de unidades configuradas explícitamente.
- Dirección lógica de nodo y marcas de tiempo; no se almacenan IP de clientes ni credenciales de usuario en SQLite.
- **Nombres de procesos y servicios pueden revelar aplicaciones internas**: protege el acceso al panel y al historial.

## Claves y autenticación

1. Nunca subas `.env`, tokens Telegram, contraseña del dashboard, token Bearer o bases de datos a GitHub. El `.gitignore` los excluye de Git por defecto, pero comprueba `git status` antes de confirmar cambios.
2. Genera `SW_INGEST_TOKEN` con `secrets.token_urlsafe(48)` (al menos 32 caracteres). El token es compartido por los agentes; rotarlo exige configurar central y agentes.
3. `SW_DASHBOARD_PASSWORD` protege la vista y la API de lectura mediante HTTP Basic. Usuario fijo: `serverwatch`. Si el proceso escucha en `0.0.0.0`, el programa exige al menos 16 caracteres, pero **HTTP Basic NO cifra** la contraseña: usa siempre túnel SSH o proxy HTTPS.
4. No expongas el puerto incorporado en Internet. Para agentes remotos instala TLS válido en proxy inverso, firewall, límites de peticiones y filtrado según riesgos.
5. Todo mensaje enviado al hub se limita a 30 KB, valida campos y no permite ejecutar shell ni código remoto. El token de ingreso no habilita lectura de datos.
6. Reduce los permisos de los servicios Linux; puedes ejecutarlos con usuario `serverwatch` sin privilegios.
7. El servidor web no entrega `.env`, datos SQLite ni archivos de carpetas: únicamente rutas explícitas. El dashboard HTML está empaquetado dentro del módulo Python.
8. Las notificaciones fallidas no se reintentan; evita asumir que son garantía de detección de incidentes. El sistema no está diseñado para sustituir herramientas especializadas de respuesta ante incidentes.
9. Mantén Python, el sistema operativo y las dependencias actualizados. Revisa el historial de Git si alguna credencial fue publicada accidentalmente: **revócala** de inmediato.
10. Instala y opera agentes únicamente en sistemas propios o administrados con autorización.

## Despliegue responsable

**Opción preferida:** `SW_DASHBOARD_HOST=127.0.0.1` + acceso mediante SSH local, sin puertos HTTP públicos. Para un hub accesible desde servidores externos, termina HTTPS en Nginx/Caddy y reenvía a 127.0.0.1. Protege el dashboard con contraseña y, preferentemente, restricción de red adicional. Ten un plan de respaldo y recuperación de SQLite.

## No hace

No repara el servidor, no tiene consola de ejecución remota, no instala paquetes, no modifica unidades systemd, no accede a otros equipos por SSH y no contiene credenciales predeterminadas.
