from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from monitor.binance.rest import build_indicator_context, build_indicator_contexts


REQUIRED_FIELDS_WHEN_READY = {
    "return_24h",
    "oi_change_24h",
    "return_15m",
    "oi_change_15m",
    "distance_to_high_1h_bps",
    "distance_to_high_24h_bps",
    "distance_to_low_1h_bps",
    "distance_to_low_24h_bps",
    "range_compression_15m",
    "volume_robust_z_5m",
    "taker_buy_ratio_5m",
    "taker_sell_ratio_5m",
    "market_relative_return_5m",
    "return_7d",
    "range_position_7d",
    "last_up_leg_return",
    "pullback_from_high",
    "pullback_retrace_ratio",
    "low_vs_ema20_4h",
    "low_vs_ema50_4h",
    "pullback_bars_4h",
    "pullback_structure_payload",
}


def synthetic_klines(symbol: str = "ALTUSDT", return_5m: Decimal = Decimal("0.02")) -> list[dict]:
    start = datetime(2026, 5, 2, 23, 59, tzinfo=UTC)
    rows = []
    for i in range(1441):
        close = Decimal("100") + Decimal(i % 20) / Decimal("100")
        if i >= 1436:
            step = Decimal(i - 1436) / Decimal("4")
            close = Decimal("100") * (Decimal("1") + return_5m * step)
        quote_volume = Decimal("1000") + Decimal(i % 17) * Decimal("11")
        if i >= 1436:
            quote_volume = Decimal("1800") + Decimal(i - 1436) * Decimal("20")
        rows.append(
            {
                "ts": start + timedelta(minutes=i),
                "symbol": symbol,
                "open": close - Decimal("0.02"),
                "high": close + Decimal("0.10"),
                "low": close - Decimal("0.10"),
                "close": close,
                "base_volume": Decimal("10"),
                "quote_volume": quote_volume,
                "trade_count": 10,
                "taker_buy_base_volume": Decimal("6.5"),
                "taker_buy_quote_volume": quote_volume * Decimal("0.65"),
            }
        )
    return rows


def synthetic_open_interest(symbol: str = "ALTUSDT") -> list[dict]:
    start = datetime(2026, 5, 2, 23, 59, tzinfo=UTC)
    return [
        {
            "ts": start + timedelta(minutes=i * 5),
            "symbol": symbol,
            "open_interest": Decimal("1000") + Decimal(i),
            "open_interest_value": Decimal("100000") + Decimal(i) * Decimal("100"),
            "period": "5m",
            "source": "openInterestHist",
        }
        for i in range(288)
    ]


def synthetic_klines_4h(symbol: str = "ALTUSDT") -> list[dict]:
    start = datetime(2026, 4, 22, tzinfo=UTC)
    rows = []
    for i in range(60):
        rows.append(
            {
                "ts": start + timedelta(hours=i * 4),
                "symbol": symbol,
                "open": Decimal("100"),
                "high": Decimal("105"),
                "low": Decimal("96"),
                "close": Decimal("100"),
                "base_volume": Decimal("10"),
                "quote_volume": Decimal("1000"),
                "trade_count": 10,
                "taker_buy_base_volume": Decimal("5"),
                "taker_buy_quote_volume": Decimal("500"),
                "close_time": start + timedelta(hours=(i + 1) * 4) - timedelta(milliseconds=1),
            }
        )
    rows[0]["low"] = Decimal("90")
    rows[50]["high"] = Decimal("120")
    rows[50]["close"] = Decimal("118")
    return rows


def symbol_data(symbol: str, return_5m: Decimal) -> SimpleNamespace:
    return SimpleNamespace(
        klines=synthetic_klines(symbol, return_5m),
        open_interest=synthetic_open_interest(symbol),
        klines_4h=synthetic_klines_4h(symbol),
    )


def test_build_indicator_context_fills_per_symbol_fields() -> None:
    klines = synthetic_klines(return_5m=Decimal("0.02"))
    open_interest = synthetic_open_interest()

    context = build_indicator_context("ALTUSDT", klines, open_interest, synthetic_klines_4h())

    assert context.baseline_ready is True
    assert context.is_altcoin is True
    assert context.return_24h == (klines[-1]["close"] - klines[1]["close"]) / klines[1]["close"]
    assert context.oi_change_24h == (open_interest[-1]["open_interest"] - open_interest[1]["open_interest"]) / open_interest[1]["open_interest"]
    assert context.return_15m == (klines[-1]["close"] - klines[-15]["close"]) / klines[-15]["close"]
    assert context.oi_change_15m == (open_interest[-1]["open_interest"] - open_interest[-3]["open_interest"]) / open_interest[-3]["open_interest"]
    assert context.distance_to_high_1h_bps is not None
    assert context.distance_to_high_24h_bps is not None
    assert context.distance_to_low_1h_bps is not None
    assert context.distance_to_low_24h_bps is not None
    assert context.range_compression_15m is not None
    assert context.volume_robust_z_5m is not None
    assert context.taker_buy_ratio_5m == Decimal("0.65")
    assert context.taker_sell_ratio_5m == Decimal("0.35")
    assert context.return_7d is not None
    assert context.pullback_structure_payload is not None


