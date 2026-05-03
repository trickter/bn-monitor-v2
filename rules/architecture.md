# Architecture

## 1. 核心目标

本项目是一个 Binance USD-M Futures 市场异常监控系统。

核心目标：

```text
以 1m K 线作为最低原始行情周期，
通过 1m / 5m / 15m 多周期指标分层判断异常，
降低秒级采样带来的磁盘压力，
并通过 shadow/live 模式安全调参和推送告警。
```

告警分层：

```text
INFO      = 1m 探测信号，只落库，默认不发 Discord
WARNING   = 5m / 15m / 24h 确认与观察信号，主力告警
CRITICAL  = 5m 冲击 + 15m 合约结构共振，高优先级告警
```

---

## 2. 核心技术决策

### 后端技术栈

```text
Python 3.12+
asyncio
websockets 或 aiohttp
httpx
SQLAlchemy 2.x
Alembic
pydantic-settings
structlog / loguru
Docker Compose
TimescaleDB
Discord Webhook
```

### 数据库

采用：

```text
TimescaleDB = PostgreSQL + 时序扩展
```

原因：

```text
保留 PostgreSQL SQL / 生态 / Alembic 迁移体验
支持 hypertable、自动 chunk、压缩、连续聚合
比 vanilla PostgreSQL 更适合 K 线、指标、告警、baseline 这类时序数据
```

### 数据粒度

不采用全市场秒级采样。

最低原始行情周期：

```text
1m closed kline
```

原因：

```text
秒级 mark price / trade / order book 数据量过大
当前策略核心依赖 1m / 5m / 15m 结构，不需要全量秒级数据
5m / 15m 指标可以从 1m K 线和 OI snapshot 聚合得到
```

例外：

```text
liquidation_snapshots 保留事件级数据
```

因为强平事件不是全市场连续秒级采样，体量相对可控，且对极端行情有较高价值。

---

## 3. 项目结构

```text
project-root/
├── docs/
│   ├── README.md
│   ├── alert-signals.md
│   └── discord-delivery.md
├── plans/
│   ├── README.md
│   ├── 001-done-basic-constraints.md
│   └── 002-done-altcoin-mvp-alert-signals.md
├── rules/
│   ├── architecture.md
│   └── database-schema.md

├── AGENTS.md
├── CLAUDE.md
│
├── monitor/
│   ├── __init__.py
│   ├── app.py
│   ├── cli.py
│   ├── config.py
│   ├── db.py
│   ├── logging.py
│   │
│   ├── models.py
│   ├── repository.py
│   │
│   ├── binance/
│   │   ├── __init__.py
│   │   ├── rest.py
│   │   ├── ws.py
│   │   ├── parser.py
│   │   └── universe.py
│   │
│   ├── indicators/
│   │   ├── __init__.py
│   │   ├── compute.py
│   │   ├── baseline.py
│   │   ├── market_factor.py
│   │   └── normalization.py
│   │
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── rules.py
│   │   ├── cooldown.py
│   │   ├── aggregation.py
│   │   └── delivery.py
│   │
│   ├── discord.py
│   ├── quality.py
│   └── reports.py
│
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial.py
│
├── tests/
│   ├── test_binance.py
│   ├── test_indicators.py
│   ├── test_alerts.py
│   ├── test_discord.py
│   ├── test_repository.py
│   └── test_schema.py
│
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md

```

## 4. 告警模式

必须支持：

```text
ALERT_MODE=shadow | live
```

默认先用 `shadow` 跑 3-7 天：

```text
shadow：只落库，不发 Discord
live：落库并发送 Discord
```

这是避免阈值未调好时把 Discord 频道炸掉的关键设计。

### Discord 最低推送等级

新增：

```text
DISCORD_MIN_SEVERITY=WARNING
DISCORD_ALERT_TYPE_ALLOWLIST=
```

默认行为：

```text
INFO      只落库，delivery_status=suppressed
WARNING   发 Discord
CRITICAL  发 Discord，高优先级
```

如果调试阶段希望把 1m 探测也推送，可以改为：

```text
DISCORD_MIN_SEVERITY=INFO
```

### Discord 告警类型白名单

可选配置：

```env
DISCORD_ALERT_TYPE_ALLOWLIST=daily_flat_oi_buildup,breakout_watch,breakdown_watch,long_squeeze_risk,short_squeeze_risk
```

发送 Discord 必须同时满足：

```text
ALERT_MODE == live
AND severity >= DISCORD_MIN_SEVERITY
AND alert_type in DISCORD_ALERT_TYPE_ALLOWLIST if configured
```

规则：

```text
未配置或空值表示不启用白名单
白名单只影响 Discord 投递
不影响告警生成、告警落库、shadow 复盘和统计
未知 alert_type 配置应启动失败
第一版不支持 symbol、direction、通配符、排除列表或多频道路由
```

---

## 5. 数据采集架构

### 数据源

