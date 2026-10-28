# VD-7384 Databricks probe (2026-10-28)

What the Databricks port's decisions rest on. Each probe states its setup, what ran and what came back.

**Estate:** Azure Databricks workspace `uk-vd-spike-dbx` (Unity Catalog metastore `metastore_azure_eastus`), serverless SQL warehouse `nyctaxi-wh` (2X-Small). Two catalogs made for this port:
- `nyctaxi_prod`, standing in for the Domain: schema `bronze` with a 3-row table `zones` and a view `v_zones`.
- `nyctaxi_ephm`, standing in for the Domain's shared Ephemeral catalog, with an Intent's mirror schema named the way Studio names it (`databricks-mirror-names.ts`): prefix `ephm__nyc_taxi_databricks__probe__`, mirror `ephm__nyc_taxi_databricks__probe__main`.

Every probe ran as one user who owns both catalogs. Studio's driving user holds only `SELECT` on production and create-only rights on the Ephemeral catalog (Studio `databricks-dbt-profiles.yml`, plugin `dbt.md` § Schema resolution), so a write the probes made to production says nothing about what an Intent can do. All probe objects were dropped afterwards; both catalogs hold only `default` and `information_schema`.

**Tools:** dbt-core 1.12.5, dbt-databricks 1.12.6, dbt-duckdb 1.11.0, dlt 1.30.0, sqlfluff 4.4.0, `dbt_project_evaluator` 1.x, vibedata-dlt-databricks-notebook 0.1.0 (the plugin's managed constraints). Plugin read at vde `origin/main` `5ec5dbe5f`. Macros: the plugin's `_family/shared-container/templates/{source_defer,generate_schema_name}.sql`, copied unchanged.

## P1 How a sandbox reads the Domain

dbt profile in Studio's shape: `dbt_databricks`, target `databricks_sandbox`, catalog `nyctaxi_ephm`, schema the mirror. A `prod` target (catalog `nyctaxi_prod`, schema `main`) built the same project first, and its `target/manifest.json` became the defer state. The source names `database: nyctaxi_prod`, `schema: bronze`.

| Step | Result |
| --- | --- |
| `dbt compile -s stg_zones` with the prefix set and no sandbox copy | `` from `nyctaxi_prod`.`bronze`.`zones` `` |
| `dbt build` of a view and a table over that source in the sandbox | both OK, in the mirror schema |
| after creating `nyctaxi_ephm.<prefix>bronze.zones`, compile again | `` from `nyctaxi_ephm`.`<prefix>bronze`.`zones` `` |
| `dbt build -s mart_zone_count --defer --state prod-state` (its parent `dim_zone` not built in the sandbox) | OK; compiled `` from `nyctaxi_prod`.`main`.`dim_zone` `` |
| the same build without `--defer` | `TABLE_OR_VIEW_NOT_FOUND`: `` `nyctaxi_ephm`.`<mirror>`.`dim_zone` `` |
| a model with `+schema: agg` | built in `<prefix>agg` |
| a unit test on a model that reads `source()` | PASS |
| a `merge` incremental with `unique_key` and `liquid_clustered_by`, run twice | OK both runs; Delta, with clustering columns |
| a `delete+insert` incremental with `unique_key` (`fct_trip`'s strategy), run twice | OK both runs; 3 rows, 3 distinct keys |

- A view over a production source builds and reads in the Ephemeral catalog; nothing like the Lakehouse SQL endpoint's refusal of Spark views applies.
- The shared `source()` template needs no unit-test guard here: `adapter.get_relation` with the unit test's relation returns nothing, and the test passes. (Redshift's override needed one.)

## P2 Dev-schema cleanup never touches the Domain

The plugin's own `drop_dev_mode_schemas.py` and `platforms/databricks.py`, with only `_connect` replaced so a workstation can authenticate through the CLI profile instead of Studio's metadata service. Setup: dev-mode copies `<prefix>bronze_20261028100000` (with a table), `<prefix>bronze_20261028100000_staging` and `<prefix>bronze_20261028110000` in `nyctaxi_ephm`, and a decoy `<prefix>bronze_20261028100000` with a table in `nyctaxi_prod`.

- Target catalog `nyctaxi_ephm`; physical dataset `<prefix>bronze` (`cleanup_dataset`).
- Dropped: the three `nyctaxi_ephm` schemas. Kept: `<prefix>bronze`, the mirror and `<prefix>agg` in `nyctaxi_ephm`, and the decoy in `nyctaxi_prod`.
- The listing is the session catalog's `information_schema.schemata` filtered on the catalog, and each drop is qualified by it (`drop_schemas`), so a production schema of the same name is never listed.

## P3 Bronze preview reads the pipeline's dataset

The plugin's `platforms/databricks.py` `preview()`, same connection swap. It listed every table under the Intent's prefix: `<prefix>bronze.zones`, and also the dbt-built `<prefix>main.*` and `<prefix>agg.custom_schema_model`. It reads the pipeline's dataset (the VD-7121 class does not apply), and it also shows dbt models when the Intent has built any, as plugin `dlt.md` § Bronze preview says ("every table in the Ephemeral catalog's schemas that start with the Intent's prefix").

## P4 sqlfluff dialect

No CI bundle chooses one: `domain-ci-databricks-bundle` publishes the production manifest and runs no PR gates. Lint ran with the jinja templater, `apply_dbt_builtins`, and every project macro except `source_defer.sql` (it calls dbt's `builtins`, which the jinja templater lacks), over the 64 current models:

| Dialect | Parse errors | Other hits |
| --- | --- | --- |
| `sparksql` | 0 | 1 `LT02` |
| `databricks` | 0 | 1 `LT02` |

## P5 The project evaluator on dbt-duckdb

In a copy of the repo: the plugin's two macros, and `config(file_format='delta', liquid_clustered_by=[...], tblproperties={...})` on a mart. Then the repo's own quality workflow steps on dbt-duckdb (`.github/profiles/dbt-quality`): `dbt deps`, `dbt parse`, and `dbt build --select dbt_project_evaluator --vars '{dbt_project_evaluator_enabled: true}'`. Parse OK; build `PASS=66 WARN=12 ERROR=0`. The Databricks-only configs and the sandbox macros do not break the evaluator.

## P6 Committed config cannot point an Intent's dlt load at the Domain

The plugin's `templates/dlt-config.toml` commits `[destination.databricks.credentials]` with the production `catalog` and `http_path`; a sandbox run overrides both through the notebook's `dlt_env` widget, which the notebook copies into `os.environ` before it builds the pipeline (`templates/dlt-pipeline.ipynb`). One-row loads, host and token from the environment:

| `ingestion/.dlt/config.toml` | Environment | Destination | Result |
| --- | --- | --- | --- |
| template's `[…credentials]` with `catalog = "nyctaxi_prod"` | `CATALOG=nyctaxi_ephm`, `HTTP_PATH` | dlt `databricks` | `ValueNotSecretException`: ``Provider `config.toml` cannot hold secret values but key `destination.databricks.credentials` with secret value is present`` |
| the same | only `CATALOG` | dlt `databricks` | the same exception |
| no credentials section | `CATALOG=nyctaxi_ephm`, `HTTP_PATH` | dlt `databricks` | loaded; `current_catalog()` = `nyctaxi_ephm` |
| any of the above | any | `databricks_files_api()` | `ConfigFieldMissingException`: credentials tried only from explicit values, which Databricks compute supplies inside a notebook |

- The environment wins over the file for every key it sets, so a sandbox run cannot land in the catalog the file names.
- dlt 1.30's resolver refuses the template's credentials section in `config.toml`, with or without an override. `databricks_files_api` is dlt's destination with a different upload, so it should hit the same check on compute; off compute it cannot be run at all. **Unconfirmed on compute: the first live notebook run in VD-7385 settles it.**

## P7 Macros and dialect on Databricks

Rendered with `dbt show --inline` on the sandbox target, the repo's own macros:

| Expression | Result |
| --- | --- |
| `current_timezone()` | `Etc/UTC` |
| `utc_date(timestamp '2024-01-15 00:00:00')` | `2024-01-15` |
| `7/3600` | `0.0019444444444444444` (`/` is always fractional) |
| `safe_divide('7', '3600e0')`, `safe_divide('1', '0')` | `0.0019…`, `null` |
| `trip_natural_key(...)` | a 32-character md5 |
| `cast(timestamp '2024-01-01 00:05:07.120' as string)` | `2024-01-01 00:05:07.12` (trailing zeros trimmed) |
| `cast(cast(3.10 as double) as string)` | `3.1` |
| `in_report_window(timestamp '2024-01-10')` | `true` |

What dlt 1.30 lands on Databricks (`schema.naming = "direct"`), from one row:

| Python value | Column type |
| --- | --- |
| `int` | `bigint` |
| `datetime.date` | `date` |
| `datetime` (naive and UTC) | `timestamp` |
| `float` | `double` |
| `bool` | `boolean` |

The repo's generators: `ops` builds its dates as `DATE '2012-01-01' + INTERVAL (…) DAY` (`ingestion/sources/ops.py`), and DuckDB 1.x types that expression `TIMESTAMP` (`DATE + 3` stays `DATE`), so those columns reach dlt as timestamps and land as timestamps at UTC midnight. `mdm` yields literal `DATE`s, which land as `date`.

A key named `VendorID` landed as the column `vendorid`: dlt folds identifiers to lower case on Databricks. Spark SQL resolves identifiers case-insensitively, so `VendorID` in a model still reads it.
