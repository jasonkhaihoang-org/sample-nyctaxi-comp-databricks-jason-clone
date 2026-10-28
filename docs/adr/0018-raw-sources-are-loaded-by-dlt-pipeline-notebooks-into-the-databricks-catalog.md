---
status: decided
date: 2026-10-28
---

# Every raw source is loaded into the Databricks catalog by a dlt pipeline notebook

The TLC trips and zone lookup, the fleet operator's platform (`ops_raw`) and the master-data platform (`mdm_raw`) are each loaded by a dlt pipeline notebook in `ingestion/` (`<name>_pipeline.ipynb`), made from the plugin's Databricks template. Each notebook loads Delta tables into the Domain's catalog through `databricks_files_api()` from `vibedata-dlt-databricks-notebook`, dlt's `databricks` destination staging its files through the Files API. The TLC pipeline downloads its files from the public TLC site; nothing is downloaded or staged by hand first. No notebook builds a table itself: dlt lands each source as it arrives, and every transformation is a dbt model. The loaded window is three months, reloaded in full on every run (`replace`), with no sampling. This restates ADR 0017 for Databricks.

## Considered options

- **Lakeflow Declarative Pipelines or Auto Loader** — rejected: no dlt schema contract or load metadata, a second load framework beside the plugin's, and the simulated sources would still need code.
- **dlt run as a plain Python script in the agent's container** — rejected: the plugin runs a Databricks load on serverless compute only, and an Intent could not prove the artifact the job runs.
- **A dlt pipeline notebook per source** — chosen. It is the plugin's `databricks` pipeline artifact: one notebook runs as an Intent's sandbox load (`run_notebook.py`) and as a task of the `nyc_taxi_refresh` job.

## Consequences

- Source column names are kept as the source has them (`naming = "direct"`), which Databricks folds to lower case (`VendorID` lands as `vendorid`); every row carries `_dlt_load_id` and `_dlt_id`.
- A source date that dlt receives as a timestamp lands as a timestamp at UTC midnight, and staging turns it back into that date.
- The notebook names no catalog or warehouse, and `config.toml` holds none: dlt refuses credentials there. A sandbox run passes the Ephemeral catalog and warehouse in the notebook's `dlt_env` widget. The `nyc_taxi_refresh` job passes its `dlt_env` variable, which defaults to the catalog and warehouse the job is deployed with, so a production deploy loads into the Domain catalog.
- A one-off fixed window has no freshness check.
- Every resource here is `replace`, so dlt's merge behaviour does not apply until a resource changes disposition.
- Changing the dlt normalisation settings against existing tables fails; the dataset's tables are dropped and reloaded instead.
- A new pipeline is run by adding its notebook as a task ahead of the dbt task in `orchestration/nyc_taxi_refresh.job.yml`.

## Affected designs

- [`pipelines/tlc.md`](../design/pipelines/tlc.md)
- [`pipelines/ops.md`](../design/pipelines/ops.md)
- [`pipelines/mdm.md`](../design/pipelines/mdm.md)
- [`models/staging/stg_tlc__yellow_tripdata.md`](../design/models/staging/stg_tlc__yellow_tripdata.md)
- [`models/staging/stg_tlc__green_tripdata.md`](../design/models/staging/stg_tlc__green_tripdata.md)
