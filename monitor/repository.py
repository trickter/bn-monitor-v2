from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from monitor.models import Alert, FuturesKline1m, FuturesOpenInterest, Symbol


SYMBOL_UPDATE_COLUMNS = (
    "base_asset",
    "quote_asset",
    "contract_type",
    "status",
    "tick_size",
    "step_size",
    "min_notional",
    "tier",
    "is_active",
    "updated_at",
)

KLINE_UPDATE_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "base_volume",
    "quote_volume",
    "trade_count",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
)

OPEN_INTEREST_UPDATE_COLUMNS = (
    "open_interest",
    "open_interest_value",
    "source",
)


def build_upsert_symbol_statement(values: Mapping[str, Any]):
    stmt = insert(Symbol).values(**values)
    return stmt.on_conflict_do_update(
        index_elements=["exchange", "market_type", "symbol"],
        set_={column: getattr(stmt.excluded, column) for column in SYMBOL_UPDATE_COLUMNS if column in values},
    )


def upsert_symbol(session: Session, values: Mapping[str, Any]) -> None:
    session.execute(build_upsert_symbol_statement(values))


def build_upsert_kline_1m_statement(values: Mapping[str, Any]):
    stmt = insert(FuturesKline1m).values(**values)
    return stmt.on_conflict_do_update(
        index_elements=["ts", "symbol"],
        set_={column: getattr(stmt.excluded, column) for column in KLINE_UPDATE_COLUMNS if column in values},
    )


def upsert_kline_1m(session: Session, values: Mapping[str, Any]) -> None:
    session.execute(build_upsert_kline_1m_statement(values))


def build_upsert_open_interest_statement(values: Mapping[str, Any]):
    stmt = insert(FuturesOpenInterest).values(**values)
    return stmt.on_conflict_do_update(
        index_elements=["ts", "symbol", "period"],
        set_={column: getattr(stmt.excluded, column) for column in OPEN_INTEREST_UPDATE_COLUMNS if column in values},
    )


def upsert_open_interest(session: Session, values: Mapping[str, Any]) -> None:
    session.execute(build_upsert_open_interest_statement(values))


def build_insert_alert_once_statement(values: Mapping[str, Any]):
    stmt = insert(Alert).values(**values)
    return stmt.on_conflict_do_nothing(index_elements=["ts", "symbol", "alert_type", "mode"])


def insert_alert_once(session: Session, values: Mapping[str, Any]) -> None:
    session.execute(build_insert_alert_once_statement(values))
