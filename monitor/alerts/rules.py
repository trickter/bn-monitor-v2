from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from monitor.indicators import AlertDecision, IndicatorContext


DAILY_FLAT_RETURN_LIMIT = Decimal("0.03")
DAILY_OI_BUILDUP_THRESHOLD = Decimal("0.10")
FLAT_15M_RETURN_LIMIT = Decimal("0.005")
OI_BUILDUP_15M_THRESHOLD = Decimal("0.03")
BREAKOUT_NEAR_HIGH_BPS = Decimal("250")
BREAKOUT_RANGE_COMPRESSION_MAX = Decimal("0.70")
BREAKOUT_VOLUME_ROBUST_Z_MIN = Decimal("2")
BREAKOUT_TAKER_BUY_RATIO_MIN = Decimal("0.60")
BREAKOUT_MARKET_RELATIVE_RETURN_MIN = Decimal("0")
BREAKDOWN_LOW_DISTANCE_BPS = Decimal("250")
BREAKDOWN_RANGE_COMPRESSION_MAX = Decimal("0.70")
BREAKDOWN_VOLUME_ROBUST_Z_MIN = Decimal("2")
BREAKDOWN_TAKER_SELL_RATIO_MIN = Decimal("0.60")
LONG_PULLBACK_RETURN_7D_MIN = Decimal("0.08")
LONG_PULLBACK_RANGE_POSITION_7D_MIN = Decimal("0.55")
LONG_PULLBACK_UP_LEG_MIN = Decimal("0.15")
LONG_PULLBACK_RETRACE_MIN = Decimal("0.382")
LONG_PULLBACK_RETRACE_MAX = Decimal("0.764")
LONG_PULLBACK_FROM_HIGH_MIN = Decimal("0.08")
LONG_PULLBACK_FROM_HIGH_MAX = Decimal("0.38")
LONG_PULLBACK_EMA20_LOW = Decimal("-0.05")
LONG_PULLBACK_EMA20_HIGH = Decimal("0.03")
LONG_PULLBACK_EMA50_LOW = Decimal("-0.08")
LONG_PULLBACK_BARS_MIN = Decimal("3")
LONG_PULLBACK_BARS_MAX = Decimal("24")
LONG_PULLBACK_VOLUME_ROBUST_Z_MIN = Decimal("2")
LONG_PULLBACK_TAKER_BUY_RATIO_MIN = Decimal("0.60")

RuleEvaluator = Callable[[IndicatorContext, dict[str, Decimal] | None], AlertDecision | None]
RULE_REGISTRY: list[tuple[str, RuleEvaluator]] = []


def register_rule(alert_type: str) -> Callable[[RuleEvaluator], RuleEvaluator]:
    def decorator(fn: RuleEvaluator) -> RuleEvaluator:
        RULE_REGISTRY.append((alert_type, fn))
        return fn
    return decorator


def _threshold_cond(field: str, op: str, value: Decimal, threshold: Decimal) -> dict[str, Any]:
    return {"field": field, "operator": op, "value": str(value), "threshold": str(threshold)}


def _between_cond(field: str, value: Decimal, min_val: Decimal, max_val: Decimal) -> dict[str, Any]:
    return {"field": field, "operator": "between", "value": str(value), "min": str(min_val), "max": str(max_val)}


