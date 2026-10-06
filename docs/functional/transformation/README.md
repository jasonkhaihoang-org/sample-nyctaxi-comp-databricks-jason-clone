# Transformation — single dbt project

One dbt project (`nyc_taxi_analytics`, v2.1.0, profile `nyc_taxi_analytics`,
Lakehouse connection on `nyc_taxi_lakehouse`), sources under `transformation/`
with a deploy mirror at `src/dbt/dbt/`. Layer flow: `staging` views →
`intermediate` tables → `core` / `agg` / `finance` / `ops` tables, plus `seeds`
band tables (daypart, distance, duration, fare) and five singular tests
(`assert_airport_fee_only_on_yellow`,
`assert_fct_trip_matches_silver_rowcount`,
`assert_no_negative_status_intervals`,
`assert_scd2_zone_intervals_do_not_overlap`,
`assert_shift_time_budget_reconciles`).

## Per-group selectors

Each pipeline slice builds exactly one model group via dbt `select`:

| Selector | Group built | Pipeline activity |
| --- | --- | --- |
| `staging.*` | All staging views (TLC, MDM, ops) | main `BuildStagingSlice` |
| `marts.*` | intermediate + core + agg | main `BuildMartsSlice` |
| `finance.*` | Finance marts (daily zone revenue, monthly service summary, revenue component bridge) | finance `BuildFinanceSlice` |
| `ops.*` | Ops marts (driver scorecard, vehicle utilisation, trip quality scorecard) | ops `BuildOpsSlice` |

Source location is indirection, not duplication: `bronze/silver/ops/mdm`
`_database`/`_schema` vars resolve every `source()` identically everywhere the
project runs.

## Billable-trip and window rules

**Billable trip** is `total_amount > 0` (`is_billable`, computed in
`int_trip_quality_flags`). Finance revenue marts and selected aggregates opt
into it; `core.fct_trip` retains all trips and exposes the flag, so
data-quality and operational models can still analyse refunds, voids, and meter
errors.

**Reporting window** is `report_start = 2024-01-01` / `report_end =
2024-07-01` — the Finance-agreed window, not a sampling control. Changing it
changes the numbers in the Monday revenue pack. Implausibility bounds
(`max_plausible_mph = 80`, `min_plausible_seconds = 30`) flag, never delete.

## Threads

The dbt job runs with `threads: 4`
(`src/dbt/nyc_taxi_analytics.DataBuildToolJob/dbt-content.json`). Model
materializations follow `dbt_project.yml`: staging as views, intermediate and
all marts as tables into their own schemas.
