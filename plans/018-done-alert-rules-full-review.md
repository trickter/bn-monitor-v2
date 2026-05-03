# Alert Rules Full Review

Status: done

## Goal

Fully review and activate the four implemented alert rules:

- `flat_oi_buildup_15m`
- `daily_flat_oi_buildup`
- `breakout_watch`
- `breakdown_watch`

Success criteria:

- Production indicator building fills every field referenced by the four rules when baseline data is ready.
- `flat_oi_buildup_15m` keeps `return_limit=0.005` and `oi_buildup_threshold=0.03`.
- `daily_flat_oi_buildup` keeps `return_limit=0.03` and `oi_buildup_threshold=0.10`.
- `breakout_watch` defaults move to `near_high_bps=80` and `volume_z_min=2.5`.
- `breakdown_watch` defaults move to `low_distance_bps=80` and `volume_z_min=2.5`.
- `market_relative_return_5m` uses the same cross-symbol altcoin median 5m return as baseline.
- Regression tests fail if a rule references an indicator field that the producer silently leaves as `None`.

## Changes

### Indicator producer

Update `monitor/binance/rest.py`:

- Compute `return_15m` from the last 15 closed 1m candles.
- Compute `oi_change_15m` from the last three 5m OI samples.
- Compute 1h and 24h distance to recent highs and lows in basis points.
- Compute `range_compression_15m` from the current 15m amplitude relative to historical disjoint 15m median amplitude.
- Compute `volume_robust_z_5m` from the latest 5m quote volume against historical disjoint 5m quote-volume buckets.
- Compute `taker_buy_ratio_5m` and `taker_sell_ratio_5m`.
- Add `build_indicator_contexts(...)` to compute cross-symbol `market_relative_return_5m`.

### Runtime path

Update `monitor/app.py` so live smoke gathers all symbol market data first, then builds contexts through `build_indicator_contexts(...)`.

### Rule defaults

Update `monitor/alerts/rules.py`:

- `breakout_watch.near_high_bps`: `50` -> `80`
- `breakout_watch.volume_z_min`: `3.0` -> `2.5`
- `breakdown_watch.low_distance_bps`: `50` -> `80`
- `breakdown_watch.volume_z_min`: `3.0` -> `2.5`

### Documentation and config

Update `docs/alert-rules.md` and `.env.example` so formulas, defaults, and threshold override examples match code.

### Tests

Add `tests/test_indicator_context.py` for numeric indicator checks, insufficient-sample behavior, and regression guards.

Update existing alert and live-smoke tests for the new defaults and producer path.

Add an end-to-end AlertEngine test that uses `build_indicator_contexts(...)` output and verifies all four alert types can be generated from produced contexts.

## Verification

- `python -m pytest tests -q`
- Result: `89 passed`
