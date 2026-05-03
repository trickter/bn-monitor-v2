from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from monitor.alerts.rules import IndicatorContext
from monitor.app import generate_and_persist_alerts
from monitor.config import Settings


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

