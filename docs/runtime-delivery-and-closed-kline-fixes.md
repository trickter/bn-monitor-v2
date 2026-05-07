# Runtime Delivery and Closed Kline Fixes

## REST closed kline filtering

The REST polling path uses Binance kline row close time to filter unfinished 1m candles before persistence and alert evaluation.

`close_time` is an in-memory parsing aid. It is removed before writing repository values, so `futures_kline_1m` still only stores the schema fields.

Acceptance:

- REST latest unfinished 1m kline is not persisted.
- REST latest unfinished 1m kline is not used for alert evaluation.

## Discord delivery result persistence

For alerts that pass delivery checks, the app persists the alert, attempts Discord delivery, and then updates the same alert row:

```text
sent          = Discord accepted the webhook request
rate_limited  = Discord returned 429
failed        = Discord returned another error or delivery raised an error
```

Discord delivery failures must not abort the polling cycle. Market data, generated alerts, cooldown state, and final delivery status are still committed for replay.
