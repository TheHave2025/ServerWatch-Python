# Instalación como servicio systemd (Ubuntu)

> Esta guía mantiene el modo de terminal (`serverwatch watch`). Para desplegar el **panel web v2** y agentes remotos, utiliza [`DESPLIEGUE_MULTISERVIDOR.md`](DESPLIEGUE_MULTISERVIDOR.md).

Esta guía es para ejecutar ServerWatch-Python en tu **propio VPS**, iniciarlo con el sistema y mantener el monitor funcionando aunque cierres la sesión SSH. Los comandos de `sudo` son necesarios solo para instalar el servicio, no para obtener métricas comunes.

## 1. Instala dependencias de Linux

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

Para Python 3.10+ usa Ubuntu 22.04 o superior, o una instalación equivalente de Python actualizada. Comprueba:

```bash
python3 --version
```

## 2. Prepara una cuenta de servicio y una carpeta fija

Desde **el directorio del proyecto descomprimido**:

```bash
sudo useradd --system --user-group --home /opt/serverwatch-python --shell /usr/sbin/nologin serverwatch
sudo install -d -m 755 -o root -g root /opt/serverwatch-python
sudo cp -r src deploy pyproject.toml README.md LICENSE /opt/serverwatch-python/
```

Si el usuario `serverwatch` ya existe por una instalación anterior, **no lo vuelvas a crear**. Revisa primero `id serverwatch` y conserva tus archivos existentes.

## 3. Crea entorno Python y configura el monitor

```bash
sudo python3 -m venv /opt/serverwatch-python/.venv
sudo /opt/serverwatch-python/.venv/bin/python -m pip install /opt/serverwatch-python
sudo install -m 600 .env.example /opt/serverwatch-python/.env
sudo nano /opt/serverwatch-python/.env
```

Edita umbrales y, opcionalmente, agrega tus dos valores privados de Telegram. Después restringe lectura del archivo:

```bash
sudo chown root:serverwatch /opt/serverwatch-python/.env
sudo chmod 640 /opt/serverwatch-python/.env
```

> Si instalaste previamente el proyecto y tienes un `.env` configurado, **no ejecutes de nuevo** `sudo install ... .env`: lo reemplazarías. Para actualizar código conserva el archivo actual.

## 4. Verifica configuración con los permisos del servicio

```bash
cd /opt/serverwatch-python
sudo -u serverwatch /opt/serverwatch-python/.venv/bin/serverwatch config
sudo -u serverwatch /opt/serverwatch-python/.venv/bin/serverwatch once
```

Si activaste Telegram:

```bash
sudo -u serverwatch /opt/serverwatch-python/.venv/bin/serverwatch notify-test
```

Si `notify-test` devuelve error, comprueba el chat ID, que hayas iniciado conversación con el bot y que el servidor tenga salida a internet.

## 5. Instala el servicio

```bash
sudo cp /opt/serverwatch-python/deploy/serverwatch.service /etc/systemd/system/serverwatch.service
sudo systemctl daemon-reload
sudo systemctl enable --now serverwatch
sudo systemctl status serverwatch --no-pager
```

Verifica en tiempo real:

```bash
sudo journalctl -u serverwatch -f
```

El servicio ejecuta `serverwatch watch --quiet`, por lo que no escribe una lectura cada 30 segundos: solo eventos de alerta y errores. Para consultar el estado manualmente ejecuta `serverwatch once`.

## 6. Operación habitual

```bash
sudo systemctl restart serverwatch
sudo systemctl stop serverwatch
sudo systemctl start serverwatch
sudo systemctl status serverwatch --no-pager
sudo journalctl -u serverwatch -n 100 --no-pager
```

Para cambiar los umbrales, edita `/opt/serverwatch-python/.env` y reinicia el servicio.

## 7. Verificaciones tras reiniciar Ubuntu

```bash
sudo systemctl is-enabled serverwatch
sudo systemctl is-active serverwatch
```

Ambos deben responder `enabled` y `active` respectivamente cuando el servicio se haya instalado y esté funcionando.

## Recomendaciones de seguridad

- Instala el monitor en un sistema del que seas administrador.
- Conserva `.env` con grupo `serverwatch` y modo `640`.
- No ejecutes la aplicación con root; el servicio utiliza su propio usuario.
- No abras puertos de entrada: para Telegram solo necesitas salida HTTPS.
- Evita compartir registros de procesos y nombres de servidor públicamente.
- Revisa el archivo `deploy/serverwatch.service` antes de instalarlo. Incluye restricciones de permisos y acceso al sistema.

## Desinstalación (conservando copia de configuración si la necesitas)

```bash
sudo systemctl disable --now serverwatch
sudo rm /etc/systemd/system/serverwatch.service
sudo systemctl daemon-reload
```

**No se borra automáticamente** `/opt/serverwatch-python`: revisa y respalda sus archivos antes de eliminar manualmente esa carpeta. Tampoco se elimina el usuario del servicio sin tu intervención.
