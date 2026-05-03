from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from monitor.alerts.engine import AlertEngine
from monitor.indicators import IndicatorContext
from monitor.binance.rest import BinanceRestClient
from monitor.config import Settings
from monitor.discord import format_alert_message, send_discord_message
from monitor.repository import insert_alert_once, upsert_kline_1m, upsert_open_interest
from monitor.reports import summarize_alert_projection


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


def run_live_smoke(
    settings: Settings,
    session: Session,
    symbols: Iterable[str],
    binance_client: BinanceRestClient | None = None,
    send_discord: bool = True,
) -> dict:
    client = binance_client or BinanceRestClient(settings)
    snapshots = []
    for symbol in symbols:
        market_data = client.fetch_symbol_market_data(symbol)
        snapshots.append(market_data.indicator)
        for kline in market_data.klines:
            upsert_kline_1m(session, kline)
        for open_interest in market_data.open_interest:
            upsert_open_interest(session, open_interest)

    engine = AlertEngine(settings)
    alert_values = engine.evaluate(snapshots)
    for values in alert_values:
        insert_alert_once(session, values)
        if send_discord and values["delivery_status"] == "pending":
            send_discord_message(settings, format_alert_message(values))

    return {
        "symbols": [symbol.upper() for symbol in symbols],
        "alerts": alert_values,
        "summary": summarize_alert_projection(alert_values),
    }
