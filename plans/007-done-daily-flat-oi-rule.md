# Daily Flat OI Rule

状态：done

## 目标

实现第一版核心妖币观察信号 `daily_flat_oi_buildup`，用于识别 24h 价格基本横盘但 OI 明显增长的 altcoin。

成功标准：

- 当 `-0.03 <= return_24h <= 0.03`、`oi_change_24h >= 0.10`、baseline ready、且 symbol 属于 altcoin universe 时触发 WARNING。
- baseline 样本不足时不触发。
- 非 altcoin universe 不触发。
- 价格 24h return 超出范围不触发。
- OI 24h change 不足 10% 不触发。
- 输出 payload 包含 `symbol`、`signal_window`、`confirmation_window`、`confirmations`、`trigger_conditions`。

## 涉及变化

新增或修改：

- `monitor/alerts/rules.py`
- `docs/alert-rules.md`
- `tests/test_alerts.py`

## 行为说明

- `return_24h` 和 `oi_change_24h` 使用比例值表示，例如 3% 为 `0.03`，10% 为 `0.10`。
- `daily_flat_oi_buildup` 是 WARNING 观察信号，不表示交易方向，不给自动交易建议。
- 当前版本只实现单条规则，不做冷却、聚合、market digest 或 Discord 投递。

## 测试与验收

- `python -m pytest`
- 覆盖触发、不触发、OI 不足、day return 超出范围、baseline 不足、非 altcoin universe。

## 不做内容

- 不实现 breakout / breakdown / squeeze 规则。
- 不实现 alert engine 批量调度。
- 不写入数据库。
- 不发送 Discord。
