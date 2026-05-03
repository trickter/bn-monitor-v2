# Repository

当前 repository 层只负责核心表的幂等写入 statement，不做业务判断。

## 写入策略

| 表 | 冲突键 | 冲突行为 |
|---|---|---|
| `symbols` | `(exchange, market_type, symbol)` | `DO UPDATE`，更新交易对元数据。 |
| `futures_kline_1m` | `(ts, symbol)` | `DO UPDATE`，覆盖同一分钟 closed kline 字段。 |
| `alerts` | `(ts, symbol, alert_type, mode)` | `DO NOTHING`，保留首次告警事件。 |

## 边界

- repository 不判断 K 线是否 closed；采集解析层必须只传 closed kline。
- repository 不决定 Discord 是否发送；投递资格由 `monitor.alerts.delivery` 判断。
- repository 不提交事务；事务由调用方控制。
- 当前阶段不提供查询接口和批量写入优化。

## 验收

- PostgreSQL SQL 编译结果包含预期 `ON CONFLICT` 目标。
- 函数会调用传入 session 的 `execute`。
- 不需要本地 TimescaleDB 实例即可运行测试。
