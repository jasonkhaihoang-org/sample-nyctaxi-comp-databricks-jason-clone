---
status: decided
date: 2026-10-18
---

# Every raw source is loaded into the Lakehouse by a dlt pipeline notebook

The TLC trips and zone lookup, the fleet operator's platform (`ops_raw`) and the master-data platform (`mdm_raw`) are each loaded by a dlt pipeline notebook in `ingestion/` (`<name>_pipeline.Notebook/`). The notebook writes Delta tables into the Domain Lakehouse through dlt's `filesystem` destination and imports `vibedata.dlt.fabric`. The TLC pipeline downloads its files from the public TLC site; nothing is downloaded or staged by hand first. No notebook builds a table itself: dlt lands each source as it arrives, and every transformation is a dbt model. The loaded window is three months, reloaded in full on every run (`replace`), with no sampling. This restates ADR 0005 for the Fabric Lakehouse.

## Considered options

- **dlt lands raw files, then Spark builds bronze and silver in the notebook** (this repo's earlier Fabric tree) — rejected: two load paths, logic in bronze, and a silver layer outside dbt, against ADR 0006.
- **Fabric Data Factory copy activities** — rejected: no schema contract and no load metadata, and the simulated sources would still need code.
- **A dlt pipeline notebook per source** — chosen. It is the plugin's `fabric_lakehouse` pipeline artifact: the same file runs as plain Python in an Intent's sandbox and as the notebook a Data Pipeline activity invokes.

## Consequences

- Source column names are kept verbatim (`naming = "direct"`) and every row carries `_dlt_load_id` and `_dlt_id`.
- Bronze timestamps arrive tagged UTC, so staging converts them to plain timestamps.
- A one-off fixed window has no freshness check.
- Delta `merge` does not deduplicate. Every resource here is `replace`, so this does not apply until a resource changes disposition.
- Changing the dlt normalisation settings against existing tables fails; the dataset's tables are dropped and reloaded instead.
- A new pipeline is run by adding an activity to the `nyc_taxi_refresh` Data Pipeline in `orchestration/`.

## Affected designs

- [`pipelines/tlc.md`](../design/pipelines/tlc.md)
- [`pipelines/ops.md`](../design/pipelines/ops.md)
- [`pipelines/mdm.md`](../design/pipelines/mdm.md)
- [`models/staging/stg_tlc__yellow_tripdata.md`](../design/models/staging/stg_tlc__yellow_tripdata.md)
- [`models/staging/stg_tlc__green_tripdata.md`](../design/models/staging/stg_tlc__green_tripdata.md)
