# Case: Every yellow trip reports a missing airport fee

**Anchor:** `int_trips_enriched.airport_fee_status`, surfaced in `fct_trip`.
**Symptom:** every yellow trip reads `airport_fee_status = 'missing'`; the build and every test stay green.
**Window:** the three-month load built on 2026-10-14, before commit `18b2e55`.
**Category:** `data-quality`.

## RCA

**Blast radius.** `fct_trip.airport_fee_status` and `airport_fee`, and through them `mart_revenue_component_bridge` (`c_airport_fee`) and `mart_trip_quality_scorecard` (`is_missing_airport_fee`). Every yellow trip, 9,554,777 of 9,722,362 on the three-month load, reads `missing`, and airport-fee revenue reads zero. The green extras had the same defect: `ehail_fee` and `trip_type` were null on every green trip, hidden because green's fee status is `not_applicable` by fleet, not by the join.

**Root cause.**

1. `int_trips_enriched` left-joins `stg_tlc__yellow_trip_extras` on `trip_key` and labels a trip `missing` when no extras row joins. [`code-inspection`: `transformation/models/intermediate/int_trips_enriched.sql`]
2. Both sides compute `trip_key` with the `trip_natural_key` macro, but from different inputs: `int_trips_conformed` reads the staging views, which convert pickup and dropoff with `timezone('UTC', col)`, while the extras model read `source('bronze', 'yellow_tripdata')` without the conversion. [`code-inspection`: `stg_tlc__yellow_tripdata.sql`, `stg_tlc__yellow_trip_extras.sql` at `18b2e55^`]
3. dlt lands the TLC timestamps as `TIMESTAMP WITH TIME ZONE`. Cast to text inside `concat_ws`, the bronze value carries a zone offset in the session time zone (Asia/Singapore) and the converted value does not, so the two md5 inputs differ for every trip. [`schema-diff`: `describe bronze.yellow_tripdata` → `tpep_pickup_datetime TIMESTAMP WITH TIME ZONE`]
4. No yellow trip finds its extras row. [`sql-probe`: `select airport_fee_status, count(*) from core.fct_trip where service_type_key = 'yellow' group by 1` → only `missing`]
5. Nothing failed because a left join reports a miss as a null, and no test asserted that the rejoin finds its row. [`code-inspection`: `transformation/tests/` at `18b2e55^`]

**Confidence.** High. The probe in step 4 and the schema in step 3 are direct; after the fix the same probe shows `present` and `missing` in proportion to the source. Not checked: whether any consumer outside this repo read the fee before the fix (none is known).

**Checks run.**

| Check | Outcome |
| --- | --- |
| Fee-status probe before the fix | yellow only `missing`: confirms |
| Same probe with the extras keyed from the converted timestamps | present and missing both appear: confirms |
| Green extras at `18b2e55^` | also read `source('bronze', 'green_tripdata')` without the conversion: same defect, wider blast radius |

## Decision

`code-change`. Class: failing or missing dbt test. Sandbox verification: re-run the affected models and tests.

- Key the extras from the same converted timestamps as the conformed trips before calling `trip_natural_key`.
- Add `assert_enrichment_rejoin_matches_every_trip`, failing first, returning every conformed trip whose fleet's extras row does not join.

Data-loss check: the fix adds no deduplication or filter. ADR check: consistent with ADR 0007 (one key definition); it adds the input rule recorded in [`docs/design/trips/trip-identity.md`](../design/trips/trip-identity.md) `D-02`.

## Outcome

Fixed in `18b2e55` ("fleet-specific extras read staging so the trip key matches"), with the new singular test. `2f58ba5` later moved the extras back to `source()` under the staging-reads-only-`source()` rule, applying the same `timezone('UTC', col)` conversion inline. After the fix, on the three-month load: `airport_fee_status` present 8,802,815, missing 751,962, not_applicable 167,585, and the rejoin test returns no rows. The input rule became `.agents/skills/dbt-models/SKILL.md` B17 and the rejoin test rule C10.
