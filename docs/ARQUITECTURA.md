# Arquitectura técnica v2.0

## Diseño

- **`collector.py`** toma datos locales con psutil y consulta estados de `systemctl is-active -- <servicio>` mediante subprocess (sin shell, timeout de 2 s y validación de nombres).
- **`models.py`** representa muestras, procesos, servicios y eventos en `dataclasses` inmutables.
- **`alerts.py`** compara umbrales, detecta transiciones y recordatorios con reloj monótono. Un `AlertTracker` por servidor evita mezclar estados en el hub.
- **`telegram.py`** emite avisos sobre HTTPS; fallos de red no interrumpen la captura de métricas.
- **`storage.py`** inserta muestras y eventos en transacciones SQLite WAL. Usa parámetros SQL, nunca SQL concatenado con datos de usuario.
- **`remote.py`** valida tipos, valores y tamaños de muestras de agentes y transmite JSON a la central sin aceptar redirecciones HTTP.
- **`web.py`** usa `ThreadingHTTPServer` estándar, devuelve JSON, requiere Bearer para ingestión y HTTP Basic para lectura cuando se activa la contraseña.
- **`dashboard.html`** contiene interfaz CSS y JavaScript sin dependencias web ni recursos cargados de CDN. Grafica curvas SVG accesibles desde el propio navegador.
- **`cli.py`** expone `once`, `watch`, `notify-test`, `config`, `dashboard`, `agent`, `prune`.

## Modelo de ejecución

`serverwatch dashboard` arranca un servidor HTTP en el hilo principal y un hilo de recolección local en segundo plano. Cada petición HTTP se atiende en un hilo independiente. La escritura SQLite usa una conexión por operación, WAL y busy timeout; la evaluación de eventos se serializa con un `RLock` en el Hub. La notificación Telegram se envía en un hilo daemon para no bloquear la respuesta HTTP al agente.

`serverwatch agent` recolecta una muestra local, la envía de forma saliente al hub y repite el ciclo. **Nunca recibe instrucciones de ejecución remota.**

## Semántica de datos

`hostname` es el identificador lógico del nodo: `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`. El campo `timestamp` es la hora declarada por el agente; la base agrega `received_at` generado por la central. El estado online se calcula únicamente mediante la edad de `received_at`, para que el desajuste de relojes en agentes no afecte la conectividad visual.

La API de historial devuelve CPU, RAM y disco con lecturas recibidas (por defecto hasta 120 puntos). El almacenamiento guarda el `snapshot_json` completo, incluidos nombre y RAM de procesos visibles y el estado de los servicios configurados; **estos metadatos pueden ser sensibles**.

## Limitaciones conocidas

- No hay autenticación por agente individual ni perfiles de usuario con diferentes permisos.
- La interfaz y el endpoint de lectura comparten una única contraseña opcional.
- No hay rotación ni almacenamiento seguro de tokens incorporado (se gestionan en `.env`).
- Hub HTTP por diseño; requiere SSH para acceso privado o proxy TLS para conexiones externas.
- No hay agregación de métricas por minuto, compresión histórica, rate limiting de aplicación, cola de reintentos persistente ni alta disponibilidad.
- Un evento `service:` utiliza `value=0/1` para indicar inactivo/activo; la interfaz no lo interpreta como porcentaje.
- `serverwatch dashboard` y `watch` no están diseñados para ejecutarse simultáneamente sobre el mismo servidor porque duplicarían algunas alertas.
