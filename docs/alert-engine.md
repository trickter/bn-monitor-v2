# Alert Engine

当前 Alert Engine 是最小实现：接收指标上下文，执行已实现规则，返回可写入 `alerts` 表的 values。

## 规则注册机制

规则函数通过 `@register_rule` 装饰器自注册到 `RULE_REGISTRY`。`AlertEngine` 在运行时迭代该列表，**新增规则只需在 `alerts/rules.py` 中定义函数并加装饰器，不需要改 engine.py**。

## 当前规则

- `flat_oi_buildup_15m`
- `daily_flat_oi_buildup`
- `breakout_watch`
- `breakdown_watch`

## 输出行为

每条触发的规则输出：

```text
ts
symbol
alert_type
severity
direction
score
title
message
payload
mode
delivery_status
```

`mode` 来自 `ALERT_MODE`。

`delivery_status` 来自 Discord 投递资格判断：

- `pending`：live 模式且满足最低等级与白名单。
- `suppressed`：shadow 模式、等级不足或不在白名单。

如果被 suppressed，engine 会把原因写入 `payload.suppressed_reason`，便于 shadow 复盘。

## 边界

- Discord 白名单只影响投递状态，不影响告警生成。
- 当前 engine 不写数据库。
- 当前 engine 不做 cooldown、same-symbol bundle 或 market digest。
