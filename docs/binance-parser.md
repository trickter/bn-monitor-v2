# Binance Parser

当前 parser 只处理 Binance USD-M Futures WebSocket 的两类消息：

- `kline`：只接受 interval 为 `1m` 且 `x=true` 的 closed kline。
- `forceOrder`：解析 `!forceOrder@arr` 的强平 snapshot。

## Kline

解析规则：

- `e` 必须为 `kline`。
- `k.i` 必须为 `1m`。
- `k.x` 必须为 `true`，未收盘 K 线返回 `None`。
- `ts` 使用 K 线开始时间 `k.t`，转换为 UTC `datetime`。
- 输出字段直接匹配 `futures_kline_1m` repository 写入字段。

Binance 文档说明 kline stream 中 `x` 表示该 K 线是否收盘。

## Force Order

解析规则：

- `e` 必须为 `forceOrder`。
- `ts` 优先使用订单成交时间 `o.T`，缺失时使用事件时间 `E`。
- `quantity` 使用原始数量 `o.q`。
- `price` 使用 `o.p`。
- `average_price` 使用 `o.ap`。
- `quote_value = (average_price if present else price) * quantity`。
- `raw` 保存原始 payload，便于复盘。

Binance 文档说明 all-market liquidation stream 对每个 symbol 每 1000ms 只推送最大一笔强平 snapshot，因此该数据不能解释为完整逐笔强平总量。

## Combined Stream

如果输入为：

```json
{
  "stream": "btcusdt@kline_1m",
  "data": {}
}
```

parser 会先取 `data` 再解析。

## 验收

- 未收盘 kline 不落库。
- 非 1m kline 不落库。
- closed 1m kline 可生成 repository values。
- forceOrder 可生成 `liquidation_snapshots` values。
- 缺少关键字段时抛出 `BinanceParseError`。
