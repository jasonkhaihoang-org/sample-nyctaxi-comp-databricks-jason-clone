---
kinds: [transformation]
---

# Requirement: Driver status, occupancy and utilisation

Reconstructed from the repository for demonstration and context. The requirement was not captured when the models were first built; each line below is traceable to a model, test or design record in this repo.

## Ask

Turn the fleet operator's driver status events into a time basis that supports occupancy per shift, driver performance and vehicle utilisation, without letting a clock skew or an unclosed shift corrupt the numbers.

## Requirements

- [x] `R-01` Driver status events become intervals ordered by event time — accept when the unit test `status_intervals_order_ties_by_event_id` passes — source: `docs/design/models/intermediate/int_status_intervals.md`
- [x] `R-02` The last event of a shift is closed at the shift's effective end — accept when the unit test `status_intervals_close_the_terminal_event_at_the_shift_end` passes — source: `docs/design/models/intermediate/int_status_intervals.md`
- [x] `R-03` A negative duration is floored at zero and flagged, not rejected — accept when the unit test `status_intervals_floor_a_negative_duration_and_flag_it` passes and `assert_no_negative_status_intervals` returns no rows — source: `docs/design/models/intermediate/int_status_intervals.md`
- [x] `R-04` Occupancy per shift is on-trip time over online time, and every higher-level rate is a ratio of sums — accept when `assert_shift_time_budget_reconciles` returns no rows and the aggregates carry numerators and denominators — source: `docs/adr/0016-rates-are-rebuilt-from-summed-numerators-and-denominators.md`
- [x] `R-05` Drivers are ranked on revenue per online hour, and asset utilisation is taken against the 24-hour day — accept when `mart_driver_scorecard` ranks on `revenue_per_online_hour` and `agg_vehicle_daily` carries `asset_utilisation_rate` — source: `docs/adr/0010-driver-ranking-and-utilisation-definitions.md`

## Business decisions

| Decision | Value | Source |
| --- | --- | --- |
| Ordering of events | Event time, with the event id as tie-breaker, never arrival time | `docs/design/models/intermediate/int_status_intervals.md` |
| Driver ranking basis | Revenue per online hour | `docs/adr/0010-driver-ranking-and-utilisation-definitions.md` |
| Asset utilisation denominator | The 24-hour day | `docs/adr/0010-driver-ranking-and-utilisation-definitions.md` |

## Out of scope

- The trip fact (see `docs/requirement/2026-08-29-the-trip-fact.md`).
- Maintenance scheduling.

## Open questions

None.

## Approvals

- 2026-08-29 — requirement approved — reconstructed from the repository; no recorded answer exists — 97862f7
