# Core Repository Upserts

状态：done

## 目标

实现第一版核心 repository 写入层，覆盖交易对元数据、1m closed kline 和告警记录的幂等写入。

成功标准：

- `symbols` 可按 `(exchange, market_type, symbol)` upsert，重复写入更新元数据。
- `futures_kline_1m` 可按 `(ts, symbol)` upsert，重复写入覆盖同一分钟闭合 K 线字段。
- `alerts` 可按唯一索引 `(ts, symbol, alert_type, mode)` 幂等插入，重复写入不改写已有告警。
- repository 函数只构造和执行 SQLAlchemy statement，不承担业务判断。
- 测试覆盖 PostgreSQL SQL 编译结果与 session execute 调用。

## 涉及变化

新增文件：

- `monitor/repository.py`
- `docs/repository.md`
- `tests/test_repository.py`

## 行为说明

- 行情和交易对属于可重放数据，重复写入时以后到数据为准。
- 告警属于事件记录，重复生成同一来源信号时保持首次记录，不执行 update。
- 真实事务边界由调用方通过 `session_scope` 或上层应用控制。

## 测试与验收

- `python -m pytest`
- 编译出的 SQL 包含预期 `ON CONFLICT` 目标。

## 不做内容

- 不连接真实 PostgreSQL / TimescaleDB。
- 不实现查询接口。
- 不实现 delivery status 后置更新。
- 不实现批量写入优化。
