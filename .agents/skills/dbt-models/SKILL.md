---
name: dbt-models
description: "Use when creating, renaming or editing a dbt model, its properties file or its materialisation in transformation/."
---

# dbt models

Operator conventions for dbt models in `transformation/`. Where files live is declared in `repo-map.json`; this file covers naming and shape.

## Medallion mapping (B1)

- **Bronze**: raw data loaded by the dlt pipelines in `ingestion/` (schemas `bronze`, `ops_raw`, `mdm_raw`). dbt reads it as sources and never writes to it.
- **Silver**: dbt `staging` and `intermediate` (tables). Staging renames and casts one source table. Intermediate applies business logic and joins, with no grain commitment of its own.
- **Gold**: dbt marts (`core`, `agg`, `finance`, `ops`): grain-committed facts, conformed dimensions, aggregates.

## Time zones (B17)

dlt lands timestamps as UTC `timestamp`, and Spark shows a timestamp in the session time zone; the SQL warehouse's session zone is UTC ([probe](../../../docs/verify/2026-10-28-vd-7384-databricks-probe.md) P7). Staging still converts every dlt-loaded timestamp with `to_utc_timestamp(col, current_timezone())`, so later models see the wall-clock value the source recorded whatever the session's zone. A source date lands as whatever type the source yields (P7): a `DATE` from the source (TLC, `mdm`) lands as `date`, but the `ops` generator's `DATE + INTERVAL` dates are DuckDB `TIMESTAMP`s and land as a timestamp at UTC midnight. Staging casts a `date` column with `cast(col as date)`, and a midnight timestamp with `utc_date()`, which keeps the calendar day the source recorded whatever the session's zone.

## Division by a constant (B17b)

Divide by a double literal: `seconds / 3600e0`, not `seconds / 3600.0`. In Spark `3600.0` is a decimal, so the quotient is a decimal rounded to six places; a ratio or rank built on it disagrees with the unrounded value.

## Sources name the Domain catalog (B18)

A source in `_sources.yml` names its `schema`, its tables and, as `database`, `"{{ env_var('VD_DOMAIN_DATABRICKS_CATALOG', target.database) }}"`: in an Intent that is the Domain's catalog, and in a release the `prod` target's. Never write a catalog name into the file. `macros/source_defer.sql`, the plugin's shared template, reads the Intent's own table (`<VD_EPHM_SCHEMA_PREFIX><schema>` in the Ephemeral catalog) when this Intent loaded it, and the Domain's table the source names otherwise (the plugin's `databricks/dbt.md` § Source reads). Without the `database` a sandbox source reads the Ephemeral catalog only. dbt's `--defer` covers `ref()`, never `source()`.

## Naming (B2, B3)

| Prefix | Layer | Responsibility |
| --- | --- | --- |
| `stg_` | staging | One source table: rename and cast only |
| `int_` | intermediate | Business logic and joins, no grain commitment |
| `fct_` | gold | Grain-committed events |
| `dim_` | gold | Descriptive entities, conformed across facts |
| `agg_` | gold | Aggregates built from facts |
| `mart_` | gold | Consumption-shaped marts |

- Staging models are `stg_<source>__<entity>` (B3; double underscore), for example `stg_tlc__yellow_tripdata`.
- Intermediate and gold models name the entity directly.
- No `_fact` or `_dimension` suffix: the prefix carries it.

## Properties files (B6)

One YAML file per folder, named `_<folder>.yml` (`_staging.yml`, `_intermediate.yml`, `_core.yml`). Unit tests sit in `_unit_tests.yml` beside the models they cover.

## Columns (B8)

List columns explicitly. No `select *` in a mart.

## Audit columns (B12)

None unless a requirement asks for them. When one does: gold only, all or none of `_loaded_at`, `_dbt_invocation_id`, `_git_sha`.

## Materialisation (B15)

| Layer | Default |
| --- | --- |
| staging | table |
| intermediate | table |
| gold | table |

Every model is a table, by choice: a view over a Domain source builds and reads in the Ephemeral catalog (P1), so nothing on Databricks forces a table, but one rule covers every layer.

Each layer sets its own `+schema:` in `dbt_project.yml`, and `macros/generate_schema_name.sql` (the plugin's shared template) lands it as `<VD_EPHM_SCHEMA_PREFIX><schema>` in a sandbox and as `<schema>` in the Domain. A new folder of models sets a `+schema:` too, so no model writes the Intent's mirror schema or the Domain's Primary Schema.

`fct_trip` is incremental by `trip_key` with no `on_schema_change`; a late-arriving trip at or before the loaded boundary, or a new or changed column upstream of it, needs `dbt build --full-refresh --select fct_trip` (see its design record).
