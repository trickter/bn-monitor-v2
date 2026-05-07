# 024 - Done runtime delivery and closed kline fixes

## Summary

Fix two production runtime issues:

- REST polling must not persist or evaluate the latest unfinished 1m kline.
- Discord delivery failures must not abort the polling cycle or roll back market data and alert inserts.

This change does not add a retry worker, queue table, new configuration, or WebSocket ingestion.

## Design

### Closed REST klines

Binance REST kline rows include close time at index `6`. The REST polling path should:

```text
fetch /fapi/v1/klines interval=1m
parse rows with close_time metadata
keep only rows whose close_time <= current UTC time
persist and evaluate only closed rows
```

The repository values stay unchanged; `close_time` is an in-memory parsing aid and is not stored in `futures_kline_1m`.

### Discord delivery isolation

The app should persist generated alerts first, attempt Discord only for `delivery_status=pending`, then update the stored alert delivery fields:

```text
204 / 2xx -> delivery_status=sent, discord_sent_at=current UTC time
429      -> delivery_status=rate_limited, payload.delivery_error recorded
4xx/5xx  -> delivery_status=failed, payload.delivery_error recorded
```

Discord delivery errors must not escape `run_live_smoke`, so the session can still commit market data, alerts, cooldown rows, and final delivery status.

## Validation

- Unit tests cover REST kline filtering of unfinished rows.
- Unit tests cover Discord success, failure, and rate limit delivery status persistence.
- Existing test expectations are adjusted so the live smoke path accounts for closed kline filtering and delivery status updates.
- Full suite should pass with Python 3.12:

```bash
python -m pytest tests -q
```
