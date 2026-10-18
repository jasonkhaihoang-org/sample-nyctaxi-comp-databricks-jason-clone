# Plan: The trip fact

Reconstructed from the repository for demonstration and context, like its Requirement. The tasks describe the models as they stand; the execution evidence was gathered on 2026-10-15 against the seeded Domain (January 2024).

**Goal:** One trip-level fact across yellow and green, keeping every trip, with its quality verdicts, conformed dimensions and optional fleet attribution.

**Requirement:** [`docs/requirement/2026-08-29-the-trip-fact.md`](../requirement/2026-08-29-the-trip-fact.md)

**Constraints:**

- Grain of `fct_trip`: one row per distinct TLC trip.
- Billable trip: a positive total, applied where revenue and flows are reported ([ADR 0003](../adr/0003-billable-trip-definition-and-where-it-applies.md)).
- Quality verdicts flag trips and never delete them ([ADR 0004](../adr/0004-quality-verdicts-flag-trips-and-never-delete-them.md)).
- Unmatched dimension keys stay null, with no placeholder member ([ADR 0015](../adr/0015-unmatched-dimension-keys-stay-null.md)).
- `trip_key` has one definition, the `trip_natural_key` macro ([ADR 0007](../adr/0007-trip-key-has-one-definition.md)).

## Scope and impact

| Artifact | Kind | Action | Requirements | Design record | Gate |
| --- | --- | --- | --- | --- | --- |
| `trip_natural_key` | macro | create | `R-06` | [trip identity](../design/trips/trip-identity.md) | `dbt test --select "test_type:unit,+fct_trip" --target dev` |
| `int_trips_conformed` | model | create | `R-01`, `R-06` | [`int_trips_conformed.md`](../design/models/intermediate/int_trips_conformed.md) | `dbt test --select "test_type:unit,+fct_trip" --target dev` |
| `int_trips_enriched` | model | create | `R-02` | [`int_trips_enriched.md`](../design/models/intermediate/int_trips_enriched.md) | `dbt build --select +fct_trip --exclude test_type:unit --target dev` |
| `int_trip_quality_flags` | model | create | `R-03` | [`int_trip_quality_flags.md`](../design/models/intermediate/int_trip_quality_flags.md) | `dbt build --select +fct_trip --exclude test_type:unit --target dev` |
| `fct_trip` | model | create | `R-01`, `R-03`, `R-04`, `R-05` | [`fct_trip.md`](../design/models/core/fct_trip.md) | the Task 3 singular tests |

**Change impact:** all new; nothing existing is touched. `dbt ls --select fct_trip+` lists the marts and aggregates built on the fact, which arrive in later intents.

## Tasks

### Task 1: The trip key and the conformed trips

**Requirements:** `R-01`, `R-06` · **Design:** [trip identity](../design/trips/trip-identity.md), [`int_trips_conformed.md`](../design/models/intermediate/int_trips_conformed.md) · **Skill:** `generating-dbt-model` · **Depends on:** none

- [x] Author `transformation/macros/trip_keys.sql`, `transformation/models/intermediate/int_trips_conformed.sql` and the unit tests `trips_conformed_keeps_one_row_per_distinct_trip` and `trips_conformed_distinguishes_fleets_with_the_same_natural_columns` in `transformation/models/intermediate/_unit_tests.yml`
- [x] Run `dbt test --select "test_type:unit,+fct_trip" --target dev`; expect `PASS=3`
- [x] Run the acceptance condition of `R-06`: only `transformation/macros/trip_keys.sql` writes the key expression, and the unit tests above pin it; expect one writer
- [x] Commit and push the macro, the model and the unit tests

### Task 2: Fleet-specific columns and quality verdicts

**Requirements:** `R-02`, `R-03` · **Design:** [`int_trips_enriched.md`](../design/models/intermediate/int_trips_enriched.md), [`int_trip_quality_flags.md`](../design/models/intermediate/int_trip_quality_flags.md) · **Skill:** `generating-dbt-model` · **Depends on:** Task 1

- [x] Author `transformation/models/intermediate/int_trips_enriched.sql`, `transformation/models/intermediate/int_trip_quality_flags.sql` and `transformation/tests/assert_enrichment_rejoin_matches_every_trip.sql`
- [x] Run `dbt build --select +fct_trip --exclude test_type:unit --target dev`; expect every node to pass
- [x] Run the acceptance condition of `R-02`: `airport_fee_status` holds only `present`, `missing` or `not_applicable`, and `assert_enrichment_rejoin_matches_every_trip` returns no rows
- [x] Commit and push both models and the rejoin test

### Task 3: The trip fact

**Requirements:** `R-01`, `R-03`, `R-04`, `R-05` · **Design:** [`fct_trip.md`](../design/models/core/fct_trip.md) · **Skill:** `generating-dbt-model` · **Depends on:** Tasks 1 and 2

- [x] Author `transformation/models/marts/core/fct_trip.sql`, its entry in `transformation/models/marts/core/_core.yml` and `transformation/tests/assert_fct_trip_matches_conformed_rowcount.sql`
- [x] Run `dbt test --select assert_fct_trip_matches_conformed_rowcount assert_enrichment_rejoin_matches_every_trip assert_scd2_zone_intervals_do_not_overlap assert_airport_fee_only_on_yellow --target dev`; expect `PASS=4`
- [x] Run the acceptance conditions of `R-01`, `R-03`, `R-04` and `R-05`: the row-count test returns no rows; `fct_trip` exposes `is_billable` and `trip_quality_key`; the zone and vendor `relationships` tests and `assert_scd2_zone_intervals_do_not_overlap` pass; `is_fleet_attributed` disagrees with driver, vehicle and shift presence in no row
- [x] Commit and push the model, its properties entry and the row-count test

## Execution evidence

- Task 1: `dbt test --select "test_type:unit,+fct_trip" --target dev` — exit 0 — PASS=3 — `transformation/macros/trip_keys.sql` sha256:c8f9b8f44f99dbc7…, `transformation/models/intermediate/int_trips_conformed.sql` sha256:5cf1721f8fb108c5…
- Task 2: `dbt build --select +fct_trip --exclude test_type:unit --target dev` — exit 0 — PASS=82 — `int_trips_enriched.sql` sha256:4a801d608befe8df…, `int_trip_quality_flags.sql` sha256:e33a8febee5a2d54…
- Task 3: the four singular tests above — exit 0 — PASS=4 — `fct_trip.sql` sha256:3dceea49fce62d13…, `assert_fct_trip_matches_conformed_rowcount.sql` sha256:8b9fa528519ea9dd…
