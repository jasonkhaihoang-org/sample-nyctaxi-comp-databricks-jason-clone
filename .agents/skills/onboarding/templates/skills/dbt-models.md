---
name: dbt-models
description: "Use when creating, renaming or editing a dbt model, its properties file or its materialisation in transformation/."
---

# dbt models
<!-- onboarding
ask: no
reason: Index text; sections below carry the decisions.
-->

Operator conventions for dbt models in `transformation/`. Where files live is declared in `repo-map.json`; this file covers naming and shape.

## Medallion mapping (B1)
<!-- onboarding
ask: yes
question: Which raw schemas, layers and mart areas?
recommended: The answer given for AGENTS.md "Medallion layers".
alternatives: as in AGENTS.md
fills: <raw schemas>, <mart areas>
-->

- **Bronze**: raw data loaded by the dlt pipelines in `ingestion/` into <raw schemas, one per source system>. dbt reads it as sources and never writes to it.
- **Silver**: dbt `staging` and `intermediate` (tables). Staging renames and casts one source table. Intermediate applies business logic and joins, with no grain commitment of its own.
- **Gold**: dbt marts in <mart areas, `core` first>: grain-committed facts, conformed dimensions, aggregates.

## Time zones (B17)
<!-- onboarding
ask: no
reason: the types dlt lands on Databricks; the same for every Databricks domain.
-->

dlt lands timestamps as `timestamp` in UTC, and a date as whatever type the source yields: a `DATE` as `date`, a date computed as a timestamp as a timestamp at UTC midnight. Staging carries every dlt-loaded timestamp as the wall-clock value the source recorded, so later models see that value; a sample load shows whether bronze already holds it, and this section names a conversion only if one is needed. Staging casts a `date` column with `cast(... as date)` and turns a midnight timestamp into its calendar day without letting the session's zone move it. A model that hashes a key from a converted and an unconverted timestamp matches nothing and stays green.

## Sources name the Domain catalog (B18)
<!-- onboarding
ask: no
reason: An Intent's target catalog is the Ephemeral one; the same for every Databricks domain.
-->

A source in `_sources.yml` names a literal `schema`, its tables and, as `database`, `"{{ env_var('VD_DOMAIN_DATABRICKS_CATALOG', target.database) }}"`: in an Intent that is the Domain's catalog, and in a release the `prod` target's. Never write a catalog name into the file, and no var feeds the schema or tables. In a Studio Intent the target catalog is the Domain's Ephemeral catalog, so a source without a `database` reads only that. `macros/source_defer.sql` reads the Intent's prefixed copy of a source (`<VD_EPHM_SCHEMA_PREFIX><schema>`) when the Intent loaded that table, and the Domain table the YAML names otherwise.

## Naming (B2, B3)
<!-- onboarding
ask: yes
question: How are models named?
recommended: Prefixes `stg_`, `int_`, `fct_`, `dim_`, `agg_`, `mart_`; staging `stg_<source>__<entity>`.
alternatives: suffixes instead of prefixes; a single underscore in staging names.
-->

| Prefix | Layer | Responsibility |
| --- | --- | --- |
| `stg_` | staging | One source table: rename and cast only |
| `int_` | intermediate | Business logic and joins, no grain commitment |
| `fct_` | gold | Grain-committed events |
| `dim_` | gold | Descriptive entities, conformed across facts |
| `agg_` | gold | Aggregates built from facts |
| `mart_` | gold | Consumption-shaped marts |

- Staging models are `stg_<source>__<entity>` (double underscore).
- Intermediate and gold models name the entity directly.
- No `_fact` or `_dimension` suffix: the prefix carries it.

## Properties files (B6)
<!-- onboarding
ask: yes
question: How are properties files organised?
recommended: One `_<folder>.yml` per folder; unit tests in `_unit_tests.yml` beside the models.
alternatives: one YAML file per model.
-->

One YAML file per folder, named `_<folder>.yml`. Unit tests sit in `_unit_tests.yml` beside the models they cover. Generic-test arguments go under `arguments:`.

YAML names a bronze column by its landed name. dlt folds column names to lower case on Databricks: `VendorID` lands as `vendorid`. Spark SQL resolves identifiers case-insensitively, so SQL may keep the source's casing.

## Columns (B8)
<!-- onboarding
ask: yes
question: May marts select every column?
recommended: No: marts list their columns.
alternatives: allow `select *` in marts.
-->

List columns explicitly. No `select *` in a mart.

## Audit columns (B12)
<!-- onboarding
ask: yes
question: Do models carry audit columns?
recommended: None unless a requirement asks; then gold only, all of `_loaded_at`, `_dbt_invocation_id`, `_git_sha`.
alternatives: audit columns on every gold model.
-->

None unless a requirement asks for them. When one does: gold only, all or none of `_loaded_at`, `_dbt_invocation_id`, `_git_sha`.

## Materialisation (B15)
<!-- onboarding
ask: yes
question: How is each layer materialised?
recommended: Every layer a table, so one rule covers the project.
alternatives: views where a layer gains nothing from a table (a view over a Domain source builds and reads in the Ephemeral catalog); incremental facts from the start.
-->

| Layer | Default |
| --- | --- |
| staging | table |
| intermediate | table |
| gold | table |
