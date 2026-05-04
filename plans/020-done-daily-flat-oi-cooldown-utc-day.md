# Daily Flat OI Cooldown And UTC Day Return

Status: done

## Goal

Reduce repeated Discord delivery for `daily_flat_oi_buildup` and align daily return calculation with UTC calendar day boundaries.

Success criteria:

- `daily_flat_oi_buildup` Discord delivery has a dedicated 24 hour cooldown by default.
- `daily_flat_oi_buildup` Discord delivery is only allowed during UTC hour `0`.
- Cooldown suppresses Discord delivery only; alert generation and database inserts remain available for shadow/projection review.
- Around UTC hour `0`, `return_24h` uses the completed UTC day window: previous `00:00 UTC` to current `00:00 UTC` when both boundary samples are available.
- Outside that boundary window, `return_24h` may fall back to UTC day-to-date for shadow/projection, but Discord delivery remains suppressed.
- `oi_change_24h` uses the same UTC boundary logic for 5m OI.
- Documentation and `.env.example` describe `DAILY_FLAT_OI_COOLDOWN_MINUTES`.
- Tests cover cooldown suppression and UTC day boundary return.

## Changes

- Add `DAILY_FLAT_OI_COOLDOWN_MINUTES`, default `1440`.
- Add a fixed UTC hour-0 Discord delivery window for `daily_flat_oi_buildup`.
- Use the existing `alert_cooldowns` table in the delivery path.
- Add repository helpers for reading and upserting cooldown rows.
- Change daily indicator producer fields from rolling fetch-window return/OI to UTC day-to-date return/OI.
- Add tests for both behaviors.

## Verification

- `python -m pytest tests -q`
