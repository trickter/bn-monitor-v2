from __future__ import annotations

from dataclasses import dataclass

from monitor.config import AlertMode, Settings, Severity, SEVERITY_RANK


@dataclass(frozen=True)
class DeliveryDecision:
    should_send: bool
    delivery_status: str
    suppressed_reason: str | None = None


def evaluate_discord_delivery(settings: Settings, alert_type: str, severity: Severity | str) -> DeliveryDecision:
    severity_value = Severity(severity)

    if settings.alert_mode == AlertMode.SHADOW:
        return DeliveryDecision(False, "suppressed", "alert_mode_shadow")

    if SEVERITY_RANK[severity_value] < SEVERITY_RANK[settings.discord_min_severity]:
        return DeliveryDecision(False, "suppressed", "severity_below_minimum")

    allowlist = settings.discord_alert_type_allowlist
    if allowlist and alert_type not in allowlist:
        return DeliveryDecision(False, "suppressed", "discord_alert_type_not_allowed")

    return DeliveryDecision(True, "pending")

