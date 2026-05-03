# Live Smoke Test

本地 live smoke 用于验证最小真实链路：

```text
TimescaleDB
Binance USD-M Futures public REST
daily_flat_oi_buildup rule
alerts repository
Discord webhook
```

## 启动数据库

```bash
docker compose up -d timescaledb
python -m alembic upgrade head
```

## Discord 连通性

```bash
python -m monitor.cli test-discord
```

该命令只发送测试消息，不依赖告警触发。

## Binance Live Smoke

```bash
python -m monitor.cli live-smoke --symbols SOLUSDT,BNBUSDT
```

行为：

- 从 Binance `/fapi/v1/klines` 拉取 1m K 线。
- 从 Binance `/futures/data/openInterestHist` 拉取 5m OI 历史。
- 计算 24h return 和 24h OI change。
- 运行当前已实现的 `daily_flat_oi_buildup`。
- 将触发的告警写入 `alerts`。
- 若 Discord 投递状态为 `pending`，发送 webhook。

## 边界

- Binance 数据是公开市场数据，不需要 API key。
- 当前只实现 `daily_flat_oi_buildup` 的真实数据冒烟。
- 未触发告警时不会伪造告警；可通过 `test-discord` 验证 webhook。
- 不打印 webhook URL 或数据库密码。
