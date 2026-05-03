# Database Schema

本项目使用 TimescaleDB 存储 Binance USD-M Futures 市场数据、指标快照和告警记录。

核心设计：

- 不存全市场秒级行情，避免磁盘快速膨胀。
- 原始行情最低周期为 `1m closed kline`。
- `5m / 15m` 信号从 1m K 线和 OI snapshot 聚合计算。
- 告警分层：
  - `INFO`：1m 探测，只落库，默认不发 Discord。
  - `WARNING`：5m / 15m / 24h 确认与观察，主力告警。
  - `CRITICAL`：5m 冲击 + 15m 合约结构共振。

所有大时序表使用 TimescaleDB hypertable。

---

## Data Granularity

| 数据 | 粒度 | 用途 |
|---|---:|---|
| Kline | 1m closed | 价格、量能、主动买卖、插针 |
| Mark Price / Funding | 1m snapshot | funding 上下文 |
| Open Interest | 5m snapshot | OI 5m / 15m 变化 |
| Liquidation | event-level | 强平 spike |
| Indicator Snapshot | 1m calculation | 多周期告警输入 |
| Alerts | event-level | 告警与投递状态 |

不落库：

```text
全市场秒级行情
全量 aggTrade
全量 order book
秒级 K 线
```

---

## symbols

交易对元数据。

```sql
CREATE TABLE symbols (
  exchange text NOT NULL,
  market_type text NOT NULL,
  symbol text NOT NULL,
  base_asset text NOT NULL,
  quote_asset text NOT NULL,
  contract_type text,
  status text NOT NULL,
  tick_size numeric(38, 18),
  step_size numeric(38, 18),
  min_notional numeric(38, 18),
  tier integer NOT NULL DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (exchange, market_type, symbol)
);
```

---

## futures_kline_1m

1m 闭合 K 线，是最核心的原始行情表。

```sql
CREATE TABLE futures_kline_1m (
  ts timestamptz NOT NULL,
  symbol text NOT NULL,

  open numeric(38, 18) NOT NULL,
  high numeric(38, 18) NOT NULL,
  low numeric(38, 18) NOT NULL,
  close numeric(38, 18) NOT NULL,

  base_volume numeric(38, 18) NOT NULL,
  quote_volume numeric(38, 18) NOT NULL,
  trade_count integer NOT NULL,

  taker_buy_base_volume numeric(38, 18) NOT NULL,
  taker_buy_quote_volume numeric(38, 18) NOT NULL,

  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts, symbol)
);

SELECT create_hypertable('futures_kline_1m', 'ts', if_not_exists => TRUE);

CREATE INDEX ix_futures_kline_1m_symbol_ts
ON futures_kline_1m (symbol, ts DESC);
```

说明：

- 只写入 closed kline。
- 不单独落库 5m / 15m K 线。
- 5m / 15m 指标从该表聚合。

---

## futures_open_interest

Open Interest snapshot 表。

```sql
CREATE TABLE futures_open_interest (
  ts timestamptz NOT NULL,
  symbol text NOT NULL,

  open_interest numeric(38, 18) NOT NULL,
  open_interest_value numeric(38, 18),

  period text NOT NULL DEFAULT '5m',
  source text NOT NULL DEFAULT 'openInterestHist',

  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts, symbol, period)
);

SELECT create_hypertable('futures_open_interest', 'ts', if_not_exists => TRUE);

CREATE INDEX ix_futures_open_interest_symbol_ts
ON futures_open_interest (symbol, ts DESC);
```

用途：

- `oi_change_5m`
- `oi_change_15m`
- `oi_robust_z_15m`
- `oi_move_norm_15m`
- 横盘增仓
- 多杀多 / 逼空结构确认

---

## futures_mark_price

Mark price 与 funding 上下文。

```sql
CREATE TABLE futures_mark_price (
  ts timestamptz NOT NULL,
  symbol text NOT NULL,

  mark_price numeric(38, 18) NOT NULL,
  index_price numeric(38, 18),
  funding_rate numeric(38, 18),
  next_funding_time timestamptz,

  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts, symbol)
);

SELECT create_hypertable('futures_mark_price', 'ts', if_not_exists => TRUE);

CREATE INDEX ix_futures_mark_price_symbol_ts
ON futures_mark_price (symbol, ts DESC);
```

说明：

- 建议按 1m snapshot 落库。
- 不保留全量 1s mark price。

---

## liquidation_snapshots

