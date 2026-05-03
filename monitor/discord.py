from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from monitor.config import Settings


class DiscordDeliveryError(RuntimeError):
    pass


def send_discord_message(settings: Settings, content: str, client: httpx.Client | None = None) -> None:
    if not settings.discord_webhook_url:
        raise DiscordDeliveryError("DISCORD_WEBHOOK_URL is not configured")

    resolved_client = client or httpx.Client(timeout=20)
    response = resolved_client.post(settings.discord_webhook_url, json={"content": content})
    if response.status_code == 429:
        raise DiscordDeliveryError(f"Discord rate limited request: {response.text}")
    if response.status_code >= 400:
        raise DiscordDeliveryError(f"Discord webhook failed with status {response.status_code}: {response.text}")


def format_alert_message(alert: Mapping[str, Any]) -> str:
    return (
        f"[{alert['severity']}] {alert['alert_type']} {alert['symbol']}\n"
        f"{alert['title']}\n"
        f"{alert['message']}"
    )

