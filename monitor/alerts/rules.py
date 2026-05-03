from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


DAILY_FLAT_RETURN_LIMIT = Decimal("0.03")
DAILY_OI_BUILDUP_THRESHOLD = Decimal("0.10")
FLAT_15M_RETURN_LIMIT = Decimal("0.005")
OI_BUILDUP_15M_THRESHOLD = Decimal("0.03")


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

