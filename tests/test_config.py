from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from monitor.config import AlertMode, Settings, Severity, UniverseMode


def write_env(tmp_path: Path, content: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def settings_from_env(env_file: Path) -> Settings:
    return Settings(_env_file=env_file)


def test_default_settings_load_without_env_file(tmp_path: Path) -> None:
    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.alert_mode == AlertMode.SHADOW
    assert settings.discord_min_severity == Severity.WARNING
    assert settings.universe_mode == UniverseMode.TOP_USDT
    assert settings.discord_alert_type_allowlist == ()
    assert settings.monitor_poll_interval_seconds == 300
    assert settings.daily_flat_oi_cooldown_minutes == 1440


def test_unknown_env_key_fails_startup(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "ALERT_MODE=shadow\nTYPO_ALERT_MODE=live\n")

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        settings_from_env(env_file)


def test_invalid_enum_fails_startup(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "ALERT_MODE=paper\n")

    with pytest.raises(ValidationError):
        settings_from_env(env_file)


def test_explicit_universe_requires_symbols(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "UNIVERSE_MODE=explicit\nSYMBOLS=\n")

    with pytest.raises(ValidationError, match="SYMBOLS must be set"):
        settings_from_env(env_file)


def test_symbols_are_normalized_and_deduplicated(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "UNIVERSE_MODE=explicit\nSYMBOLS=solusdt, BNBUSDT, solusdt\n")

    settings = settings_from_env(env_file)

    assert settings.symbols == ("SOLUSDT", "BNBUSDT")


def test_monitor_poll_interval_must_be_positive(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "MONITOR_POLL_INTERVAL_SECONDS=0\n")

    with pytest.raises(ValidationError):
        settings_from_env(env_file)


def test_daily_flat_oi_cooldown_must_be_positive(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "DAILY_FLAT_OI_COOLDOWN_MINUTES=0\n")

    with pytest.raises(ValidationError):
        settings_from_env(env_file)


def test_unknown_discord_allowlist_type_fails_startup(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "DISCORD_ALERT_TYPE_ALLOWLIST=daily_flat_oi_buildup,unknown_type\n")

    with pytest.raises(ValidationError, match="unknown alert_type"):
        settings_from_env(env_file)


def test_config_dump_masks_discord_webhook(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/example\n")

    settings = settings_from_env(env_file)

    assert settings.masked_dump()["discord_webhook_url"] == "***"


def test_rule_thresholds_default_is_empty(tmp_path: Path) -> None:
    settings = Settings(_env_file=tmp_path / "missing.env")

    assert settings.rule_thresholds == {}


def test_rule_thresholds_parses_valid_json(tmp_path: Path) -> None:
    from decimal import Decimal

    env_file = write_env(tmp_path, 'RULE_THRESHOLDS={"flat_oi_buildup_15m": {"return_limit": "0.01"}}\n')
    settings = settings_from_env(env_file)

    assert settings.rule_thresholds == {"flat_oi_buildup_15m": {"return_limit": Decimal("0.01")}}


def test_rule_thresholds_rejects_unknown_alert_type(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, 'RULE_THRESHOLDS={"unknown_rule": {"return_limit": "0.01"}}\n')

    with pytest.raises(ValidationError, match="unknown alert_type in RULE_THRESHOLDS"):
        settings_from_env(env_file)


def test_rule_thresholds_rejects_unknown_key(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, 'RULE_THRESHOLDS={"flat_oi_buildup_15m": {"bad_key": "0.05"}}\n')

    with pytest.raises(ValidationError, match="unknown key in RULE_THRESHOLDS"):
        settings_from_env(env_file)


def test_rule_thresholds_rejects_invalid_json(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "RULE_THRESHOLDS=not-json\n")

    with pytest.raises(ValidationError, match="not valid JSON"):
        settings_from_env(env_file)


def test_rule_thresholds_rejects_non_decimal_value(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, 'RULE_THRESHOLDS={"flat_oi_buildup_15m": {"return_limit": "abc"}}\n')

    with pytest.raises(ValidationError, match="cannot be converted to Decimal"):
        settings_from_env(env_file)
