# Configuration

本项目采用显式 `.env` 配置策略：所有允许的配置项必须写入文档和代码，未知配置项启动失败，避免拼写错误被静默忽略。

## 配置项

| 配置项 | 默认值 | 允许值 / 格式 | 行为 |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/bn_monitor` | PostgreSQL URL | 后续数据库连接使用。当前骨架只校验存在非空值。 |
| `BINANCE_REST_URL` | `https://fapi.binance.com` | URL | Binance USD-M REST 基础地址。 |
| `BINANCE_WS_URL` | `wss://fstream.binance.com/stream` | URL | Binance USD-M WebSocket 基础地址。 |
| `UNIVERSE_MODE` | `top_usdt` | `top_usdt` / `explicit` | `explicit` 时必须配置 `SYMBOLS`。 |
| `SYMBOLS` | 空 | 逗号分隔 symbol，如 `SOLUSDT,BNBUSDT` | 显式交易对列表；会去空格、转大写、去重。 |
| `ALERT_MODE` | `shadow` | `shadow` / `live` | `shadow` 只落库不投递 Discord；`live` 才允许进入投递判断。 |
| `DISCORD_WEBHOOK_URL` | 空 | 空或 URL | 真实 Discord Webhook 地址。当前骨架不发送网络请求。 |
| `DISCORD_MIN_SEVERITY` | `WARNING` | `INFO` / `WARNING` / `CRITICAL` | Discord 最低投递等级。 |
| `DISCORD_ALERT_TYPE_ALLOWLIST` | 空 | 逗号分隔已知 `alert_type` | 未配置或空值表示不启用白名单；配置后只允许命中的 `alert_type` 投递。 |
| `DATA_RETENTION_DAYS` | `30` | 正整数 | 后续数据保留任务使用。 |
| `PRICE_THRESHOLD_BPS` | `100` | 正数 | 后续价格异动阈值。 |
| `VOLUME_PERCENTILE_THRESHOLD` | `0.95` | `0` 到 `1` | 后续成交量分位阈值。 |
| `VOLUME_ROBUST_Z_THRESHOLD` | `3.0` | 正数 | 后续成交量 robust z 阈值。 |
| `ALERT_COOLDOWN_MINUTES` | `10` | 正整数 | 默认告警冷却分钟数。 |

## Discord 投递资格

Discord 投递必须同时满足：

```text
ALERT_MODE == live
AND severity >= DISCORD_MIN_SEVERITY
AND alert_type in DISCORD_ALERT_TYPE_ALLOWLIST if configured
```

未满足时应返回 `delivery_status=suppressed`，并给出可复盘原因：

- `alert_mode_shadow`
- `severity_below_minimum`
- `discord_alert_type_not_allowed`

## 已知 alert_type

第一版允许配置以下告警类型：

```text
price_probe
volume_expansion_5m
active_buy_impulse
active_sell_impulse
wick_hunt
liquidation_spike_5m
flat_oi_buildup_15m
daily_flat_oi_buildup
breakout_watch
breakdown_watch
long_squeeze_risk
short_squeeze_risk
market_digest
symbol_alert_bundle
```

`DISCORD_ALERT_TYPE_ALLOWLIST` 中出现未知 `alert_type` 时必须启动失败。

## 验收

- 默认配置可加载，且 `ALERT_MODE=shadow`、`DISCORD_MIN_SEVERITY=WARNING`。
- `.env` 中出现未知配置项时启动失败。
- `ALERT_MODE`、`DISCORD_MIN_SEVERITY`、`UNIVERSE_MODE` 非法时启动失败。
- `UNIVERSE_MODE=explicit` 但 `SYMBOLS` 为空时启动失败。
- Discord 白名单覆盖未配置、命中、不命中、severity 不达标、shadow 模式五类场景。
