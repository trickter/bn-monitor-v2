from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from monitor.alerts.engine import AlertEngine
from monitor.binance.rest import build_indicator_contexts
from monitor.indicators import IndicatorContext
from monitor.config import Settings


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def snapshot(
    *,
    return_24h: Decimal = Decimal("0.01"),
    oi_change_24h: Decimal = Decimal("0.12"),
    return_15m: Decimal | None = None,
    oi_change_15m: Decimal | None = None,
) -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="SOLUSDT",
        return_24h=return_24h,
        oi_change_24h=oi_change_24h,
        baseline_ready=True,
        is_altcoin=True,
        return_15m=return_15m,
        oi_change_15m=oi_change_15m,
    )


def breakout_snapshot() -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="SOLUSDT",
        return_24h=Decimal("0.10"),
        oi_change_24h=Decimal("0.01"),
        baseline_ready=True,
        is_altcoin=True,
        distance_to_high_1h_bps=Decimal("40"),
        distance_to_high_24h_bps=Decimal("120"),
        range_compression_15m=Decimal("0.65"),
        oi_change_15m=Decimal("0.03"),
        volume_robust_z_5m=Decimal("3.5"),
        taker_buy_ratio_5m=Decimal("0.62"),
        market_relative_return_5m=Decimal("0.002"),
    )


def breakdown_snapshot() -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="SOLUSDT",
        return_24h=None,
        oi_change_24h=None,
        baseline_ready=True,
        is_altcoin=True,
        distance_to_low_1h_bps=Decimal("45"),
        distance_to_low_24h_bps=Decimal("90"),
        range_compression_15m=Decimal("0.60"),
        oi_change_15m=Decimal("0.02"),
        volume_robust_z_5m=Decimal("3.5"),
        taker_sell_ratio_5m=Decimal("0.65"),
        market_relative_return_5m=Decimal("-0.01"),
    )


def market_symbol_data(
    symbol: str,
    *,
    return_5m: Decimal,
    taker_buy_ratio: Decimal,
) -> SimpleNamespace:
    start = datetime(2026, 5, 2, 23, 59, tzinfo=UTC)
    final_close = Decimal("101")
    first_last_5_close = final_close / (Decimal("1") + return_5m)
    klines = []
    for i in range(1441):
        close = Decimal("100") + Decimal(i % 15) * Decimal("0.02")
        high = close + Decimal("1")
        low = close - Decimal("1")
        quote_volume = Decimal("1000") + Decimal(i % 17) * Decimal("7")
        if i >= 1381:
            close = final_close + Decimal(i - 1426) * Decimal("0.0005")
            high = close + Decimal("0.03")
            low = close - Decimal("0.03")
            quote_volume = Decimal("1005") + Decimal(i % 3)
        if i >= 1436:
            step = Decimal(i - 1436) / Decimal("4")
            close = first_last_5_close + (final_close - first_last_5_close) * step
            high = close + Decimal("0.03")
            low = close - Decimal("0.03")
            quote_volume = Decimal("5000") + Decimal(i - 1436) * Decimal("10")
        klines.append(
            {
                "ts": start + timedelta(minutes=i),
                "symbol": symbol,
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "base_volume": Decimal("10"),
                "quote_volume": quote_volume,
                "trade_count": 10,
                "taker_buy_base_volume": Decimal("5"),
                "taker_buy_quote_volume": quote_volume * taker_buy_ratio,
            }
        )

    open_interest = [
        {
            "ts": start + timedelta(minutes=i * 5),
            "symbol": symbol,
            "open_interest": Decimal("1000") + Decimal(i) * Decimal("0.5"),
            "open_interest_value": Decimal("100000") + Decimal(i) * Decimal("50"),
            "period": "5m",
            "source": "openInterestHist",
        }
        for i in range(288)
    ]
    open_interest[-3]["open_interest"] = Decimal("1080")
    open_interest[-2]["open_interest"] = Decimal("1100")
    open_interest[-1]["open_interest"] = Decimal("1120")
    return SimpleNamespace(klines=klines, open_interest=open_interest)


