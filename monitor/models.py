from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


DECIMAL = Numeric(38, 18)
RATIO = Numeric(8, 6)
JSONB_TYPE = JSONB


class Base(DeclarativeBase):
    pass


class Symbol(Base):
    __tablename__ = "symbols"

    exchange: Mapped[str] = mapped_column(Text, nullable=False)
    market_type: Mapped[str] = mapped_column(Text, nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    base_asset: Mapped[str] = mapped_column(Text, nullable=False)
    quote_asset: Mapped[str] = mapped_column(Text, nullable=False)
    contract_type: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    tick_size: Mapped[Decimal | None] = mapped_column(DECIMAL)
    step_size: Mapped[Decimal | None] = mapped_column(DECIMAL)
    min_notional: Mapped[Decimal | None] = mapped_column(DECIMAL)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (PrimaryKeyConstraint("exchange", "market_type", "symbol"),)


class FuturesKline1m(Base):
    __tablename__ = "futures_kline_1m"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    open: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    high: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    low: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    close: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    base_volume: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    quote_volume: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    taker_buy_base_volume: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    taker_buy_quote_volume: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("ts", "symbol"),
        Index("ix_futures_kline_1m_symbol_ts", "symbol", ts.desc()),
    )


class FuturesOpenInterest(Base):
    __tablename__ = "futures_open_interest"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    open_interest: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    open_interest_value: Mapped[Decimal | None] = mapped_column(DECIMAL)
    period: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'5m'"))
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'openInterestHist'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("ts", "symbol", "period"),
        Index("ix_futures_open_interest_symbol_ts", "symbol", ts.desc()),
    )


class FuturesMarkPrice(Base):
    __tablename__ = "futures_mark_price"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    mark_price: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    index_price: Mapped[Decimal | None] = mapped_column(DECIMAL)
    funding_rate: Mapped[Decimal | None] = mapped_column(DECIMAL)
    next_funding_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("ts", "symbol"),
        Index("ix_futures_mark_price_symbol_ts", "symbol", ts.desc()),
    )


class LiquidationSnapshot(Base):
    __tablename__ = "liquidation_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    side: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    average_price: Mapped[Decimal | None] = mapped_column(DECIMAL)
    quantity: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    quote_value: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("ts", "id"),
        Index("ix_liquidation_snapshots_symbol_side_ts", "symbol", "side", ts.desc()),
    )


class MarketFactor1m(Base):
    __tablename__ = "market_factor_1m"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    btc_return_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    eth_return_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    market_median_return_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    market_dispersion_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    btc_return_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    eth_return_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    market_median_return_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    market_dispersion_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class IndicatorSnapshot1m(Base):
    __tablename__ = "indicator_snapshot_1m"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    return_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    return_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    return_15m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    return_24h: Mapped[Decimal | None] = mapped_column(DECIMAL)
    btc_relative_return_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    market_relative_return_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    btc_relative_return_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    market_relative_return_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    quote_volume_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    quote_volume_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    volume_percentile_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    volume_robust_z_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    volume_percentile_5m: Mapped[Decimal | None] = mapped_column(RATIO)
    volume_robust_z_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    taker_buy_ratio_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    taker_sell_ratio_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    taker_buy_ratio_5m: Mapped[Decimal | None] = mapped_column(RATIO)
    candle_body_ratio_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    candle_body_ratio_5m: Mapped[Decimal | None] = mapped_column(RATIO)
    candle_range_bps_1m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    candle_range_bps_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    upper_wick_ratio_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    lower_wick_ratio_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    close_position_ratio_1m: Mapped[Decimal | None] = mapped_column(RATIO)
    distance_to_high_1h_bps: Mapped[Decimal | None] = mapped_column(DECIMAL)
    distance_to_low_1h_bps: Mapped[Decimal | None] = mapped_column(DECIMAL)
    distance_to_high_24h_bps: Mapped[Decimal | None] = mapped_column(DECIMAL)
    distance_to_low_24h_bps: Mapped[Decimal | None] = mapped_column(DECIMAL)
    range_compression_15m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    oi_change_5m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    oi_change_15m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    oi_change_24h: Mapped[Decimal | None] = mapped_column(DECIMAL)
    oi_robust_z_15m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    price_move_norm_15m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    oi_move_norm_15m: Mapped[Decimal | None] = mapped_column(DECIMAL)
    funding_rate: Mapped[Decimal | None] = mapped_column(DECIMAL)
    funding_percentile: Mapped[Decimal | None] = mapped_column(RATIO)
    price_spike_score: Mapped[Decimal | None] = mapped_column(DECIMAL)
    flat_oi_buildup_score: Mapped[Decimal | None] = mapped_column(DECIMAL)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("ts", "symbol"),
        Index("ix_indicator_snapshot_1m_symbol_ts", "symbol", ts.desc()),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    alert_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB_TYPE, nullable=False)
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(Text, nullable=False)
    discord_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_alert_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        PrimaryKeyConstraint("ts", "id"),
        CheckConstraint("severity IN ('INFO', 'WARNING', 'CRITICAL')", name="ck_alerts_severity"),
        CheckConstraint("direction IN ('none', 'up', 'down', 'long', 'short')", name="ck_alerts_direction"),
        CheckConstraint("state IN ('open', 'escalated', 'resolved', 'expired')", name="ck_alerts_state"),
        CheckConstraint("mode IN ('shadow', 'live')", name="ck_alerts_mode"),
        CheckConstraint(
            "delivery_status IN ('shadow', 'pending', 'sent', 'failed', 'rate_limited', 'suppressed')",
            name="ck_alerts_delivery_status",
        ),
        Index("uq_alerts_source_signal", "ts", "symbol", "alert_type", "mode", unique=True),
        Index("ix_alerts_replay", "symbol", "alert_type", "severity", ts.desc()),
    )


class AlertCooldown(Base):
    __tablename__ = "alert_cooldowns"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_score: Mapped[Decimal] = mapped_column(DECIMAL, nullable=False)
    count_1h: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
