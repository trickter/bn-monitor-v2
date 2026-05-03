# breakout_watch

`breakout_watch` is a WARNING watch signal for altcoins that are close to a recent upper range while 15m structure and 5m flow confirm pressure.

It is not a confirmed breakout signal and must not be described as one.

## Trigger

```text
baseline_ready == true
AND is_altcoin == true
AND (
  distance_to_high_1h_bps <= 50
  OR distance_to_high_24h_bps <= 50
)
AND range_compression_15m <= 0.70
AND oi_change_15m > 0
AND volume_robust_z_5m >= 3.0
AND taker_buy_ratio_5m >= 0.60
AND market_relative_return_5m >= 0
```

## Output

```text
alert_type = breakout_watch
severity = WARNING
direction = up
signal_window = 15m
confirmation_window = 1h
```

Required payload keys:

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "15m",
  "confirmation_window": "1h",
  "confirmations": [],
  "trigger_conditions": []
}
```

## Validation

- Trigger scenario.
- No trigger when price is not near the recent high.
- No trigger when 5m volume confirmation is missing.
- No trigger when taker buy pressure is weak.
- No trigger when market-relative return is negative.
- No trigger when baseline is insufficient.
- AlertEngine generation alongside existing rules.
