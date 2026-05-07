from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

import httpx

from monitor.indicators import IndicatorContext
from monitor.config import Settings


class BinanceRestError(RuntimeError):
    pass


@dataclass(frozen=True)
class SymbolMarketData:
    symbol: str
    klines: list[dict[str, Any]]
    open_interest: list[dict[str, Any]]
    indicator: IndicatorContext
    klines_4h: list[dict[str, Any]] | None = None


def ms_to_utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def decimal_from(value: Any) -> Decimal:
    return Decimal(str(value))


class BinanceRestClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(base_url=settings.binance_rest_url, timeout=20)
        self._klines_4h_cache: dict[str, tuple[datetime, list[dict[str, Any]]]] = {}

    def fetch_klines_1m(self, symbol: str, limit: int = 1500) -> list[dict[str, Any]]:
        response = self.client.get("/fapi/v1/klines", params={"symbol": symbol.upper(), "interval": "1m", "limit": limit})
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise BinanceRestError("unexpected kline response")
        parsed = [parse_rest_kline(symbol, row) for row in rows]
        closed = _closed_rest_klines(parsed, datetime.now(UTC))
        return [_kline_repository_values(row) for row in closed]

    def fetch_klines_4h(self, symbol: str, limit: int = 80) -> list[dict[str, Any]]:
        response = self.client.get("/fapi/v1/klines", params={"symbol": symbol.upper(), "interval": "4h", "limit": limit})
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise BinanceRestError("unexpected kline response")
        parsed = []
        for row in rows:
            kline = parse_rest_kline(symbol, row)
            kline["close_time"] = ms_to_utc(int(row[6]))
            parsed.append(kline)
        return parsed

    def fetch_open_interest_5m(self, symbol: str, limit: int = 300) -> list[dict[str, Any]]:
        response = self.client.get(
            "/futures/data/openInterestHist",
            params={"symbol": symbol.upper(), "period": "5m", "limit": limit},
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise BinanceRestError("unexpected open interest response")
        return [parse_open_interest(symbol, row) for row in rows]

    def fetch_symbol_market_data(self, symbol: str) -> SymbolMarketData:
        normalized = symbol.upper()
        klines = self.fetch_klines_1m(normalized)
        open_interest = self.fetch_open_interest_5m(normalized)
        klines_4h = self._cached_closed_klines_4h(normalized, klines[-1]["ts"])
        return SymbolMarketData(
            symbol=normalized,
            klines=klines,
            open_interest=open_interest,
            indicator=build_indicator_context(normalized, klines, open_interest, klines_4h),
            klines_4h=klines_4h,
        )

    def _cached_closed_klines_4h(self, symbol: str, latest_1m_ts: datetime) -> list[dict[str, Any]]:
        cached = self._klines_4h_cache.get(symbol)
        if cached is not None:
            refresh_at, rows = cached
            if latest_1m_ts < refresh_at:
                return rows

        rows = _closed_klines_4h(self.fetch_klines_4h(symbol), latest_1m_ts)
        self._klines_4h_cache[symbol] = (_next_4h_refresh_at(latest_1m_ts), rows)
        return rows


def parse_rest_kline(symbol: str, row: list[Any]) -> dict[str, Any]:
    if len(row) < 11:
        raise BinanceRestError("kline row has too few fields")
    return {
        "ts": ms_to_utc(int(row[0])),
        "close_time": ms_to_utc(int(row[6])),
        "symbol": symbol.upper(),
        "open": decimal_from(row[1]),
        "high": decimal_from(row[2]),
        "low": decimal_from(row[3]),
        "close": decimal_from(row[4]),
        "base_volume": decimal_from(row[5]),
        "quote_volume": decimal_from(row[7]),
        "trade_count": int(row[8]),
        "taker_buy_base_volume": decimal_from(row[9]),
        "taker_buy_quote_volume": decimal_from(row[10]),
    }


def _closed_rest_klines(klines: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    return [row for row in klines if row.get("close_time") is not None and row["close_time"] <= now]


def _kline_repository_values(kline: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kline.items() if key != "close_time"}


def _closed_klines_4h(klines_4h: list[dict[str, Any]], latest_1m_ts: datetime) -> list[dict[str, Any]]:
    latest_1m_close = latest_1m_ts + timedelta(minutes=1)
    return [row for row in klines_4h if row.get("close_time") is not None and row["close_time"] <= latest_1m_close]


def _next_4h_refresh_at(ts: datetime) -> datetime:
    utc_ts = ts.astimezone(UTC)
    next_hour = (utc_ts.hour // 4 + 1) * 4
    day = utc_ts.date()
    if next_hour >= 24:
        next_hour -= 24
        day = day + timedelta(days=1)
    return datetime.combine(day, time(next_hour, 2), tzinfo=UTC)


def parse_open_interest(symbol: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ts": ms_to_utc(int(row["timestamp"])),
        "symbol": symbol.upper(),
        "open_interest": decimal_from(row["sumOpenInterest"]),
        "open_interest_value": decimal_from(row["sumOpenInterestValue"]),
        "period": "5m",
        "source": "openInterestHist",
    }


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _window_return(klines: list[dict[str, Any]]) -> Decimal | None:
    if len(klines) < 2:
        return None
    return _safe_ratio(klines[-1]["close"] - klines[0]["close"], klines[0]["close"])


def _utc_day_start(ts: datetime) -> datetime:
    return datetime.combine(ts.astimezone(UTC).date(), time.min, tzinfo=UTC)


def _window_since(rows: list[dict[str, Any]], start_ts: datetime) -> list[dict[str, Any]]:
    return [row for row in rows if row["ts"] >= start_ts]


def _first_at_or_after(rows: list[dict[str, Any]], boundary: datetime) -> dict[str, Any] | None:
    return next((row for row in rows if row["ts"] >= boundary), None)


def _utc_day_window(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_day_start = _utc_day_start(rows[-1]["ts"])
    previous_day_start = latest_day_start - timedelta(days=1)
    previous_boundary = _first_at_or_after(rows, previous_day_start)
    current_boundary = _first_at_or_after(rows, latest_day_start)
    if (
        previous_boundary is not None
        and current_boundary is not None
        and previous_boundary is not current_boundary
        and previous_boundary["ts"] <= previous_day_start + timedelta(hours=1)
        and current_boundary["ts"] <= latest_day_start + timedelta(hours=1)
    ):
        return [previous_boundary, current_boundary]
    return _window_since(rows, latest_day_start)


def _oi_change(open_interest: list[dict[str, Any]]) -> Decimal | None:
    if len(open_interest) < 2:
        return None
    return _safe_ratio(open_interest[-1]["open_interest"] - open_interest[0]["open_interest"], open_interest[0]["open_interest"])


def _distance_to_high_bps(klines: list[dict[str, Any]], last_close: Decimal) -> Decimal | None:
    if not klines or last_close == 0:
        return None
    return (max(row["high"] for row in klines) - last_close) / last_close * Decimal("10000")


def _distance_to_low_bps(klines: list[dict[str, Any]], last_close: Decimal) -> Decimal | None:
    if not klines or last_close == 0:
        return None
    return (last_close - min(row["low"] for row in klines)) / last_close * Decimal("10000")


def _amplitude_ratio(klines: list[dict[str, Any]]) -> Decimal | None:
    if not klines or klines[0]["open"] == 0:
        return None
    return (max(row["high"] for row in klines) - min(row["low"] for row in klines)) / klines[0]["open"]


def _range_compression_15m(klines: list[dict[str, Any]]) -> Decimal | None:
    if len(klines) < 30:
        return None
    current = _amplitude_ratio(klines[-15:])
    samples = [
        sample
        for i in range(0, len(klines[-1440:]) - 14, 15)
        if (sample := _amplitude_ratio(klines[-1440:][i : i + 15])) is not None
    ]
    if current is None or len(samples) < 20:
        return None
    baseline = median(samples)
    if baseline == 0:
        return None
    return current / baseline


def _disjoint_5m_quote_volumes(klines: list[dict[str, Any]]) -> list[Decimal]:
    return [
        sum(row["quote_volume"] for row in klines[i : i + 5])
        for i in range(0, len(klines) - 4, 5)
    ]


def _volume_robust_z_5m(klines: list[dict[str, Any]]) -> Decimal | None:
    if len(klines) < 1000:
        return None
    current = sum(row["quote_volume"] for row in klines[-5:])
    samples = _disjoint_5m_quote_volumes(klines[:-5])
    if len(samples) < 200:
        return None
    med = median(samples)
    mad = median([abs(value - med) for value in samples])
    if mad == 0:
        return None
    return (current - med) / (Decimal("1.4826") * mad)


def _taker_buy_ratio_5m(klines: list[dict[str, Any]]) -> Decimal | None:
    if len(klines) < 5:
        return None
    quote_volume = sum(row["quote_volume"] for row in klines[-5:])
    if quote_volume == 0:
        return None
    taker_buy_quote = sum(row["taker_buy_quote_volume"] for row in klines[-5:])
    return taker_buy_quote / quote_volume


def _ema_with_seed(values: list[Decimal], period: int) -> Decimal | None:
    if len(values) < period:
        return None
    ema = sum(values[:period]) / Decimal(period)
    alpha = Decimal("2") / Decimal(period + 1)
    for value in values[period:]:
        ema = value * alpha + ema * (Decimal("1") - alpha)
    return ema


def _trend_pullback_metrics(klines_4h: list[dict[str, Any]], last_close: Decimal) -> dict[str, Any]:
    none_metrics: dict[str, Any] = {
        "return_7d": None,
        "range_position_7d": None,
        "last_up_leg_return": None,
        "pullback_from_high": None,
        "pullback_retrace_ratio": None,
        "low_vs_ema20_4h": None,
        "low_vs_ema50_4h": None,
        "pullback_bars_4h": None,
        "payload": None,
    }
    if len(klines_4h) < 60:
        return none_metrics

    candles = klines_4h[-60:]
    closes = [row["close"] for row in candles]
    ema20 = _ema_with_seed(closes, 20)
    ema50 = _ema_with_seed(closes, 50)
    if ema20 is None or ema50 is None or ema20 == 0 or ema50 == 0:
        return none_metrics

    swing_high = max(row["high"] for row in candles)
    high_idx = next(i for i, row in enumerate(candles) if row["high"] == swing_high)
    swing_low = min(row["low"] for row in candles[: high_idx + 1])
    up_leg = swing_high - swing_low
    if swing_low == 0 or swing_high == 0 or up_leg == 0:
        return none_metrics

    last_7d = candles[-42:]
    min7d_low = min(row["low"] for row in last_7d)
    max7d_high = max(row["high"] for row in last_7d)
    range_7d = max7d_high - min7d_low
    seven_day_open = candles[-42]["close"]
    if range_7d == 0 or seven_day_open == 0:
        return none_metrics

    pullback_bars = len(candles) - high_idx - 1
    return {
        "return_7d": _safe_ratio(last_close - seven_day_open, seven_day_open),
        "range_position_7d": _safe_ratio(last_close - min7d_low, range_7d),
        "last_up_leg_return": _safe_ratio(up_leg, swing_low),
        "pullback_from_high": _safe_ratio(swing_high - last_close, swing_high),
        "pullback_retrace_ratio": _safe_ratio(swing_high - last_close, up_leg),
        "low_vs_ema20_4h": _safe_ratio(last_close - ema20, ema20),
        "low_vs_ema50_4h": _safe_ratio(last_close - ema50, ema50),
        "pullback_bars_4h": Decimal(pullback_bars),
        "payload": {
            "ema20_4h": str(ema20),
            "ema50_4h": str(ema50),
            "recent_swing_high_4h": str(swing_high),
            "recent_swing_low_4h": str(swing_low),
            "bars_since_high": str(pullback_bars),
        },
    }


def build_indicator_context(
    symbol: str,
    klines: list[dict[str, Any]],
    open_interest: list[dict[str, Any]],
    klines_4h: list[dict[str, Any]] | None = None,
) -> IndicatorContext:
    if len(klines) < 2 or len(open_interest) < 2:
        raise BinanceRestError("not enough market data to build indicator context")

    last_close = klines[-1]["close"]
    pullback_metrics = _trend_pullback_metrics(klines_4h or [], last_close)
    return_24h = _window_return(_utc_day_window(klines))
    oi_change_24h = _oi_change(_utc_day_window(open_interest))
    return_15m = _window_return(klines[-15:]) if len(klines) >= 15 else None
    oi_change_15m = _oi_change(open_interest[-3:]) if len(open_interest) >= 3 else None
    distance_to_high_1h_bps = _distance_to_high_bps(klines[-60:], last_close) if len(klines) >= 60 else None
    distance_to_high_24h_bps = _distance_to_high_bps(klines[-1440:], last_close) if len(klines) >= 1440 else None
    distance_to_low_1h_bps = _distance_to_low_bps(klines[-60:], last_close) if len(klines) >= 60 else None
    distance_to_low_24h_bps = _distance_to_low_bps(klines[-1440:], last_close) if len(klines) >= 1440 else None
    taker_buy_ratio_5m = _taker_buy_ratio_5m(klines)

    return IndicatorContext(
        ts=klines[-1]["ts"],
        symbol=symbol.upper(),
        return_24h=return_24h,
        oi_change_24h=oi_change_24h,
        baseline_ready=len(klines) >= 1000 and len(open_interest) >= 200,
        is_altcoin=symbol.upper() not in {"BTCUSDT", "ETHUSDT"},
        return_15m=return_15m,
        oi_change_15m=oi_change_15m,
        distance_to_high_1h_bps=distance_to_high_1h_bps,
        distance_to_high_24h_bps=distance_to_high_24h_bps,
        distance_to_low_1h_bps=distance_to_low_1h_bps,
        distance_to_low_24h_bps=distance_to_low_24h_bps,
        range_compression_15m=_range_compression_15m(klines),
        volume_robust_z_5m=_volume_robust_z_5m(klines),
        taker_buy_ratio_5m=taker_buy_ratio_5m,
        taker_sell_ratio_5m=None if taker_buy_ratio_5m is None else Decimal("1") - taker_buy_ratio_5m,
        return_7d=pullback_metrics["return_7d"],
        range_position_7d=pullback_metrics["range_position_7d"],
        last_up_leg_return=pullback_metrics["last_up_leg_return"],
        pullback_from_high=pullback_metrics["pullback_from_high"],
        pullback_retrace_ratio=pullback_metrics["pullback_retrace_ratio"],
        low_vs_ema20_4h=pullback_metrics["low_vs_ema20_4h"],
        low_vs_ema50_4h=pullback_metrics["low_vs_ema50_4h"],
        pullback_bars_4h=pullback_metrics["pullback_bars_4h"],
        pullback_structure_payload=pullback_metrics["payload"],
    )


def build_indicator_contexts(symbol_data: dict[str, SymbolMarketData]) -> dict[str, IndicatorContext]:
    contexts = {
        symbol.upper(): build_indicator_context(symbol, data.klines, data.open_interest, getattr(data, "klines_4h", None))
        for symbol, data in symbol_data.items()
    }
    returns_5m = {
        symbol.upper(): value
        for symbol, data in symbol_data.items()
        if contexts[symbol.upper()].is_altcoin and (value := _window_return(data.klines[-5:])) is not None
    }
    if not returns_5m:
        return contexts

    market_median = median(list(returns_5m.values()))
    return {
        symbol: replace(context, market_relative_return_5m=returns_5m.get(symbol) - market_median if symbol in returns_5m else None)
        for symbol, context in contexts.items()
    }
