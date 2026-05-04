from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.dialects import postgresql

from monitor.repository import (
    build_insert_alert_once_statement,
    build_upsert_alert_cooldown_statement,
    build_upsert_kline_1m_statement,
    build_upsert_open_interest_statement,
    build_upsert_symbol_statement,
    insert_alert_once,
    upsert_alert_cooldown,
    upsert_kline_1m,
    upsert_open_interest,
    upsert_symbol,
)


class FakeSession:
    def __init__(self) -> None:
        self.executed = []

    def execute(self, statement) -> None:
        self.executed.append(statement)


def compile_sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def symbol_values() -> dict:
    return {
        "exchange": "binance",
        "market_type": "usd_m_futures",
        "symbol": "SOLUSDT",
        "base_asset": "SOL",
        "quote_asset": "USDT",
        "contract_type": "PERPETUAL",
        "status": "TRADING",
        "tick_size": Decimal("0.001"),
        "step_size": Decimal("1"),
        "min_notional": Decimal("5"),
        "tier": 1,
        "is_active": True,
    }


def kline_values() -> dict:
    return {
        "ts": datetime(2026, 5, 3, 1, 2, tzinfo=timezone.utc),
        "symbol": "SOLUSDT",
        "open": Decimal("100"),
        "high": Decimal("101"),
        "low": Decimal("99"),
        "close": Decimal("100.5"),
        "base_volume": Decimal("123"),
        "quote_volume": Decimal("12345"),
        "trade_count": 42,
        "taker_buy_base_volume": Decimal("60"),
        "taker_buy_quote_volume": Decimal("6000"),
    }


def alert_values() -> dict:
    return {
        "ts": datetime(2026, 5, 3, 1, 2, tzinfo=timezone.utc),
        "symbol": "SOLUSDT",
        "alert_type": "daily_flat_oi_buildup",
        "severity": "WARNING",
        "direction": "none",
        "state": "open",
        "score": Decimal("82.5"),
        "title": "SOLUSDT OI buildup",
        "message": "SOLUSDT is flat while OI builds.",
        "payload": {
            "symbol": "SOLUSDT",
            "signal_window": "24h",
            "confirmation_window": "24h",
            "confirmations": [],
            "trigger_conditions": [],
        },
        "mode": "shadow",
        "delivery_status": "suppressed",
    }


def open_interest_values() -> dict:
    return {
        "ts": datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc),
        "symbol": "SOLUSDT",
        "open_interest": Decimal("1000"),
        "open_interest_value": Decimal("100000"),
        "period": "5m",
        "source": "openInterestHist",
    }


def alert_cooldown_values() -> dict:
    return {
        "key": "live:SOLUSDT:daily_flat_oi_buildup:discord",
        "last_sent_at": datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc),
        "last_score": Decimal("72"),
        "count_1h": 1,
        "updated_at": datetime(2026, 5, 3, 1, 0, tzinfo=timezone.utc),
    }


def test_symbol_upsert_uses_primary_key_conflict_target() -> None:
    sql = compile_sql(build_upsert_symbol_statement(symbol_values()))

    assert "ON CONFLICT (exchange, market_type, symbol) DO UPDATE" in sql
    assert "base_asset = excluded.base_asset" in sql
    assert "status = excluded.status" in sql


def test_kline_upsert_uses_ts_symbol_conflict_target() -> None:
    sql = compile_sql(build_upsert_kline_1m_statement(kline_values()))

    assert "ON CONFLICT (ts, symbol) DO UPDATE" in sql
    assert "close = excluded.close" in sql
    assert "quote_volume = excluded.quote_volume" in sql


def test_alert_insert_is_idempotent_do_nothing() -> None:
    sql = compile_sql(build_insert_alert_once_statement(alert_values()))

    assert "ON CONFLICT (ts, symbol, alert_type, mode) DO NOTHING" in sql
    assert "DO UPDATE" not in sql


def test_alert_cooldown_upsert_uses_key_conflict_target() -> None:
    sql = compile_sql(build_upsert_alert_cooldown_statement(alert_cooldown_values()))

    assert "ON CONFLICT (key) DO UPDATE" in sql
    assert "last_sent_at = excluded.last_sent_at" in sql


def test_open_interest_upsert_uses_ts_symbol_period_conflict_target() -> None:
    sql = compile_sql(build_upsert_open_interest_statement(open_interest_values()))

    assert "ON CONFLICT (ts, symbol, period) DO UPDATE" in sql
    assert "open_interest = excluded.open_interest" in sql
    assert "open_interest_value = excluded.open_interest_value" in sql


def test_repository_functions_execute_statements() -> None:
    session = FakeSession()

    upsert_symbol(session, symbol_values())
    upsert_kline_1m(session, kline_values())
    upsert_open_interest(session, open_interest_values())
    insert_alert_once(session, alert_values())
    upsert_alert_cooldown(session, alert_cooldown_values())

    assert len(session.executed) == 5
