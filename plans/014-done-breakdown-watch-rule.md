# 014 - breakdown_watch rule

## Status

done

## Goal

Implement the first-version `breakdown_watch` alert rule as a WARNING watch signal for altcoins that are near recent lows with compression, rising OI, volume expansion, taker sell pressure, and non-positive market-relative return.

This signal is observational only. It must not be described as a confirmed breakdown.

## Assumptions

- The rule consumes already-computed indicator snapshot fields; this change does not implement indicator calculation.
- A symbol is considered near support when either 1h or 24h low distance is at or below 50 bps.
- Missing optional metrics should make this rule return no alert, preserving existing tests and callers.
- `confirmation_window` is `1h` because the low-distance confirmation can use the 1h or 24h low context.

## Implementation Steps

1. Update docs for rule behavior and acceptance.
   Verification: `docs/alert-rules.md` documents trigger conditions, payload, and watch-only wording.
2. Extend `IndicatorContext` with optional breakdown-watch metrics.
   Verification: existing tests can still build snapshots without new fields.
3. Add pure `evaluate_breakdown_watch` rule.
   Verification: focused tests cover trigger and non-trigger cases.
4. Evaluate the new rule from `AlertEngine`.
   Verification: engine tests show `breakdown_watch` values are generated.
5. Run the test suite.
   Verification: `python -m pytest` passes.

## Acceptance

- `breakdown_watch` emits `severity=WARNING` and `direction=down`.
- The rule requires `baseline_ready` and `is_altcoin`.
- The rule requires all of:
  - `distance_to_low_1h_bps <= 50` or `distance_to_low_24h_bps <= 50`
  - `range_compression_15m <= 0.70`
  - `oi_change_15m > 0`
  - `volume_robust_z_5m >= 3.0`
  - `taker_sell_ratio_5m >= 0.60`
  - `market_relative_return_5m <= 0`
- Payload includes `symbol`, `signal_window`, `confirmation_window`, `confirmations`, and `trigger_conditions`.
- Tests cover trigger, not near low, no volume, weak taker sell, positive market-relative return, baseline insufficient, and engine generation.
