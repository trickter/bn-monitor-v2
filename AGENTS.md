# Agents Development Guide

本项目是 **币安二级市场 altcoin 异动监控告警系统（bn-monitor）**。

```text
Binance Futures Public Data
  -> 1m K线 / OI / Mark Price / Funding / ForceOrder Snapshot
  -> 市场相对指标
  -> 价格 × 量能 × 主动方向 × OI 结构信号
  -> Shadow / Live 告警
  -> Discord Webhook
  -> TimescaleDB 复盘
```

## 1. 通用规范

### bn-monitor-v2 核心通用约束

本项目为币安二级市场 altcoin 指标异动监控告警项目，开发时请遵循：

1. **规则优先**：先从 `/rules` 了解项目架构、开发规范等。
2. **文档同步**：功能级新增或修改前，先在 `/plans` 中输出实施计划（计划文件名包含 `序号-状态-计划总结`），再更新 `/docs`，再修改代码，避免文档与代码不一致，然后我review之后，你通过git提交推送到https://github.com/trickter/bn-monitor-v2。
3. **解耦与可扩展**：设计模块化，单文件建议不超过700行。
4. **代码修改原则**：遵循以下 **Surgical Changes** 和 **Simplicity First**。
5. **测试优先**：任何功能修改或新增必须有可验证测试。
---

### 变更流程约束

**原则：功能级变更先计划、再文档、后代码。**

- 功能级新增、行为修改、配置新增、schema 调整、告警规则调整，都必须先写 `/plans`。
- `/plans` 文件命名使用 `序号-状态-计划总结.md`，例如 `001-draft-discord-alert-allowlist.md`。
- 计划确认后，必须同步 `/docs` 中的功能说明、配置说明和验收方式。
- 完成计划与文档同步后，才允许修改业务代码。
- typo、格式、纯注释等不改变行为的小修可以不写计划，但不得借小修改变功能。

### .env 配置原则

**原则：显式配置，拒绝隐藏拼写错误。**

- 所有 `.env` 配置项必须先写入规则或文档，再进入代码实现。
- 配置项必须有默认值、允许值、行为说明和验收方式。
- 第一版采用显式白名单策略：未知配置项应导致启动失败。
- 布尔、枚举、列表类配置必须在启动时校验，避免运行时才暴露错误。

### Discord 投递白名单原则

**原则：白名单只控制投递，不控制信号生成。**

- Discord 白名单按 `alert_type` 过滤，配置项为 `DISCORD_ALERT_TYPE_ALLOWLIST`。
- 白名单只影响 Discord 投递，不影响告警生成、告警落库、shadow 复盘和统计。
- Discord 投递必须同时满足 `ALERT_MODE == live`、`severity >= DISCORD_MIN_SEVERITY`、以及配置白名单时 `alert_type` 在白名单内。
- 未配置或空白名单表示不启用白名单，继续只按模式和等级判断投递。
- 第一版不支持 symbol、direction、通配符、排除列表或多频道路由。

### Think Before Coding / 编码前思考

**原则：不要假设，不隐藏困惑。**

在实现前：
- 明确陈述你的假设。如果不确定，先提问。
- 如果有多种理解方式，列出它们，不要默认选择。
- 如果有更简单的实现方案，说明它。必要时提出反对意见。
- 对于不明确的要求，先停下，指出困惑点，再行动。

---

### Simplicity First / 简洁优先

**原则：最小可行代码，避免无关复杂性。**

- 不增加未请求的功能。
- 对一次性使用的代码不要设计复杂抽象。
- 不要实现额外配置或灵活性，除非被要求。
- 不要处理不可能发生的异常。
- 若200行可以压缩到50行，请重写。
- 问自己：“资深工程师会觉得这太复杂吗？” 若是，则简化。

---

### Surgical Changes / 精准修改

**原则：只修改必要部分，只清理自己造成的“垃圾”。**

