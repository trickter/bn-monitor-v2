from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from monitor.alerts.delivery import evaluate_discord_delivery
from monitor.alerts.rules import AlertDecision, IndicatorContext, evaluate_daily_flat_oi_buildup
from monitor.config import Settings


def alert_decision_to_values(settings: Settings, decision: AlertDecision) -> dict[str, Any]:
    delivery = evaluate_discord_delivery(settings, decision.alert_type, decision.severity)
    payload = deepcopy(decision.payload)
    if delivery.suppressed_reason is not None:
        payload["suppressed_reason"] = delivery.suppressed_reason

    return {
        "ts": decision.ts,
        "symbol": decision.symbol,
        "alert_type": decision.alert_type,
        "severity": decision.severity,
        "direction": decision.direction,
        "state": "open",
        "score": decision.score,
        "title": decision.title,
        "message": decision.message,
        "payload": payload,
        "mode": settings.alert_mode.value,
        "delivery_status": delivery.delivery_status,
    }


class AlertEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, snapshots: Iterable[IndicatorContext]) -> list[dict[str, Any]]:
        alert_values = []
        for snapshot in snapshots:
            decision = evaluate_daily_flat_oi_buildup(snapshot)
            if decision is None:
                continue
            alert_values.append(alert_decision_to_values(self.settings, decision))
        return alert_values