def test_daily_metrics_prefer_completed_utc_day_boundaries() -> None:
    start = datetime(2026, 5, 3, tzinfo=UTC)
    klines = []
    for i in range(1447):
        close = Decimal("100") + Decimal(i) / Decimal("100")
        klines.append(
            {
                "ts": start + timedelta(minutes=i),
                "symbol": "ALTUSDT",
                "open": close,
                "high": close + Decimal("0.10"),
                "low": close - Decimal("0.10"),
                "close": close,
                "base_volume": Decimal("10"),
                "quote_volume": Decimal("1000") + Decimal(i % 17),
                "trade_count": 10,
                "taker_buy_base_volume": Decimal("6.5"),
                "taker_buy_quote_volume": Decimal("650"),
            }
        )
    open_interest = [
        {
            "ts": start + timedelta(minutes=i * 5),
            "symbol": "ALTUSDT",
            "open_interest": Decimal("1000") + Decimal(i),
            "open_interest_value": Decimal("100000") + Decimal(i) * Decimal("100"),
            "period": "5m",
            "source": "openInterestHist",
        }
        for i in range(290)
    ]

    context = build_indicator_context("ALTUSDT", klines, open_interest)

    assert klines[-1]["ts"] == datetime(2026, 5, 4, 0, 6, tzinfo=UTC)
    assert context.return_24h == (klines[1440]["close"] - klines[0]["close"]) / klines[0]["close"]
    assert context.oi_change_24h == (open_interest[288]["open_interest"] - open_interest[0]["open_interest"]) / open_interest[0]["open_interest"]


def test_build_indicator_contexts_computes_market_relative_return_5m() -> None:
    contexts = build_indicator_contexts(
        {
            "ALTUSDT": symbol_data("ALTUSDT", Decimal("0.04")),
            "BNBUSDT": symbol_data("BNBUSDT", Decimal("0.02")),
            "XRPUSDT": symbol_data("XRPUSDT", Decimal("0.00")),
        }
    )

    assert contexts["ALTUSDT"].market_relative_return_5m == Decimal("0.02")
    assert contexts["BNBUSDT"].market_relative_return_5m == Decimal("0.00")
    assert contexts["XRPUSDT"].market_relative_return_5m == Decimal("-0.02")


def test_indicator_fields_return_none_when_samples_are_insufficient() -> None:
    context = build_indicator_context("ALTUSDT", synthetic_klines()[:100], synthetic_open_interest()[:2])

    assert context.baseline_ready is False
    assert context.oi_change_15m is None
    assert context.volume_robust_z_5m is None


def test_no_silent_none_when_baseline_ready() -> None:
    context = build_indicator_contexts(
        {
            "ALTUSDT": symbol_data("ALTUSDT", Decimal("0.04")),
            "BNBUSDT": symbol_data("BNBUSDT", Decimal("0.02")),
            "XRPUSDT": symbol_data("XRPUSDT", Decimal("0.00")),
        }
    )["ALTUSDT"]

    assert context.baseline_ready is True
    missing = [field for field in REQUIRED_FIELDS_WHEN_READY if getattr(context, field) is None]
    assert not missing, f"these indicator fields are silently None: {missing}"


def test_indicator_context_fields_have_producer() -> None:
    rules_path = Path("monitor/alerts/rules.py")
    tree = ast.parse(rules_path.read_text(encoding="utf-8"))
    used_fields = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "snapshot"
    }
    ignored = {"ts", "symbol", "baseline_ready", "is_altcoin"}
    context = build_indicator_contexts(
        {
            "ALTUSDT": symbol_data("ALTUSDT", Decimal("0.04")),
            "BNBUSDT": symbol_data("BNBUSDT", Decimal("0.02")),
            "XRPUSDT": symbol_data("XRPUSDT", Decimal("0.00")),
        }
    )["ALTUSDT"]

    unfilled = [field for field in sorted(used_fields - ignored) if getattr(context, field) is None]
    assert not unfilled, (
        f"rules reference fields not filled by build_indicator_contexts: {unfilled}. "
        "Update monitor/binance/rest.py when adding rule indicator fields."
    )
