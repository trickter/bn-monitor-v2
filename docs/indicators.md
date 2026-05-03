# Indicators

`monitor/indicators.py` 是中性领域层，存放跨模块共用的指标与告警决策数据结构。

## 设计原则

- 不依赖 `alerts/`、`binance/` 或 `config`。
- `binance/rest.py`（数据源层）和 `alerts/rules.py`（规则层）都从这里 import。
- 任何新交易所客户端或新指标计算模块都应输出 `IndicatorContext`，以复用告警规则层。

## IndicatorContext

规则评估所需的市场指标快照，由数据源层（如 `binance/rest.py`）填充。

字段说明：

| 字段 | 类型 | 含义 |
|---|---|---|
| `ts` | datetime | 快照时间戳（交易所时间） |
| `symbol` | str | 交易对符号 |
| `return_24h` | Decimal \| None | 24h 价格涨跌幅 |
| `oi_change_24h` | Decimal \| None | 24h OI 变化率 |
| `baseline_ready` | bool | baseline 样本是否充足 |
| `is_altcoin` | bool | 是否属于 altcoin universe |
| `return_15m` | Decimal \| None | 15m 价格涨跌幅 |
| `oi_change_15m` | Decimal \| None | 15m OI 变化率 |
| `distance_to_high_1h_bps` | Decimal \| None | 距离 1h 最高点（bps） |
| `distance_to_high_24h_bps` | Decimal \| None | 距离 24h 最高点（bps） |
| `distance_to_low_1h_bps` | Decimal \| None | 距离 1h 最低点（bps） |
| `distance_to_low_24h_bps` | Decimal \| None | 距离 24h 最低点（bps） |
| `range_compression_15m` | Decimal \| None | 15m 价格区间压缩比 |
| `volume_robust_z_5m` | Decimal \| None | 5m 成交量 robust z-score |
| `taker_buy_ratio_5m` | Decimal \| None | 5m 主动买入占比 |
| `taker_sell_ratio_5m` | Decimal \| None | 5m 主动卖出占比 |
| `market_relative_return_5m` | Decimal \| None | 5m 相对市场超额收益 |

## AlertDecision

规则评估结果，由 `alerts/rules.py` 中的规则函数返回，`AlertEngine` 消费并转换为可写入数据库的 values dict。
