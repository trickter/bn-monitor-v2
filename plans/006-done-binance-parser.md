# Binance Parser

状态：done

## 目标

实现 Binance USD-M Futures WebSocket 消息的第一版纯解析层，覆盖 1m closed kline 与 all-market liquidation snapshot。

成功标准：

- 只解析 `x=true` 且 interval 为 `1m` 的 kline。
- kline `ts` 使用 K 线开始时间 `k.t` 转换为 UTC `datetime`。
- forceOrder `ts` 优先使用订单成交时间 `o.T`，缺失时回退事件时间 `E`。
- forceOrder `quote_value` 使用 `average_price * quantity`，缺失 average price 时使用 `price * quantity`。
- 支持 Binance combined stream 包装 `{ "stream": "...", "data": ... }`。
- malformed payload 明确抛出 `BinanceParseError`。

## 涉及变化

新增文件：

- `monitor/binance/__init__.py`
- `monitor/binance/parser.py`
- `docs/binance-parser.md`
- `tests/test_binance.py`

## 参考依据

- Binance USD-M Futures kline 文档说明 `x` 字段表示 K 线是否收盘。
- Binance USD-M Futures `!forceOrder@arr` 文档说明每个 symbol 每 1000ms 只推送最大一笔强平快照。

## 测试与验收

- `python -m pytest`
- 覆盖 closed kline、未收盘 kline、非 1m kline、combined stream、forceOrder quote value、malformed payload。

## 不做内容

- 不连接 Binance WebSocket。
- 不做 REST backfill。
- 不写入数据库。
- 不把强平 snapshot 描述为完整强平总量。
