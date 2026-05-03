# Continuous Monitor Container

Status: done

## Goal

Deployment must start a long-running application process, not only TimescaleDB. The process should periodically fetch Binance REST market data, persist market data, evaluate alert rules, and deliver Discord alerts when configured.

Success criteria:

- `docker-compose.yml` includes an `app` service.
- The app service waits for TimescaleDB health, runs migrations, then starts the monitor.
- CLI exposes `bn-monitor run` for a long-running loop.
- `bn-monitor run --once` runs exactly one cycle for operational checks.
- Poll interval is explicit config: `MONITOR_POLL_INTERVAL_SECONDS`, default `300`, positive integer.
- The first version requires explicit `SYMBOLS`; `top_usdt` universe selection remains out of scope.
- Tests cover config parsing and one-cycle CLI execution.

## Changes

- Add `MONITOR_POLL_INTERVAL_SECONDS` to `monitor/config.py`, `.env.example`, and `docs/configuration.md`.
- Add `run` CLI command in `monitor/cli.py`.
- Add `Dockerfile` for the Python app.
- Add hatch wheel package selection so `pip install .` works in Docker.
- Add `app` service to `docker-compose.yml`.
- Add tests for the new run command and config field.

## Verification

- `python -m pytest tests -q`
- `docker compose up --build`

## Out Of Scope

- Automatic `top_usdt` universe discovery.
- WebSocket streaming daemon.
- Multi-worker scheduling.
