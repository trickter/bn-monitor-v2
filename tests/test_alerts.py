from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from monitor.alerts.rules import (
    AlertDecision,
    IndicatorContext,
    evaluate_daily_flat_oi_buildup,
    evaluate_flat_oi_buildup_15m,
)


def snapshot(
    *,
    return_24h: Decimal | None = Decimal("0.01"),
    oi_change_24h: Decimal | None = Decimal("0.12"),
    return_15m: Decimal | None = None,
    oi_change_15m: Decimal | None = None,
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
        return_15m=return_15m,
        oi_change_15m=oi_change_15m,
    )


def test_flat_oi_buildup_15m_triggers_warning() -> None:
    decision = evaluate_flat_oi_buildup_15m(
        snapshot(return_15m=Decimal("0.002"), oi_change_15m=Decimal("0.04"))
    )

    assert isinstance(decision, AlertDecision)
    assert decision.alert_type == "flat_oi_buildup_15m"
    assert decision.severity == "WARNING"
    assert decision.direction == "none"
    assert decision.symbol == "SOLUSDT"
    assert decision.score == Decimal("64.00")
    assert decision.payload["symbol"] == "SOLUSDT"
    assert decision.payload["signal_window"] == "15m"
    assert decision.payload["confirmation_window"] == "15m"
    assert "oi_change_15m" in decision.payload["confirmations"]
    assert decision.payload["trigger_conditions"]


def test_flat_oi_buildup_15m_does_not_trigger_when_oi_too_low() -> None:
    decision = evaluate_flat_oi_buildup_15m(
        snapshot(return_15m=Decimal("0.002"), oi_change_15m=Decimal("0.029"))
    )

    assert decision is None


def test_flat_oi_buildup_15m_does_not_trigger_when_return_too_high() -> None:
    assert (
        evaluate_flat_oi_buildup_15m(
            snapshot(return_15m=Decimal("0.006"), oi_change_15m=Decimal("0.04"))
        )
        is None
    )
    assert (
        evaluate_flat_oi_buildup_15m(
            snapshot(return_15m=Decimal("-0.006"), oi_change_15m=Decimal("0.04"))
        )
        is None
    )


def test_flat_oi_buildup_15m_does_not_trigger_without_baseline() -> None:
    decision = evaluate_flat_oi_buildup_15m(
        snapshot(
            return_15m=Decimal("0.002"),
            oi_change_15m=Decimal("0.04"),
            baseline_ready=False,
        )
    )

    assert decision is None


def test_flat_oi_buildup_15m_does_not_trigger_for_non_altcoin() -> None:
    decision = evaluate_flat_oi_buildup_15m(
        snapshot(
            return_15m=Decimal("0.002"),
            oi_change_15m=Decimal("0.04"),
            is_altcoin=False,
        )
    )

    assert decision is None


def test_flat_oi_buildup_15m_does_not_trigger_with_missing_metrics() -> None:
    assert (
        evaluate_flat_oi_buildup_15m(snapshot(return_15m=None, oi_change_15m=Decimal("0.04")))
        is None
    )
    assert (
        evaluate_flat_oi_buildup_15m(snapshot(return_15m=Decimal("0.002"), oi_change_15m=None))
        is None
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

