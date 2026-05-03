from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from monitor.config import Settings
from monitor.discord import DiscordDeliveryError, format_alert_message, send_discord_message


def settings_from_text(tmp_path: Path, text: str) -> Settings:
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    return Settings(_env_file=env_file)


def test_send_discord_message_posts_content(tmp_path: Path) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(204)

    settings = settings_from_text(tmp_path, "DISCORD_WEBHOOK_URL=https://discord.example/webhook\n")
    client = httpx.Client(transport=httpx.MockTransport(handler))

    send_discord_message(settings, "hello", client=client)

    assert len(requests) == 1
    assert requests[0].url == "https://discord.example/webhook"
    assert requests[0].read() == b'{"content":"hello"}'


def test_send_discord_message_requires_webhook(tmp_path: Path) -> None:
    settings = settings_from_text(tmp_path, "DISCORD_WEBHOOK_URL=\n")

    with pytest.raises(DiscordDeliveryError, match="not configured"):
        send_discord_message(settings, "hello")


def test_format_alert_message_contains_key_fields() -> None:
    message = format_alert_message(
        {
            "severity": "WARNING",
            "alert_type": "daily_flat_oi_buildup",
            "symbol": "SOLUSDT",
            "title": "title",
            "message": "body",
        }
    )

    assert "[WARNING] daily_flat_oi_buildup SOLUSDT" in message
    assert "title" in message
    assert "body" in message

