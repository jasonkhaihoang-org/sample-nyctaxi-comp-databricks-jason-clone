---
artifacts: [int_trips_conformed]
---

# int_trips_conformed

Yellow and green trips conformed onto one grain, built in dbt from two staging models.

## Grain

One row per distinct trip across both fleets, identified by `trip_key`.

## Decisions

- `D-01` Union the two staging models on the columns both fleets share, with a `service_type` discriminator. Columns that exist on only one fleet are dropped rather than carried as a column that is null for a whole fleet ([ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md)). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-02, [ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md).
- `D-02` Compute `trip_key` with the `trip_natural_key` macro and deduplicate on the natural columns, keeping the first row by `_dlt_load_id`; identical duplicates are interchangeable, so ties among them are arbitrary ([ADR 0007](../../../adr/0007-trip-key-has-one-definition.md)). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-02, [ADR 0007](../../../adr/0007-trip-key-has-one-definition.md).
- `D-03` Derive duration, speed and calendar keys here once, so no downstream model recomputes them. Apply no filter: refunds, zero-distance trips and out-of-window pickups all survive. Source: docs/requirement/2026-08-29-the-trip-fact.md R-01.
- `D-04` Materialise as a view. The trip grain is stored once, in `fct_trip`; storing it again here made the seeded Domain file 1,158 MiB for one month, over Studio's 1 GiB upload, and only `fct_trip`'s build reads this model in full. Source: user answer, new-intent seed-domain (2026-10-15).

## Rejected

- A `silver` schema built by dbt models: a layer the dbt layering already covers ([ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md)).
- Keeping the script that built the grain: it sat outside the project with no tests or lineage.

## Consumers

Depended on by: `agg_driver_daily`, `agg_driver_monthly`, `agg_garage_monthly`, `agg_od_flow_matrix`, `agg_trip_band_profile`, `agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`, `agg_vehicle_daily`, `agg_vehicle_monthly`, `agg_weather_demand_daily`, `dim_trip_quality`, `fct_shift`, `fct_trip`, `int_shift_economics`, `int_trip_fare_components`, `int_trip_quality_flags`, `int_trips_enriched`, `mart_daily_zone_revenue`, `mart_driver_scorecard`, `mart_monthly_service_summary`, `mart_revenue_component_bridge`, `mart_trip_quality_scorecard`, `mart_vehicle_utilisation`.

## History

- - 2026-10-14 — setup-dlt-ingestion — design record written when the grain moved from a script into dbt — D-01, D-02, D-03
- 2026-10-15 — seed-domain — materialised as a view — D-04
