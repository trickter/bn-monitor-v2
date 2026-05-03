from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from monitor.app import run_live_smoke
from monitor.binance.rest import build_indicator_context, parse_open_interest, parse_rest_kline
from monitor.config import Settings


class FakeSession:
    def __init__(self) -> None:
        self.executed = []

    def execute(self, statement) -> None:
        self.executed.append(statement)


class FakeBinanceClient:
    def fetch_symbol_market_data(self, symbol: str):
        return SimpleNamespace(
            klines=synthetic_klines(symbol),
            open_interest=synthetic_open_interest(symbol),
        )


def synthetic_klines(symbol: str) -> list[dict]:
    start = datetime(2026, 5, 3, tzinfo=UTC)
    rows = []
    for i in range(1441):
        close = Decimal("100") + Decimal(i) / Decimal("1440")
        quote_volume = Decimal("1000") + Decimal(i % 11)
        rows.append(
            {
                "ts": start + timedelta(minutes=i),
                "symbol": symbol.upper(),
                "open": close,
                "high": close + Decimal("1"),
                "low": close - Decimal("1"),
                "close": close,
                "base_volume": Decimal("10"),
                "quote_volume": quote_volume,
                "trade_count": 10,
                "taker_buy_base_volume": Decimal("5"),
                "taker_buy_quote_volume": quote_volume * Decimal("0.5"),
            }
        )
    return rows


def synthetic_open_interest(symbol: str) -> list[dict]:
    start = datetime(2026, 5, 3, tzinfo=UTC)
    return [
        {
            "ts": start + timedelta(minutes=i * 5),
            "symbol": symbol.upper(),
            "open_interest": Decimal("1000") + Decimal(i) * Decimal("0.5"),
            "open_interest_value": Decimal("100000") + Decimal(i) * Decimal("50"),
            "period": "5m",
            "source": "openInterestHist",
        }
        for i in range(288)
    ]


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def test_parse_rest_kline_maps_fields() -> None:
    values = parse_rest_kline(
        "SOLUSDT",
        [1714700000000, "100", "101", "99", "100.5", "10", 1714700059999, "1000", 42, "5", "500", "0"],
    )

    assert values["symbol"] == "SOLUSDT"
    assert values["close"] == Decimal("100.5")
    assert values["quote_volume"] == Decimal("1000")
    assert values["trade_count"] == 42


def test_parse_open_interest_maps_fields() -> None:
    values = parse_open_interest(
        "SOLUSDT",
        {"sumOpenInterest": "100", "sumOpenInterestValue": "1000", "timestamp": 1714700000000},
    )

    assert values["symbol"] == "SOLUSDT"
    assert values["open_interest"] == Decimal("100")
    assert values["period"] == "5m"


def test_build_indicator_context_computes_return_and_oi_change() -> None:
    klines = synthetic_klines("SOLUSDT")
    open_interest = synthetic_open_interest("SOLUSDT")

    context = build_indicator_context("SOLUSDT", klines, open_interest)

    assert context.return_24h == Decimal("0.01")
    assert context.oi_change_24h == Decimal("143.5") / Decimal("1000")
    assert context.baseline_ready is True
    assert context.is_altcoin is True


def test_run_live_smoke_persists_market_data_and_alert(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=shadow\n")
    session = FakeSession()

    result = run_live_smoke(settings, session, ["SOLUSDT"], binance_client=FakeBinanceClient(), send_discord=False)

    assert result["summary"]["total"] == 1
    assert result["summary"]["by_type"] == {"daily_flat_oi_buildup": 1}
    assert len(session.executed) == 1441 + 288 + 1
