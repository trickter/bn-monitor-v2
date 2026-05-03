# Reports

当前 reports 模块只提供 shadow 复盘的基础统计函数。

## summarize_alert_projection

输入：alert values iterable。

输出：

```json
{
  "total": 0,
  "by_type": {},
  "by_severity": {}
}
```

用途：

- shadow 阶段统计当前规则触发密度。
- 后续 `alert-projection` CLI 可复用该函数。

边界：

- 当前不读取数据库。
- 当前不负责规则回放。
- 当前不输出文件。
