# Configuration

The project uses explicit `.env` configuration. Unknown keys fail startup so typos are not silently ignored.

## Keys

| Key | Default | Allowed values / format | Behavior |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/bn_monitor` | PostgreSQL URL | Database connection string. In Docker Compose the app overrides this to use the `timescaledb` service host. |
| `BINANCE_REST_URL` | `https://fapi.binance.com` | URL | Binance USD-M REST base URL. |
| `BINANCE_WS_URL` | `wss://fstream.binance.com/stream` | URL | Reserved for WebSocket work. |
| `UNIVERSE_MODE` | `top_usdt` | `top_usdt` / `explicit` | `explicit` requires `SYMBOLS`. The continuous runner currently requires explicit symbols because `top_usdt` discovery is not implemented yet. |
| `SYMBOLS` | empty | Comma-separated symbols, for example `SOLUSDT,BNBUSDT` | Symbols are trimmed, uppercased, and deduplicated. |
| `ALERT_MODE` | `shadow` | `shadow` / `live` | `shadow` persists alerts but suppresses Discord. `live` allows Discord delivery checks. |
| `DISCORD_WEBHOOK_URL` | empty | Empty or URL | Discord webhook URL. Required for actual Discord delivery in `live` mode. |
| `DISCORD_MIN_SEVERITY` | `WARNING` | `INFO` / `WARNING` / `CRITICAL` | Minimum severity for Discord delivery. |
| `DISCORD_ALERT_TYPE_ALLOWLIST` | empty | Comma-separated known `alert_type` values | Empty means no allowlist. When set, only listed alert types are delivered to Discord. |
| `DATA_RETENTION_DAYS` | `30` | Positive integer | Reserved for retention jobs. |
| `PRICE_THRESHOLD_BPS` | `100` | Positive number | Reserved price-move threshold. |
| `VOLUME_PERCENTILE_THRESHOLD` | `0.95` | `0` to `1` | Reserved volume percentile threshold. |
| `VOLUME_ROBUST_Z_THRESHOLD` | `3.0` | Positive number | Reserved volume robust-z threshold. |
| `ALERT_COOLDOWN_MINUTES` | `10` | Positive integer | Default alert cooldown minutes. |
| `DAILY_FLAT_OI_COOLDOWN_MINUTES` | `1440` | Positive integer | Documents the once-per-day Discord cadence for `daily_flat_oi_buildup`. Delivery uses UTC calendar-date dedupe to avoid time drift. |
| `MONITOR_POLL_INTERVAL_SECONDS` | `300` | Positive integer | Continuous runner sleep interval between REST polling cycles. |
| `RULE_THRESHOLDS` | `{}` | JSON object | Per-rule threshold overrides. Empty or `{}` uses built-in defaults. |

## Discord Delivery

Discord delivery requires all of:

```text
ALERT_MODE == live
AND severity >= DISCORD_MIN_SEVERITY
AND alert_type in DISCORD_ALERT_TYPE_ALLOWLIST if configured
```

If a check fails, the alert is still generated and persisted with `delivery_status=suppressed`.

`daily_flat_oi_buildup` is only eligible for Discord delivery during UTC hour `0`. Within that window, the app deduplicates by UTC calendar date, so each `(mode, symbol, alert_type)` can deliver at most once per UTC day. This avoids drift from relative `last_sent_at + 24h` arithmetic. Outside that hour, generated alerts are persisted with `delivery_status=suppressed`.

## RULE_THRESHOLDS

Format:

```env
RULE_THRESHOLDS={"breakout_watch":{"volume_z_min":"2.2"},"flat_oi_buildup_15m":{"oi_buildup_threshold":"0.02"}}
```

Available keys:

| alert_type | Keys |
|---|---|
| `flat_oi_buildup_15m` | `return_limit`, `oi_buildup_threshold` |
| `daily_flat_oi_buildup` | `return_limit`, `oi_buildup_threshold` |
| `breakout_watch` | `near_high_bps`, `range_compression_max`, `volume_z_min`, `taker_buy_min`, `market_return_min` |
| `breakdown_watch` | `low_distance_bps`, `range_compression_max`, `volume_z_min`, `taker_sell_min` |

Unknown alert types, unknown keys, invalid JSON, and non-decimal values fail startup.

## Continuous Runner

Use:

```bash
bn-monitor run
```

The runner:

1. Reads `SYMBOLS`.
2. Fetches 1m klines and 5m OI for each symbol.
3. Persists market data.
4. Builds cross-symbol indicator contexts.
5. Evaluates alert rules.
6. Persists alerts and sends Discord messages only when delivery checks pass.
7. Sleeps for `MONITOR_POLL_INTERVAL_SECONDS`, then repeats.

For a single operational check:

```bash
bn-monitor run --once
```

## Docker Compose

`docker compose up --build` starts:

- `timescaledb`
- `app`

The app service runs `alembic upgrade head` before `bn-monitor run`.

For live Discord delivery, set at least:

```env
UNIVERSE_MODE=explicit
SYMBOLS=SOLUSDT,BNBUSDT
ALERT_MODE=live
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## Acceptance

- Default config loads in `shadow` mode.
- Unknown `.env` keys fail startup.
- Invalid enum values fail startup.
- `UNIVERSE_MODE=explicit` with empty `SYMBOLS` fails startup.
- `MONITOR_POLL_INTERVAL_SECONDS` must be positive.
- `DAILY_FLAT_OI_COOLDOWN_MINUTES` must be positive.
- Discord allowlist covers unset, hit, miss, severity below minimum, and shadow mode.