def _payload_value(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


@register_rule("flat_oi_buildup_15m")
def evaluate_flat_oi_buildup_15m(snapshot: IndicatorContext, thresholds: dict[str, Decimal] | None = None) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None
    if snapshot.return_15m is None or snapshot.oi_change_15m is None:
        return None

    t = thresholds or {}
    flat_return_limit = t.get("return_limit", FLAT_15M_RETURN_LIMIT)
    oi_buildup_threshold = t.get("oi_buildup_threshold", OI_BUILDUP_15M_THRESHOLD)

    if abs(snapshot.return_15m) > flat_return_limit:
        return None
    if snapshot.oi_change_15m < oi_buildup_threshold:
        return None

    score = min(Decimal("100"), Decimal("60") + snapshot.oi_change_15m * Decimal("100"))
    symbol = snapshot.symbol.upper()
    payload = {
        "symbol": symbol,
        "signal_window": "15m",
        "confirmation_window": "15m",
        "confirmations": ["oi_change_15m"],
        "trigger_conditions": [
            _between_cond("return_15m", snapshot.return_15m, -flat_return_limit, flat_return_limit),
            _threshold_cond("oi_change_15m", ">=", snapshot.oi_change_15m, oi_buildup_threshold),
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


@register_rule("daily_flat_oi_buildup")
def evaluate_daily_flat_oi_buildup(snapshot: IndicatorContext, thresholds: dict[str, Decimal] | None = None) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None
    if snapshot.return_24h is None or snapshot.oi_change_24h is None:
        return None

    t = thresholds or {}
    flat_return_limit = t.get("return_limit", DAILY_FLAT_RETURN_LIMIT)
    oi_buildup_threshold = t.get("oi_buildup_threshold", DAILY_OI_BUILDUP_THRESHOLD)

    if abs(snapshot.return_24h) > flat_return_limit:
        return None
    if snapshot.oi_change_24h < oi_buildup_threshold:
        return None

    score = min(Decimal("100"), Decimal("60") + snapshot.oi_change_24h * Decimal("100"))
    symbol = snapshot.symbol.upper()
    payload = {
        "symbol": symbol,
        "signal_window": "24h",
        "confirmation_window": "24h",
        "confirmations": ["oi_change_24h"],
        "trigger_conditions": [
            _between_cond("return_24h", snapshot.return_24h, -flat_return_limit, flat_return_limit),
            _threshold_cond("oi_change_24h", ">=", snapshot.oi_change_24h, oi_buildup_threshold),
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


@register_rule("breakout_watch")
def evaluate_breakout_watch(snapshot: IndicatorContext, thresholds: dict[str, Decimal] | None = None) -> AlertDecision | None:
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

    t = thresholds or {}
    near_high_bps = t.get("near_high_bps", BREAKOUT_NEAR_HIGH_BPS)
    range_compression_max = t.get("range_compression_max", BREAKOUT_RANGE_COMPRESSION_MAX)
    volume_z_min = t.get("volume_z_min", BREAKOUT_VOLUME_ROBUST_Z_MIN)
    taker_buy_min = t.get("taker_buy_min", BREAKOUT_TAKER_BUY_RATIO_MIN)
    market_return_min = t.get("market_return_min", BREAKOUT_MARKET_RELATIVE_RETURN_MIN)

    near_1h_high = snapshot.distance_to_high_1h_bps is not None and snapshot.distance_to_high_1h_bps <= near_high_bps
    near_24h_high = snapshot.distance_to_high_24h_bps is not None and snapshot.distance_to_high_24h_bps <= near_high_bps
    if not (near_1h_high or near_24h_high):
        return None
    if snapshot.range_compression_15m > range_compression_max:
        return None
    if snapshot.oi_change_15m <= 0:
        return None
    if snapshot.volume_robust_z_5m < volume_z_min:
        return None
    if snapshot.taker_buy_ratio_5m < taker_buy_min:
        return None
    if snapshot.market_relative_return_5m < market_return_min:
        return None

    symbol = snapshot.symbol.upper()
    score = min(
        Decimal("100"),
        Decimal("65") + snapshot.volume_robust_z_5m * Decimal("3") + snapshot.oi_change_15m * Decimal("100"),
    )
    high_confirmations = []
    if near_1h_high:
        high_confirmations.append("distance_to_high_1h_bps")
    if near_24h_high:
        high_confirmations.append("distance_to_high_24h_bps")

    high_cond: dict[str, Any] = {
        "field": "distance_to_high_1h_bps|distance_to_high_24h_bps",
        "operator": "<=",
        "threshold": str(near_high_bps),
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
            _threshold_cond("range_compression_15m", "<=", snapshot.range_compression_15m, range_compression_max),
            _threshold_cond("oi_change_15m", ">", snapshot.oi_change_15m, Decimal("0")),
            _threshold_cond("volume_robust_z_5m", ">=", snapshot.volume_robust_z_5m, volume_z_min),
            _threshold_cond("taker_buy_ratio_5m", ">=", snapshot.taker_buy_ratio_5m, taker_buy_min),
            _threshold_cond("market_relative_return_5m", ">=", snapshot.market_relative_return_5m, market_return_min),
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


@register_rule("breakdown_watch")
def evaluate_breakdown_watch(snapshot: IndicatorContext, thresholds: dict[str, Decimal] | None = None) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None

    t = thresholds or {}
    low_distance_bps = t.get("low_distance_bps", BREAKDOWN_LOW_DISTANCE_BPS)
    range_compression_max = t.get("range_compression_max", BREAKDOWN_RANGE_COMPRESSION_MAX)
    volume_z_min = t.get("volume_z_min", BREAKDOWN_VOLUME_ROBUST_Z_MIN)
    taker_sell_min = t.get("taker_sell_min", BREAKDOWN_TAKER_SELL_RATIO_MIN)

    near_1h_low = snapshot.distance_to_low_1h_bps is not None and snapshot.distance_to_low_1h_bps <= low_distance_bps
    near_24h_low = snapshot.distance_to_low_24h_bps is not None and snapshot.distance_to_low_24h_bps <= low_distance_bps
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
    if snapshot.range_compression_15m > range_compression_max:
        return None
    if snapshot.oi_change_15m <= 0:
        return None
    if snapshot.volume_robust_z_5m < volume_z_min:
        return None
    if snapshot.taker_sell_ratio_5m < taker_sell_min:
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

    low_cond: dict[str, Any] = {
        "field": "distance_to_low_1h_bps|distance_to_low_24h_bps",
        "operator": "<=",
        "threshold": str(low_distance_bps),
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
            _threshold_cond("range_compression_15m", "<=", snapshot.range_compression_15m, range_compression_max),
            _threshold_cond("oi_change_15m", ">", snapshot.oi_change_15m, Decimal("0")),
            _threshold_cond("volume_robust_z_5m", ">=", snapshot.volume_robust_z_5m, volume_z_min),
            _threshold_cond("taker_sell_ratio_5m", ">=", snapshot.taker_sell_ratio_5m, taker_sell_min),
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


@register_rule("long_pullback_reclaim_watch")
def evaluate_long_pullback_reclaim_watch(snapshot: IndicatorContext, thresholds: dict[str, Decimal] | None = None) -> AlertDecision | None:
    if not snapshot.baseline_ready:
        return None
    if not snapshot.is_altcoin:
        return None
    if (
        snapshot.return_7d is None
        or snapshot.range_position_7d is None
        or snapshot.last_up_leg_return is None
        or snapshot.pullback_from_high is None
        or snapshot.pullback_retrace_ratio is None
        or snapshot.low_vs_ema20_4h is None
        or snapshot.low_vs_ema50_4h is None
        or snapshot.pullback_bars_4h is None
        or snapshot.return_15m is None
        or snapshot.market_relative_return_5m is None
        or snapshot.volume_robust_z_5m is None
        or snapshot.taker_buy_ratio_5m is None
        or snapshot.oi_change_15m is None
    ):
        return None

    t = thresholds or {}
    return_7d_min = t.get("return_7d_min", LONG_PULLBACK_RETURN_7D_MIN)
    range_pos_7d_min = t.get("range_pos_7d_min", LONG_PULLBACK_RANGE_POSITION_7D_MIN)
    up_leg_min = t.get("up_leg_min", LONG_PULLBACK_UP_LEG_MIN)
    retrace_min = t.get("retrace_min", LONG_PULLBACK_RETRACE_MIN)
    retrace_max = t.get("retrace_max", LONG_PULLBACK_RETRACE_MAX)
    pullback_from_high_min = t.get("pullback_from_high_min", LONG_PULLBACK_FROM_HIGH_MIN)
    pullback_from_high_max = t.get("pullback_from_high_max", LONG_PULLBACK_FROM_HIGH_MAX)
    ema20_low = t.get("ema20_low", LONG_PULLBACK_EMA20_LOW)
    ema20_high = t.get("ema20_high", LONG_PULLBACK_EMA20_HIGH)
    ema50_low = t.get("ema50_low", LONG_PULLBACK_EMA50_LOW)
    pullback_bars_min = t.get("pullback_bars_min", LONG_PULLBACK_BARS_MIN)
    pullback_bars_max = t.get("pullback_bars_max", LONG_PULLBACK_BARS_MAX)
    volume_z_min = t.get("volume_z_min", LONG_PULLBACK_VOLUME_ROBUST_Z_MIN)
    taker_buy_min = t.get("taker_buy_min", LONG_PULLBACK_TAKER_BUY_RATIO_MIN)

    if snapshot.return_7d < return_7d_min:
        return None
    if snapshot.range_position_7d < range_pos_7d_min:
        return None
    if snapshot.last_up_leg_return < up_leg_min:
        return None
    if not (retrace_min <= snapshot.pullback_retrace_ratio <= retrace_max):
        return None
    if not (pullback_from_high_min <= snapshot.pullback_from_high <= pullback_from_high_max):
        return None
    if not (ema20_low <= snapshot.low_vs_ema20_4h <= ema20_high):
        return None
    if snapshot.low_vs_ema50_4h < ema50_low:
        return None
    if not (pullback_bars_min <= snapshot.pullback_bars_4h <= pullback_bars_max):
        return None
    if snapshot.return_15m < 0:
        return None
    if snapshot.market_relative_return_5m < 0:
        return None
    if snapshot.volume_robust_z_5m < volume_z_min:
        return None
    if snapshot.taker_buy_ratio_5m < taker_buy_min:
        return None
    if snapshot.oi_change_15m <= 0:
        return None

    symbol = snapshot.symbol.upper()
    score = min(
        Decimal("100"),
        Decimal("65")
        + snapshot.volume_robust_z_5m * Decimal("3")
        + min(Decimal("0.10"), snapshot.pullback_from_high) * Decimal("100")
        + max(Decimal("0"), snapshot.taker_buy_ratio_5m - Decimal("0.5")) * Decimal("30"),
    )
    structure_payload = snapshot.pullback_structure_payload or {}
    payload = {
        "symbol": symbol,
        "signal_window": "4h/7d",
        "confirmation_window": "5m/15m",
        "return_7d": _payload_value(snapshot.return_7d),
        "range_position_7d": _payload_value(snapshot.range_position_7d),
        "last_up_leg_return": _payload_value(snapshot.last_up_leg_return),
        "pullback_from_high": _payload_value(snapshot.pullback_from_high),
        "pullback_retrace_ratio": _payload_value(snapshot.pullback_retrace_ratio),
        "low_vs_ema20_4h": _payload_value(snapshot.low_vs_ema20_4h),
        "low_vs_ema50_4h": _payload_value(snapshot.low_vs_ema50_4h),
        "pullback_bars_4h": _payload_value(snapshot.pullback_bars_4h),
        "ema20_4h": structure_payload.get("ema20_4h"),
        "ema50_4h": structure_payload.get("ema50_4h"),
        "recent_swing_high_4h": structure_payload.get("recent_swing_high_4h"),
        "recent_swing_low_4h": structure_payload.get("recent_swing_low_4h"),
        "bars_since_high": structure_payload.get("bars_since_high"),
        "confirmations": [
            "return_7d",
            "range_position_7d",
            "last_up_leg_return",
            "pullback_retrace_ratio",
            "pullback_from_high",
            "low_vs_ema20_4h",
            "low_vs_ema50_4h",
            "pullback_bars_4h",
            "return_15m",
            "market_relative_return_5m",
            "volume_robust_z_5m",
            "taker_buy_ratio_5m",
            "oi_change_15m",
        ],
        "trigger_conditions": [
            _threshold_cond("return_7d", ">=", snapshot.return_7d, return_7d_min),
            _threshold_cond("range_position_7d", ">=", snapshot.range_position_7d, range_pos_7d_min),
            _threshold_cond("last_up_leg_return", ">=", snapshot.last_up_leg_return, up_leg_min),
            _between_cond("pullback_retrace_ratio", snapshot.pullback_retrace_ratio, retrace_min, retrace_max),
            _between_cond("pullback_from_high", snapshot.pullback_from_high, pullback_from_high_min, pullback_from_high_max),
            _between_cond("low_vs_ema20_4h", snapshot.low_vs_ema20_4h, ema20_low, ema20_high),
            _threshold_cond("low_vs_ema50_4h", ">=", snapshot.low_vs_ema50_4h, ema50_low),
            _between_cond("pullback_bars_4h", snapshot.pullback_bars_4h, pullback_bars_min, pullback_bars_max),
            _threshold_cond("return_15m", ">=", snapshot.return_15m, Decimal("0")),
            _threshold_cond("market_relative_return_5m", ">=", snapshot.market_relative_return_5m, Decimal("0")),
            _threshold_cond("volume_robust_z_5m", ">=", snapshot.volume_robust_z_5m, volume_z_min),
            _threshold_cond("taker_buy_ratio_5m", ">=", snapshot.taker_buy_ratio_5m, taker_buy_min),
            _threshold_cond("oi_change_15m", ">", snapshot.oi_change_15m, Decimal("0")),
        ],
    }

    return AlertDecision(
        ts=snapshot.ts,
        symbol=symbol,
        alert_type="long_pullback_reclaim_watch",
        severity="WARNING",
        direction="up",
        score=score,
        title=f"{symbol} long pullback reclaim watch",
        message=(
            f"{symbol} is in a 4h long-structure pullback with 5m/15m reclaim pressure."
        ),
        payload=payload,
    )
