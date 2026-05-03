# Breakout Watch Rule

Status: done

## Goal

Implement the first version of the `breakout_watch` alert rule as a WARNING watch signal for altcoins approaching a recent upper range with supporting 15m/5m confirmations.

Success criteria:

- Triggers only when `baseline_ready == true` and `is_altcoin == true`.
- Requires price near the 1h or 24h high: `distance_to_high_1h_bps <= 50` or `distance_to_high_24h_bps <= 50`.
- Requires compression and confirmation: `range_compression_15m <= 0.70`, `oi_change_15m > 0`, `volume_robust_z_5m >= 3.0`, `taker_buy_ratio_5m >= 0.60`, and `market_relative_return_5m >= 0`.
- Emits `severity=WARNING`, `direction=up`, and `alert_type=breakout_watch`.
- Payload includes `symbol`, `signal_window`, `confirmation_window`, `confirmations`, and `trigger_conditions`.
- Does not describe the event as a confirmed breakout.
- AlertEngine evaluates the rule alongside `daily_flat_oi_buildup`.

## Changes

- Update `docs/alert-rules.md` before code and add `docs/breakout-watch.md` for trigger conditions, payload, and validation.
- Expand `IndicatorContext` with optional/default-safe fields needed by `breakout_watch`.
- Add a pure `evaluate_breakout_watch` rule function in `monitor/alerts/rules.py`.
- Update `AlertEngine` to evaluate both implemented rules.
- Add focused tests for trigger and non-trigger conditions.

## Validation

- `python -m pytest`
- Rule tests cover trigger, not near high, no volume confirmation, weak taker buy, negative market-relative return, baseline insufficient, and missing metrics.
- Engine tests cover generation of a `breakout_watch` alert value.

## Non-goals

- No confirmed breakout signal.
- No `breakdown_watch`, `flat_oi_buildup_15m`, squeeze rules, cooldown, bundle, or market digest implementation in this branch.
- No new config or database schema change.
