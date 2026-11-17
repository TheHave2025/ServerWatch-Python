# Registro de cambios

## 2.0.0 — 2026-11-17

- Panel web responsivo oscuro (HTTP integrado), métricas e historial con SVG.
- Almacenamiento SQLite con WAL y política de retención de datos.
- Hub multiservidor: `dashboard` y agentes `agent` con autenticación Bearer.
- Detección de servidores offline en el panel.
- Monitoreo opcional de servicios systemd y alertas/recuperación por Telegram.
- Comando `prune`, despliegue Docker, unit files systemd para hub y agentes.
- Pruebas del protocolo remoto, base de datos y endpoints HTTP.

## 1.0.0 — 2026-11-17

- Monitor local (`once`, `watch`), métricas psutil y notificaciones opcionales.
- Configuración segura, pruebas y documentación Ubuntu.
