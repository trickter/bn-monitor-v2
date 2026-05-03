# Project Scaffold And Config Validation

状态：done

## 目标

建立第一版可运行 Python 工程骨架，并实现显式 `.env` 配置校验与 Discord 投递资格判断，为后续 Binance 采集、指标计算和告警规则落地提供基础。

成功标准：

- 项目可通过 `python -m monitor.cli healthcheck` 执行基础健康检查。
- `python -m monitor.cli config-dump` 可输出脱敏后的有效配置。
- 未知 `.env` 配置项会启动失败。
- 枚举、布尔、列表类配置会在启动时校验。
- Discord 投递资格同时满足 `ALERT_MODE == live`、`severity >= DISCORD_MIN_SEVERITY`、以及配置白名单时 `alert_type` 命中白名单。
- 测试覆盖默认配置、未知配置、枚举非法、白名单命中/不命中、severity 不达标和 shadow 模式。

## 涉及变化

配置项：

- `DATABASE_URL`
- `BINANCE_REST_URL`
- `BINANCE_WS_URL`
- `UNIVERSE_MODE`
- `SYMBOLS`
- `ALERT_MODE`
- `DISCORD_WEBHOOK_URL`
- `DISCORD_MIN_SEVERITY`
- `DISCORD_ALERT_TYPE_ALLOWLIST`
- `DATA_RETENTION_DAYS`
- `PRICE_THRESHOLD_BPS`
- `VOLUME_PERCENTILE_THRESHOLD`
- `VOLUME_ROBUST_Z_THRESHOLD`
- `ALERT_COOLDOWN_MINUTES`

代码接口：

- 新增 `monitor.config.Settings` 负责配置读取、默认值、允许值和未知项拒绝。
- 新增 `monitor.alerts.delivery.evaluate_discord_delivery` 负责 Discord 投递资格判断。
- 新增 `monitor.cli` 提供 `healthcheck` 和 `config-dump`。

## 实施步骤

1. 新增配置文档，记录所有 `.env` 配置默认值、允许值和验收方式。
2. 创建 `pyproject.toml`、`.env.example` 和 `monitor/` 基础包。
3. 实现 `Settings`、枚举、白名单解析和脱敏配置输出。
4. 实现 Discord 投递资格判断，不进行真实网络发送。
5. 新增 pytest 测试覆盖配置校验与投递资格。

## 测试与验收

- `python -m pytest`
- `python -m monitor.cli healthcheck`
- `python -m monitor.cli config-dump`

## 不做内容

- 不连接 Binance WebSocket 或 REST。
- 不连接 TimescaleDB，不新增 Alembic 迁移。
- 不真实发送 Discord Webhook。
- 不实现指标计算、告警规则、冷却、聚合或落库。
