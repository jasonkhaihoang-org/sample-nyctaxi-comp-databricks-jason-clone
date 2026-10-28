---
artifacts: [int_trips_enriched]
---

# int_trips_enriched

The only intermediate model that rejoins the fleet-specific attributes removed when trips were conformed: the airport fee for yellow, and the e-hail fee and trip type for green.

## Grain

One row per conformed trip (`trip_key`).

## Decisions

- `D-01` Rejoin through the two dedicated, deduplicated extras models on `trip_key`. Joining raw rows would allow duplicate source records to multiply a trip; carrying all fleet-specific columns in the conformed model would reverse the conformed-intersection contract ([ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md)). Source: docs/requirement/2026-08-29-the-trip-fact.md R-02, [ADR 0006](../../../adr/0006-silver-is-built-in-dbt.md).
- `D-02` Preserve three airport-fee states: `present`, `missing` and `not_applicable`. A null green fee is not missing data; it is a field that does not exist for that fleet. Collapsing the states would corrupt fleet-blind fee metrics. Source: docs/requirement/2026-08-29-the-trip-fact.md R-02.
- `D-03` Use left joins. Every conformed trip survives even when its optional, fleet-specific companion is absent; the extras models enforce the required at-most-one match. Source: docs/requirement/2026-08-29-the-trip-fact.md R-02.
- `D-04` Materialise as a view. The trip grain is stored once, in `fct_trip`; storing it again here made the seeded Domain file 1,158 MiB for one month, over Studio's 1 GiB upload, and only `fct_trip`'s build reads this model in full. Superseded by `D-05`. Source: user answer, new-intent seed-domain (2026-10-15).
- `D-05` Materialise as a table. On the Fabric Lakehouse the SQL analytics endpoint cannot read a Spark view, and the Domain has no file-size limit, so the reason for `D-04` no longer applies. Superseded by `D-06`. Source: [`dbt-models`](../../../../.agents/skills/dbt-models/SKILL.md) B15.
- `D-06` Materialise as a table, by choice. On Databricks a view over a Domain source builds and reads in the Ephemeral catalog, so nothing forces a table, and the Domain is a Unity Catalog catalog, not an uploaded file, so the reason for `D-04` does not return; every layer stays a table so one rule covers the project ([probe](../../../verify/2026-10-28-vd-7384-databricks-probe.md) P1). Source: [`dbt-models`](../../../../.agents/skills/dbt-models/SKILL.md) B15.

## Rejected

- Carrying every fleet-specific column in `int_trips_conformed`: a column null for a whole fleet invites silently wrong averages.
- Joining bronze rows directly: duplicates would multiply trips.

## Consumers

Depended on by: `agg_driver_daily`, `agg_driver_monthly`, `agg_garage_monthly`, `agg_od_flow_matrix`, `agg_trip_band_profile`, `agg_trip_zone_daily`, `agg_trip_zone_daypart_dow`, `agg_vehicle_daily`, `agg_vehicle_monthly`, `agg_weather_demand_daily`, `dim_trip_quality`, `fct_shift`, `fct_trip`, `int_shift_economics`, `int_trip_fare_components`, `int_trip_quality_flags`, `mart_daily_zone_revenue`, `mart_driver_scorecard`, `mart_monthly_service_summary`, `mart_revenue_component_bridge`, `mart_trip_quality_scorecard`, `mart_vehicle_utilisation`.

## History

- 2026-08-29 — trip-fact — design record written (commit 97862f7) — D-01, D-02, D-03
- 2026-10-14 — setup-dlt-ingestion — conformed trips now come from `int_trips_conformed`; the extras models apply the same timestamp conversion as staging; record conformed to the template
- 2026-10-15 — seed-domain — materialised as a view — D-04
- 2026-10-19 — fabric-port — materialised as a table — D-05
- 2026-10-28 — databricks-port — still a table, by choice — D-06
