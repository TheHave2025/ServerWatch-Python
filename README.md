# ServerWatch-Python 🖥️

**Monitoreo de servidores Linux en Python con panel web, agentes remotos, historial SQLite y alertas por Telegram.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?logo=python&logoColor=white) ![Linux](https://img.shields.io/badge/Linux-Ubuntu%2FDebian-FCC624?logo=linux&logoColor=black) ![Licencia](https://img.shields.io/badge/Licencia-MIT-green) ![Versión](https://img.shields.io/badge/Versión-2.0.0-blue)

> Proyecto educativo y de portafolio de **TheHave2025**. No necesita permisos root para leer CPU, RAM, disco o red. El panel web incorpora HTTPS **solo a través de un proxy inverso configurado por ti**; el servidor incorporado sirve HTTP. No lo publiques directamente en Internet.

## Funcionalidades

| Función | Disponible |
| --- | --- |
| CPU, RAM, disco, carga, red, tiempo encendido, procesos | ✅ |
| Terminal (`once`, `watch`) y JSON | ✅ |
| Panel web responsivo con gráficas históricas | ✅ |
| Historial SQLite, retención y limpieza | ✅ |
| Monitoreo multiservidor con agentes autenticados | ✅ |
| Vista de nodos que dejaron de enviar datos | ✅ |
| Supervisión de servicios `systemd` (opcional) | ✅ |
| Alertas de umbral y servicios por Telegram (opcional) | ✅ |
| Antispam de alertas con cooldown y recuperación | ✅ |
| Pruebas, GitHub Actions, Docker y servicios systemd | ✅ |
| Autorreparación del sistema y actualización automática | ❌ No implementadas |
| Autenticación por usuario/permisos múltiples | ❌ Solo contraseña HTTP Basic opcional |

## Vista del panel

El panel muestra servidores registrados y su estado de conexión, tarjetas de métricas, barras de uso, **tres curvas históricas** y actividad de alertas. Se actualiza cada diez segundos, sin plataformas de terceros ni CDN. Funciona desde navegador móvil o de escritorio.

**Arquitectura:**

```text
 ┌──────────────────────────┐   HTTPS + Bearer token    ┌───────────────────────────────┐
 │ Ubuntu 1: agent          │ ────────────────────────→ │ Central: serverwatch dashboard│
 ├──────────────────────────┤                           │ HTTP local + proxy HTTPS      │
 │ Ubuntu 2: agent          │ ────────────────────────→ │ SQLite (WAL + retención)      │
 └──────────────────────────┘                           │ Panel /api/overview, history  │
                                                        │ Alertas opcionales Telegram   │
                                                        └───────────────────────────────┘
                                                                    ↑
                                                          navegador por SSH tunnel
```

La central también monitorea sus propios recursos. Cada agente **envía datos agregados**; no habilita comandos remotos ni ejecuta scripts enviados desde el panel.

## Requisitos

- Linux (Ubuntu 20.04/22.04/24.04 o Debian reciente); Python 3.10 o superior.
- Git opcional, acceso a PyPI para instalar las dependencias `psutil` y `python-dotenv`.
- Telegram Bot API solo si quieres notificaciones.
- Para agentes remotos, URL pública bajo **HTTPS válido** (o pruebas locales en `localhost`).

## Instalación rápida en Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git

git clone https://github.com/TheHave2025/ServerWatch-Python.git
cd ServerWatch-Python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
chmod 600 .env
```

> Si el repositorio aún no está publicado, descomprime el ZIP de esta entrega y entra en su carpeta en vez de usar `git clone`. El enlace de GitHub anterior es el **nombre sugerido** para cuando lo publiques.

### Opción A. Leer una vez o vigilar desde terminal

```bash
serverwatch once
serverwatch once --json
serverwatch watch
serverwatch watch --quiet
serverwatch config
```

Detén el modo continuo con `Ctrl+C`. Los comandos de la versión 1 siguen disponibles.

### Opción B. Activar panel web e historial

```bash
serverwatch dashboard
```

Accede en el mismo equipo a **http://127.0.0.1:8787**. Los datos se almacenan en `./serverwatch.sqlite3` (ignorado por Git). Se ven apenas llegue la primera muestra. El panel recopila datos locales incluso si no hay agentes configurados.

Para usarlo desde otra computadora sin exponerlo públicamente, abre un túnel SSH desde tu laptop:

```bash
ssh -N -L 8787:127.0.0.1:8787 usuario@IP_DEL_SERVIDOR
```

Luego abre `http://127.0.0.1:8787` en tu laptop. Si tu puerto 8787 está ocupado, usa `-L 8877:127.0.0.1:8787` y abre `http://127.0.0.1:8877`.

### Opción C. Conectar agentes de otros servidores

1. En el equipo **central**, crea un token aleatorio (no lo pongas nunca en GitHub):

   ```bash
   python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```

2. Edita `.env` de la central y configura:

   ```dotenv
   SW_INGEST_TOKEN=TOKEN_GENERADO_ARRIBA
   SW_DASHBOARD_PASSWORD=CONTRASENA_ALEATORIA_DE_AL_MENOS_16_CARACTERES
   SW_DATABASE=./serverwatch.sqlite3
   ```

3. Expón la central **solo detrás de un proxy inverso HTTPS** (Nginx/Caddy, certificado TLS válido) hacia `127.0.0.1:8787` en la misma máquina. La central puede seguir escuchando en localhost. Mira `docs/DESPLIEGUE_MULTISERVIDOR.md`.
4. En **cada agente**, instala el proyecto y edita su `.env`:

   ```dotenv
   SW_HUB_URL=https://monitor.example.com
   SW_INGEST_TOKEN=EL_MISMO_TOKEN_DE_LA_CENTRAL
   SW_NODE_NAME=ubuntu-web-01
   SW_INTERVAL=30
   SW_SERVICES=ssh,nginx
   ```

5. Inicia la central con `serverwatch dashboard` y cada agente con:

   ```bash
   serverwatch agent
   ```

Cada nodo aparecerá automáticamente en el panel. `SW_NODE_NAME` debe ser diferente para cada servidor. Un nodo se muestra **offline** cuando supera `SW_OFFLINE_AFTER` segundos sin enviar métricas (por defecto, 120). *Offline* en el panel no equivale a comprobar mediante un ping ni dispara por sí solo una alerta Telegram.

## Alertas por Telegram

Crea un bot en [@BotFather](https://t.me/BotFather), envía un mensaje al chat de destino y consigue el `chat_id`. Configura los dos valores en `.env` del proceso que evalúa las métricas (central o `watch`):

```dotenv
SW_TELEGRAM_BOT_TOKEN=TU_TOKEN_PRIVADO
SW_TELEGRAM_CHAT_ID=TU_CHAT_ID
SW_CPU_THRESHOLD=90
SW_RAM_THRESHOLD=90
SW_DISK_THRESHOLD=90
SW_ALERT_COOLDOWN=1800
SW_RECOVERY_MARGIN=5
SW_SERVICES=ssh,nginx
```

Envía una prueba:

```bash
serverwatch notify-test
```

- **Nuevo problema:** cuando CPU/RAM/disco supera un límite o un servicio aparece inactivo.
- **Recordatorio:** si persiste después de `SW_ALERT_COOLDOWN` segundos.
- **Recuperación:** después de que el consumo baje por debajo del umbral menos el margen, o cuando el servicio vuelve a estar activo.
- El historial de alertas se guarda en la central, pero el estado de alertas activas (antispam) se reinicia si se reinicia el proceso.
- El envío a Telegram requiere conectividad a Internet. Las notificaciones fallidas **no se reintentan** ni se encolan persistemente.

## Configuración

Copia `.env.example` y ajusta:

| Variable | Valor predeterminado | Significado |
| --- | --- | --- |
| `SW_INTERVAL` | `30` | Segundos entre muestras |
| `SW_CPU_THRESHOLD` | `90` | Umbral CPU (%) |
| `SW_RAM_THRESHOLD` | `90` | Umbral RAM (%) |
| `SW_DISK_THRESHOLD` | `90` | Umbral disco (%) |
| `SW_DISK_PATH` | `/` | Partición a observar |
| `SW_TOP_PROCESSES` | `5` | Procesos destacados por RAM |
| `SW_ALERT_COOLDOWN` | `1800` | Segundos entre recordatorios |
| `SW_RECOVERY_MARGIN` | `5` | Margen de recuperación (%) |
| `SW_SERVICES` | vacío | Servicios systemd, ej. `ssh,nginx` |
| `SW_DATABASE` | `./serverwatch.sqlite3` | Ruta SQLite en la central |
| `SW_RETENTION_DAYS` | `30` | Retención de muestras y eventos |
| `SW_OFFLINE_AFTER` | `120` | Tiempo de desconexión visual |
| `SW_DASHBOARD_HOST` | `127.0.0.1` | Dirección de escucha |
| `SW_DASHBOARD_PORT` | `8787` | Puerto del panel |
| `SW_DASHBOARD_PASSWORD` | vacío | Protección HTTP Basic para panel y API de lectura |
| `SW_INGEST_TOKEN` | vacío | Bearer token de agentes (mín. 32 caracteres) |
| `SW_HUB_URL` | vacío | URL HTTPS de la central; solo agentes |
| `SW_NODE_NAME` | hostname real | Nombre del nodo (único) |
| `SW_TELEGRAM_BOT_TOKEN` | vacío | Token privado de Telegram |
| `SW_TELEGRAM_CHAT_ID` | vacío | Chat que recibe alertas |

**Nota:** Si configuras `SW_DASHBOARD_HOST=0.0.0.0`, se exige contraseña de al menos 16 caracteres; eso **no cifra** el tráfico. Evita exponer HTTP público: HTTPS siempre en proxy inverso, con reglas de firewall. La validación del token no sustituye protección de red o rate limiting.

## Base de datos y API

El archivo SQLite incluye `samples` (muestras de servidores) y `events` (eventos de alerta). WAL permite consultas mientras se insertan muestras. Se descartan registros antiguos al ejecutar:

```bash
serverwatch prune
```

La central también aplica retención periódicamente mientras está ejecutándose (una vez por cada ~100 muestras locales). Las principales rutas son:

| Ruta | Método | Acceso | Descripción |
| --- | --- | --- | --- |
| `/` | GET | Local o HTTP Basic | Panel |
| `/healthz` | GET | Público, sin datos privados | Estado simple |
| `/api/overview` | GET | Local o HTTP Basic | Última muestra por servidor |
| `/api/history?server=...&limit=120` | GET | Local o HTTP Basic | Historial CPU/RAM/disco |
| `/api/events` | GET | Local o HTTP Basic | Últimos eventos |
| `/api/ingest` | POST | `Authorization: Bearer TOKEN` | Registrar muestra remota |

`/api/ingest` acepta solo JSON validado (máx. 30 KB). El token de ingesta no da acceso automático a la vista web.

## Docker y systemd

**Docker:** define primero `SW_DASHBOARD_PASSWORD` en `.env` (mínimo 16 caracteres) y ejecuta:

```bash
docker compose up -d --build
docker compose logs -f serverwatch
```

El contenedor se publica **solamente en 127.0.0.1:8787 del anfitrión**, almacena SQLite en volumen persistente y ejecuta como usuario sin privilegios. Requiere Docker Engine y Compose instalados. Una imagen Docker no contiene certificados TLS ni activa HTTPS por sí sola.

**systemd:** se incluyen plantillas en `deploy/` para el monitor de terminal (v1), el hub (v2) y los agentes (v2). Consulta [`docs/DESPLIEGUE_MULTISERVIDOR.md`](docs/DESPLIEGUE_MULTISERVIDOR.md) para permisos y ubicaciones correctas.

## Pruebas y calidad

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check .
```

Las pruebas son locales: no requieren Telegram ni un servidor remoto. GitHub Actions ejecuta la suite en distintas versiones de Python. Importante: este proyecto es una base extensible de portafolio; para producción de alta disponibilidad incorpora métricas de observabilidad, backups de SQLite, TLS/rate limiting en proxy, supervisión y pruebas de carga.

## Estructura del repositorio

```text
ServerWatch-Python/
├── src/serverwatch/
│   ├── cli.py              # CLI: once, watch, dashboard, agent, prune
│   ├── collector.py        # psutil + systemd
│   ├── alerts.py           # Umbrales, recuperación y cooldown
│   ├── remote.py           # Validación y transmisión de agentes
│   ├── storage.py          # SQLite
│   ├── web.py              # API local y autenticación
│   ├── dashboard.html      # Panel web autónomo
│   ├── config.py           # Variables de entorno
│   └── telegram.py         # Notificaciones
├── tests/                  # Tests con pytest
├── docs/                   # Guías y arquitectura
├── deploy/                 # Servicios systemd
├── Dockerfile
├── compose.yaml
├── .env.example
├── .github/workflows/tests.yml
└── LICENSE
```

## Seguridad y atribución

No subas `.env`, tokens, credenciales SSH, logs ni bases de datos de sistemas reales. Monitorea solo equipos propios o con autorización. El programa **no** ejecuta comandos remotos ni administra contenedores. Revisa [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) antes de exponer una central.

MIT © 2026 **TheHave2025**. Contribuciones y propuestas bienvenidas.
