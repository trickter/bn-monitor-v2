# 023 — Draft long_pullback_reclaim_watch

## Summary

Add one observation alert, `long_pullback_reclaim_watch`, for altcoins that are in a healthy 4h pullback inside a broader long structure and then show 5m/15m reclaim pressure.

This version does not add `long_pullback_zone_watch`, volatility buckets, 4h kline persistence, database schema changes, or new cooldown configuration.

## Design

Use Binance native 4h klines as a lightweight structure input:

```text
GET /fapi/v1/klines?symbol={symbol}&interval=4h&limit=80
```

The app should cache 4h klines in memory and refresh on startup, cache miss, or after a 4h close. The latest unfinished 4h candle must not be used for structure metrics.

Trigger conditions:

```text
baseline_ready == true
AND is_altcoin == true
AND return_7d >= 0.08
AND range_position_7d >= 0.55
AND last_up_leg_return >= 0.15
AND 0.382 <= pullback_retrace_ratio <= 0.764
AND 0.08 <= pullback_from_high <= 0.38
AND -0.05 <= low_vs_ema20_4h <= 0.03
AND low_vs_ema50_4h >= -0.08
AND 3 <= pullback_bars_4h <= 24
AND return_15m >= 0
AND market_relative_return_5m >= 0
AND volume_robust_z_5m >= 2.0
AND taker_buy_ratio_5m >= 0.60
AND oi_change_15m > 0
```

Output:

```text
alert_type = long_pullback_reclaim_watch
severity = WARNING
direction = up
signal_window = 4h/7d
confirmation_window = 5m/15m
```

## Implementation

- Extend `IndicatorContext` with the 4h structure fields needed by the rule and a payload-only structure details mapping.
- Add native 4h kline fetching and fixed 60-candle pullback metric calculation in `monitor/binance/rest.py`.
- Add the rule and threshold overrides in `monitor/alerts/rules.py` and `monitor/config.py`.
- Document the signal, indicators, configuration, and payload.
- Keep the alert wording observational and avoid entry/buy/trade advice language.

## Validation

- Unit tests cover 4h metric calculation, SMA-seed EMA, unfinished 4h filtering, insufficient 4h data, trigger and non-trigger rule cases, threshold validation, and AlertEngine payload output.
- Full suite must pass with `python -m pytest tests -q`.
