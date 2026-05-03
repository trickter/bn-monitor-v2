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


def test_unknown_discord_allowlist_type_fails_startup(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "DISCORD_ALERT_TYPE_ALLOWLIST=daily_flat_oi_buildup,unknown_type\n")

    with pytest.raises(ValidationError, match="unknown alert_type"):
        settings_from_env(env_file)


def test_config_dump_masks_discord_webhook(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/example\n")

    settings = settings_from_env(env_file)

    assert settings.masked_dump()["discord_webhook_url"] == "***"

