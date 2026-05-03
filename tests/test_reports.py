from __future__ import annotations

from monitor.reports import summarize_alert_projection


def test_summarize_alert_projection_empty() -> None:
    assert summarize_alert_projection([]) == {
        "total": 0,
        "by_type": {},
        "by_severity": {},
    }


def test_summarize_alert_projection_counts_type_and_severity() -> None:
    summary = summarize_alert_projection(
        [
            {"alert_type": "daily_flat_oi_buildup", "severity": "WARNING"},
            {"alert_type": "daily_flat_oi_buildup", "severity": "WARNING"},
            {"alert_type": "short_squeeze_risk", "severity": "CRITICAL"},
        ]
    )

    assert summary == {
        "total": 3,
        "by_type": {
            "daily_flat_oi_buildup": 2,
            "short_squeeze_risk": 1,
        },
        "by_severity": {
            "CRITICAL": 1,
            "WARNING": 2,
        },
    }

