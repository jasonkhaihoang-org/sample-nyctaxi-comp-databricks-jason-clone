---
artifacts: [tlc]
---

# tlc

Loads the NYC TLC yellow and green trip files and the zone lookup into `bronze`.

## Grain

Three resources: one row per row of each source file (`yellow_tripdata`, `green_tripdata`) and one per zone (`taxi_zone_lookup`).

## Decisions

- `D-01` Fetch the files from the public TLC site for 2024-01 to 2024-03; nothing is downloaded or staged by hand ([ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md)). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, R-04, [ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md).
- `D-02` Load the source verbatim: no casts, filters or sampling. Column names are kept (`naming = "direct"`), and every row carries `_dlt_load_id` and `_dlt_id`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01.
- `D-03` `yellow_tripdata`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none removed, because bronze is not deduplicated (`int_trips_conformed` does that). Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md).
- `D-04` `green_tripdata`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none removed, as for yellow. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md).
- `D-05` `taxi_zone_lookup`: write disposition `replace` (each run reloads the whole fixed window); no incremental cursor; contract `columns: freeze`, `tables: evolve`, `data_type: freeze`; duplicate keys: none expected: one row per zone. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md).
- `D-06` `tables` stays `evolve`: the database is rebuilt from empty on every run, so freezing it would forbid creating the tables. Superseded by `D-09`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01.
- `D-07` The pipeline imports `setup_environment` and `finalize` from `vibedata.dlt.duckdb`. Outside Studio it needs `VD_DOMAIN_DATA_PLATFORM=duckdb_local`, `VD_DOMAIN_SECRET_STORE_KIND=local_toml` and `VD_EPHM_DUCKDB_LOCAL_PATH`; `orchestration/run_ingest.py` sets them. Superseded by `D-08`. Source: docs/requirement/2026-10-14-load-every-raw-source-with-dlt-and-build-silver-in-dbt.md R-01, [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-08` The pipeline is the notebook `ingestion/tlc_pipeline.Notebook/`, which imports `setup_environment` and `finalize` from `vibedata.dlt.fabric` and writes Delta through the `filesystem` destination into the Lakehouse named by `[destination.filesystem]`. Studio retargets a sandbox run to the Intent's Ephemeral Lakehouse; the `nyc_taxi_refresh` Data Pipeline runs it in production. Superseded by `D-10`. Source: [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md), plugin `fabric_lakehouse/dlt.md`.
- `D-09` `tables` stays `evolve`: every Intent's Ephemeral Lakehouse starts empty, so freezing it would forbid creating the tables in the sandbox. Superseded by `D-11`. Source: [ADR 0017](../../adr/0017-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-lakehouse.md).
- `D-10` The pipeline is the notebook `ingestion/tlc_pipeline.ipynb`, from the plugin's Databricks template. It loads Delta tables through `databricks_files_api()` into the catalog its `dlt_env` widget names: the Intent's Ephemeral catalog in a sandbox run (`run_notebook.py`); in the `nyc_taxi_refresh` job, the catalog and warehouse it is deployed with (its `dlt_env` variable's default). Source: [ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md), plugin `databricks/dlt.md`.
- `D-11` `tables` stays `evolve`: every Intent's prefixed schemas start empty, so freezing it would forbid creating the tables in the sandbox. Source: [ADR 0018](../../adr/0018-raw-sources-are-loaded-by-dlt-pipeline-notebooks-into-the-databricks-catalog.md).

## Rejected

- Sampling the trips: a row filter has no place in bronze, and three months already limits volume.
- A download script that stages files before the load.

## Consumers

Depended on by: `stg_tlc__yellow_tripdata`, `stg_tlc__green_tripdata`; and by the `ops` and `mdm` pipelines, which reuse its source code (the yellow trips and the zone lookup).

## History

- 2026-10-14 — setup-dlt-ingestion — design record written when TLC loading moved from scripts to dlt — D-01 to D-07
- 2026-10-18 — fabric-port — the pipeline became a Fabric notebook loading the Lakehouse — D-08, D-09
- 2026-10-28 — databricks-port — the pipeline became a Databricks notebook loading the catalog — D-10, D-11
