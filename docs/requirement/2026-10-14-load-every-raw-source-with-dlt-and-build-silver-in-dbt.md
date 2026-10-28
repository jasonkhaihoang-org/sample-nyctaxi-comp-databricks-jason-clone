---
kinds: [ingestion, transformation]
---

# Requirement: Load every raw source with dlt and build silver in dbt

The full requirement and its decisions are in the DuckDB repo's `docs/setup/requirements.md` (R-10, R-12, with the decisions table), in [`accelerate-data/sample-nyctaxi-comp`](https://github.com/accelerate-data/sample-nyctaxi-comp/blob/main/docs/setup/requirements.md). This document keeps the four requirements that govern the pipelines and the silver move.

This intent was built on the DuckDB Domain this repo was ported from. On Databricks the pipelines are `ingestion/<name>_pipeline.ipynb` notebooks and the `nyc_taxi_refresh` job runs them; the requirements and decisions are unchanged.

## Ask

Make the repo look like a real data product: raw sources loaded by dlt pipelines that fetch from the source, the conformed trip grain built in dbt, and a data volume small enough to rebuild anywhere.

## Requirements

- [x] `R-01` Every raw source is loaded by a dlt pipeline that fetches from its source — accept when `ingestion/` holds the `tlc`, `ops` and `mdm` pipelines, `orchestration/run_ingest.py` runs them, and a second run leaves every table's row count unchanged — source: `docs/adr/0005-all-raw-sources-are-loaded-by-dlt.md`
- [x] `R-02` The conformed trip grain is built in dbt and equals the grain it replaced — accept when `int_trips_conformed` has the same row count and the same set of trip keys as the script it replaced on the same inputs — source: `docs/adr/0006-silver-is-built-in-dbt.md`
- [x] `R-03` The operator source carries natural columns, and `trip_key` is derived in dbt — accept when `stg_ops__trip_assignments` derives the key with `trip_natural_key` and no assignment is missing from `int_trips_conformed` — source: `docs/adr/0007-trip-key-has-one-definition.md`
- [x] `R-04` The loaded window is three months and the reporting window matches it — accept when the pipelines load 2024-01 to 2024-03 and `report_start` and `report_end` in `dbt_project.yml` are 2024-01-01 and 2024-04-01 — source: `docs/design/pipelines/tlc.md`

## Business decisions

| Decision | Value | Source |
| --- | --- | --- |
| Sampling | None; volume is limited by the three-month window | DuckDB repo `docs/setup/requirements.md` |
| Simulated sources | Generated inside their pipelines | `docs/adr/0008-simulated-sources-are-generated-inside-their-pipelines.md` |
| Reference data | Needed to load raw: a dlt resource. Used in staging: a dbt seed | DuckDB repo `docs/setup/requirements.md` |

## Out of scope

- Orchestration beyond the three run scripts.
- Porting the work to another repository.

## Open questions

None.

## Approvals

- 2026-10-14 — requirement approved — reconstructed: the user approved the work plan that implements it with "proceed" — 4ccbc8c
