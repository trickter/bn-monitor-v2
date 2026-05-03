from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class BinanceParseError(ValueError):
    pass


def unwrap_stream_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict) and "stream" in payload:
        return data
    return payload


def ms_to_utc(ms: Any) -> datetime:
    try:
        value = int(ms)
    except (TypeError, ValueError) as exc:
        raise BinanceParseError(f"invalid millisecond timestamp: {ms!r}") from exc
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def decimal_from(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise BinanceParseError(f"invalid decimal field {field_name}: {value!r}") from exc


def require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BinanceParseError(f"missing object field: {field_name}")
    return value


def require_field(payload: dict[str, Any], field_name: str) -> Any:
    if field_name not in payload:
        raise BinanceParseError(f"missing field: {field_name}")
    return payload[field_name]


def parse_closed_kline_1m(payload: dict[str, Any]) -> dict[str, Any] | None:
    event = unwrap_stream_data(payload)
    if event.get("e") != "kline":
        raise BinanceParseError("expected kline event")

    kline = require_mapping(event.get("k"), "k")
    if kline.get("i") != "1m":
        return None
    if kline.get("x") is not True:
        return None

    return {
        "ts": ms_to_utc(require_field(kline, "t")),
        "symbol": str(require_field(kline, "s")).upper(),
        "open": decimal_from(require_field(kline, "o"), "o"),
        "high": decimal_from(require_field(kline, "h"), "h"),
        "low": decimal_from(require_field(kline, "l"), "l"),
        "close": decimal_from(require_field(kline, "c"), "c"),
        "base_volume": decimal_from(require_field(kline, "v"), "v"),
        "quote_volume": decimal_from(require_field(kline, "q"), "q"),
        "trade_count": int(require_field(kline, "n")),
        "taker_buy_base_volume": decimal_from(require_field(kline, "V"), "V"),
        "taker_buy_quote_volume": decimal_from(require_field(kline, "Q"), "Q"),
    }


def parse_force_order(payload: dict[str, Any]) -> dict[str, Any]:
    event = unwrap_stream_data(payload)
    if event.get("e") != "forceOrder":
        raise BinanceParseError("expected forceOrder event")

    order = require_mapping(event.get("o"), "o")
    ts_source = order.get("T", event.get("E"))
    price = decimal_from(require_field(order, "p"), "p")
    average_price = decimal_from(require_field(order, "ap"), "ap")
    quantity = decimal_from(require_field(order, "q"), "q")
    quote_price = average_price if average_price != Decimal("0") else price

    return {
        "ts": ms_to_utc(ts_source),
        "symbol": str(require_field(order, "s")).upper(),
        "side": str(require_field(order, "S")).upper(),
        "price": price,
        "average_price": average_price,
        "quantity": quantity,
        "quote_value": quote_price * quantity,
        "raw": event,
    }

