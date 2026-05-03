from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
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


def build_indicator_context(symbol: str, klines: list[dict[str, Any]], open_interest: list[dict[str, Any]]) -> IndicatorContext:
    if len(klines) < 2 or len(open_interest) < 2:
        raise BinanceRestError("not enough market data to build indicator context")

    first_close = klines[0]["close"]
    last_close = klines[-1]["close"]
    first_oi = open_interest[0]["open_interest"]
    last_oi = open_interest[-1]["open_interest"]
    return_24h = (last_close - first_close) / first_close
    oi_change_24h = (last_oi - first_oi) / first_oi

    return IndicatorContext(
        ts=klines[-1]["ts"],
        symbol=symbol.upper(),
        return_24h=return_24h,
        oi_change_24h=oi_change_24h,
        baseline_ready=len(klines) >= 1000 and len(open_interest) >= 200,
        is_altcoin=symbol.upper() not in {"BTCUSDT", "ETHUSDT"},
    )

