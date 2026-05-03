# Altcoin MVP Alert Signals

状态：done

## 目标

将 MVP 告警信号调整为更适合 altcoin / 妖币监控，重点识别横盘增仓、临界突破、临界跌破和短线冲击确认。

## 变更

- `AGENTS.md` 的 `2.5 MVP 信号集合` 已调整为 altcoin 优先。
- 新增核心信号：`daily_flat_oi_buildup`、`breakout_watch`、`breakdown_watch`。
- 将 `flat_oi_buildup` 明确为 `flat_oi_buildup_15m`，避免和日内横盘增仓混淆。
- 同步 `rules/architecture.md` 的多周期告警设计。
- 同步 `rules/database-schema.md` 的 Alert Type Mapping。
- 补充 `indicator_snapshot_1m` 的 24h return、24h OI 变化、距离高低点和压缩度派生字段。
- 新增 `docs/alert-signals.md` 记录具体条件和验收方式。

## 验收

- `daily_flat_oi_buildup` 条件包含 `-3% <= day_return <= 3%` 和 `oi_change_24h >= 10%`。
- `breakout_watch` / `breakdown_watch` 明确是 watch 类信号，不表示已突破或已跌破。
- 白名单可使用这些 `alert_type` 控制 Discord 投递。
- 本次不新增业务代码。
