# Minimal Alert Engine

状态：done

## 目标

实现第一版最小 Alert Engine，将纯规则输出转换为可写入 `alerts` 表的 values，并应用 Discord 投递资格判断。

成功标准：

- 输入 `IndicatorContext` 列表，输出 alert repository values 列表。
- 当前 engine 调用 `daily_flat_oi_buildup` 规则。
- 输出 values 包含 `ts`、`symbol`、`alert_type`、`severity`、`direction`、`score`、`title`、`message`、`payload`、`mode`、`delivery_status`。
- shadow 模式生成告警但 `delivery_status=suppressed`。
- live 模式且满足 severity / allowlist 时 `delivery_status=pending`。
- 不满足 Discord 白名单时 `payload.suppressed_reason=discord_alert_type_not_allowed`。

## 涉及变化

新增或修改：

- `monitor/alerts/engine.py`
- `docs/alert-engine.md`
- `tests/test_alert_engine.py`

## 行为说明

- Alert Engine 只负责生成 alert values，不写入数据库。
- Discord 白名单只影响投递状态，不影响告警生成。
- 当前版本不做 cooldown、symbol bundle、market digest。

## 测试与验收

- `python -m pytest`
- 覆盖 shadow、live pending、allowlist miss、规则不触发。

## 不做内容

- 不实现真实 Discord 发送。
- 不实现数据库 repository 调用。
- 不实现多规则调度配置。
- 不实现聚合、冷却或 market-relative 过滤。
