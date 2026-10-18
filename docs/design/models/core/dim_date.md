---
artifacts: [dim_date]
---

# dim_date

The date spine over the calendar master.

## Grain

One row per calendar date.

## Decisions

- `D-01` `week_start_date` truncates a date to its week; weeks start on Monday, and this column is the only week boundary in the warehouse ([ADR 0014](../../../adr/0014-weeks-start-on-monday.md)). Source: [ADR 0014](../../../adr/0014-weeks-start-on-monday.md).
- `D-02` Holiday, weekend and school-term flags come from master data rather than being computed, so a calendar correction restates reports without a code change. A combined `is_non_working_day` is kept beside the separate flags. Source: docs/requirement/2026-08-29-the-trip-fact.md R-04.

## Rejected

- Computing holidays in the model: a calendar correction would need a code change.

## Consumers

Depended on by: `agg_od_flow_matrix`, `agg_trip_band_profile`, `agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`, `agg_weather_demand_daily`, `fct_trip`, `mart_daily_zone_revenue`, `mart_monthly_service_summary`, `mart_revenue_component_bridge`, `mart_trip_quality_scorecard`.

## History

- - 2026-10-14 — setup-dlt-ingestion — design record written — D-01, D-02
