from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
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


def ms_to_utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def decimal_from(value: Any) -> Decimal:
    return Decimal(str(value))


class BinanceRestClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(base_url=settings.binance_rest_url, timeout=20)

    def fetch_klines_1m(self, symbol: str, limit: int = 1441) -> list[dict[str, Any]]:
        response = self.client.get("/fapi/v1/klines", params={"symbol": symbol.upper(), "interval": "1m", "limit": limit})
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise BinanceRestError("unexpected kline response")
        return [parse_rest_kline(symbol, row) for row in rows]

    def fetch_open_interest_5m(self, symbol: str, limit: int = 288) -> list[dict[str, Any]]:
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
        return SymbolMarketData(
            symbol=normalized,
            klines=klines,
            open_interest=open_interest,
            indicator=build_indicator_context(normalized, klines, open_interest),
        )


def parse_rest_kline(symbol: str, row: list[Any]) -> dict[str, Any]:
    if len(row) < 11:
        raise BinanceRestError("kline row has too few fields")
    return {
        "ts": ms_to_utc(int(row[0])),
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


def build_indicator_context(symbol: str, klines: list[dict[str, Any]], open_interest: list[dict[str, Any]]) -> IndicatorContext:
    if len(klines) < 2 or len(open_interest) < 2:
        raise BinanceRestError("not enough market data to build indicator context")

    last_close = klines[-1]["close"]
    return_24h = _window_return(klines)
    oi_change_24h = _oi_change(open_interest)
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
    )


def build_indicator_contexts(symbol_data: dict[str, SymbolMarketData]) -> dict[str, IndicatorContext]:
    contexts = {
        symbol.upper(): build_indicator_context(symbol, data.klines, data.open_interest)
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
