# Alert Rules

当前版本只实现 `daily_flat_oi_buildup` 纯规则函数。

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

## 验收

- 覆盖触发场景。
- 覆盖 OI 不足 10%。
- 覆盖 24h return 超出 -3% 到 3%。
- 覆盖 baseline 样本不足。
- 覆盖非 altcoin universe。
