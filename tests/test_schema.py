from __future__ import annotations

from pathlib import Path
import importlib.util

from sqlalchemy import CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB

from monitor.models import Base


EXPECTED_TABLES = {
    "symbols",
    "futures_kline_1m",
    "futures_open_interest",
    "futures_mark_price",
    "liquidation_snapshots",
    "market_factor_1m",
    "indicator_snapshot_1m",
    "alerts",
    "alert_cooldowns",
}

TIMESERIES_TABLES = {
    "futures_kline_1m",
    "futures_open_interest",
    "futures_mark_price",
    "liquidation_snapshots",
    "market_factor_1m",
    "indicator_snapshot_1m",
    "alerts",
}


def test_metadata_contains_core_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_alerts_table_has_replay_columns_and_payload_jsonb() -> None:
    alerts = Base.metadata.tables["alerts"]

    for column_name in (
        "ts",
        "symbol",
        "alert_type",
        "severity",
        "direction",
        "state",
        "score",
        "title",
        "message",
        "payload",
        "mode",
        "delivery_status",
    ):
        assert column_name in alerts.c

    assert isinstance(alerts.c.payload.type, JSONB)


def test_liquidation_raw_is_jsonb() -> None:
    liquidations = Base.metadata.tables["liquidation_snapshots"]

    assert isinstance(liquidations.c.raw.type, JSONB)


def test_alerts_constraints_and_unique_index_exist() -> None:
    alerts = Base.metadata.tables["alerts"]
    constraint_names = {constraint.name for constraint in alerts.constraints if isinstance(constraint, CheckConstraint)}
    index_names = {index.name for index in alerts.indexes if isinstance(index, Index)}

    assert {
        "ck_alerts_severity",
        "ck_alerts_direction",
        "ck_alerts_state",
        "ck_alerts_mode",
        "ck_alerts_delivery_status",
    }.issubset(constraint_names)
    assert "uq_alerts_source_signal" in index_names
    assert "ix_alerts_replay" in index_names
    assert next(index for index in alerts.indexes if index.name == "uq_alerts_source_signal").unique is True


def test_primary_keys_match_schema() -> None:
    tables = Base.metadata.tables

    assert [column.name for column in tables["symbols"].primary_key] == ["exchange", "market_type", "symbol"]
    assert [column.name for column in tables["futures_kline_1m"].primary_key] == ["ts", "symbol"]
    assert [column.name for column in tables["futures_open_interest"].primary_key] == ["ts", "symbol", "period"]
    assert [column.name for column in tables["liquidation_snapshots"].primary_key] == ["ts", "id"]
    assert [column.name for column in tables["alerts"].primary_key] == ["ts", "id"]
    assert [column.name for column in tables["alert_cooldowns"].primary_key] == ["key"]


def test_initial_migration_contains_timescale_hypertables() -> None:
    migration_path = Path("alembic/versions/0001_initial.py")
    migration = migration_path.read_text(encoding="utf-8")
    spec = importlib.util.spec_from_file_location("migration_0001_initial", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in migration
    assert "create_hypertable" in migration
    assert set(module.TIMESERIES_TABLES) == TIMESERIES_TABLES
