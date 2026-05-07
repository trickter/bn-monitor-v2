from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from monitor.indicators import IndicatorContext
from monitor.app import (
    COOLDOWN_SUPPRESSED_REASON,
    DAILY_FLAT_OI_WINDOW_SUPPRESSED_REASON,
    apply_delivery_cooldown,
    deliver_pending_alert,
    generate_and_persist_alerts,
    record_delivery_cooldown,
)
from monitor.config import Settings
from monitor.discord import DiscordDeliveryError


class FakeSession:
    def __init__(self) -> None:
        self.executed = []

    def execute(self, statement) -> None:
        self.executed.append(statement)


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def snapshot(oi_change_24h: Decimal = Decimal("0.12")) -> IndicatorContext:
    return IndicatorContext(
        ts=datetime(2026, 5, 3, 1, 2, tzinfo=UTC),
        symbol="SOLUSDT",
        return_24h=Decimal("0.01"),
        oi_change_24h=oi_change_24h,
        baseline_ready=True,
        is_altcoin=True,
    )


def test_generate_and_persist_alerts_inserts_generated_alert(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\n")
    session = FakeSession()

    count = generate_and_persist_alerts(settings, session, [snapshot()])

    assert count == 1
    assert len(session.executed) == 1


def test_generate_and_persist_alerts_does_not_insert_when_no_rule_triggers(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\n")
    session = FakeSession()

    count = generate_and_persist_alerts(settings, session, [snapshot(oi_change_24h=Decimal("0.01"))])

    assert count == 0
    assert session.executed == []


def alert_values(ts: datetime) -> dict:
    return {
        "ts": ts,
        "symbol": "SOLUSDT",
        "alert_type": "daily_flat_oi_buildup",
        "severity": "WARNING",
        "direction": "none",
        "state": "open",
        "score": Decimal("72"),
        "title": "SOLUSDT daily flat OI buildup",
        "message": "SOLUSDT 24h return is 1.00% while OI changed 12.00%.",
        "payload": {"symbol": "SOLUSDT"},
        "mode": "live",
        "delivery_status": "pending",
    }


def test_daily_flat_oi_delivery_cooldown_suppresses_same_utc_date(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDAILY_FLAT_OI_COOLDOWN_MINUTES=1440\n")
    sent_at = datetime(2026, 5, 3, 0, 0, tzinfo=UTC)
    values = alert_values(sent_at + timedelta(minutes=30))
    monkeypatch.setattr("monitor.app.get_alert_cooldown", lambda session, key: SimpleNamespace(last_sent_at=sent_at))
    upserts = []
    monkeypatch.setattr("monitor.app.upsert_alert_cooldown", lambda session, row: upserts.append(row))

    apply_delivery_cooldown(settings, FakeSession(), values)

    assert values["delivery_status"] == "suppressed"
    assert values["payload"]["suppressed_reason"] == COOLDOWN_SUPPRESSED_REASON
    assert values["payload"]["cooldown_utc_date"] == "2026-05-03"
    assert upserts == []


def test_daily_flat_oi_delivery_cooldown_records_when_not_active(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDAILY_FLAT_OI_COOLDOWN_MINUTES=1440\n")
    values = alert_values(datetime(2026, 5, 3, 0, 10, tzinfo=UTC))
    monkeypatch.setattr("monitor.app.get_alert_cooldown", lambda session, key: None)
    upserts = []
    monkeypatch.setattr("monitor.app.upsert_alert_cooldown", lambda session, row: upserts.append(row))

    apply_delivery_cooldown(settings, FakeSession(), values)

    assert values["delivery_status"] == "pending"
    assert upserts == []

    record_delivery_cooldown(FakeSession(), values)

    assert upserts == [
        {
            "key": "live:SOLUSDT:daily_flat_oi_buildup:discord",
            "last_sent_at": values["ts"],
            "last_score": Decimal("72"),
            "count_1h": 1,
            "updated_at": values["ts"],
        }
    ]


def test_daily_flat_oi_delivery_does_not_drift_after_late_previous_day_send(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDAILY_FLAT_OI_COOLDOWN_MINUTES=1440\n")
    values = alert_values(datetime(2026, 5, 4, 0, 0, tzinfo=UTC))
    monkeypatch.setattr(
        "monitor.app.get_alert_cooldown",
        lambda session, key: SimpleNamespace(last_sent_at=datetime(2026, 5, 3, 0, 55, tzinfo=UTC)),
    )
    upserts = []
    monkeypatch.setattr("monitor.app.upsert_alert_cooldown", lambda session, row: upserts.append(row))

    apply_delivery_cooldown(settings, FakeSession(), values)

    assert values["delivery_status"] == "pending"
    assert upserts == []

    record_delivery_cooldown(FakeSession(), values)

    assert upserts[0]["last_sent_at"] == datetime(2026, 5, 4, 0, 0, tzinfo=UTC)


def test_daily_flat_oi_delivery_is_suppressed_outside_utc_zero_hour(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\n")
    values = alert_values(datetime(2026, 5, 3, 1, 0, tzinfo=UTC))
    monkeypatch.setattr("monitor.app.get_alert_cooldown", lambda session, key: None)
    upserts = []
    monkeypatch.setattr("monitor.app.upsert_alert_cooldown", lambda session, row: upserts.append(row))

    apply_delivery_cooldown(settings, FakeSession(), values)

    assert values["delivery_status"] == "suppressed"
    assert values["payload"]["suppressed_reason"] == DAILY_FLAT_OI_WINDOW_SUPPRESSED_REASON
    assert values["payload"]["delivery_utc_hour"] == 0
    assert upserts == []


def test_deliver_pending_alert_marks_sent_and_records_cooldown(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDISCORD_WEBHOOK_URL=https://discord.example/webhook\n")
    values = alert_values(datetime(2026, 5, 3, 0, 10, tzinfo=UTC))
    sent = []
    upserts = []
    updates = []
    monkeypatch.setattr("monitor.app.send_discord_message", lambda settings_arg, content: sent.append(content))
    monkeypatch.setattr("monitor.app.upsert_alert_cooldown", lambda session, row: upserts.append(row))
    monkeypatch.setattr("monitor.app.update_alert_delivery", lambda session, row: updates.append(row.copy()))

    deliver_pending_alert(settings, FakeSession(), values)

    assert sent
    assert values["delivery_status"] == "sent"
    assert values["discord_sent_at"].tzinfo == UTC
    assert upserts[0]["key"] == "live:SOLUSDT:daily_flat_oi_buildup:discord"
    assert updates[0]["delivery_status"] == "sent"


def test_deliver_pending_alert_marks_rate_limited_without_raising(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDISCORD_WEBHOOK_URL=https://discord.example/webhook\n")
    values = alert_values(datetime(2026, 5, 3, 0, 10, tzinfo=UTC))
    updates = []

    def raise_rate_limited(settings_arg, content):
        raise DiscordDeliveryError("Discord rate limited request", status_code=429)

    monkeypatch.setattr("monitor.app.send_discord_message", raise_rate_limited)
    monkeypatch.setattr("monitor.app.update_alert_delivery", lambda session, row: updates.append(row.copy()))

    deliver_pending_alert(settings, FakeSession(), values)

    assert values["delivery_status"] == "rate_limited"
    assert values["payload"]["delivery_error"] == "Discord rate limited request"
    assert updates[0]["delivery_status"] == "rate_limited"


def test_deliver_pending_alert_marks_failed_without_raising(monkeypatch, tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDISCORD_WEBHOOK_URL=https://discord.example/webhook\n")
    values = alert_values(datetime(2026, 5, 3, 0, 10, tzinfo=UTC))
    updates = []

    def raise_failed(settings_arg, content):
        raise DiscordDeliveryError("Discord webhook failed", status_code=500)

    monkeypatch.setattr("monitor.app.send_discord_message", raise_failed)
    monkeypatch.setattr("monitor.app.update_alert_delivery", lambda session, row: updates.append(row.copy()))

    deliver_pending_alert(settings, FakeSession(), values)

    assert values["delivery_status"] == "failed"
    assert values["payload"]["delivery_error"] == "Discord webhook failed"
    assert updates[0]["delivery_status"] == "failed"
