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

dlt lands timestamps as UTC instants, and Spark shows a timestamp in the session time zone, which is not always UTC. Staging converts every dlt-loaded timestamp with `to_utc_timestamp(col, current_timezone())`, so later models see the wall-clock value the source recorded. Some source dates land as timestamps at UTC midnight (the ops generator's hire, lease, maintenance and vehicle dates): staging turns each back into the calendar date with the `utc_date()` macro. Use it only on a timestamp; a column that already lands as a date needs nothing. A model that reads bronze without the conversion, or hashes a key from a converted and an unconverted timestamp, matches nothing and stays green.

## Division by a constant (B17b)

Divide by a double literal: `seconds / 3600e0`, not `seconds / 3600.0`. In Spark `3600.0` is a decimal, so the quotient is a decimal rounded to six places; a ratio or rank built on it disagrees with the unrounded value.

## Sources name no database (B18)

A source in `_sources.yml` names its `schema` and tables, never a `database`, and no var feeds either. In a Studio Intent `macros/source_defer.sql` resolves a source in the Intent's Ephemeral Lakehouse and, under `--defer`, falls back to the Domain's; a source that names a database is pinned to one Lakehouse and breaks that fallback.

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

Every model is a table, never a view: the Lakehouse SQL analytics endpoint cannot read a Spark view, so a view is invisible to anyone querying the Lakehouse over SQL.

`fct_trip` is incremental by `trip_key` with no `on_schema_change`; a late-arriving trip at or before the loaded boundary, or a new or changed column upstream of it, needs `dbt build --full-refresh --select fct_trip` (see its design record).
