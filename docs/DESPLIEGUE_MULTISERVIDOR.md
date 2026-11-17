# Despliegue multiservidor ServerWatch-Python v2.0

## 1. Central en Ubuntu

Instala el proyecto en `/opt/serverwatch-python` con permisos del usuario `serverwatch`:

```bash
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin serverwatch || true
sudo install -d -o serverwatch -g serverwatch -m 0750 /opt/serverwatch-python
sudo install -d -o serverwatch -g serverwatch -m 0750 /var/lib/serverwatch
```

Copia los archivos del proyecto a `/opt/serverwatch-python` **sin la carpeta `.venv`**. Instala dependencias Python:

```bash
sudo python3 -m venv /opt/serverwatch-python/.venv
sudo /opt/serverwatch-python/.venv/bin/pip install -e /opt/serverwatch-python
```

Crea `/opt/serverwatch-python/.env` a partir de `.env.example`. Para la central:

```dotenv
SW_DATABASE=/var/lib/serverwatch/serverwatch.sqlite3
SW_DASHBOARD_HOST=127.0.0.1
SW_DASHBOARD_PORT=8787
SW_INGEST_TOKEN=GENERA_TOKEN_SEGURO_DE_64_CARACTERES
SW_DASHBOARD_PASSWORD=GENERA_CONTRASENA_UNICA_DE_32_CARACTERES
```

Genera cada secreto con `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`, sin copiar literalmente los valores de ejemplo. Asegura permisos:

```bash
sudo chown -R serverwatch:serverwatch /opt/serverwatch-python /var/lib/serverwatch
sudo chmod 640 /opt/serverwatch-python/.env
sudo cp /opt/serverwatch-python/deploy/serverwatch-hub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now serverwatch-hub
sudo journalctl -u serverwatch-hub -n 50 --no-pager
```

La central se ejecuta sin root y escribe SQLite solo en `/var/lib/serverwatch`. Evita ejecutar simultáneamente `watch` y `dashboard` si no quieres alertas repetidas.

## 2. Acceso al panel por SSH (recomendado para uso personal)

Desde la laptop:

```bash
ssh -N -L 8787:127.0.0.1:8787 usuario@IP_CENTRAL
```

En el navegador local: `http://127.0.0.1:8787` (autenticación HTTP Basic: usuario `serverwatch` y la contraseña de `.env`, si se configuró). Este método no necesita abrir el puerto 8787 en Internet.

## 3. Agentes remotos con HTTPS

El agente exige un endpoint `SW_HUB_URL` por **HTTPS válido** (salvo localhost para pruebas). Para permitir agentes desde otras redes usa Nginx o Caddy con certificado TLS válido frente a la central, que sigue escuchando solo en `127.0.0.1:8787`.

Ejemplo **parcial** de Nginx (agrega configuración TLS/certificados con tu proveedor de certificados y configuración de seguridad):

```nginx
server {
    listen 443 ssl;
    server_name monitor.example.com;
    ssl_certificate /etc/letsencrypt/live/monitor.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/monitor.example.com/privkey.pem;
    client_max_body_size 30k;
    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        limit_req zone=serverwatch_ingest burst=10 nodelay; # definir zone en bloque http si se usa
    }
}
```

**Nota:** `limit_req` requiere una definición previa de `limit_req_zone` en el bloque HTTP y el ejemplo supone que Certbot/Let's Encrypt ya emitió los certificados. No ejecutes este fragmento sin completar ambos pasos. Revisa firewall, rotación de certificados y registro de accesos. Nginx no debe publicar el 8787 directamente.

En **cada agente**, instala el proyecto en su servidor y crea `.env`:

```dotenv
SW_HUB_URL=https://monitor.example.com
SW_INGEST_TOKEN=MISMO_TOKEN_DEL_HUB
SW_NODE_NAME=app-ubuntu-01
SW_INTERVAL=30
SW_SERVICES=ssh,nginx
```

Arranca manualmente para probar `serverwatch agent`, o con el servicio:

```bash
sudo chown -R serverwatch:serverwatch /opt/serverwatch-python
sudo chmod 640 /opt/serverwatch-python/.env
sudo cp /opt/serverwatch-python/deploy/serverwatch-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now serverwatch-agent
sudo journalctl -u serverwatch-agent -n 50 --no-pager
```

El usuario `serverwatch` no necesita SSH entrante del hub; el agente **solo hace HTTPS saliente**. Cada servidor necesita nombre de nodo diferente. Usa una contraseña y un token fuertes y rótalos si se filtran.

## 4. Requisitos operativos y limitaciones

- Haz respaldo periódico de `/var/lib/serverwatch/serverwatch.sqlite3`. Para respaldar con WAL activo usa `sqlite3 ... '.backup ...'` o la API SQLite, no copies solo el fichero mientras se escribe.
- `SW_RETENTION_DAYS` limita la cantidad de registros; estima espacio según intervalo y número de nodos. No hay compresión/downsampling automático.
- Reiniciar el hub reinicia en memoria los trackers de antispam: puede volver a enviar una alerta persistente.
- Si la central queda inaccesible, el agente **no** guarda cola local: los datos fallidos se pierden. El fallo se escribe en consola / journal.
- Se puede consultar estado `offline` en panel; por ahora no hay avisos Telegram específicos de desaparición de un agente.
- No hay ejecución remota, autoreinicio de procesos, herramientas de reparación ni autoactualización.
- Los agentes comparten un único token de ingreso; para producción multicliente se recomienda autenticación por agente y límites de tráfico por identidad.
