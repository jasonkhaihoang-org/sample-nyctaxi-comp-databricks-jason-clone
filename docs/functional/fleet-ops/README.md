# Fleet ops — dispatch/telematics feed

Harbour Point Taxi Management's dispatch and telematics platform as a source
system (`ops_raw`), executed by
`src/dlt/fleet_ops.Notebook/notebook-content.py` (fixed `_loaded_at`
`2024-07-02 04:10:00`, `_source_file = build_fleet_ops.py`; stamps on every
write). Chain order: garage → vehicle → driver → lease → shift → trip
assignment → status events → maintenance. Deterministic — every pseudo-random
choice is `hb()` of a key, no RNG. The timing skeleton is derived from real
`silver_trips` timestamps (shifts built from gaps between actual trips, status
stream brackets real pickups/dropoffs), so shift lengths and sequencing behave
plausibly while every identity is fiction.

## Counts

| Table | Rows | Grain |
| --- | --- | --- |
| `ops_raw_garage` | 6 | Garage |
| `ops_raw_vehicle` | 420 | Medallion |
| `ops_raw_driver` | 760 | Hack licence |
| `ops_raw_lease_agreement` | 760 | One row per driver |
| `ops_raw_shift` | ~73k | Driver sign-on |
| `ops_raw_trip_assignment` | ~978k | Trip-to-shift attribution |
| `ops_raw_driver_status_event` | ~3.8M | LOGIN → AVAILABLE → DISPATCHED → ON_TRIP → … → LOGOUT per shift, BREAK on >25min fare gaps |
| `ops_raw_maintenance_event` | 848 | Work order |

## Four imperfections (kept, flagged downstream — never cleaned here)

1. **Missing LOGOUTs.** ~3-in-200 shifts keep a null `shift_end_ts` (tablet died
   mid-shift). Downstream `stg_ops__shifts` flags `is_unclosed_shift` and
   substitutes `derived_end_ts` via `effective_end_ts`.
2. **Out-of-order status events.** ~1-in-333 events carry `received_ts` skewed
   +2min past `event_ts`. Downstream `stg_ops__status_events` exposes
   `skew_seconds`; `int_status_intervals` flags `is_negative_interval`,
   guarded by `assert_no_negative_status_intervals`.
3. **"Mis-windowed assignments" — does not occur.** The builder's docstring
   bullet claims some trips land in shifts whose window does not contain them,
   but the attribution join requires containment
   (`shift_start_ts <= pickup`, `coalesce(shift_end_ts, derived_end_ts) >=
   dropoff`, gap-built windows per vehicle — exactly one row per trip). Windows
   contain their trips; the reconciliation invariant is intact and guarded by
   `assert_shift_time_budget_reconciles` over `int_shift_occupancy`. The
   ~1-in-500 `manual` `assignment_method` is labeling only, not mis-attribution.
4. **Missing odometers.** ~1-in-50 shifts carry null `odometer_end`.
   Downstream `odometer_miles` goes null and `fct_shift`'s nullif-guarded
   `paid_mile_ratio` stays null instead of dividing.

## Provenance

Tier 4 (fully synthetic): Harbour Point does not exist — no garage, medallion,
VIN, driver, lease, or maintenance record has a real counterpart, and TLC trips
carry no driver or vehicle identity at all. Real: the timing skeleton (actual
trip timestamps) and the `trip_assignment.trip_key` pointers into real trips.
Consequence: every dollar here is real, every person is not — driver rankings
and weather-to-demand correlations test the mechanism, not New York.
