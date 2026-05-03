# Alert Projection Summary

状态：done

## 目标

实现 shadow 复盘所需的告警统计核心函数，对 alert values 汇总 `total`、`by_type` 和 `by_severity`。

成功标准：

- 输入 alert values iterable，输出稳定字典结构。
- 统计 `total`。
- 统计 `by_type`。
- 统计 `by_severity`。
- 空输入返回 total 为 0，两个分组为空 dict。

## 涉及变化

新增或修改：

- `monitor/reports.py`
- `docs/reports.md`
- `tests/test_reports.py`

## 行为说明

- 当前函数只统计内存中的 alert values。
- 后续 CLI `alert-projection` 可在读取数据库或回放规则后复用该函数。

## 测试与验收

- `python -m pytest`
- 覆盖空输入、单类型、多类型、多 severity。

## 不做内容

- 不读取数据库。
- 不实现 CLI `alert-projection`。
- 不输出文件。