强平事件表。

```sql
CREATE TABLE liquidation_snapshots (
  id bigint GENERATED ALWAYS AS IDENTITY,
  ts timestamptz NOT NULL,

  symbol text NOT NULL,
  side text NOT NULL,

  price numeric(38, 18) NOT NULL,
  average_price numeric(38, 18),
  quantity numeric(38, 18) NOT NULL,
  quote_value numeric(38, 18) NOT NULL,

  raw jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts, id)
);

SELECT create_hypertable('liquidation_snapshots', 'ts', if_not_exists => TRUE);

CREATE INDEX ix_liquidation_snapshots_symbol_side_ts
ON liquidation_snapshots (symbol, side, ts DESC);
```

注意：

不要用 `(ts, symbol, side, price)` 当主键，强平事件可能同时间同价格碰撞。

---

## market_factor_1m

市场因子表，用于 BTC-relative 和 market-relative 降噪。

```sql
CREATE TABLE market_factor_1m (
  ts timestamptz NOT NULL,

  btc_return_1m numeric(38, 18),
  eth_return_1m numeric(38, 18),
  market_median_return_1m numeric(38, 18),
  market_dispersion_1m numeric(38, 18),

  btc_return_5m numeric(38, 18),
  eth_return_5m numeric(38, 18),
  market_median_return_5m numeric(38, 18),
  market_dispersion_5m numeric(38, 18),

  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts)
);

SELECT create_hypertable('market_factor_1m', 'ts', if_not_exists => TRUE);
```

---

## indicator_snapshot_1m

每分钟生成一次的多周期指标快照。

```sql
CREATE TABLE indicator_snapshot_1m (
  ts timestamptz NOT NULL,
  symbol text NOT NULL,

  return_1m numeric(38, 18),
  return_5m numeric(38, 18),
  return_15m numeric(38, 18),
  return_24h numeric(38, 18),

  btc_relative_return_1m numeric(38, 18),
  market_relative_return_1m numeric(38, 18),
  btc_relative_return_5m numeric(38, 18),
  market_relative_return_5m numeric(38, 18),

  quote_volume_1m numeric(38, 18),
  quote_volume_5m numeric(38, 18),
  volume_percentile_1m numeric(8, 6),
  volume_robust_z_1m numeric(38, 18),
  volume_percentile_5m numeric(8, 6),
  volume_robust_z_5m numeric(38, 18),

  taker_buy_ratio_1m numeric(8, 6),
  taker_sell_ratio_1m numeric(8, 6),
  taker_buy_ratio_5m numeric(8, 6),

  candle_body_ratio_1m numeric(8, 6),
  candle_body_ratio_5m numeric(8, 6),
  candle_range_bps_1m numeric(38, 18),
  candle_range_bps_5m numeric(38, 18),

  upper_wick_ratio_1m numeric(8, 6),
  lower_wick_ratio_1m numeric(8, 6),
  close_position_ratio_1m numeric(8, 6),

  distance_to_high_1h_bps numeric(38, 18),
  distance_to_low_1h_bps numeric(38, 18),
  distance_to_high_24h_bps numeric(38, 18),
  distance_to_low_24h_bps numeric(38, 18),
  range_compression_15m numeric(38, 18),

  oi_change_5m numeric(38, 18),
  oi_change_15m numeric(38, 18),
  oi_change_24h numeric(38, 18),
  oi_robust_z_15m numeric(38, 18),

  price_move_norm_15m numeric(38, 18),
  oi_move_norm_15m numeric(38, 18),

  funding_rate numeric(38, 18),
  funding_percentile numeric(8, 6),

  price_spike_score numeric(38, 18),
  flat_oi_buildup_score numeric(38, 18),

  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts, symbol)
);

SELECT create_hypertable('indicator_snapshot_1m', 'ts', if_not_exists => TRUE);

CREATE INDEX ix_indicator_snapshot_1m_symbol_ts
ON indicator_snapshot_1m (symbol, ts DESC);
```

说明：

```text
表名是 1m，因为每分钟生成一行。
字段中同时包含 1m / 5m / 15m 指标。
return_24h 可作为 daily_flat_oi_buildup 的 day_return。
distance_to_high_* / distance_to_low_* 和 range_compression_15m 用于 breakout_watch / breakdown_watch。
```

---

## alerts

告警表。

