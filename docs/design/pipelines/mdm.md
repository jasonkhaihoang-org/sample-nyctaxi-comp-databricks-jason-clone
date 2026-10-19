---
artifacts: [mdm]
---

# mdm

Loads the master-data platform, a simulated source system, into `mdm_raw`.

## Grain

Nine resources, one row per master record: zone master, vendor master, payment method master, rate plan master, fare regime master, borough master, zone points of interest, calendar master and daily weather.

## Decisions

- `D-01` Generate the masters deterministically in memory with DuckDB, from the zone lookup the `tlc` pipeline fetches ([ADR 0008](../../adr/0008-simulated-sources-are-generated-inside-their-pipelines.md)). The rows are identical to those of the script this replaced, compared in both directions on every table. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0008](../../adr/0008-simulated-sources-are-generated-inside-their-pipelines.md).
- `D-02` Two masters are versioned at source (zone and vendor), with validity dates and a natural key; conforming and Type 2 assembly happen in dbt, not here ([ADR 0009](../../adr/0009-type-2-only-where-the-source-versions-history.md)). Source: [ADR 0009](../../adr/0009-type-2-only-where-the-source-versions-history.md).
- `D-03` Weather covers the loaded months; the calendar spans a wider range because it is reference data, not tied to the trip window. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-04.
- `D-04` `zone_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: unique by `location_id` and `source_version`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-05` `vendor_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: unique by `vendor_id` and `source_version`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-06` `payment_method_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `payment_type_code` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-07` `rate_plan_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `rate_code` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-08` `fare_regime_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `regime_code` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-09` `borough_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `borough_name` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-10` `zone_poi`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `poi_id` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-11` `calendar_master`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `calendar_date` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-12` `weather_daily`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: `observation_id` is unique. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-13` `tables` stays `evolve` for the same reason as the `tlc` pipeline. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01.
- `D-14` The pipeline is the notebook `ingestion/mdm_pipeline.Notebook/` and loads the Lakehouse as `tlc` `D-08` does. Its generator still runs DuckDB in memory as a library ([ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md), [ADR 0008](../../adr/0008-simulated-sources-are-generated-inside-their-pipelines.md)); nothing is written to a DuckDB file. Source: [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).

## Rejected

- Hand-maintained reference tables in the warehouse: they belong to the source that owns them.

## Consumers

Depended on by: `stg_mdm__boroughs`, `stg_mdm__calendar`, `stg_mdm__fare_regimes`, `stg_mdm__payment_methods`, `stg_mdm__rate_plans`, `stg_mdm__vendors`, `stg_mdm__weather`, `stg_mdm__zone_poi`, `stg_mdm__zones`.

## History

- - 2026-10-14 — setup-dlt-ingestion — design record written when the generators moved from scripts into a dlt pipeline — D-01 to D-13
- - 2026-10-18 — fabric-port — the pipeline became a Fabric notebook loading the Lakehouse — D-14
