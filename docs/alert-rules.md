# Alert Rules

当前版本实现 `daily_flat_oi_buildup` 与 `breakdown_watch` 纯规则函数。

## daily_flat_oi_buildup

用途：扫描 24h 价格基本横盘但合约持仓明显增长的 altcoin。

触发条件：

```text
-0.03 <= return_24h <= 0.03
AND oi_change_24h >= 0.10
AND baseline_ready == true
AND is_altcoin == true
```

说明：

- `return_24h` 和 `oi_change_24h` 使用比例值表示，3% 为 `0.03`，10% 为 `0.10`。
- 输出等级为 `WARNING`。
- `direction` 为 `none`，因为该信号只表示横盘增仓观察，不预测方向。
- 样本不足时不得触发正式告警。

payload 必须包含：

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "24h",
  "confirmation_window": "24h",
  "confirmations": [],
  "trigger_conditions": []
}
```

## daily_flat_oi_buildup 验收

- 覆盖触发场景。
- 覆盖 OI 不足 10%。
- 覆盖 24h return 超出 -3% 到 3%。
- 覆盖 baseline 样本不足。
- 覆盖非 altcoin universe。

## breakdown_watch

用途：扫描接近近期下沿、价格区间压缩，同时出现增仓、5m 放量、主动卖出压力且弱于市场的 altcoin。

`breakdown_watch` 是 WARNING 观察信号，只表示临界跌破观察，不表示已经跌破，也不得命名为 `breakdown_confirmed`。

触发条件：

```text
baseline_ready == true
AND is_altcoin == true
AND (distance_to_low_1h_bps <= 50 OR distance_to_low_24h_bps <= 50)
AND range_compression_15m <= 0.70
AND oi_change_15m > 0
AND volume_robust_z_5m >= 3.0
AND taker_sell_ratio_5m >= 0.60
AND market_relative_return_5m <= 0
```

说明：

- `distance_to_low_*_bps` 使用 bps 表示，50 bps 表示距离近期低点 0.50% 以内。
- `range_compression_15m` 越低表示区间越压缩，第一版阈值为 `0.70`。
- `oi_change_15m` 使用比例值表示，必须大于 0。
- `volume_robust_z_5m` 必须达到 `3.0`，避免无放量的贴近低点刷屏。
- `taker_sell_ratio_5m` 必须达到 `0.60`，表示 5m 主动卖出占优。
- `market_relative_return_5m <= 0` 用于过滤强于市场的同步波动。
- 输出等级为 `WARNING`，`direction` 为 `down`。
- 样本不足或任一必要指标缺失时不触发。

payload 必须包含：

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "15m",
  "confirmation_window": "1h",
  "confirmations": [],
  "trigger_conditions": []
}
```

## breakdown_watch 验收

- 覆盖完整触发场景。
- 覆盖未接近 1h / 24h 低点。
- 覆盖 5m 放量不足。
- 覆盖 taker sell 不足。
- 覆盖 market-relative return 为正。
- 覆盖 baseline 样本不足。
- 覆盖 AlertEngine 生成 `breakdown_watch` 告警 values。
