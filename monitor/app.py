from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, timedelta

from sqlalchemy.orm import Session

from monitor.alerts.engine import AlertEngine
from monitor.indicators import IndicatorContext
from monitor.binance.rest import BinanceRestClient, build_indicator_contexts
from monitor.config import Settings
from monitor.discord import format_alert_message, send_discord_message
from monitor.repository import get_alert_cooldown, insert_alert_once, upsert_alert_cooldown, upsert_kline_1m, upsert_open_interest
from monitor.reports import summarize_alert_projection


COOLDOWN_SUPPRESSED_REASON = "alert_cooldown_active"
DAILY_FLAT_OI_WINDOW_SUPPRESSED_REASON = "daily_flat_oi_delivery_window"
DAILY_FLAT_OI_DELIVERY_UTC_HOUR = 0


def generate_and_persist_alerts(
    settings: Settings,
    session: Session,
    snapshots: Iterable[IndicatorContext],
) -> int:
    engine = AlertEngine(settings)
    alert_values = engine.evaluate(snapshots)
    for values in alert_values:
        insert_alert_once(session, values)
    return len(alert_values)


def _delivery_cooldown_minutes(settings: Settings, alert_type: str) -> int | None:
    if alert_type == "daily_flat_oi_buildup":
        return settings.daily_flat_oi_cooldown_minutes
    return None


def _delivery_cooldown_key(values: dict) -> str:
    return f"{values['mode']}:{values['symbol']}:{values['alert_type']}:discord"


def _inside_delivery_window(values: dict) -> bool:
    if values["alert_type"] != "daily_flat_oi_buildup":
        return True
    return values["ts"].astimezone(UTC).hour == DAILY_FLAT_OI_DELIVERY_UTC_HOUR


def apply_delivery_cooldown(settings: Settings, session: Session, values: dict) -> None:
    if values["delivery_status"] != "pending":
        return
    if not _inside_delivery_window(values):
        values["delivery_status"] = "suppressed"
        values["payload"]["suppressed_reason"] = DAILY_FLAT_OI_WINDOW_SUPPRESSED_REASON
        values["payload"]["delivery_utc_hour"] = DAILY_FLAT_OI_DELIVERY_UTC_HOUR
        return
    cooldown_minutes = _delivery_cooldown_minutes(settings, values["alert_type"])
    if cooldown_minutes is None:
        return

    key = _delivery_cooldown_key(values)
    cooldown = get_alert_cooldown(session, key)
    cooldown_until = None if cooldown is None else cooldown.last_sent_at + timedelta(minutes=cooldown_minutes)
    if cooldown_until is not None and values["ts"] < cooldown_until:
        values["delivery_status"] = "suppressed"
        values["payload"]["suppressed_reason"] = COOLDOWN_SUPPRESSED_REASON
        values["payload"]["cooldown_until"] = cooldown_until.isoformat()
        return

    upsert_alert_cooldown(
        session,
        {
            "key": key,
            "last_sent_at": values["ts"],
            "last_score": values["score"],
            "count_1h": 1,
            "updated_at": values["ts"],
        },
    )


def run_live_smoke(
    settings: Settings,
    session: Session,
    symbols: Iterable[str],
    binance_client: BinanceRestClient | None = None,
    send_discord: bool = True,
) -> dict:
    client = binance_client or BinanceRestClient(settings)
    symbol_data = {}
    for symbol in symbols:
        market_data = client.fetch_symbol_market_data(symbol)
        symbol_data[symbol.upper()] = market_data
        for kline in market_data.klines:
            upsert_kline_1m(session, kline)
        for open_interest in market_data.open_interest:
            upsert_open_interest(session, open_interest)

    snapshots = list(build_indicator_contexts(symbol_data).values())
    engine = AlertEngine(settings)
    alert_values = engine.evaluate(snapshots)
    for values in alert_values:
        if send_discord:
            apply_delivery_cooldown(settings, session, values)
        insert_alert_once(session, values)
        if send_discord and values["delivery_status"] == "pending":
            send_discord_message(settings, format_alert_message(values))

    return {
        "symbols": [symbol.upper() for symbol in symbols],
        "alerts": alert_values,
        "summary": summarize_alert_projection(alert_values),
    }
