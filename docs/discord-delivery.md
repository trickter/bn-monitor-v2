# Discord Delivery

Discord 投递只负责把已经生成并落库的告警发送到 Discord，不参与信号生成。

## 配置

```env
ALERT_MODE=shadow
DISCORD_WEBHOOK_URL=
DISCORD_MIN_SEVERITY=WARNING
DISCORD_ALERT_TYPE_ALLOWLIST=
```

## 投递资格

发送 Discord 必须同时满足：

```text
ALERT_MODE == live
AND severity >= DISCORD_MIN_SEVERITY
AND alert_type in DISCORD_ALERT_TYPE_ALLOWLIST if configured
```

## 白名单规则

- `DISCORD_ALERT_TYPE_ALLOWLIST` 使用逗号分隔的 `alert_type` 列表。
- 未配置或空值表示不启用白名单。
- 配置后只允许列表中的 `alert_type` 发 Discord。
- 白名单只影响 Discord 投递，不影响告警生成、告警落库、shadow 复盘和统计。
- 未知 `alert_type` 配置应启动失败。
- 第一版不支持 symbol、direction、通配符、排除列表或多频道路由。

## suppressed

`delivery_status=suppressed` 表示告警已生成并落库，但不会发送 Discord。

典型原因：

```text
ALERT_MODE=shadow
severity 低于 DISCORD_MIN_SEVERITY
alert_type 不在 DISCORD_ALERT_TYPE_ALLOWLIST
```

若需要复盘过滤原因，写入 `payload.suppressed_reason`。
