# Verification: The trip fact

Reconstructed from the repository for demonstration and context, like its [Requirement](../requirement/2026-08-29-the-trip-fact.md) and [Plan](../plans/2026-08-29-the-trip-fact.md). Every gate below was run on 2026-10-15 at `48ba80f` against a copy of the seeded Domain (January 2024).

## Verification

`verdict: verified` at `48ba80f`: every requirement and every Plan scope row has independent evidence.

## Coverage

| Item | Evidence | Result | At |
| --- | --- | --- | --- |
| `R-01` one row per distinct TLC trip | `assert_fct_trip_matches_conformed_rowcount`; row and key counts | test passes; `fct_trip` 3,021,175 rows, 3,021,175 distinct `trip_key`; conformed 2,964,624 yellow + 56,551 green | `48ba80f` |
| `R-02` fleet-specific fields and three fee states | `assert_enrichment_rejoin_matches_every_trip`; `accepted_values` on `airport_fee_status`; fee-state counts | test passes; present 2,824,462, missing 140,162, not_applicable 56,551 | `48ba80f` |
| `R-03` verdicts and billable flag, nothing deleted | row count equals conformed; null probe | no null `is_billable` or `trip_quality_key`; 2,985,029 billable, 36,146 not | `48ba80f` |
| `R-04` zone and vendor as of pickup date | `relationships` tests on zone and vendor keys; `assert_scd2_zone_intervals_do_not_overlap` | tests pass; 5 trips with pickup before any version keep null keys (ADR 0015) | `48ba80f` |
| `R-05` explicit fleet attribution | probe: `is_fleet_attributed` disagrees with driver, vehicle and shift presence | 0 rows; 147,434 attributed | `48ba80f` |
| `R-06` one definition of `trip_key` | search for the key expression; unit tests | only `transformation/macros/trip_keys.sql` writes it (the other two `md5(concat_ws(` are `trip_quality_key` and `dim_trip_quality`); unit tests PASS=3 | `48ba80f` |
| `trip_natural_key`, `int_trips_conformed` | Task 1 gate | exit 0, PASS=3 | `48ba80f` |
| `int_trips_enriched`, `int_trip_quality_flags` | Task 2 gate | exit 0, PASS=82 | `48ba80f` |
| `fct_trip` | Task 3 gate | exit 0, PASS=4 | `48ba80f` |

## Gate results

| Gate | Command | Exit | Outcome |
| --- | --- | --- | --- |
| Build and data tests, `fct_trip` and its parents | `dbt build --select +fct_trip --exclude test_type:unit --target dev` | 0 | pass (PASS=82) |
| Unit tests on the parents | `dbt test --select "test_type:unit,+fct_trip" --target dev` | 0 | pass (PASS=3) |
| Singular tests | `dbt test --select assert_fct_trip_matches_conformed_rowcount assert_enrichment_rejoin_matches_every_trip assert_scd2_zone_intervals_do_not_overlap assert_airport_fee_only_on_yellow --target dev` | 0 | pass (PASS=4) |
