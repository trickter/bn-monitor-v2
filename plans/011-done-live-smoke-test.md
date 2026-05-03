# Live Smoke Test

状态：done

## 目标

补齐第一版本地真实链路冒烟测试能力：启动 TimescaleDB、从 Binance USD-M Futures REST 拉取真实公开数据、生成 `daily_flat_oi_buildup` 候选告警，并通过 Discord webhook 做连通性测试或发送本轮结果。

成功标准：

- `docker compose up -d timescaledb` 可启动本地 TimescaleDB。
- `alembic upgrade head` 可创建 schema。
- `bn-monitor test-discord` 可向配置的 Discord webhook 发送测试消息。
- `bn-monitor live-smoke --symbols ...` 可拉取 Binance 真实 kline 与 OI 数据。
- live smoke 可将触发的 alert 写入数据库，并按投递资格发送 Discord；未触发时输出 projection summary。
- 不打印 `.env` 中的 webhook、数据库密码等敏感值。

## 涉及变化

新增或修改：

- `docker-compose.yml`
- `monitor/binance/rest.py`
- `monitor/discord.py`
- `monitor/cli.py`
- `docs/live-smoke-test.md`
- `tests/test_live_smoke.py`
- `tests/test_discord_client.py`

## 行为说明

- Binance 使用公开 REST API，不需要私有 API key。
- Kline 使用 `/fapi/v1/klines`，interval 为 `1m`。
- OI 使用 `/futures/data/openInterestHist`，period 为 `5m`。
- 当前 live smoke 只支撑 `daily_flat_oi_buildup`，不会凭空实现其它 alert types。
- 如果没有真实触发的告警，`test-discord` 仍可验证 Discord webhook 连通性。

## 测试与验收

- `python -m pytest`
- `docker compose up -d timescaledb`
- `python -m alembic upgrade head`
- `python -m monitor.cli test-discord`
- `python -m monitor.cli live-smoke --symbols <symbol>`

## 不做内容

- 不启动长期 daemon。
- 不接 WebSocket。
- 不实现全部告警规则。
- 不发送交易建议或自动交易动作。