| 数据 | 来源 | 落库周期 | 表 |
|---|---|---:|---|
| 1m K 线 | Binance kline stream / REST backfill | 1m closed | `futures_kline_1m` |
| Mark price / Funding | mark price stream / REST | 1m snapshot | `futures_mark_price` |
| Open Interest | REST openInterestHist | 5m | `futures_open_interest` |
| 强平事件 | forceOrder stream | event-level | `liquidation_snapshots` |
| 交易对元数据 | exchangeInfo | startup / periodic | `symbols` |

### 不采集的数据

第一版不采集：

```text
秒级 K 线
全量 aggTrade
全量 order book
spot 数据
用户私有数据
链上数据
自动交易数据
```

---

## 6. 数据处理流水线

整体流程：

```text
Binance WS / REST
        |
        v
Raw Time-Series Tables
        |
        v
Indicator Computation
        |
        v
indicator_snapshot_1m
        |
        v
Alert Decision Engine
        |
        v
alerts
        |
        v
Discord Delivery
```

### 采集层

职责：

```text
连接 Binance WS
处理断线重连
只写入 closed 1m kline
定期 REST backfill
定期拉取 OI / funding / exchangeInfo
写入 TimescaleDB hypertable
```

### 指标层

每分钟计算一次多周期指标。

输入：

```text
futures_kline_1m
futures_open_interest
futures_mark_price
liquidation_snapshots
market_factor_1m
```

输出：

```text
indicator_snapshot_1m
```

虽然表名是 `indicator_snapshot_1m`，但它表示：

```text
每分钟生成一次的多周期指标快照
```

包含：

```text
1m price / volume / taker / wick
5m price / volume / taker confirmation
15m OI / funding / flat OI structure
1h / 24h high-low distance, range compression, rolling return and OI change
```

---

## 7. 多周期告警设计

### INFO：1m 探测

目的：

```text
快速捕捉异常，但避免噪声推送
```

典型类型：

```text
price_probe
```

特点：

```text
1m 快
噪声大
默认只落库
用于复盘和后续升级判断
```

### WARNING：5m / 15m / 24h 确认与观察

目的：

```text
确认真实放量、真实主动方向、临界突破/跌破观察、横盘增仓结构
```

典型类型：

```text
volume_expansion_5m
active_buy_impulse
active_sell_impulse
wick_hunt
liquidation_spike_5m
flat_oi_buildup_15m
daily_flat_oi_buildup
breakout_watch
breakdown_watch
```

特点：

```text
这是主力告警层
默认发送 Discord
需要更强确认条件
watch 类信号只表示临界观察，不表示已经突破或跌破
```

### CRITICAL：5m + 15m 共振

目的：

```text
只把真正的结构性风险提升为高优先级
```

升级条件：

```text
5m 价格 / 量能 / 主动方向冲击
+
至少一个 15m 合约结构确认
```

15m 结构确认包括：

```text
OI 快速变化
funding 极端分位
强平 5m spike
横盘增仓
OI 收缩 / 增仓与价格方向共振
```

典型类型：

```text
long_squeeze_risk
short_squeeze_risk
active_buy_impulse with CRITICAL
active_sell_impulse with CRITICAL
liquidation_spike_5m with CRITICAL
```

---

## 8. Alert Engine

告警引擎输入：

```text
latest indicator_snapshot_1m
latest liquidation aggregation
settings thresholds
cooldown state
```

告警引擎输出：

```text
AlertDecision
```

核心字段：

```text
alert_type
severity
direction
score
title
message
payload
```

payload 必须包含：

```json
{
  "symbol": "SOLUSDT",
  "signal_window": "5m",
  "confirmation_window": "15m",
  "confirmations": [],
  "trigger_conditions": []
}
```

### Alert State

```text
open
escalated
resolved
expired
```

### Delivery Status

```text
shadow
pending
sent
failed
rate_limited
suppressed
```

---

## 9. 降噪设计

### Market-relative 过滤

普通 alt 告警需要同时满足：

```text
BTC-relative
market-median-relative
```

BTC / ETH 特殊处理：

```text
BTC-relative 对 BTC 无意义
BTC / ETH 使用 market-relative 路径
```

### Same-symbol 聚合

同一 symbol 短时间内触发多个信号时，合并为：

```text
symbol_alert_bundle
```

目的：

```text
避免同一个币在几秒内连续刷屏
保留 component alert types 和 scores
```

### Market Digest

同一分钟内多个 symbol 触发时，合并为：

```text
market_digest
```

目的：

```text
识别市场共振
避免 BTC 大波动时全市场刷屏
```

### Cooldown

冷却 key：

```text
{symbol}:{alert_type}
```

默认建议：

```json
{
  "CRITICAL": 5,
  "WARNING": 10,
  "INFO": 10,
  "flat_oi_buildup_15m": 60,
  "daily_flat_oi_buildup": 240,
  "breakout_watch": 60,
  "breakdown_watch": 60
}
```

---

## 10. 数据库架构

核心表：

