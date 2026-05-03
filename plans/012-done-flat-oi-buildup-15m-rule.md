# 012 - done - flat OI buildup 15m rule

## Goal

Implement `flat_oi_buildup_15m` as a WARNING observation alert for altcoins that stay nearly flat over 15m while open interest grows quickly.

## Scope

- Add optional 15m fields to `IndicatorContext` without breaking existing tests or callers.
- Add a focused rule evaluator in `monitor/alerts/rules.py`.
- Evaluate the new rule from `AlertEngine` alongside `daily_flat_oi_buildup`.
- Document trigger conditions and payload requirements in `docs/alert-rules.md`.
- Add tests for trigger, non-trigger, missing metrics, and engine generation.

## Trigger

```text
baseline_ready == true
AND is_altcoin == true
AND abs(return_15m) <= 0.005
AND oi_change_15m >= 0.03
```

## Output

- `alert_type`: `flat_oi_buildup_15m`
- `severity`: `WARNING`
- `direction`: `none`
- `signal_window`: `15m`
- `confirmation_window`: `15m`
- payload includes `symbol`, `confirmations`, and `trigger_conditions`.

## Verification

- Unit tests cover trigger, OI too low, return too large, baseline insufficient, non-altcoin, and missing metrics.
- Engine test confirms the rule is included in generated alert values.
- Run `python -m pytest`.
