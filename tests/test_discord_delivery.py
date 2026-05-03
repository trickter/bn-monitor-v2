from __future__ import annotations

from pathlib import Path

from monitor.alerts.delivery import evaluate_discord_delivery
from monitor.config import Settings


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def test_live_warning_without_allowlist_is_pending(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\n")

    decision = evaluate_discord_delivery(settings, "daily_flat_oi_buildup", "WARNING")

    assert decision.should_send is True
    assert decision.delivery_status == "pending"
    assert decision.suppressed_reason is None


def test_live_allowlist_hit_is_pending(tmp_path: Path) -> None:
    settings = settings_from_text(
        tmp_path,
        "ALERT_MODE=live\nDISCORD_ALERT_TYPE_ALLOWLIST=daily_flat_oi_buildup,breakout_watch\n",
    )

    decision = evaluate_discord_delivery(settings, "breakout_watch", "WARNING")

    assert decision.should_send is True
    assert decision.delivery_status == "pending"


def test_live_allowlist_miss_is_suppressed(tmp_path: Path) -> None:
    settings = settings_from_text(
        tmp_path,
        "ALERT_MODE=live\nDISCORD_ALERT_TYPE_ALLOWLIST=daily_flat_oi_buildup\n",
    )

    decision = evaluate_discord_delivery(settings, "breakout_watch", "WARNING")

    assert decision.should_send is False
    assert decision.delivery_status == "suppressed"
    assert decision.suppressed_reason == "discord_alert_type_not_allowed"


def test_severity_below_minimum_is_suppressed(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=live\nDISCORD_MIN_SEVERITY=WARNING\n")

    decision = evaluate_discord_delivery(settings, "price_probe", "INFO")

    assert decision.should_send is False
    assert decision.delivery_status == "suppressed"
    assert decision.suppressed_reason == "severity_below_minimum"


def test_shadow_mode_is_suppressed(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "ALERT_MODE=shadow\n")

    decision = evaluate_discord_delivery(settings, "daily_flat_oi_buildup", "CRITICAL")

    assert decision.should_send is False
    assert decision.delivery_status == "suppressed"
    assert decision.suppressed_reason == "alert_mode_shadow"

