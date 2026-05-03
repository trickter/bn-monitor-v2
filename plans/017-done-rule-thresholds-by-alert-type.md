# 017 — 重构 RULE_THRESHOLDS：按 alert_type 分组嵌套

## 背景与动机

016 实现的 RULE_THRESHOLDS 采用平坦命名空间，key 需要带规则前缀（`BREAKOUT_NEAR_HIGH_BPS`、`FLAT_15M_RETURN_LIMIT`）才能区分归属，随着规则增多会越来越冗长且难以一眼对应到哪条规则。

改为按 alert_type 分组嵌套后：

```
# 旧
RULE_THRESHOLDS={"BREAKOUT_NEAR_HIGH_BPS": "40", "FLAT_15M_RETURN_LIMIT": "0.008"}

# 新
RULE_THRESHOLDS={"breakout_watch": {"near_high_bps": "40"}, "flat_oi_buildup_15m": {"return_limit": "0.008"}}
```

顺带将 `register_rule` 改为接收 `alert_type` 参数，使 alert_type 在注册时声明，而非仅存在于函数体内的 `AlertDecision` 构造调用中。

## 目标与成功标准

- `RULE_THRESHOLDS` 改为两层 JSON：`{alert_type: {key: value}}`。
- 顶层 key 只允许拥有可配置阈值的已知 alert_type；二层 key 只允许该规则的已知阈值名。
- 规则函数内部的 thresholds 参数仍为平坦 `dict[str, Decimal]`（取自对应 alert_type 的子 dict），接口不变。
- `pytest tests/` 全部通过，更新相关测试。

## 涉及变化

| 文件 | 变化类型 |
|---|---|
| `monitor/config.py` | `KNOWN_RULE_THRESHOLD_KEYS` → `KNOWN_RULE_THRESHOLDS`（嵌套 dict），property 返回类型变为 `dict[str, dict[str, Decimal]]`，校验逻辑更新 |
| `monitor/alerts/rules.py` | `register_rule(alert_type)` 变为装饰器工厂；`RULE_REGISTRY` 改为 `list[tuple[str, RuleEvaluator]]`；threshold key 缩短（去掉规则前缀） |
| `monitor/alerts/engine.py` | 迭代 `(alert_type, evaluator)`，传 `settings.rule_thresholds.get(alert_type, {})` |
| `docs/configuration.md` | 更新 RULE_THRESHOLDS 格式说明和可用 key 列表 |
| `.env.example` | 更新示例注释 |
| `tests/test_config.py` | 更新阈值相关测试的 JSON 格式 |
| `tests/test_alerts.py` | 更新自定义阈值测试的 key 名 |

## 各规则可配置的阈值 key（二层）

| alert_type | 可用 key |
|---|---|
| `flat_oi_buildup_15m` | `return_limit`, `oi_buildup_threshold` |
| `daily_flat_oi_buildup` | `return_limit`, `oi_buildup_threshold` |
| `breakout_watch` | `near_high_bps`, `range_compression_max`, `volume_z_min`, `taker_buy_min`, `market_return_min` |
| `breakdown_watch` | `low_distance_bps`, `range_compression_max`, `volume_z_min`, `taker_sell_min` |

## 实施步骤

1. `config.py`：`KNOWN_RULE_THRESHOLD_KEYS` → `KNOWN_RULE_THRESHOLDS: dict[str, frozenset[str]]`，更新校验和 property。
2. `rules.py`：`register_rule(alert_type)` → 装饰器工厂；`RULE_REGISTRY` → `list[tuple[str, RuleEvaluator]]`；规则内 threshold key 缩短。
3. `engine.py`：迭代 `(alert_type, evaluator)`，按 alert_type 取阈值子 dict。
4. 同步文档和 `.env.example`。
5. 更新测试。

## 测试与验收

1. `pytest tests/` 全部通过。
2. 嵌套 JSON 格式的有效配置可加载。
3. 顶层未知 alert_type、二层未知 key、非法 JSON、非法 Decimal 均启动失败。

## 明确不做

- 不校验阈值数值的合理范围。
- 不支持 per-symbol 阈值。
- AlertDecision 内 alert_type 字段保持不变（仍由规则函数自己填写）。
