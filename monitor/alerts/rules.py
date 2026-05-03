from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


DAILY_FLAT_RETURN_LIMIT = Decimal("0.03")
DAILY_OI_BUILDUP_THRESHOLD = Decimal("0.10")


@dataclass(frozen=True)
class IndicatorContext:
    ts: datetime
    symbol: str
    return_24h: Decimal | None
    oi_change_24h: Decimal | None
    baseline_ready: bool
    is_altcoin: bool


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

