# Alert Signals

第一版信号优先服务 altcoin / 妖币监控，目标不是预测价格，而是识别值得盯盘的异常结构。

## 核心信号

| alert_type | 周期 | 默认等级 | 用途 |
|---|---:|---|---|
| `price_probe` | 1m | INFO | 价格快速偏离探测 |
| `volume_expansion_5m` | 5m | WARNING | 放量确认 |
| `active_buy_impulse` | 5m | WARNING / CRITICAL | 主动买入冲击 |
| `active_sell_impulse` | 5m | WARNING / CRITICAL | 主动卖出冲击 |
| `wick_hunt` | 1m | WARNING | 插针 / 猎杀流动性 |
| `liquidation_spike_5m` | 5m | WARNING / CRITICAL | 强平 spike 确认 |
| `flat_oi_buildup_15m` | 15m | WARNING | 短线横盘增仓 |
| `daily_flat_oi_buildup` | 24h | WARNING | 当天涨跌幅收敛但 OI 明显增长 |
| `breakout_watch` | 15m / 1h | WARNING | 接近近期上沿，疑似向上突破前兆 |
| `breakdown_watch` | 15m / 1h | WARNING | 接近近期下沿，疑似向下跌破前兆 |
| `long_squeeze_risk` | 5m + 15m | CRITICAL | 多杀多风险 |
| `short_squeeze_risk` | 5m + 15m | CRITICAL | 逼空风险 |

## daily_flat_oi_buildup

用途：扫描市场，找出价格当天基本没动、但合约持仓明显增长的币。

MVP 条件：

```text
-3% <= day_return <= 3%
AND oi_change_24h >= 10%
AND baseline 样本足够
AND symbol 属于 altcoin universe
```

说明：

- `day_return` 第一版使用 rolling 24h return，对应指标字段 `return_24h`。
- `oi_change_24h` 第一版使用 OI 数量变化率。
- 因为价格被限制在 -3% 到 3%，OI 数量变化率的解释成本可接受。
- 后续如果要更精确，可以增加 open interest value 维度。

## breakout_watch

用途：识别可能向上突破的临界币。

MVP 条件：

```text
price 接近 recent_high_1h 或 recent_high_24h
AND 最近 15m 价格波动压缩
AND oi_change_15m > 0
AND volume_robust_z_5m 达到放量阈值
AND taker_buy_ratio_5m 偏强
AND market_relative_return_5m >= 0
```

`breakout_watch` 不表示已经突破。确认突破应在后续版本中使用独立的 `breakout_confirmed`。

## breakdown_watch

用途：识别可能向下跌破的临界币。

MVP 条件：

```text
price 接近 recent_low_1h 或 recent_low_24h
AND 最近 15m 价格波动压缩
AND oi_change_15m > 0
AND volume_robust_z_5m 达到放量阈值
AND taker_sell_ratio_5m 偏强
AND market_relative_return_5m <= 0
```

`breakdown_watch` 不表示已经跌破。确认跌破应在后续版本中使用独立的 `breakdown_confirmed`。

## Discord 投递

这些信号可通过 `DISCORD_ALERT_TYPE_ALLOWLIST` 控制是否发送 Discord。

示例：

```env
DISCORD_ALERT_TYPE_ALLOWLIST=daily_flat_oi_buildup,breakout_watch,breakdown_watch,long_squeeze_risk,short_squeeze_risk
```

白名单只影响 Discord 投递，不影响告警生成、告警落库、shadow 复盘和统计。

## 验收

- `daily_flat_oi_buildup` 覆盖触发、不触发、OI 不足 10%、day return 超出范围、baseline 不足。
- `breakout_watch` 覆盖接近上沿但无放量、放量但 taker 不强、市场相对收益为负等不触发场景。
- `breakdown_watch` 覆盖接近下沿但无放量、放量但 taker sell 不强、市场相对收益为正等不触发场景。
- watch 类信号不得被文案描述为已经突破或已经跌破。
