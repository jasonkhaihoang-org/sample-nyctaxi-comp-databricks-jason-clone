---
name: dlt
description: "Use when adding or changing a dlt source or pipeline in ingestion/, or when running a sample or full load."
---

# dlt ingestion

Operator conventions for the pipelines in `ingestion/`. Where files live is declared in `repo-map.json`.

## Datasets (D5)

A pipeline's dataset is the schema it feeds: `bronze` (TLC), `ops_raw`, `mdm_raw`. Not `src_<connection>`. In an Intent the notebook's `dataset()` call lands it as `<VD_EPHM_SCHEMA_PREFIX><dataset>` in the Ephemeral catalog (`<prefix>bronze`).

## Write disposition (D6)

Set per resource, never per run: `append` for immutable events that arrive once, `replace` for a full reload of a fixed window, `merge` for mutable records with a key. Every resource here is `replace`: each run reloads the whole fixed window.

## Schema contract (D7)

`columns: freeze`, `tables: evolve`, `data_type: freeze`. `tables` stays `evolve` because an Intent's prefixed schemas in the Ephemeral catalog start empty, so freezing it would forbid creating the tables in a sample load. Any other value carries a `# why:` line in the pipeline and a decision in its design record.

## Merge keys (D6b)

A resource that moves to `merge` deduplicates its source on the merge key first and records how in its design record. Do not rely on the destination to settle a repeated key.

## Bronze carries no logic (D8)

No transformation, casts, joins or filters in a pipeline. A pipeline loads what the source gives it. Simulated sources generate their data, but do not clean it.

## `_dlt_*` columns (D8b)

Never drop or alias them.

## Column names

dlt lands every column name in lower case on Databricks: `VendorID` lands as `vendorid`. Spark SQL resolves identifiers case-insensitively, so SQL may keep the source's spelling, but YAML that names a bronze column (resource docs, `_sources.yml` columns, tests) uses the landed lower-case name.

## Sample loads (D10)

A safety run or sample load passes `--limit <N>` to the plugin's `run_notebook.py`, which requires it and sets the notebook's `dlt_ingest_limit` widget; a full load passes `--limit -1`. No committed limit: the widget and the job task keep `-1`.

In an intent, every run while the pipeline is being written is a sample load. A full load runs at most once, after the pipeline and its docs are final, and only when the requirement asks for loaded data. A change after the full load gets a sample load to prove it, not a second full load.

Prove `replace` with two sample loads, not two full loads: run the sample load twice with the same `--limit`; the table then holds the limit's row count and one load package. Verify cites that evidence and never re-runs a full load to prove it again.

## Local-files feeds (D14)

A local-files feed is a one-off load and is not scheduled. Not applicable until this repo has one.

## Profiling a remote file (D16)

Profile a remote source file once per intent: row count, columns and types, null counts, value ranges and anything else the design or resource docs need. Save the results to `.agents_tmp/<source>-profile.json` with the file URL and the time read, and take every later figure (design record, resource docs, verify) from that file. Read the remote file again only if the profile is missing or the URL changed.

## Adding a source

- A new source mirrors an existing entry in `repo-map.json` `sources`: create every artifact it lists (module, config section, pipeline, resource docs, tests, design record). Mirror `tlc` for a downloaded file source.
- Mirror `tlc.py` for a large file: it yields one pyarrow table per monthly Parquet file, which is proven on three months of TLC data.
- Sources are custom modules under `ingestion/sources/`, registered as `[sources.<name>]` with `connector = "custom"` and `connector_source = "local"`. The connector catalog is not used.
- The pipeline is a Databricks notebook, `ingestion/<name>_pipeline.ipynb`, from the plugin's `databricks/templates/dlt-pipeline.ipynb` (`databricks/dlt.md` § Authoring), never a `<name>_pipeline.py` script. Its destination is `databricks_files_api()`, exactly as the template builds it; the notebook names no host, catalog, warehouse, schema or secret.
- Then add a notebook task for it to `orchestration/nyc_taxi_refresh.job.yml`, ahead of the dbt task (the plugin's `databricks/orchestration.md` § Authoring), run `validate-job.py` until it exits 0, and add the source to `repo-map.json` and `test-map.json`.
- `tests/test_maps.py` fails when a source's listed paths or its config section are missing.
- To see whether a source exists, read `repo-map.json` `sources`; query the catalog with `lakehouse_query` only for data questions.

## Adding a resource to an existing source

Another table from a source that is already loaded (for example another TLC trip file) is a resource on that source, not a new source:

- Add it to the source module's resources, and a `resources.<name>` block to the source's resource docs (`ingestion/docs/<source>.yml`). Each source column there has exactly one of `source_ref` or `source_fields`, and each `_dlt_` control column has only its fixed description; `tests/ingestion/test_docs.py` checks both.
- Extend the source's tests, its pipeline design record, `_sources.yml` and a new `stg_` model.
