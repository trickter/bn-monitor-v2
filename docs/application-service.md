# Application Service

当前应用服务提供一条最小路径：

```text
IndicatorContext
  -> AlertEngine
  -> alert values
  -> repository.insert_alert_once
```

## generate_and_persist_alerts

职责：

- 接收 `Settings`、SQLAlchemy `Session` 和指标上下文列表。
- 调用 Alert Engine。
- 对每条告警调用幂等插入。
- 返回本轮生成的告警数量。

边界：

- 不创建 session。
- 不提交或回滚事务。
- 不发送 Discord。
- 不读取数据库。

事务控制应由调用方使用 `session_scope` 或上层任务编排完成。
