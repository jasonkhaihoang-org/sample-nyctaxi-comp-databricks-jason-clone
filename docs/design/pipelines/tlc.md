---
artifacts: [tlc]
---

# tlc

Loads the NYC TLC yellow and green trip files and the zone lookup into `bronze`.

## Grain

Three resources: one row per row of each source file (`yellow_tripdata`, `green_tripdata`) and one per zone (`taxi_zone_lookup`).

## Decisions

- `D-01` Fetch the files from the public TLC site for 2024-01 to 2024-03; nothing is downloaded or staged by hand ([ADR 0005](../../adr/0005-all-raw-sources-are-loaded-by-dlt.md)). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, R-04, [ADR 0005](../../adr/0005-all-raw-sources-are-loaded-by-dlt.md).
- `D-02` Load the source verbatim: no casts, filters or sampling. Column names are kept (`naming = "direct"`), and every row carries `_dlt_load_id` and `_dlt_id`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01.
- `D-03` `yellow_tripdata`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none removed, because bronze is not deduplicated (`int_trips_conformed` does that). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0005](../../adr/0005-all-raw-sources-are-loaded-by-dlt.md).
- `D-04` `green_tripdata`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none removed, as for yellow. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0005](../../adr/0005-all-raw-sources-are-loaded-by-dlt.md).
- `D-05` `taxi_zone_lookup`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: one row per zone. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0005](../../adr/0005-all-raw-sources-are-loaded-by-dlt.md).
- `D-06` `tables` stays `evolve`: the database is rebuilt from empty on every run, so freezing it would forbid creating the tables. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01.
- `D-07` The pipeline imports `setup_environment` and `finalize` from `vibedata.dlt.duckdb`. Outside Studio it needs `VD_DOMAIN_DATA_PLATFORM=duckdb_local`, `VD_DOMAIN_SECRET_STORE_KIND=local_toml` and `VD_EPHM_DUCKDB_LOCAL_PATH`; `orchestration/run_ingest.py` sets them. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0005](../../adr/0005-all-raw-sources-are-loaded-by-dlt.md).

## Rejected

- Sampling the trips: a row filter has no place in bronze, and three months already limits volume.
- A download script that stages files before the load.

## Consumers

Depended on by: `stg_tlc__yellow_tripdata`, `stg_tlc__green_tripdata`; and by the `ops` and `mdm` pipelines, which reuse its source code (the yellow trips and the zone lookup).

## History

- - 2026-10-14 — setup-dlt-ingestion — design record written when TLC loading moved from scripts to dlt — D-01 to D-07
