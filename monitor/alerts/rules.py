from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from monitor.indicators import AlertDecision, IndicatorContext


DAILY_FLAT_RETURN_LIMIT = Decimal("0.03")
DAILY_OI_BUILDUP_THRESHOLD = Decimal("0.10")
FLAT_15M_RETURN_LIMIT = Decimal("0.005")
OI_BUILDUP_15M_THRESHOLD = Decimal("0.03")
BREAKOUT_NEAR_HIGH_BPS = Decimal("50")
BREAKOUT_RANGE_COMPRESSION_MAX = Decimal("0.70")
BREAKOUT_VOLUME_ROBUST_Z_MIN = Decimal("3.0")
BREAKOUT_TAKER_BUY_RATIO_MIN = Decimal("0.60")
BREAKOUT_MARKET_RELATIVE_RETURN_MIN = Decimal("0")
BREAKDOWN_LOW_DISTANCE_BPS = Decimal("50")
BREAKDOWN_RANGE_COMPRESSION_MAX = Decimal("0.70")
BREAKDOWN_VOLUME_ROBUST_Z_MIN = Decimal("3.0")
BREAKDOWN_TAKER_SELL_RATIO_MIN = Decimal("0.60")

RULE_REGISTRY: list[Callable[[IndicatorContext], AlertDecision | None]] = []


def register_rule(fn: Callable[[IndicatorContext], AlertDecision | None]) -> Callable[[IndicatorContext], AlertDecision | None]:
    RULE_REGISTRY.append(fn)
    return fn


def _threshold_cond(field: str, op: str, value: Decimal, threshold: Decimal) -> dict:
    return {"field": field, "operator": op, "value": str(value), "threshold": str(threshold)}


def _between_cond(field: str, value: Decimal, min_val: Decimal, max_val: Decimal) -> dict:
    return {"field": field, "operator": "between", "value": str(value), "min": str(min_val), "max": str(max_val)}


@register_rule
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
            _between_cond("return_15m", snapshot.return_15m, -FLAT_15M_RETURN_LIMIT, FLAT_15M_RETURN_LIMIT),
            _threshold_cond("oi_change_15m", ">=", snapshot.oi_change_15m, OI_BUILDUP_15M_THRESHOLD),
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


@register_rule
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
            _between_cond("return_24h", snapshot.return_24h, -DAILY_FLAT_RETURN_LIMIT, DAILY_FLAT_RETURN_LIMIT),
            _threshold_cond("oi_change_24h", ">=", snapshot.oi_change_24h, DAILY_OI_BUILDUP_THRESHOLD),
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


@register_rule
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

    high_cond: dict = {
        "field": "distance_to_high_1h_bps|distance_to_high_24h_bps",
        "operator": "<=",
        "threshold": str(BREAKOUT_NEAR_HIGH_BPS),
        "distance_to_high_1h_bps": None if snapshot.distance_to_high_1h_bps is None else str(snapshot.distance_to_high_1h_bps),
        "distance_to_high_24h_bps": None if snapshot.distance_to_high_24h_bps is None else str(snapshot.distance_to_high_24h_bps),
    }
    payload = {
        "symbol": symbol,
        "signal_window": "15m",
        "confirmation_window": "1h",
        "confirmations": [*high_confirmations, "range_compression_15m", "oi_change_15m", "volume_robust_z_5m", "taker_buy_ratio_5m", "market_relative_return_5m"],
        "trigger_conditions": [
            high_cond,
            _threshold_cond("range_compression_15m", "<=", snapshot.range_compression_15m, BREAKOUT_RANGE_COMPRESSION_MAX),
            _threshold_cond("oi_change_15m", ">", snapshot.oi_change_15m, Decimal("0")),
            _threshold_cond("volume_robust_z_5m", ">=", snapshot.volume_robust_z_5m, BREAKOUT_VOLUME_ROBUST_Z_MIN),
            _threshold_cond("taker_buy_ratio_5m", ">=", snapshot.taker_buy_ratio_5m, BREAKOUT_TAKER_BUY_RATIO_MIN),
            _threshold_cond("market_relative_return_5m", ">=", snapshot.market_relative_return_5m, BREAKOUT_MARKET_RELATIVE_RETURN_MIN),
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


@register_rule
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
    if not (near_1h_low or near_24h_low):
        return None
    if (
        snapshot.range_compression_15m is None
        or snapshot.oi_change_15m is None
        or snapshot.volume_robust_z_5m is None
        or snapshot.taker_sell_ratio_5m is None
        or snapshot.market_relative_return_5m is None
    ):
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

    low_cond: dict = {
        "field": "distance_to_low_1h_bps|distance_to_low_24h_bps",
        "operator": "<=",
        "threshold": str(BREAKDOWN_LOW_DISTANCE_BPS),
        "distance_to_low_1h_bps": None if snapshot.distance_to_low_1h_bps is None else str(snapshot.distance_to_low_1h_bps),
        "distance_to_low_24h_bps": None if snapshot.distance_to_low_24h_bps is None else str(snapshot.distance_to_low_24h_bps),
    }
    payload = {
        "symbol": symbol,
        "signal_window": "15m",
        "confirmation_window": "1h",
        "confirmations": [*low_confirmations, "range_compression_15m", "oi_change_15m", "volume_robust_z_5m", "taker_sell_ratio_5m", "market_relative_return_5m"],
        "trigger_conditions": [
            low_cond,
            _threshold_cond("range_compression_15m", "<=", snapshot.range_compression_15m, BREAKDOWN_RANGE_COMPRESSION_MAX),
            _threshold_cond("oi_change_15m", ">", snapshot.oi_change_15m, Decimal("0")),
            _threshold_cond("volume_robust_z_5m", ">=", snapshot.volume_robust_z_5m, BREAKDOWN_VOLUME_ROBUST_Z_MIN),
            _threshold_cond("taker_sell_ratio_5m", ">=", snapshot.taker_sell_ratio_5m, BREAKDOWN_TAKER_SELL_RATIO_MIN),
            _threshold_cond("market_relative_return_5m", "<=", snapshot.market_relative_return_5m, Decimal("0")),
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
