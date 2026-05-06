from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


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
    distance_to_low_1h_bps: Decimal | None = None
    distance_to_low_24h_bps: Decimal | None = None
    range_compression_15m: Decimal | None = None
    volume_robust_z_5m: Decimal | None = None
    taker_buy_ratio_5m: Decimal | None = None
    taker_sell_ratio_5m: Decimal | None = None
    market_relative_return_5m: Decimal | None = None
    return_7d: Decimal | None = None
    range_position_7d: Decimal | None = None
    last_up_leg_return: Decimal | None = None
    pullback_from_high: Decimal | None = None
    pullback_retrace_ratio: Decimal | None = None
    low_vs_ema20_4h: Decimal | None = None
    low_vs_ema50_4h: Decimal | None = None
    pullback_bars_4h: Decimal | None = None
    pullback_structure_payload: dict[str, str | None] | None = None


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
