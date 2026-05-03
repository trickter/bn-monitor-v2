# Docs

本目录记录已经确认的功能说明和使用说明。

## 文档索引

- `configuration.md`：`.env` 配置项、默认值、允许值和启动校验。
- `binance-parser.md`：Binance WebSocket 消息解析规则。
- `database.md`：SQLAlchemy models 与 Alembic 初始迁移说明。
- `discord-delivery.md`：Discord 投递资格与白名单规则。
- `repository.md`：核心表幂等写入策略。
- `reports.md`：shadow 复盘统计函数。
- `live-smoke-test.md`：本地 TimescaleDB、Binance REST 和 Discord webhook 冒烟测试。
- `alert-signals.md`：第一版 altcoin MVP 告警信号说明。
- `alert-rules.md`：已实现告警规则的输入、行为和验收方式。
- `alert-engine.md`：告警规则输出到 alerts 表 values 的转换行为。
- `application-service.md`：应用服务的最小调用路径。

## 文档同步原则

功能级新增或修改必须先有 `/plans` 实施计划，再同步本目录文档，最后修改代码。

## 内容要求

功能文档应至少包含：

- 功能目标
- 相关 `.env` 配置项、默认值和允许值
- 运行行为和边界条件
- 告警、投递或数据写入影响
- 测试与验收方式

所有 `.env` 配置必须显式写入文档。未知配置项应在启动时失败，避免拼写错误被静默忽略。