修改现有代码时：
- 不“顺手改进”旁边代码、注释或格式。
- 不重构未损坏的逻辑。
- 遵循现有风格，即使你会写不同风格。
- 发现死代码，记录并提醒，不随意删除。

你的修改导致的孤立代码：
- 移除你引入但未使用的 imports/变量/函数。
- 不要删除已有死代码，除非被明确要求。

---

### Goal-Driven Execution / 目标驱动执行

**原则：定义成功标准，循环迭代直至验证通过。**

- 将任务拆分为可验证的目标：
    - “增加验证” → 写测试覆盖无效输入 → 使测试通过
    - “修复bug” → 写复现测试 → 使测试通过
    - “重构X” → 确保测试前后通过
- 对多步骤任务，列出计划：
  [步骤] → 验证: [检查点]
  [步骤] → 验证: [检查点]
  [步骤] → 验证: [检查点]

成功标准明确，可独立循环；模糊标准需要持续澄清。


## 2. 指标与信号设计


### 2.1 设计目标

信号用于识别二级市场异常状态，不用于预测价格或自动交易。
系统优先识别以下共振：

- 价格异动
- 成交量异常
- 主动买卖冲击
- K线结构异常
- OI / funding 合约结构变化
- 强平事件确认
- BTC / 全市场噪声过滤

### 2.2 指标分层

INFO 使用 1m 探测指标。
WARNING 使用 5m / 15m / 24h 确认与观察指标。
CRITICAL 必须包含 5m 冲击 + 15m 合约结构共振。

### 2.3 Baseline 原则

所有 percentile / robust z 指标必须有 warmup。
样本不足时不得触发正式告警。
新 symbol 默认进入观察期，避免缺少历史数据导致误报。

### 2.4 Market-relative 原则

普通 altcoin 信号必须同时参考：

- BTC-relative return
- market-median-relative return
- market dispersion

当 BTC 或全市场同步大幅波动时，优先生成 market_digest，而不是对每个 symbol 单独刷屏。

### 2.5 MVP 信号集合

第一版信号优先服务 altcoin / 妖币监控，核心目标是识别：

- 当天价格横盘但 OI 明显增长的蓄力币
- 接近区间上沿、可能向上突破的币
- 接近区间下沿、可能向下跌破的币
- 已经发生的短线放量、主动买卖和强平确认

第一版只实现有限信号，避免 shadow 阶段不可调参。`watch` 类信号表示临界观察，不表示已经突破或跌破。

| alert_type | 周期 | 默认等级 | 用途 |
|---|---:|---|---|
| `price_probe` | 1m | INFO | 价格快速偏离探测 |
| `volume_expansion_5m` | 5m | WARNING | 放量确认 |
| `active_buy_impulse` | 5m | WARNING / CRITICAL | 主动买入冲击 |
| `active_sell_impulse` | 5m | WARNING / CRITICAL | 主动卖出冲击 |
| `wick_hunt` | 1m | WARNING | 插针 / 猎杀流动性 |
| `liquidation_spike_5m` | 5m | WARNING / CRITICAL | 强平 spike 确认 |
| `flat_oi_buildup_15m` | 15m | WARNING | 短线横盘增仓 |
| `daily_flat_oi_buildup` | 24h | WARNING | 当天涨跌幅在 -3% 到 3% 内，且 OI 增长超过 10% |
| `breakout_watch` | 15m / 1h | WARNING | 接近近期上沿，疑似向上突破前兆 |
| `breakdown_watch` | 15m / 1h | WARNING | 接近近期下沿，疑似向下跌破前兆 |
| `long_squeeze_risk` | 5m + 15m | CRITICAL | 多杀多风险 |
| `short_squeeze_risk` | 5m + 15m | CRITICAL | 逼空风险 |

`daily_flat_oi_buildup` 是第一版核心妖币信号，基础条件：

```text
-3% <= day_return <= 3%
AND oi_change_24h >= 10%
AND baseline 样本足够
AND symbol 属于 altcoin universe
```

