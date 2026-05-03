from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def summarize_alert_projection(alerts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    by_type: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    total = 0

    for alert in alerts:
        total += 1
        by_type[str(alert["alert_type"])] += 1
        by_severity[str(alert["severity"])] += 1

    return {
        "total": total,
        "by_type": dict(sorted(by_type.items())),
        "by_severity": dict(sorted(by_severity.items())),
    }

