from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from monitor.alerts.engine import AlertEngine
from monitor.alerts.rules import IndicatorContext
from monitor.config import Settings


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def snapshot(
    *,
    return_24h: Decimal = Decimal("0.01"),
    oi_change_24h: Decimal = Decimal("0.12"),
) -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="SOLUSDT",
        return_24h=return_24h,
        oi_change_24h=oi_change_24h,
        baseline_ready=True,
        is_altcoin=True,
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