`breakout_watch` / `breakdown_watch` 的第一版判断应使用近期高低点、价格压缩、OI 变化、5m 放量和 taker 方向共同确认；没有确认前不得命名为 `breakout_confirmed` 或 `breakdown_confirmed`。

强平流是 Binance 推送的 snapshot，不代表完整逐笔强平统计。`liquidation_spike_5m` 只能作为极端行情确认信号，不应声明为完整强平总量。

### 2.6 信号升级规则

- INFO 只依赖 1m 探测条件，默认只落库。
- WARNING 必须有 5m / 15m / 24h 维度确认或观察，包括价格、量能、主动方向、K 线结构、强平 spike、横盘增仓或临界突破/跌破观察。
- CRITICAL 必须先满足 5m 冲击，再至少满足一个 15m 合约结构确认。
- 15m 合约结构确认包括 OI 快速变化、funding 极端分位、强平 spike、横盘增仓、OI 与价格方向共振。
- `score` 用于排序、聚合和升级辅助，不等同于交易方向预测。
- 同一 symbol 短时间内多个信号优先合并为 `symbol_alert_bundle`。
- 同一分钟多个 symbol 共振时优先生成 `market_digest`，避免 Discord 刷屏。

### 2.7 不做什么

第一版信号设计不做：

```text
自动交易决策
订单执行建议
order book 微结构判断
机器学习预测
链上数据解释
完整强平总量统计
```

没有 order book 时，不得声明真实盘口吸收。若后续重新引入吸收类信号，只能表达 K 线、量能、taker 方向和价格位移不足推断出的吸收迹象。

### 2.8 测试验收方式

- 每个 alert rule 必须有单元测试覆盖触发、不触发、baseline 样本不足三类场景。
- Discord 白名单必须测试未配置、命中、不命中、severity 不达标、shadow 模式五类场景。
- market-relative 过滤必须测试 BTC 带动的全市场噪声不会产生大量单 symbol Discord 告警。
- 每条告警必须包含可复盘 `payload`，至少包括 `symbol`、`signal_window`、`confirmation_window`、`confirmations`、`trigger_conditions`。
- shadow 阶段必须可通过 `alert-projection` 统计 `by_type`、`by_severity` 和 total。


## 3. 验收标准

### 稳定性

```text
单进程 MVP 连续运行 7 天
WebSocket 自动重连
REST 限速处理
数据库写入幂等
日志不会无限增长
重启后可继续运行
```

### 数据质量

```text
closed kline 无明显缺口
OI 轮询稳定
时间戳统一使用交易所时间
baseline 有 warmup 机制
新 symbol 不因缺历史数据误报
```

### 信号质量

```text
能识别真实拉盘 / 砸盘
能过滤 BTC 带动的全市场噪声
能识别放量但价格不动的吸收
能识别横盘增仓
每条告警有解释和 payload
```

### 告警质量

```text
默认 shadow 起步
live 模式不刷屏
Discord 429 可恢复
市场共振时发 digest
CRITICAL 不被普通冷却误伤
```


## 4. 参考依据

- Binance Spot WebSocket 文档说明单连接 stream 上限、24h 断连、ping/pong、market-data-only endpoint 等机制：<https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams>
- Binance USD-M Futures kline 文档说明 `x` 字段表示 K 线是否收盘：<https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Kline-Candlestick-Streams>
- Binance USD-M Futures `!forceOrder@arr` 文档说明每个 symbol 每 1000ms 只推送最大一笔强平快照：<https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Liquidation-Order-Streams>
- Discord rate limit 文档要求根据 `X-RateLimit-*` headers 和 429 `retry_after` 处理限流：<https://docs.discord.com/developers/topics/rate-limits>
- TimescaleDB hypertable 文档说明 hypertable 按时间 chunk 分区，并保持普通 PostgreSQL 表的使用方式：<https://www.tigerdata.com/docs/use-timescale/latest/hypertables>
