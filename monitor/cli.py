from __future__ import annotations

import argparse
import json
import time
from typing import Sequence

from pydantic import ValidationError

from monitor.app import run_live_smoke
from monitor.config import load_settings
from monitor.db import build_engine, build_session_factory, session_scope
from monitor.discord import DiscordDeliveryError, send_discord_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bn-monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("healthcheck")
    subparsers.add_parser("config-dump")
    subparsers.add_parser("test-discord")
    run = subparsers.add_parser("run")
    run.add_argument("--symbols", help="Comma-separated symbols. Defaults to SYMBOLS from .env.")
    run.add_argument("--once", action="store_true", help="Run one polling cycle and exit.")
    run.add_argument("--no-discord", action="store_true", help="Do not send pending alerts to Discord.")
    run.add_argument("--poll-interval-seconds", type=int, help="Override MONITOR_POLL_INTERVAL_SECONDS.")
    live_smoke = subparsers.add_parser("live-smoke")
    live_smoke.add_argument("--symbols", help="Comma-separated symbols. Defaults to SYMBOLS from .env.")
    live_smoke.add_argument("--no-discord", action="store_true", help="Do not send pending alerts to Discord.")
    return parser


def _parse_symbols(raw: str) -> tuple[str, ...]:
    return tuple(item.strip().upper() for item in raw.split(",") if item.strip())


def _resolve_symbols(settings, symbols_arg: str | None) -> tuple[str, ...]:
    return _parse_symbols(symbols_arg) if symbols_arg is not None else settings.symbols


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings()
    except ValidationError as exc:
        parser.exit(2, f"configuration error:\n{exc}\n")

    if args.command == "healthcheck":
        print("ok")
        return 0

    if args.command == "config-dump":
        print(json.dumps(settings.masked_dump(), indent=2, sort_keys=True))
        return 0

    if args.command == "test-discord":
        try:
            send_discord_message(settings, "bn-monitor Discord webhook smoke test")
        except DiscordDeliveryError as exc:
            parser.exit(1, f"discord error: {exc}\n")
        print("discord ok")
        return 0

    if args.command == "run":
        symbols = _resolve_symbols(settings, args.symbols)
        if not symbols:
            parser.exit(2, "run requires --symbols or SYMBOLS in .env; top_usdt discovery is not implemented yet\n")
        poll_interval = args.poll_interval_seconds or settings.monitor_poll_interval_seconds
        if poll_interval <= 0:
            parser.exit(2, "--poll-interval-seconds must be a positive integer\n")
        engine = build_engine(settings)
        session_factory = build_session_factory(engine)
        while True:
            with session_scope(session_factory) as session:
                result = run_live_smoke(settings, session, symbols, send_discord=not args.no_discord)
            print(json.dumps(result["summary"], indent=2, sort_keys=True), flush=True)
            if args.once:
                return 0
            time.sleep(poll_interval)

    if args.command == "live-smoke":
        symbols = _resolve_symbols(settings, args.symbols)
        if not symbols:
            parser.exit(2, "live-smoke requires --symbols or SYMBOLS in .env\n")
        engine = build_engine(settings)
        session_factory = build_session_factory(engine)
        with session_scope(session_factory) as session:
            result = run_live_smoke(settings, session, symbols, send_discord=not args.no_discord)
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
