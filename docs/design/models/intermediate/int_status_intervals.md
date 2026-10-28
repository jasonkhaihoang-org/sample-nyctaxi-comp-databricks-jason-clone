---
artifacts: [int_status_intervals]
---

# int_status_intervals

The durable time basis for occupancy, vehicle utilisation and locatable idle time.

## Grain

One row per driver status event, read as the interval from that event until the next event on the same shift.

## Decisions

- `D-01` Order within each shift by `event_ts`, with `event_id` as the deterministic tie-breaker. `received_ts` is arrival metadata and can invert the business event order. Source: docs/requirement/2026-08-29-driver-status-occupancy-and-utilisation.md R-01.
- `D-02` Close a terminal event at the shift's effective end. Leaving it open drops real time; using an arbitrary wall-clock boundary fabricates it. Source: docs/requirement/2026-08-29-driver-status-occupancy-and-utilisation.md R-02.
- `D-03` Floor a negative duration at zero but retain `is_negative_interval`. Rejecting the record would hide feed disorder, while retaining a negative measure would invalidate every rollup. Source: docs/requirement/2026-08-29-driver-status-occupancy-and-utilisation.md R-03.

## Rejected

- Ordering on `received_ts`: a skewed arrival time produces negative durations.
- Leaving the last event of a shift open.

## Consumers

Depended on by: `agg_driver_daily`, `agg_driver_monthly`, `agg_garage_monthly`, `agg_vehicle_daily`, `agg_vehicle_monthly`, `agg_zone_occupancy_hourly`, `fct_shift`, `fct_status_interval`, `int_shift_economics`, `int_shift_occupancy`, `mart_driver_scorecard`, `mart_vehicle_utilisation`.

## History

- 2026-08-29 — status-occupancy — design record written (commit 97862f7) — D-01, D-02, D-03
- 2026-10-14 — setup-dlt-ingestion — record conformed to the template; evidence refreshed for the dlt-loaded sources