```text
symbols
futures_kline_1m
futures_open_interest
futures_mark_price
liquidation_snapshots
market_factor_1m
indicator_snapshot_1m
alerts
alert_cooldowns
```

所有大时序表使用 TimescaleDB hypertable：

```text
futures_kline_1m
futures_open_interest
futures_mark_price
liquidation_snapshots
market_factor_1m
indicator_snapshot_1m
alerts
```

不把 5m / 15m K 线作为原始表落库。

原因：

```text
减少存储
减少迁移复杂度
避免同一事实在多个周期表中重复存储
5m / 15m 指标可以从 1m 原始数据计算
```

---

## 11. Retention Strategy

推荐初始保留策略：

| 表 | 保留时间 |
|---|---:|
| `futures_kline_1m` | 30-90 天 |
| `futures_open_interest` | 30-90 天 |
| `futures_mark_price` | 7-30 天 |
| `liquidation_snapshots` | 7-30 天 |
| `market_factor_1m` | 30-90 天 |
| `indicator_snapshot_1m` | 30-90 天 |
| `alerts` | 长期 |
| `alert_cooldowns` | 长期 |
| `symbols` | 长期 |

如果后续需要长期强平统计，可以增加分钟级聚合表：

```text
liquidation_1m_agg
```

而不是永久保留全部 raw liquidation events。

---

## 12. Deployment

推荐使用 Docker Compose：

```text
app
timescaledb
```

启动流程：

```text
alembic upgrade head
start monitor app
healthcheck
```

关键环境变量：

```text
DATABASE_URL
BINANCE_REST_URL
BINANCE_WS_URL
UNIVERSE_MODE
SYMBOLS
ALERT_MODE
DISCORD_WEBHOOK_URL
DISCORD_MIN_SEVERITY
DISCORD_ALERT_TYPE_ALLOWLIST
DATA_RETENTION_DAYS
PRICE_THRESHOLD_BPS
VOLUME_PERCENTILE_THRESHOLD
VOLUME_ROBUST_Z_THRESHOLD
ALERT_COOLDOWN_MINUTES
```

配置原则：

```text
所有 .env 配置必须显式列入规则或文档
未知配置项应启动失败
枚举、布尔、列表类配置必须在启动时校验
```

---

## 13. Observability

日志建议使用结构化日志：

```text
structlog / loguru
```

关键日志事件：

```text
binance_ws_connected
binance_ws_reconnected
binance_ws_message_failed
kline_upserted
open_interest_polled
mark_price_polled
indicators_computed
alerts_generated
alert_suppressed
discord_sent
discord_rate_limited
retention_completed
```

关键监控指标：

```text
latest kline staleness
latest OI staleness
latest mark price staleness
indicator compute latency
alerts generated per cycle
Discord send success rate
database write latency
WS reconnect count
```

---

## 14. Failure Handling

### Binance WS 断线

策略：

```text
自动重连
记录 reconnect count
恢复后通过 REST backfill 补最近 K 线
```

### REST rate limit

策略：

```text
限制并发
限制每秒请求数
失败指数退避
优先保证核心 symbol
```

### Discord 失败

策略：

```text
429 按 retry_after 等待
5xx 重试
4xx 记录 failed
delivery_status 持久化
```

### 数据缺口

策略：

```text
data-quality command 检查 gap ratio
缺失数据时该 symbol 暂停告警
指标 baseline 样本不足时不触发
```

---

## 15. CLI Tools

建议提供：

```text
bn-monitor run
bn-monitor healthcheck
bn-monitor config-dump
bn-monitor poll-once
bn-monitor compute-indicators
bn-monitor generate-alerts
bn-monitor alert-projection --hours 48
bn-monitor alert-summary --lookback-hours 24
bn-monitor alert-show <id>
bn-monitor data-quality --lookback-hours 24
bn-monitor retention-run
bn-monitor test-discord
```

其中：

```text
alert-projection
```

用于 shadow 阶段回放当前规则，统计：

```text
by_type
by_severity
total
```

方便判断 INFO / WARNING / CRITICAL 的触发密度是否合理。

---

## 16. Non-goals

第一版不做：

```text
自动交易
订单执行
仓位管理
用户私有账户接入
秒级全量行情存储
order book 微结构分析
跨交易所套利
链上数据分析
机器学习预测
```

这些可以后续作为独立模块演进，不应影响当前监控系统的稳定性。

---

## 17. 总结

本架构的核心取舍是：

```text
用 1m 原始数据控制存储成本
用 5m 确认降低噪声
用 15m 合约结构识别高优先级风险
用 shadow/live 保护告警频道
用 TimescaleDB 保持时序查询和 PostgreSQL 生态兼容
```

最终目标不是捕捉每一次秒级波动，而是稳定识别：

```text
价格异动
真实放量
主动买卖冲击
插针 / 猎杀
强平 spike
OI 快速变化
短线横盘增仓
日内横盘增仓
临界突破观察
临界跌破观察
多杀多 / 逼空风险
```
