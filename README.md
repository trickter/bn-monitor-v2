# bn-monitor-v2

Binance USD-M Futures altcoin anomaly monitor.

## Current Runtime

The production entrypoint is a REST polling runner:

```bash
bn-monitor run
```

It periodically fetches Binance 1m klines and 5m open interest, persists market data, evaluates alert rules, stores alerts, and sends Discord messages when delivery checks pass.

For a single check:

```bash
bn-monitor run --once
```

## Local Verification

```bash
python -m pytest tests -q
python -m monitor.cli healthcheck
python -m monitor.cli config-dump
python -m monitor.cli run --once --symbols SOLUSDT,BNBUSDT
```

## Docker Compose

Create `.env` from `.env.example`, then run:

```bash
docker compose up --build
```

`docker-compose.yml` starts TimescaleDB and the app container. The app runs migrations before starting the continuous monitor.

Configuration details are in `docs/configuration.md`.
