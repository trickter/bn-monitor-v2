from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from monitor.binance.rest import _closed_klines_4h, _closed_rest_klines, _ema_with_seed, _kline_repository_values, _trend_pullback_metrics


def kline_4h(
    index: int,
    *,
    open_: Decimal = Decimal("100"),
    high: Decimal = Decimal("105"),
    low: Decimal = Decimal("95"),
    close: Decimal = Decimal("100"),
) -> dict:
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=4 * index)
    return {
        "ts": start,
        "symbol": "ALTUSDT",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "base_volume": Decimal("10"),
        "quote_volume": Decimal("1000"),
        "trade_count": 10,
        "taker_buy_base_volume": Decimal("5"),
        "taker_buy_quote_volume": Decimal("500"),
        "close_time": start + timedelta(hours=4) - timedelta(milliseconds=1),
    }


def pullback_klines() -> list[dict]:
    rows = []
    for i in range(60):
        rows.append(kline_4h(i, high=Decimal("105"), low=Decimal("96"), close=Decimal("100")))
    rows[0] = kline_4h(0, high=Decimal("102"), low=Decimal("90"), close=Decimal("100"))
    rows[50] = kline_4h(50, high=Decimal("120"), low=Decimal("110"), close=Decimal("118"))
    return rows


def test_ema_with_seed_uses_first_period_sma() -> None:
    assert _ema_with_seed([Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("5")], 3) == Decimal("4.000")


def test_trend_pullback_metrics_uses_fixed_60_candles() -> None:
    metrics = _trend_pullback_metrics(pullback_klines(), Decimal("108"))

    assert metrics["last_up_leg_return"] == Decimal("30") / Decimal("90")
    assert metrics["pullback_from_high"] == Decimal("12") / Decimal("120")
    assert metrics["pullback_retrace_ratio"] == Decimal("12") / Decimal("30")
    assert metrics["pullback_bars_4h"] == Decimal("9")
    assert metrics["return_7d"] == Decimal("8") / Decimal("100")
    assert metrics["range_position_7d"] == Decimal("12") / Decimal("24")
    assert metrics["payload"]["recent_swing_high_4h"] == "120"
    assert metrics["payload"]["recent_swing_low_4h"] == "90"
    assert metrics["payload"]["bars_since_high"] == "9"


def test_trend_pullback_metrics_return_none_when_samples_are_insufficient() -> None:
    metrics = _trend_pullback_metrics(pullback_klines()[:59], Decimal("108"))

    assert metrics["return_7d"] is None
    assert metrics["payload"] is None


def test_closed_klines_4h_filters_unfinished_candle() -> None:
    rows = pullback_klines()[:3]
    latest_1m_ts = rows[1]["close_time"] - timedelta(seconds=30)

    closed = _closed_klines_4h(rows, latest_1m_ts)

    assert [row["ts"] for row in closed] == [rows[0]["ts"], rows[1]["ts"]]


def test_closed_rest_klines_filters_unfinished_rows_and_strips_close_time() -> None:
    first = kline_4h(0)
    second = kline_4h(1)

    closed = _closed_rest_klines([first, second], first["close_time"] + timedelta(seconds=1))

    assert closed == [first]
    assert "close_time" not in _kline_repository_values(closed[0])
