---
artifacts: [stg_ops__trip_assignments]
---

# stg_ops__trip_assignments

The operator's trip assignments, with the warehouse's trip key derived from the operator's natural columns.

## Grain

One row per trip assignment (`assignment_id`), one per attributed trip.

## Decisions

- `D-01` Derive `trip_key` with the `trip_natural_key` macro from the natural columns the operator's records carry; the operator source has no key of its own ([ADR 0007](../../../adr/0007-trip-key-has-one-definition.md)). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-03, [ADR 0007](../../../adr/0007-trip-key-has-one-definition.md).
- `D-02` Convert the operator's UTC-tagged timestamps to plain timestamps before the key is computed, so the key equals the one `int_trips_conformed` produces ([ADR 0008](../../../adr/0008-simulated-sources-are-generated-inside-their-pipelines.md)). Superseded by `D-03`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-03, [ADR 0008](../../../adr/0008-simulated-sources-are-generated-inside-their-pipelines.md).
- `D-03` Convert the operator's timestamps with `to_utc_timestamp(col, current_timezone())` before the key is computed, so the key equals the one `int_trips_conformed` produces: the key's inputs must be the same plain timestamps everywhere ([ADR 0007](../../../adr/0007-trip-key-has-one-definition.md)). This corrects `D-02`'s source: ADR 0008 says nothing about timestamps. Source: [`dbt-models`](../../../../.agents/skills/dbt-models/SKILL.md) B17, [ADR 0007](../../../adr/0007-trip-key-has-one-definition.md).

## Rejected

- Carrying `trip_key` in the operator source: a source system cannot know the warehouse's key.

## Consumers

Depended on by: `agg_driver_daily`, `agg_driver_monthly`, `agg_garage_monthly`, `agg_od_flow_matrix`, `agg_trip_band_profile`, `agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`, `agg_vehicle_daily`, `agg_vehicle_monthly`, `agg_weather_demand_daily`, `fct_shift`, `fct_trip`, `int_shift_economics`, `mart_daily_zone_revenue`, `mart_driver_scorecard`, `mart_monthly_service_summary`, `mart_revenue_component_bridge`, `mart_trip_quality_scorecard`, `mart_vehicle_utilisation`.

## History

- 2026-10-14 — setup-dlt-ingestion — design record written — D-01, D-02
- 2026-10-28 — design-record audit — timestamp conversion sourced from ADR 0007 — D-03
