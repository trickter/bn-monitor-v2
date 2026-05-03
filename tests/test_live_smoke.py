from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from monitor.indicators import IndicatorContext
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
        class MarketData:
            pass

        data = MarketData()
        data.klines = [
            {
                "ts": datetime(2026, 5, 3, 1, 0, tzinfo=UTC),
                "symbol": symbol,
                "open": Decimal("100"),
                "high": Decimal("101"),
                "low": Decimal("99"),
                "close": Decimal("100"),
                "base_volume": Decimal("1"),
                "quote_volume": Decimal("100"),
                "trade_count": 1,
                "taker_buy_base_volume": Decimal("0.5"),
                "taker_buy_quote_volume": Decimal("50"),
            }
        ]
        data.open_interest = [
            {
                "ts": datetime(2026, 5, 3, 1, 0, tzinfo=UTC),
                "symbol": symbol,
                "open_interest": Decimal("100"),
                "open_interest_value": Decimal("1000"),
                "period": "5m",
                "source": "openInterestHist",
            }
        ]
        data.indicator = IndicatorContext(
            ts=datetime(2026, 5, 3, 1, 0, tzinfo=UTC),
            symbol=symbol,
            return_24h=Decimal("0.01"),
            oi_change_24h=Decimal("0.12"),
            baseline_ready=True,
            is_altcoin=True,
        )
        return data


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
    klines = [
        {"ts": datetime(2026, 5, 3, 1, 0, tzinfo=UTC), "close": Decimal("100")},
        {"ts": datetime(2026, 5, 4, 1, 0, tzinfo=UTC), "close": Decimal("102")},
    ] * 600
    open_interest = [
        {"open_interest": Decimal("100")},
        {"open_interest": Decimal("115")},
    ] * 120

    context = build_indicator_context("SOLUSDT", klines, open_interest)

    assert context.return_24h == Decimal("0.02")
    assert context.oi_change_24h == Decimal("0.15")
    assert context.baseline_ready is True
    assert context.is_altcoin is True


def test_run_live_smoke_persists_market_data_and_alert(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=shadow\n")
    session = FakeSession()

    result = run_live_smoke(settings, session, ["SOLUSDT"], binance_client=FakeBinanceClient(), send_discord=False)

    assert result["summary"]["total"] == 1
    assert result["summary"]["by_type"] == {"daily_flat_oi_buildup": 1}
    assert len(session.executed) == 3

