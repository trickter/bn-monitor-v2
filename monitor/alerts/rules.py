from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


DAILY_FLAT_RETURN_LIMIT = Decimal("0.03")
DAILY_OI_BUILDUP_THRESHOLD = Decimal("0.10")
FLAT_15M_RETURN_LIMIT = Decimal("0.005")
OI_BUILDUP_15M_THRESHOLD = Decimal("0.03")
BREAKOUT_NEAR_HIGH_BPS = Decimal("50")
BREAKOUT_RANGE_COMPRESSION_MAX = Decimal("0.70")
BREAKOUT_VOLUME_ROBUST_Z_MIN = Decimal("3.0")
BREAKOUT_TAKER_BUY_RATIO_MIN = Decimal("0.60")
BREAKOUT_MARKET_RELATIVE_RETURN_MIN = Decimal("0")


@dataclass(frozen=True)
class IndicatorContext:
    ts: datetime
    symbol: str
    return_24h: Decimal | None
    oi_change_24h: Decimal | None
    baseline_ready: bool
    is_altcoin: bool
    return_15m: Decimal | None = None
    oi_change_15m: Decimal | None = None
    distance_to_high_1h_bps: Decimal | None = None
    distance_to_high_24h_bps: Decimal | None = None
    range_compression_15m: Decimal | None = None
    volume_robust_z_5m: Decimal | None = None
    taker_buy_ratio_5m: Decimal | None = None
    market_relative_return_5m: Decimal | None = None


@dataclass(frozen=True)
class AlertDecision:
    ts: datetime
    symbol: str
    alert_type: str
    severity: str
    direction: str
    score: Decimal
    title: str
    message: str
    payload: dict[str, Any]


def evaluate_flat_oi_buildup_15m(snapshot: IndicatorContext) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None
    if snapshot.return_15m is None or snapshot.oi_change_15m is None:
        return None
    if abs(snapshot.return_15m) > FLAT_15M_RETURN_LIMIT:
        return None
    if snapshot.oi_change_15m < OI_BUILDUP_15M_THRESHOLD:
        return None

    score = min(Decimal("100"), Decimal("60") + snapshot.oi_change_15m * Decimal("100"))
    symbol = snapshot.symbol.upper()
    payload = {
        "symbol": symbol,
        "signal_window": "15m",
        "confirmation_window": "15m",
        "confirmations": ["oi_change_15m"],
        "trigger_conditions": [
            {
                "field": "return_15m",
                "operator": "between",
                "value": str(snapshot.return_15m),
                "min": str(-FLAT_15M_RETURN_LIMIT),
                "max": str(FLAT_15M_RETURN_LIMIT),
            },
            {
                "field": "oi_change_15m",
                "operator": ">=",
                "value": str(snapshot.oi_change_15m),
                "threshold": str(OI_BUILDUP_15M_THRESHOLD),
            },
        ],
    }

    return AlertDecision(
        ts=snapshot.ts,
        symbol=symbol,
        alert_type="flat_oi_buildup_15m",
        severity="WARNING",
        direction="none",
        score=score,
        title=f"{symbol} 15m flat OI buildup",
        message=(
            f"{symbol} 15m return is {snapshot.return_15m:.2%} while "
            f"OI changed {snapshot.oi_change_15m:.2%}."
        ),
        payload=payload,
    )


def evaluate_daily_flat_oi_buildup(snapshot: IndicatorContext) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None
    if snapshot.return_24h is None or snapshot.oi_change_24h is None:
        return None
    if abs(snapshot.return_24h) > DAILY_FLAT_RETURN_LIMIT:
        return None
    if snapshot.oi_change_24h < DAILY_OI_BUILDUP_THRESHOLD:
        return None

    score = min(Decimal("100"), Decimal("60") + snapshot.oi_change_24h * Decimal("100"))
    symbol = snapshot.symbol.upper()
    payload = {
        "symbol": symbol,
        "signal_window": "24h",
        "confirmation_window": "24h",
        "confirmations": ["oi_change_24h"],
        "trigger_conditions": [
            {
                "field": "return_24h",
                "operator": "between",
                "value": str(snapshot.return_24h),
                "min": str(-DAILY_FLAT_RETURN_LIMIT),
                "max": str(DAILY_FLAT_RETURN_LIMIT),
            },
            {
                "field": "oi_change_24h",
                "operator": ">=",
                "value": str(snapshot.oi_change_24h),
                "threshold": str(DAILY_OI_BUILDUP_THRESHOLD),
            },
        ],
    }

    return AlertDecision(
        ts=snapshot.ts,
        symbol=symbol,
        alert_type="daily_flat_oi_buildup",
        severity="WARNING",
        direction="none",
        score=score,
        title=f"{symbol} daily flat OI buildup",
        message=(
            f"{symbol} 24h return is {snapshot.return_24h:.2%} while "
            f"OI changed {snapshot.oi_change_24h:.2%}."
        ),
        payload=payload,
    )


