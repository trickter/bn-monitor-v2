# 015 — 解耦重构：规则注册表 + Payload Helper + IndicatorContext 分层

## 目标与成功标准

- 新增一条告警规则只需改 `alerts/rules.py` 一个文件（不再手动改 engine.py）。
- `binance/rest.py` 不再依赖 `alerts/rules.py`（反向依赖消除）。
- `alerts/rules.py` 行数从 410 减到 ~310（payload 模板去重）。
- `pytest tests/` 全部通过，行为不变。

## 涉及变化

| 文件 | 变化类型 |
|---|---|
| `monitor/indicators.py` | 新增（从 rules.py 抽取） |
| `monitor/alerts/rules.py` | 重构内部结构，行为不变 |
| `monitor/alerts/engine.py` | import 简化，行为不变 |
| `monitor/binance/rest.py` | 修复 import 方向，行为不变 |
| `docs/alert-engine.md` | 说明注册表机制 |

schema、配置、告警生成行为、payload 结构均不变。

## 实施步骤

### Step 1 — 新建 `monitor/indicators.py`

把以下内容从 `alerts/rules.py` 搬到 `indicators.py`（中性领域层）：

- `IndicatorContext` dataclass
- `AlertDecision` dataclass（也属于规则域，但 engine 和 app 都用，放这里更中立）

### Step 2 — `alerts/rules.py` 内部改造

1. 顶部添加：
   ```python
   from collections.abc import Callable
   RULE_REGISTRY: list[Callable] = []
   def register_rule(fn: Callable) -> Callable:
       RULE_REGISTRY.append(fn)
       return fn
   ```
2. 4 个 `evaluate_*` 函数加 `@register_rule` 装饰器。
3. 添加 2 个 payload helper（减少重复）：
   - `_threshold_cond(field, op, value, threshold)` → `dict`
   - `_between_cond(field, value, min_val, max_val)` → `dict`
4. 用 helper 替换 4 个函数内的重复 trigger_conditions 拼装。
5. import 改为 `from monitor.indicators import IndicatorContext, AlertDecision`。

### Step 3 — `alerts/engine.py` 改造

1. 删除 4 个 `evaluate_*` 的具名 import。
2. 改为 `from monitor.alerts.rules import RULE_REGISTRY`。
3. 删除 `RULE_EVALUATORS` 元组，改用 `RULE_REGISTRY`。

### Step 4 — `binance/rest.py` 修复

1. `from monitor.alerts.rules import IndicatorContext` → `from monitor.indicators import IndicatorContext`。

### Step 5 — 更新文档

- `docs/alert-engine.md` 说明注册表机制。
- 新增 `docs/indicators.md` 说明 `IndicatorContext` 分层。

## 测试与验收

1. `pytest tests/` 全部通过。
2. 验证 `from monitor.indicators import IndicatorContext` 不会间接导入 alerts 或 binance。
3. 验证 `from monitor.binance.rest import BinanceRestClient` 不会间接导入 alerts。

## 明确不做

- 不外部化规则阈值到 .env。
- 不抽 DeliveryProvider 抽象。
- 不改 AlertEngine 输出格式（仍返回 dict 列表）。
- 不改 KNOWN_ALERT_TYPES（留到后续由 RULE_REGISTRY 推导时一起评估）。
