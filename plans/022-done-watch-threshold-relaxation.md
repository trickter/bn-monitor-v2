# Watch Threshold Relaxation

Status: done

## Goal

Make `breakout_watch` and `breakdown_watch` easier to trigger during shadow/live observation.

Success criteria:

- `breakout_watch.near_high_bps` default changes from `80` to `250`.
- `breakdown_watch.low_distance_bps` default changes from `80` to `250`.
- `breakout_watch.volume_z_min` default changes from `2.5` to `2`.
- `breakdown_watch.volume_z_min` default changes from `2.5` to `2`.
- Docs, `.env.example`, and tests match the code defaults.

## Verification

- `python -m pytest tests -q`
