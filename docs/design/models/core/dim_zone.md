---
artifacts: [dim_zone]
---

# dim_zone

The zone dimension, versioned the way the master-data source versions it.

## Grain

One row per zone version: `zone_key` is the md5 of the zone's natural key and the version's start date.

## Decisions

- `D-01` Type 2: the source delivers validity dates and a version number, and this model turns them into a surrogate-keyed dimension. Intervals are half-open, so an as-of join uses `>=` and `<`, never `between` ([ADR 0009](../../../adr/0009-type-2-only-where-the-source-versions-history.md)). Source: [ADR 0009](../../../adr/0009-type-2-only-where-the-source-versions-history.md).
- `D-02` Keep unresolved zones and mark them with `is_unresolved_zone`; do not remap or drop them ([ADR 0012](../../../adr/0012-unresolved-zones-are-retained-and-flagged.md)). Source: [ADR 0012](../../../adr/0012-unresolved-zones-are-retained-and-flagged.md).
- `D-03` Join borough attributes (code, region, whether it is a core market) from the borough master, so a zone carries them without a second lookup. Source: docs/requirement/2026-08-29-the-trip-fact.md R-04.

## Rejected

- Collapsing to the current version in the dimension: collapsing is the consumer's choice, not the dimension's.

## Consumers

Depended on by: `agg_od_flow_matrix`, `agg_trip_band_profile`, `agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`, `agg_weather_demand_daily`, `agg_zone_occupancy_hourly`, `fct_status_interval`, `fct_trip`, `mart_daily_zone_revenue`, `mart_monthly_service_summary`, `mart_revenue_component_bridge`, `mart_trip_quality_scorecard`.

## History

- 2026-10-14 — setup-dlt-ingestion — design record written — D-01, D-02, D-03