def evaluate_breakout_watch(snapshot: IndicatorContext) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None
    if (
        snapshot.range_compression_15m is None
        or snapshot.oi_change_15m is None
        or snapshot.volume_robust_z_5m is None
        or snapshot.taker_buy_ratio_5m is None
        or snapshot.market_relative_return_5m is None
    ):
        return None

    near_1h_high = (
        snapshot.distance_to_high_1h_bps is not None
        and snapshot.distance_to_high_1h_bps <= BREAKOUT_NEAR_HIGH_BPS
    )
    near_24h_high = (
        snapshot.distance_to_high_24h_bps is not None
        and snapshot.distance_to_high_24h_bps <= BREAKOUT_NEAR_HIGH_BPS
    )
    if not (near_1h_high or near_24h_high):
        return None
    if snapshot.range_compression_15m > BREAKOUT_RANGE_COMPRESSION_MAX:
        return None
    if snapshot.oi_change_15m <= 0:
        return None
    if snapshot.volume_robust_z_5m < BREAKOUT_VOLUME_ROBUST_Z_MIN:
        return None
    if snapshot.taker_buy_ratio_5m < BREAKOUT_TAKER_BUY_RATIO_MIN:
        return None
    if snapshot.market_relative_return_5m < BREAKOUT_MARKET_RELATIVE_RETURN_MIN:
        return None

    symbol = snapshot.symbol.upper()
    score = min(
        Decimal("100"),
        Decimal("65")
        + snapshot.volume_robust_z_5m * Decimal("3")
        + snapshot.oi_change_15m * Decimal("100"),
    )
    high_confirmations = []
    if near_1h_high:
        high_confirmations.append("distance_to_high_1h_bps")
    if near_24h_high:
        high_confirmations.append("distance_to_high_24h_bps")

    payload = {
        "symbol": symbol,
        "signal_window": "15m",
        "confirmation_window": "1h",
        "confirmations": [
            *high_confirmations,
            "range_compression_15m",
            "oi_change_15m",
            "volume_robust_z_5m",
            "taker_buy_ratio_5m",
            "market_relative_return_5m",
        ],
        "trigger_conditions": [
            {
                "field": "distance_to_high_1h_bps|distance_to_high_24h_bps",
                "operator": "<=",
                "threshold": str(BREAKOUT_NEAR_HIGH_BPS),
                "distance_to_high_1h_bps": (
                    None
                    if snapshot.distance_to_high_1h_bps is None
                    else str(snapshot.distance_to_high_1h_bps)
                ),
                "distance_to_high_24h_bps": (
                    None
                    if snapshot.distance_to_high_24h_bps is None
                    else str(snapshot.distance_to_high_24h_bps)
                ),
            },
            {
                "field": "range_compression_15m",
                "operator": "<=",
                "value": str(snapshot.range_compression_15m),
                "threshold": str(BREAKOUT_RANGE_COMPRESSION_MAX),
            },
            {
                "field": "oi_change_15m",
                "operator": ">",
                "value": str(snapshot.oi_change_15m),
                "threshold": "0",
            },
            {
                "field": "volume_robust_z_5m",
                "operator": ">=",
                "value": str(snapshot.volume_robust_z_5m),
                "threshold": str(BREAKOUT_VOLUME_ROBUST_Z_MIN),
            },
            {
                "field": "taker_buy_ratio_5m",
                "operator": ">=",
                "value": str(snapshot.taker_buy_ratio_5m),
                "threshold": str(BREAKOUT_TAKER_BUY_RATIO_MIN),
            },
            {
                "field": "market_relative_return_5m",
                "operator": ">=",
                "value": str(snapshot.market_relative_return_5m),
                "threshold": str(BREAKOUT_MARKET_RELATIVE_RETURN_MIN),
            },
        ],
    }

    return AlertDecision(
        ts=snapshot.ts,
        symbol=symbol,
        alert_type="breakout_watch",
        severity="WARNING",
        direction="up",
        score=score,
        title=f"{symbol} breakout watch",
        message=(
            f"{symbol} is near a recent high with compressed 15m range, "
            "positive OI change, strong 5m volume, and taker buy pressure."
        ),
        payload=payload,
    )
