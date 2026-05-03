# Alert Rules

当前版本实现 `flat_oi_buildup_15m` 和 `daily_flat_oi_buildup` 纯规则函数。

## flat_oi_buildup_15m

用途：扫描 15m 价格基本横盘但合约持仓快速增长的 altcoin，作为短线横盘增仓观察信号。

触发条件：

```text
abs(return_15m) <= 0.005
AND oi_change_15m >= 0.03
AND baseline_ready == true
AND is_altcoin == true
```

说明：

- `return_15m` 和 `oi_change_15m` 使用比例值表示，0.5% 为 `0.005`，3% 为 `0.03`。
- 输出等级为 `WARNING`。
- `direction` 为 `none`，因为该信号只表示横盘增仓观察，不预测方向。
- 样本不足、非 altcoin、15m return 缺失或 15m OI change 缺失时不触发正式告警。

payload 必须包含：

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "15m",
  "confirmation_window": "15m",
  "confirmations": ["oi_change_15m"],
  "trigger_conditions": []
}
```

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
  "confirmations": ["oi_change_24h"],
  "trigger_conditions": []
}
```

## 验收

- 覆盖触发场景。
- 覆盖 OI 不足阈值。
- 覆盖 return 超出横盘阈值。
- 覆盖 baseline 样本不足。
- 覆盖非 altcoin universe。
- 覆盖指标缺失。
- 覆盖 AlertEngine 生成对应 alert values。
