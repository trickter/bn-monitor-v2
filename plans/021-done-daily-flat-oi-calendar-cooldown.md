# Daily Flat OI Calendar Cooldown

Status: done

## Goal

Fix daily flat OI delivery drift caused by combining a relative 24h cooldown with an absolute UTC hour-0 delivery window.

Success criteria:

- `daily_flat_oi_buildup` Discord delivery is eligible only during UTC hour `0`.
- Within that window, each `(mode, symbol, alert_type)` can deliver at most once per UTC calendar date.
- The decision does not depend on `last_sent_at + 24h`, so first delivery at `00:55` does not force the next day to wait until `00:55`.
- Alert generation and database inserts remain unaffected.
- Tests cover same-day suppression and next-day `00:00` eligibility after a previous-day `00:55` send.

## Changes

- Replace relative 24h cooldown logic for `daily_flat_oi_buildup` with UTC calendar-date dedupe.
- Keep `DAILY_FLAT_OI_COOLDOWN_MINUTES=1440` as documentation of the intended once-per-day cadence, but do not use relative-minute arithmetic for this rule.
- Update docs to call out calendar-day semantics.

## Verification

- `python -m pytest tests -q`
