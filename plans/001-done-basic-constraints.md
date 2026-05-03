# 基本约束调整

状态：done

## 目标

统一项目基础约束：规则优先、功能级变更先计划再文档后代码、`.env` 显式配置、Discord 告警类型白名单可控。

## 变更

- 调整 `AGENTS.md`，补充变更流程、`.env` 配置原则、Discord 投递白名单原则。
- 补完整 `AGENTS.md` 的指标与信号设计，包括 MVP 信号集合、升级规则、不做内容和测试验收方式。
- 调整 `rules/architecture.md`，补充 `DISCORD_ALERT_TYPE_ALLOWLIST`、Discord 投递判断顺序和显式配置原则。
- 调整 `rules/database-schema.md`，补充 `delivery_status=suppressed` 的原因说明。
- 新增 `plans/README.md`、`docs/README.md` 和 Discord 投递配置文档。

## 验收

- `DISCORD_ALERT_TYPE_ALLOWLIST` 在规则和文档中有一致说明。
- `DISCORD_MIN_SEVERITY` 与白名单关系明确为 AND。
- `suppressed` 状态语义包含 shadow、severity 不达标、alert_type 不在白名单。
- 本次不新增业务代码、不新增数据库字段。
