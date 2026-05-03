from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


DAILY_FLAT_RETURN_LIMIT = Decimal("0.03")
DAILY_OI_BUILDUP_THRESHOLD = Decimal("0.10")
BREAKDOWN_LOW_DISTANCE_BPS = Decimal("50")
BREAKDOWN_RANGE_COMPRESSION_MAX = Decimal("0.70")
BREAKDOWN_VOLUME_ROBUST_Z_MIN = Decimal("3.0")
BREAKDOWN_TAKER_SELL_RATIO_MIN = Decimal("0.60")


@dataclass(frozen=True)
class IndicatorContext:
    ts: datetime
    symbol: str
    return_24h: Decimal | None
    oi_change_24h: Decimal | None
    baseline_ready: bool
    is_altcoin: bool
    distance_to_low_1h_bps: Decimal | None = None
    distance_to_low_24h_bps: Decimal | None = None
    range_compression_15m: Decimal | None = None
    oi_change_15m: Decimal | None = None
    volume_robust_z_5m: Decimal | None = None
    taker_sell_ratio_5m: Decimal | None = None
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


def evaluate_breakdown_watch(snapshot: IndicatorContext) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None

    near_1h_low = (
        snapshot.distance_to_low_1h_bps is not None
        and snapshot.distance_to_low_1h_bps <= BREAKDOWN_LOW_DISTANCE_BPS
    )
    near_24h_low = (
        snapshot.distance_to_low_24h_bps is not None
        and snapshot.distance_to_low_24h_bps <= BREAKDOWN_LOW_DISTANCE_BPS
    )
    if not near_1h_low and not near_24h_low:
        return None

    required_metrics = (
        snapshot.range_compression_15m,
        snapshot.oi_change_15m,
        snapshot.volume_robust_z_5m,
        snapshot.taker_sell_ratio_5m,
        snapshot.market_relative_return_5m,
    )
    if any(value is None for value in required_metrics):
        return None
    if snapshot.range_compression_15m > BREAKDOWN_RANGE_COMPRESSION_MAX:
        return None
    if snapshot.oi_change_15m <= 0:
        return None
    if snapshot.volume_robust_z_5m < BREAKDOWN_VOLUME_ROBUST_Z_MIN:
        return None
    if snapshot.taker_sell_ratio_5m < BREAKDOWN_TAKER_SELL_RATIO_MIN:
        return None
    if snapshot.market_relative_return_5m > 0:
        return None

    score = min(
        Decimal("100"),
        Decimal("70")
        + snapshot.volume_robust_z_5m * Decimal("3")
        + snapshot.taker_sell_ratio_5m * Decimal("10")
        + abs(snapshot.market_relative_return_5m) * Decimal("100"),
    )
    symbol = snapshot.symbol.upper()
    low_confirmations = []
    if near_1h_low:
        low_confirmations.append("distance_to_low_1h_bps")
    if near_24h_low:
        low_confirmations.append("distance_to_low_24h_bps")

    payload = {
        "symbol": symbol,
        "signal_window": "15m",
        "confirmation_window": "1h",
        "confirmations": [
            *low_confirmations,
            "range_compression_15m",
            "oi_change_15m",
            "volume_robust_z_5m",
            "taker_sell_ratio_5m",
            "market_relative_return_5m",
        ],
        "trigger_conditions": [
            {
                "field": "distance_to_low",
                "operator": "<=",
                "value": {
                    "distance_to_low_1h_bps": (
                        str(snapshot.distance_to_low_1h_bps)
                        if snapshot.distance_to_low_1h_bps is not None
                        else None
                    ),
                    "distance_to_low_24h_bps": (
                        str(snapshot.distance_to_low_24h_bps)
                        if snapshot.distance_to_low_24h_bps is not None
                        else None
                    ),
                },
                "threshold": str(BREAKDOWN_LOW_DISTANCE_BPS),
            },
            {
                "field": "range_compression_15m",
                "operator": "<=",
                "value": str(snapshot.range_compression_15m),
                "threshold": str(BREAKDOWN_RANGE_COMPRESSION_MAX),
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
                "threshold": str(BREAKDOWN_VOLUME_ROBUST_Z_MIN),
            },
            {
                "field": "taker_sell_ratio_5m",
                "operator": ">=",
                "value": str(snapshot.taker_sell_ratio_5m),
                "threshold": str(BREAKDOWN_TAKER_SELL_RATIO_MIN),
            },
            {
                "field": "market_relative_return_5m",
                "operator": "<=",
                "value": str(snapshot.market_relative_return_5m),
                "threshold": "0",
            },
        ],
    }

    return AlertDecision(
        ts=snapshot.ts,
        symbol=symbol,
        alert_type="breakdown_watch",
        severity="WARNING",
        direction="down",
        score=score,
        title=f"{symbol} breakdown watch",
        message=(
            f"{symbol} is near recent lows with 15m compression, rising OI, "
            "5m sell pressure, and weak market-relative return."
        ),
        payload=payload,
    )

