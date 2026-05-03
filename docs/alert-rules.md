# Alert Rules

当前版本实现以下纯规则函数：

- `flat_oi_buildup_15m`
- `daily_flat_oi_buildup`
- `breakout_watch`

这些规则只生成观察信号，不给自动交易建议。`breakout_watch` 是临界观察，不表示已经确认突破。

## flat_oi_buildup_15m

用途：扫描 15m 价格基本横盘但合约持仓快速增长的 altcoin。

触发条件：

```text
abs(return_15m) <= 0.005
AND oi_change_15m >= 0.03
AND baseline_ready == true
AND is_altcoin == true
```

输出：

- `alert_type=flat_oi_buildup_15m`
- `severity=WARNING`
- `direction=none`
- `signal_window=15m`
- `confirmation_window=15m`

## daily_flat_oi_buildup

用途：扫描 24h 价格基本横盘但合约持仓明显增长的 altcoin。

触发条件：

```text
-0.03 <= return_24h <= 0.03
AND oi_change_24h >= 0.10
AND baseline_ready == true
AND is_altcoin == true
```

输出：

- `alert_type=daily_flat_oi_buildup`
- `severity=WARNING`
- `direction=none`
- `signal_window=24h`
- `confirmation_window=24h`

## breakout_watch

用途：识别接近近期上沿、可能向上突破的临界观察币。

触发条件：

```text
distance_to_high_1h_bps <= 50 OR distance_to_high_24h_bps <= 50
AND range_compression_15m <= 0.70
AND oi_change_15m > 0
AND volume_robust_z_5m >= 3.0
AND taker_buy_ratio_5m >= 0.60
AND market_relative_return_5m >= 0
AND baseline_ready == true
AND is_altcoin == true
```

输出：

- `alert_type=breakout_watch`
- `severity=WARNING`
- `direction=up`
- `signal_window=15m`
- `confirmation_window=1h`

## Payload

每条规则输出 payload 至少包含：

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "15m",
  "confirmation_window": "1h",
  "confirmations": [],
  "trigger_conditions": []
}
```

## 验收

- 覆盖触发场景。
- 覆盖 OI、return、volume、taker、market-relative 等关键条件不满足。
- 覆盖 baseline 样本不足。
- 覆盖非 altcoin universe。
- 覆盖指标缺失。
- 覆盖 AlertEngine 生成对应 alert values。
