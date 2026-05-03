# Alert Application Service

状态：done

## 目标

实现最小应用服务，将指标上下文输入串联到 Alert Engine 和 repository，实现告警生成与幂等插入的调用路径。

成功标准：

- `generate_and_persist_alerts` 接收 settings、session、indicator contexts。
- 函数调用 Alert Engine 生成 alert values。
- 函数对每条 alert values 调用 `insert_alert_once`。
- 返回生成的告警数量。
- 规则不触发时不调用 repository。

## 涉及变化

新增或修改：

- `monitor/app.py`
- `docs/application-service.md`
- `tests/test_app.py`

## 行为说明

- 本服务不创建 session，不提交事务，事务边界由调用方控制。
- 本服务不发送 Discord，只把投递状态写入 alert values。
- 重复告警由 repository 的 `ON CONFLICT DO NOTHING` 保证幂等。

## 测试与验收

- `python -m pytest`
- 覆盖触发后执行插入、规则不触发不插入、返回数量。

## 不做内容

- 不实现 daemon run loop。
- 不实现 CLI `generate-alerts`。
- 不读取数据库指标快照。
- 不发送 Discord。