```sql
CREATE TABLE alerts (
  id bigint GENERATED ALWAYS AS IDENTITY,
  ts timestamptz NOT NULL,

  symbol text NOT NULL,
  alert_type text NOT NULL,
  severity text NOT NULL,
  direction text NOT NULL,

  state text NOT NULL,
  score numeric(38, 18) NOT NULL,

  title text NOT NULL,
  message text NOT NULL,
  payload jsonb NOT NULL,

  mode text NOT NULL,
  delivery_status text NOT NULL,
  discord_sent_at timestamptz,

  parent_alert_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (ts, id)
);

SELECT create_hypertable('alerts', 'ts', if_not_exists => TRUE);

CREATE UNIQUE INDEX uq_alerts_source_signal
ON alerts (ts, symbol, alert_type, mode);

CREATE INDEX ix_alerts_replay
ON alerts (symbol, alert_type, severity, ts DESC);
```

### severity

```text
INFO
WARNING
CRITICAL
```

| severity | 含义 | Discord |
|---|---|---|
| `INFO` | 1m 探测 | 默认不发 |
| `WARNING` | 5m 确认 | 默认发送 |
| `CRITICAL` | 5m + 15m 共振 | 高优先级发送 |

### state

```text
open
escalated
resolved
expired
```

### delivery_status

```text
shadow
pending
sent
failed
rate_limited
suppressed
```

`suppressed` 表示告警已生成并落库，但不会发送 Discord。典型原因：

```text
ALERT_MODE=shadow
severity 低于 DISCORD_MIN_SEVERITY
alert_type 不在 DISCORD_ALERT_TYPE_ALLOWLIST
```

不为 Discord 白名单新增数据库字段。若需要复盘过滤原因，建议写入 `payload.suppressed_reason`，例如：

```json
{
  "suppressed_reason": "discord_alert_type_not_allowed"
}
```

### payload 关键字段

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "5m",
  "confirmation_window": "15m",
  "confirmations": [],
  "trigger_conditions": []
}
```

---

## alert_cooldowns

告警冷却表。

```sql
CREATE TABLE alert_cooldowns (
  key text PRIMARY KEY,
  last_sent_at timestamptz NOT NULL,
  last_score numeric(38, 18) NOT NULL,
  count_1h integer NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

推荐 key：

```text
{symbol}:{alert_type}
```

---

## Alert Type Mapping

| alert_type | 周期 | severity |
|---|---:|---|
| `price_probe` | 1m | INFO |
| `volume_expansion_5m` | 5m | WARNING |
| `active_buy_impulse` | 5m | WARNING / CRITICAL |
| `active_sell_impulse` | 5m | WARNING / CRITICAL |
| `wick_hunt` | 1m | WARNING |
| `liquidation_spike_5m` | 5m | WARNING / CRITICAL |
| `flat_oi_buildup_15m` | 15m | WARNING |
| `daily_flat_oi_buildup` | 24h | WARNING |
| `breakout_watch` | 15m / 1h | WARNING |
| `breakdown_watch` | 15m / 1h | WARNING |
| `long_squeeze_risk` | 5m + 15m | CRITICAL |
| `short_squeeze_risk` | 5m + 15m | CRITICAL |
| `market_digest` | same-minute | WARNING / CRITICAL |
| `symbol_alert_bundle` | same-symbol | WARNING / CRITICAL |

说明：

```text
daily_flat_oi_buildup 使用 rolling 24h return 与 oi_change_24h。
breakout_watch / breakdown_watch 使用近期高低点、价格压缩、OI 变化、5m 放量和 taker 方向共同确认。
这些派生指标可从 futures_kline_1m、futures_open_interest 和 indicator_snapshot_1m 聚合得到。
watch 类信号不表示已经突破或跌破。
```

---

## Retention Policy

| 表 | 建议保留 |
|---|---:|
| `futures_kline_1m` | 30-90 天 |
| `futures_open_interest` | 30-90 天 |
| `futures_mark_price` | 7-30 天 |
| `liquidation_snapshots` | 7-30 天 |
| `market_factor_1m` | 30-90 天 |
| `indicator_snapshot_1m` | 30-90 天 |
| `alerts` | 长期 |
| `alert_cooldowns` | 长期 |
| `symbols` | 长期 |

---

## Summary

这个 schema 的核心取舍：

```text
1m 原始数据控制成本
5m / 15m / 24h 指标确认与观察主告警
15m 合约结构确认高优先级风险
INFO 默认只落库
WARNING / CRITICAL 才进入 Discord 主通道
```
