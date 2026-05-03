from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from monitor.binance.parser import BinanceParseError, parse_closed_kline_1m, parse_force_order


def kline_event(closed: bool = True, interval: str = "1m") -> dict:
    return {
        "e": "kline",
        "E": 1638747660000,
        "s": "BTCUSDT",
        "k": {
            "t": 1638747660000,
            "T": 1638747719999,
            "s": "BTCUSDT",
            "i": interval,
            "o": "100.0",
            "c": "101.0",
            "h": "102.0",
            "l": "99.0",
            "v": "1000",
            "n": 100,
            "x": closed,
            "q": "100000.0",
            "V": "600",
            "Q": "60000.0",
        },
    }


def force_order_event() -> dict:
    return {
        "e": "forceOrder",
        "E": 1568014460000,
        "o": {
            "s": "BTCUSDT",
            "S": "SELL",
            "o": "LIMIT",
            "f": "IOC",
            "q": "0.014",
            "p": "9910",
            "ap": "9920",
            "X": "FILLED",
            "l": "0.014",
            "z": "0.014",
            "T": 1568014460893,
        },
    }


def test_parse_closed_kline_1m_maps_repository_values() -> None:
    values = parse_closed_kline_1m(kline_event())

    assert values == {
        "ts": datetime(2021, 12, 5, 23, 41, tzinfo=UTC),
        "symbol": "BTCUSDT",
        "open": Decimal("100.0"),
        "high": Decimal("102.0"),
        "low": Decimal("99.0"),
        "close": Decimal("101.0"),
        "base_volume": Decimal("1000"),
        "quote_volume": Decimal("100000.0"),
        "trade_count": 100,
        "taker_buy_base_volume": Decimal("600"),
        "taker_buy_quote_volume": Decimal("60000.0"),
    }


def test_parse_kline_ignores_unclosed_and_non_1m() -> None:
    assert parse_closed_kline_1m(kline_event(closed=False)) is None
    assert parse_closed_kline_1m(kline_event(interval="5m")) is None


def test_parse_combined_stream_kline() -> None:
    payload = {"stream": "btcusdt@kline_1m", "data": kline_event()}

    values = parse_closed_kline_1m(payload)

    assert values is not None
    assert values["symbol"] == "BTCUSDT"


def test_parse_force_order_maps_repository_values() -> None:
    values = parse_force_order(force_order_event())

    assert values["ts"] == datetime(2019, 9, 9, 7, 34, 20, 893000, tzinfo=UTC)
    assert values["symbol"] == "BTCUSDT"
    assert values["side"] == "SELL"
    assert values["price"] == Decimal("9910")
    assert values["average_price"] == Decimal("9920")
    assert values["quantity"] == Decimal("0.014")
    assert values["quote_value"] == Decimal("138.880")
    assert values["raw"]["e"] == "forceOrder"


def test_force_order_uses_event_time_when_trade_time_missing() -> None:
    payload = force_order_event()
    del payload["o"]["T"]

    values = parse_force_order(payload)

    assert values["ts"] == datetime(2019, 9, 9, 7, 34, 20, tzinfo=UTC)


def test_malformed_payload_raises_parse_error() -> None:
    payload = kline_event()
    del payload["k"]["c"]

    with pytest.raises(BinanceParseError, match="missing field: c"):
        parse_closed_kline_1m(payload)
