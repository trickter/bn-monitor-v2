# 016 — 规则阈值外部化：RULE_THRESHOLDS

## 目标与成功标准

- 用一个 `RULE_THRESHOLDS` JSON 字符串字段统一管理所有规则阈值。
- 未配置时行为与现在完全一致（使用 rules.py 中的默认常量）。
- 非法 key / 非法 Decimal 值 / 非法 JSON 均导致启动失败，不可静默忽略。
- `pytest tests/` 全部通过，新增对配置阈值覆盖的测试。

## 涉及变化

| 文件 | 变化类型 |
|---|---|
| `monitor/config.py` | 新增字段 `RULE_THRESHOLDS`、`KNOWN_RULE_THRESHOLD_KEYS`、`rule_thresholds` property 和校验逻辑 |
| `monitor/alerts/rules.py` | 4 个 `evaluate_*` 函数新增可选 `thresholds` 参数 |
| `monitor/alerts/engine.py` | 调用时传入 `settings.rule_thresholds` |
| `docs/configuration.md` | 新增 `RULE_THRESHOLDS` 配置项说明 |
| `tests/test_config.py` | 新增阈值相关测试 |
| `tests/test_alerts.py` | 新增自定义阈值触发测试 |

schema、告警行为、payload 结构不变。

## 设计

**格式**：`RULE_THRESHOLDS={"FLAT_15M_RETURN_LIMIT": "0.005", "OI_BUILDUP_15M_THRESHOLD": "0.03"}`

- JSON object，key 为已知阈值名（大写字母），value 为可解析为 `Decimal` 的字符串或数字。
- 默认为空对象 `{}`，即不覆盖任何默认值。
- 未配置等同于 `{}`，不进入白名单校验。

**可配置的 13 个 key**（与 rules.py 中常量同名）：

```
DAILY_FLAT_RETURN_LIMIT, DAILY_OI_BUILDUP_THRESHOLD,
FLAT_15M_RETURN_LIMIT, OI_BUILDUP_15M_THRESHOLD,
BREAKOUT_NEAR_HIGH_BPS, BREAKOUT_RANGE_COMPRESSION_MAX,
BREAKOUT_VOLUME_ROBUST_Z_MIN, BREAKOUT_TAKER_BUY_RATIO_MIN,
BREAKOUT_MARKET_RELATIVE_RETURN_MIN,
BREAKDOWN_LOW_DISTANCE_BPS, BREAKDOWN_RANGE_COMPRESSION_MAX,
BREAKDOWN_VOLUME_ROBUST_Z_MIN, BREAKDOWN_TAKER_SELL_RATIO_MIN
```

**规则函数签名**：`evaluate_xxx(snapshot, thresholds=None)`。
`thresholds=None` 时等价于 `{}`，即全部使用模块常量默认值。不改动现有测试。

## 实施步骤

1. `config.py`：添加 `KNOWN_RULE_THRESHOLD_KEYS`、字段、property、校验（JSON 解析、key 白名单、Decimal 可转换）。
2. `rules.py`：4 个函数加 `thresholds: dict[str, Decimal] | None = None`，用 `t = thresholds or {}` + `t.get(KEY, DEFAULT)` 读阈值。
3. `engine.py`：`evaluator(snapshot, settings.rule_thresholds)` 传入 thresholds。
4. 同步文档。
5. 补测试：非法 JSON、未知 key、自定义阈值改变触发行为。

## 测试与验收

1. `pytest tests/` 全部通过。
2. 配置 `RULE_THRESHOLDS={"UNKNOWN_KEY": "1"}` 启动失败。
3. 配置 `RULE_THRESHOLDS=not-json` 启动失败。
4. 配置有效覆盖后规则使用新阈值（测试覆盖）。

## 明确不做

- 不支持逐个字段 env var（如 `FLAT_15M_RETURN_LIMIT=0.005`）。
- 不支持 per-symbol 阈值。
- 不校验阈值的数值合理性（如不验证阈值 > 0），只验证 Decimal 可转换。