def test_engine_generates_suppressed_alert_values_in_shadow_mode(tmp_path: Path) -> None:
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=shadow\n"))

    values = engine.evaluate([snapshot()])

    assert len(values) == 1
    assert values[0]["alert_type"] == "daily_flat_oi_buildup"
    assert values[0]["mode"] == "shadow"
    assert values[0]["delivery_status"] == "suppressed"
    assert values[0]["payload"]["suppressed_reason"] == "alert_mode_shadow"


def test_engine_generates_pending_alert_values_in_live_mode(tmp_path: Path) -> None:
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=live\n"))

    values = engine.evaluate([snapshot()])

    assert len(values) == 1
    assert values[0]["mode"] == "live"
    assert values[0]["delivery_status"] == "pending"
    assert "suppressed_reason" not in values[0]["payload"]


def test_engine_keeps_alert_but_suppresses_allowlist_miss(tmp_path: Path) -> None:
    settings = settings_from_text(
        tmp_path,
        "ALERT_MODE=live\nDISCORD_ALERT_TYPE_ALLOWLIST=breakout_watch\n",
    )
    engine = AlertEngine(settings)

    values = engine.evaluate([snapshot()])

    assert len(values) == 1
    assert values[0]["delivery_status"] == "suppressed"
    assert values[0]["payload"]["suppressed_reason"] == "discord_alert_type_not_allowed"


def test_engine_returns_empty_list_when_rule_does_not_trigger(tmp_path: Path) -> None:
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=live\n"))

    values = engine.evaluate([snapshot(oi_change_24h=Decimal("0.01"))])

    assert values == []


def test_engine_generates_flat_oi_buildup_15m_alert_values(tmp_path: Path) -> None:
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=live\n"))

    values = engine.evaluate(
        [
            snapshot(
                return_24h=Decimal("0.10"),
                oi_change_24h=Decimal("0.01"),
                return_15m=Decimal("0.002"),
                oi_change_15m=Decimal("0.04"),
            )
        ]
    )

    assert len(values) == 1
    assert values[0]["alert_type"] == "flat_oi_buildup_15m"
    assert values[0]["severity"] == "WARNING"
    assert values[0]["direction"] == "none"
    assert values[0]["payload"]["signal_window"] == "15m"


def test_engine_generates_breakout_watch_alert_values(tmp_path: Path) -> None:
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=live\n"))

    values = engine.evaluate([breakout_snapshot()])

    assert len(values) == 1
    assert values[0]["alert_type"] == "breakout_watch"
    assert values[0]["severity"] == "WARNING"
    assert values[0]["direction"] == "up"
    assert values[0]["mode"] == "live"
    assert values[0]["delivery_status"] == "pending"
    assert values[0]["payload"]["signal_window"] == "15m"


def test_engine_generates_breakdown_watch_values(tmp_path: Path) -> None:
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=live\n"))

    values = engine.evaluate([breakdown_snapshot()])

    assert len(values) == 1
    assert values[0]["alert_type"] == "breakdown_watch"
    assert values[0]["severity"] == "WARNING"
    assert values[0]["direction"] == "down"
    assert values[0]["payload"]["signal_window"] == "15m"
    assert values[0]["delivery_status"] == "pending"


def test_engine_generates_all_four_rules_from_produced_indicator_contexts(tmp_path: Path) -> None:
    contexts = build_indicator_contexts(
        {
            "FLATUSDT": market_symbol_data(
                "FLATUSDT",
                return_5m=Decimal("0"),
                taker_buy_ratio=Decimal("0.50"),
            ),
            "DAILYUSDT": market_symbol_data(
                "DAILYUSDT",
                return_5m=Decimal("0"),
                taker_buy_ratio=Decimal("0.50"),
            ),
            "UPUSDT": market_symbol_data(
                "UPUSDT",
                return_5m=Decimal("0.001"),
                taker_buy_ratio=Decimal("0.65"),
            ),
            "DOWNUSDT": market_symbol_data(
                "DOWNUSDT",
                return_5m=Decimal("-0.001"),
                taker_buy_ratio=Decimal("0.35"),
            ),
        }
    )
    engine = AlertEngine(settings_from_text(tmp_path, "ALERT_MODE=shadow\n"))

    values = engine.evaluate(contexts.values())

    alert_types = {value["alert_type"] for value in values}
    assert {
        "flat_oi_buildup_15m",
        "daily_flat_oi_buildup",
        "breakout_watch",
        "breakdown_watch",
    } <= alert_types
