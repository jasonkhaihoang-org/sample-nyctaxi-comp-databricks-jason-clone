---
artifacts: [stg_tlc__green_tripdata]
---

# stg_tlc__green_tripdata

Green taxi trips as loaded, renamed and typed.

## Grain

One row per row of `bronze.green_tripdata`.

## Decisions

- `D-01` Rename and type only, one-to-one with the bronze table. Every bronze column is carried, including the green-only e-hail fee and trip type. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-02` Bring the UTC-tagged timestamps back to plain timestamps with `timezone('UTC', ...)` ([ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md)). Superseded by `D-03`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-02, [ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md).
- `D-03` Bring each timestamp to the wall-clock value the meter recorded with `to_utc_timestamp(col, current_timezone())`: dlt lands UTC instants and Spark shows a timestamp in the session time zone, so the trip key and every date derived from it would otherwise depend on that zone ([ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md)). Source: [ADR 0017](../../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).

## Rejected

- Converting with a bare cast: it uses the session time zone.

## Consumers

Depended on by: `agg_driver_daily`, `agg_driver_monthly`, `agg_garage_monthly`, `agg_od_flow_matrix`, `agg_trip_band_profile`, `agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`, `agg_vehicle_daily`, `agg_vehicle_monthly`, `agg_weather_demand_daily`, `dim_trip_quality`, `fct_shift`, `fct_trip`, `int_shift_economics`, `int_trip_fare_components`, `int_trip_quality_flags`, `int_trips_conformed`, `int_trips_enriched`, `mart_daily_zone_revenue`, `mart_driver_scorecard`, `mart_monthly_service_summary`, `mart_revenue_component_bridge`, `mart_trip_quality_scorecard`, `mart_vehicle_utilisation`.

## History

- 2026-10-14 — setup-dlt-ingestion — design record written — D-01, D-02
- 2026-10-19 — fabric-port — Spark conversion — D-03
