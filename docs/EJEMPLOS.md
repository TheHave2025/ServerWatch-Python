# Ejemplos v2

## Comprobar métricas localmente

```bash
serverwatch once
serverwatch once --json
serverwatch watch --quiet
```

## Iniciar hub con interfaz

```bash
cp .env.example .env
serverwatch dashboard
# Abre http://127.0.0.1:8787
```

Para personalizar: `SW_INTERVAL=15`, `SW_RETENTION_DAYS=7`, `SW_DATABASE=/var/lib/serverwatch/serverwatch.sqlite3`.

## Iniciar agente remoto

```dotenv
SW_HUB_URL=https://monitor.example.com
SW_INGEST_TOKEN=TOKEN_ALEATORIO_SEGURO_COMPARTIDO
SW_NODE_NAME=backend-01
SW_SERVICES=ssh,nginx
```

```bash
serverwatch agent
```

`SW_HUB_URL` debe apuntar a la raíz del servidor HTTPS (sin `/api/ingest`); el cliente añadirá esa ruta automáticamente.

## Prueba de Telegram

```bash
serverwatch notify-test
```

El token y el chat ID son opcionales si no usarás alertas. Para que un hub notifique eventos de agentes, configúralos **en la central**, no en los agentes.

## Lectura local de API

```bash
curl --fail http://127.0.0.1:8787/api/overview
curl --fail 'http://127.0.0.1:8787/api/history?server=backend-01&limit=100'
```

Si hay contraseña en el panel, utiliza `curl -u serverwatch` y escribe la contraseña al solicitarla. No la incluyas directamente en el comando para evitar guardarla en el historial de shell.

## Limpieza del historial

```bash
serverwatch prune
```

Se eliminan registros más antiguos que `SW_RETENTION_DAYS`. Al borrar filas, el tamaño del fichero físico SQLite no disminuye necesariamente de inmediato; usa una tarea de mantenimiento programada cuando sea apropiado.
