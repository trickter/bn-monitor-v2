from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from monitor.alerts.rules import (
    AlertDecision,
    IndicatorContext,
    evaluate_breakdown_watch,
    evaluate_daily_flat_oi_buildup,
)


def snapshot(
    *,
    return_24h: Decimal | None = Decimal("0.01"),
    oi_change_24h: Decimal | None = Decimal("0.12"),
    baseline_ready: bool = True,
    is_altcoin: bool = True,
) -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="solusdt",
        return_24h=return_24h,
        oi_change_24h=oi_change_24h,
        baseline_ready=baseline_ready,
        is_altcoin=is_altcoin,
    )


def breakdown_snapshot(
    *,
    distance_to_low_1h_bps: Decimal | None = Decimal("40"),
    distance_to_low_24h_bps: Decimal | None = Decimal("80"),
    range_compression_15m: Decimal | None = Decimal("0.60"),
    oi_change_15m: Decimal | None = Decimal("0.02"),
    volume_robust_z_5m: Decimal | None = Decimal("3.5"),
    taker_sell_ratio_5m: Decimal | None = Decimal("0.65"),
    market_relative_return_5m: Decimal | None = Decimal("-0.01"),
    baseline_ready: bool = True,
    is_altcoin: bool = True,
) -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="solusdt",
        return_24h=None,
        oi_change_24h=None,
        baseline_ready=baseline_ready,
        is_altcoin=is_altcoin,
        distance_to_low_1h_bps=distance_to_low_1h_bps,
        distance_to_low_24h_bps=distance_to_low_24h_bps,
        range_compression_15m=range_compression_15m,
        oi_change_15m=oi_change_15m,
        volume_robust_z_5m=volume_robust_z_5m,
        taker_sell_ratio_5m=taker_sell_ratio_5m,
        market_relative_return_5m=market_relative_return_5m,
    )


def test_daily_flat_oi_buildup_triggers_warning() -> None:
    decision = evaluate_daily_flat_oi_buildup(snapshot())

    assert isinstance(decision, AlertDecision)
    assert decision.alert_type == "daily_flat_oi_buildup"
    assert decision.severity == "WARNING"
    assert decision.direction == "none"
    assert decision.symbol == "SOLUSDT"
    assert decision.score == Decimal("72.00")
    assert decision.payload["symbol"] == "SOLUSDT"
    assert decision.payload["signal_window"] == "24h"
    assert decision.payload["confirmation_window"] == "24h"
    assert "oi_change_24h" in decision.payload["confirmations"]
    assert decision.payload["trigger_conditions"]


def test_daily_flat_oi_buildup_does_not_trigger_when_oi_too_low() -> None:
    assert evaluate_daily_flat_oi_buildup(snapshot(oi_change_24h=Decimal("0.099"))) is None


def test_daily_flat_oi_buildup_does_not_trigger_when_return_too_high() -> None:
    assert evaluate_daily_flat_oi_buildup(snapshot(return_24h=Decimal("0.031"))) is None
    assert evaluate_daily_flat_oi_buildup(snapshot(return_24h=Decimal("-0.031"))) is None


def test_daily_flat_oi_buildup_does_not_trigger_without_baseline() -> None:
    assert evaluate_daily_flat_oi_buildup(snapshot(baseline_ready=False)) is None


def test_daily_flat_oi_buildup_does_not_trigger_for_non_altcoin() -> None:
    assert evaluate_daily_flat_oi_buildup(snapshot(is_altcoin=False)) is None


def test_daily_flat_oi_buildup_does_not_trigger_with_missing_metrics() -> None:
    assert evaluate_daily_flat_oi_buildup(snapshot(return_24h=None)) is None
    assert evaluate_daily_flat_oi_buildup(snapshot(oi_change_24h=None)) is None


def test_breakdown_watch_triggers_warning() -> None:
    decision = evaluate_breakdown_watch(breakdown_snapshot())

    assert isinstance(decision, AlertDecision)
    assert decision.alert_type == "breakdown_watch"
    assert decision.severity == "WARNING"
    assert decision.direction == "down"
    assert decision.symbol == "SOLUSDT"
    assert decision.payload["symbol"] == "SOLUSDT"
    assert decision.payload["signal_window"] == "15m"
    assert decision.payload["confirmation_window"] == "1h"
    assert "distance_to_low_1h_bps" in decision.payload["confirmations"]
    assert "volume_robust_z_5m" in decision.payload["confirmations"]
    assert decision.payload["trigger_conditions"]


def test_breakdown_watch_triggers_when_only_24h_low_is_near() -> None:
    decision = evaluate_breakdown_watch(
        breakdown_snapshot(distance_to_low_1h_bps=Decimal("70"), distance_to_low_24h_bps=Decimal("45"))
    )

    assert isinstance(decision, AlertDecision)
    assert "distance_to_low_24h_bps" in decision.payload["confirmations"]


def test_breakdown_watch_does_not_trigger_when_not_near_low() -> None:
    decision = evaluate_breakdown_watch(
        breakdown_snapshot(distance_to_low_1h_bps=Decimal("51"), distance_to_low_24h_bps=Decimal("70"))
    )

    assert decision is None


def test_breakdown_watch_does_not_trigger_without_volume_expansion() -> None:
    assert evaluate_breakdown_watch(breakdown_snapshot(volume_robust_z_5m=Decimal("2.9"))) is None


def test_breakdown_watch_does_not_trigger_with_weak_taker_sell() -> None:
    assert evaluate_breakdown_watch(breakdown_snapshot(taker_sell_ratio_5m=Decimal("0.59"))) is None


def test_breakdown_watch_does_not_trigger_with_positive_market_relative_return() -> None:
    assert evaluate_breakdown_watch(breakdown_snapshot(market_relative_return_5m=Decimal("0.001"))) is None


def test_breakdown_watch_does_not_trigger_without_baseline() -> None:
    assert evaluate_breakdown_watch(breakdown_snapshot(baseline_ready=False)) is None


def test_breakdown_watch_does_not_trigger_with_missing_metrics() -> None:
    assert evaluate_breakdown_watch(breakdown_snapshot(range_compression_15m=None)) is None
    assert evaluate_breakdown_watch(breakdown_snapshot(oi_change_15m=None)) is None
    assert evaluate_breakdown_watch(breakdown_snapshot(volume_robust_z_5m=None)) is None
    assert evaluate_breakdown_watch(breakdown_snapshot(taker_sell_ratio_5m=None)) is None
    assert evaluate_breakdown_watch(breakdown_snapshot(market_relative_return_5m=None)) is None

