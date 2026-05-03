# Database

当前版本提供 SQLAlchemy models 与 Alembic 初始迁移，用于描述 TimescaleDB schema。此阶段不连接真实数据库，也不执行迁移。

## 核心表

- `symbols`
- `futures_kline_1m`
- `futures_open_interest`
- `futures_mark_price`
- `liquidation_snapshots`
- `market_factor_1m`
- `indicator_snapshot_1m`
- `alerts`
- `alert_cooldowns`

大时序表在迁移中会转换为 TimescaleDB hypertable：

- `futures_kline_1m`
- `futures_open_interest`
- `futures_mark_price`
- `liquidation_snapshots`
- `market_factor_1m`
- `indicator_snapshot_1m`
- `alerts`

## 约束

- `alerts.severity` 限定为 `INFO`、`WARNING`、`CRITICAL`。
- `alerts.state` 限定为 `open`、`escalated`、`resolved`、`expired`。
- `alerts.delivery_status` 限定为 `shadow`、`pending`、`sent`、`failed`、`rate_limited`、`suppressed`。
- `alerts.direction` 第一版限定为 `none`、`up`、`down`、`long`、`short`。
- `alerts` 使用唯一索引 `(ts, symbol, alert_type, mode)` 防止同一信号重复落库。

## 验收

- SQLAlchemy metadata 能枚举全部核心表。
- 关键列类型与规则文档一致，包括 `alerts.payload`、`liquidation_snapshots.raw` 的 JSONB 字段。
- Alembic 初始迁移包含 hypertable 创建语句。
- 当前阶段不要求本地有 TimescaleDB 实例。
