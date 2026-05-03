# Alert Rules

当前版本实现以下纯规则函数：

- `flat_oi_buildup_15m`
- `daily_flat_oi_buildup`
- `breakout_watch`
- `breakdown_watch`

这些规则只生成观察信号，不给自动交易建议。`breakout_watch` / `breakdown_watch` 是临界观察，不表示已经确认突破或跌破。

## 指标计算口径

live smoke 使用 Binance USD-M Futures public REST 的 1m K 线和 5m OI 历史现场计算规则输入，不新增 schema。

| 字段 | 口径 |
|---|---|
| `return_24h` | `(last_close - first_close) / first_close`，使用拉取窗口首尾 close。 |
| `oi_change_24h` | `(last_oi - first_oi) / first_oi`，使用拉取窗口首尾 5m OI。 |
| `return_15m` | 近 15 根 1m K 线累计：`(last_close - first_close) / first_close`。 |
| `oi_change_15m` | 近 3 根 5m OI：`(last_oi - first_oi) / first_oi`，少于 3 根为 `None`。 |
| `range_compression_15m` | 最近 15m 振幅 `(max(high)-min(low))/first_open` 除以近 96 个 15m disjoint 窗口振幅中位数。 |
| `distance_to_high_1h_bps` | `(max(high,last 60 1m)-last_close)/last_close*10000`。 |
| `distance_to_high_24h_bps` | `(max(high,last 1440 1m)-last_close)/last_close*10000`。 |
| `distance_to_low_1h_bps` | `(last_close-min(low,last 60 1m))/last_close*10000`。 |
| `distance_to_low_24h_bps` | `(last_close-min(low,last 1440 1m))/last_close*10000`。 |
| `volume_robust_z_5m` | 最近 5 根 1m quote volume 求和，与历史 disjoint 5m quote volume 桶做 robust z：`(x-median)/(1.4826*MAD)`；样本 < 200 或 MAD 为 0 时为 `None`。 |
| `taker_buy_ratio_5m` | 最近 5 根 1m `sum(taker_buy_quote_volume)/sum(quote_volume)`。 |
| `taker_sell_ratio_5m` | `1 - taker_buy_ratio_5m`。 |
| `market_relative_return_5m` | 本 symbol 5m return 减去同一批 altcoin 5m return 中位数。 |

## flat_oi_buildup_15m

用途：扫描 15m 价格基本横盘但合约持仓快速增长的 altcoin。

触发条件：

```text
abs(return_15m) <= 0.005
AND oi_change_15m >= 0.03
AND baseline_ready == true
AND is_altcoin == true
```

默认阈值保持较严，用于观察短线横盘增仓结构。shadow 阶段如果长时间零触发，可临时用 `RULE_THRESHOLDS` 将 `oi_buildup_threshold` 降到 `0.02` 观察分布。

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
distance_to_high_1h_bps <= 80 OR distance_to_high_24h_bps <= 80
AND range_compression_15m <= 0.70
AND oi_change_15m > 0
AND volume_robust_z_5m >= 2.5
AND taker_buy_ratio_5m >= 0.60
AND market_relative_return_5m >= 0
AND baseline_ready == true
AND is_altcoin == true
```

`near_high_bps=80` 给 watch 信号留出临界观察空间；`volume_z_min=2.5` 比 3.0 更适合作为观察信号，而不是确认信号。

输出：

- `alert_type=breakout_watch`
- `severity=WARNING`
- `direction=up`
- `signal_window=15m`
- `confirmation_window=1h`

## breakdown_watch

用途：识别接近近期下沿、可能向下跌破的临界观察币。

触发条件：

```text
distance_to_low_1h_bps <= 80 OR distance_to_low_24h_bps <= 80
AND range_compression_15m <= 0.70
AND oi_change_15m > 0
AND volume_robust_z_5m >= 2.5
AND taker_sell_ratio_5m >= 0.60
AND market_relative_return_5m <= 0
AND baseline_ready == true
AND is_altcoin == true
```

输出：

- `alert_type=breakdown_watch`
- `severity=WARNING`
- `direction=down`
- `signal_window=15m`
- `confirmation_window=1h`

## RULE_THRESHOLDS

`.env` 可用 `RULE_THRESHOLDS` 覆盖默认阈值。格式为两层 JSON：

```env
RULE_THRESHOLDS={"breakout_watch":{"volume_z_min":"2.2"},"flat_oi_buildup_15m":{"oi_buildup_threshold":"0.02"}}
```

所有键名必须在配置白名单中，未知键启动失败。

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
- 覆盖 live producer 对规则依赖字段的填充。
- 覆盖 AlertEngine 生成对应 alert values。
