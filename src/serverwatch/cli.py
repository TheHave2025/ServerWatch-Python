"""Comandos de operación: once, watch, config y notify-test."""

import argparse
import json
import socket
import sys
import time
from dataclasses import asdict, replace
from html import escape

import psutil

from . import __version__
from .alerts import AlertTracker
from .collector import collect_snapshot
from .config import Config, ConfigError
from .formatters import format_event, format_snapshot
from .telegram import NotificationError, TelegramNotifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="serverwatch",
        description="Monitor de servidores Linux con alertas opcionales por Telegram",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    once = commands.add_parser("once", help="Muestra una lectura y evalúa alertas una vez")
    once.add_argument("--json", action="store_true", help="Imprime JSON para integraciones")
    watch = commands.add_parser("watch", help="Monitoreo continuo hasta Ctrl+C")
    watch.add_argument("--json", action="store_true", help="Imprime JSON por línea")
    watch.add_argument("--quiet", action="store_true", help="Imprime solo cambios de alerta")
    commands.add_parser("config", help="Muestra configuración validada, sin credenciales")
    commands.add_parser("notify-test", help="Envía un mensaje de prueba a Telegram")
    commands.add_parser("dashboard", help="Abre el panel web con recolección local")
    commands.add_parser("agent", help="Envía métricas a una central por HTTPS")
    commands.add_parser("prune", help="Elimina muestras antiguas de SQLite")
    return parser


def _print_reading(config: Config, tracker: AlertTracker, *, json_mode: bool, quiet: bool) -> bool:
    snapshot = collect_snapshot(
        disk_path=config.disk_path,
        top_processes=config.top_processes,
        cpu_sample_seconds=config.cpu_sample_seconds,
        services=config.services,
    )
    if config.node_name:
        snapshot = replace(snapshot, hostname=config.node_name)
    events = tracker.evaluate(snapshot)
    if not quiet or events:
        if json_mode:
            print(
                json.dumps(
                    {"snapshot": asdict(snapshot), "events": [asdict(e) for e in events]},
                    ensure_ascii=False,
                ),
                flush=True,
            )
        else:
            if not quiet:
                print(format_snapshot(snapshot), flush=True)
            for event in events:
                print(format_event(event), flush=True)
            if not quiet:
                print("-" * 50, flush=True)

    ok = True
    if config.telegram_enabled and events:
        notifier = TelegramNotifier(config.telegram_token, config.telegram_chat_id)
        for event in events:
            try:
                notifier.send_alert(event)
            except NotificationError as exc:
                print(f"Aviso: {exc}", file=sys.stderr, flush=True)
                ok = False
    return ok


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = Config.from_env()
        if args.command == "config":
            print(json.dumps(config.public_settings(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "dashboard":
            from .web import serve_dashboard
            serve_dashboard(config)
            return 0
        if args.command == "prune":
            from .storage import Database
            a, b = Database(config.database).prune(config.retention_days)
            print(f"Limpieza completada: {a} muestras y {b} eventos antiguos eliminados")
            return 0
        if args.command == "agent":
            if not config.hub_url or not config.ingest_token:
                raise ConfigError("agent requiere SW_HUB_URL y SW_INGEST_TOKEN")
            from .remote import send_snapshot
            print(f"Agente ServerWatch {__version__} iniciando; intervalo {config.interval}s", file=sys.stderr)
            while True:
                try:
                    snapshot = collect_snapshot(
                        config.disk_path, config.top_processes, config.cpu_sample_seconds,
                        services=config.services,
                    )
                    if config.node_name:
                        snapshot = replace(snapshot, hostname=config.node_name)
                    send_snapshot(snapshot, config.hub_url, config.ingest_token)
                    print(f"[{snapshot.timestamp}] Muestra entregada: {snapshot.hostname}", flush=True)
                except (OSError, psutil.Error) as exc:
                    print(f"Error temporal del agente: {exc}", file=sys.stderr)
                time.sleep(config.interval)
        if args.command == "notify-test":
            if not config.telegram_enabled:
                print("Error: configura SW_TELEGRAM_BOT_TOKEN y SW_TELEGRAM_CHAT_ID", file=sys.stderr)
                return 2
            TelegramNotifier(config.telegram_token, config.telegram_chat_id).send_message(
                f"✅ <b>ServerWatch-Python listo</b>\nServidor: "
                f"<code>{escape(socket.gethostname())}</code>"
            )
            print("Mensaje de prueba enviado a Telegram.")
            return 0

        tracker = AlertTracker(config)
        if args.command == "once":
            return 0 if _print_reading(config, tracker, json_mode=args.json, quiet=False) else 1

        print(
            f"ServerWatch {__version__}: monitoreando cada {config.interval}s. "
            "Ctrl+C para salir.",
            file=sys.stderr,
            flush=True,
        )
        while True:
            try:
                _print_reading(config, tracker, json_mode=args.json, quiet=args.quiet)
            except (OSError, psutil.Error) as exc:
                print(f"Error temporal leyendo métricas: {type(exc).__name__}", file=sys.stderr)
            time.sleep(config.interval)
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.", file=sys.stderr)
        return 0
    except (ConfigError, NotificationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (OSError, psutil.Error, ValueError) as exc:
        print(f"Error leyendo métricas: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
