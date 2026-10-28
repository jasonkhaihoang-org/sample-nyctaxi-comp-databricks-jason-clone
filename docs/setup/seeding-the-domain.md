# Seeding the Studio Domain

Repo maintenance. Build agents do not read this document.

A Studio Intent builds only the models it changes. Every other `ref()` defers to the Domain's released models (`--defer --state /cache/prod-target`), and a source the Intent has not loaded reads the Domain's table (`macros/source_defer.sql`). A Domain with no released model gives an Intent nothing to defer to, so seed the Domain before creating it in Studio.

Seeding a Databricks Domain is a release, one run, and a manifest publish:

1. The **release** is `databricks bundle deploy -t prod`. It uploads the repository to the deploying user's workspace folder and creates or updates the `nyc_taxi_refresh` job.
2. **One run of `nyc_taxi_refresh`** loads every source (`tlc`, `ops` and `mdm` in parallel) into the Domain catalog and then runs `dbt deps` and `dbt build` on the Domain's catalog and Primary Schema. The Domain then holds the full Q1 2024 window.
3. The **manifest publish** is the CI bundle's `publish-prod-manifest-databricks.yml`. It parses the project offline for the production catalog and schema, and publishes `manifest.json` on the `dbt-docs-latest` GitHub release. Studio stages that manifest into an Intent's `/cache/prod-target` on Open.

## Create the Domain's Databricks resources

You need a Unity Catalog workspace and an identity that can create catalogs and SQL warehouses in it.

1. Create the production catalog (this repo's is `nyctaxi_prod`). The jobs write managed tables, so the catalog needs managed storage. A metastore without a storage root refuses `databricks catalogs create`, but a `CREATE CATALOG nyctaxi_prod` statement run on a SQL warehouse uses the workspace's default storage.
2. Create a SQL warehouse for the Domain. This repo's is a serverless 2X-Small with a 10-minute auto-stop.
3. Write the Domain's coordinates where the plugin reads them, and nowhere else:
   - `transformation/profiles.yml`, `prod` target: `catalog` and `schema` (the Primary Schema, `main`).
   - `.workflow/ci-config.yml`: the slug, `VD_DOMAIN_DATABRICKS_CATALOG` and `VD_DOMAIN_DATABRICKS_PRIMARY_SCHEMA`.

The workspace host and the warehouse id are never committed. The release takes them from the Databricks CLI profile and the `warehouse_id` variable.

## Release and run

From the repository root, with a Databricks CLI profile for the workspace (`databricks auth login`):

```bash
VARS="--var catalog=nyctaxi_prod --var schema=main --var warehouse_id=<warehouse id>"
databricks bundle deploy -t prod -p <profile> $VARS
databricks bundle run -t prod -p <profile> $VARS nyc_taxi_refresh
```

**How the job writes to the Domain catalog.** Each pipeline notebook writes to the catalog and warehouse in its `dlt_env` parameter, and `databricks.yml` defaults that to the job's own `catalog` and `warehouse_id`. The dbt task writes to the same catalog and schema. The run is made as the deploying user (`mode: production`).

**The notebook package.** The pipeline notebooks need `vibedata-dlt-databricks-notebook` 0.2.1 or later (VD-7465), which `.github/managed-constraints.txt` pins; 0.1.0 and 0.2.0 fail every load at its first step.

**Re-running.** The loads replace every bronze table (`replace`), and the build rebuilds every model except `fct_trip`. `fct_trip` is incremental: it adds only trips picked up after the latest one it holds.
- Repeating a seed with the same window is safe: the release's third run repeated the second (seed S1).
- Seeding a Domain whose `fct_trip` was built from a different window is not. The Lakehouse Domain this repo was ported from failed `assert_fct_trip_matches_conformed_rowcount` that way, because TLC files carry trips dated before the watermark; this Domain has not been seeded with another window. After that run has loaded, rebuild `fct_trip` and everything downstream of it from `transformation/`, against the `prod` target: `dbt build --full-refresh --select fct_trip+ --target prod`. The `prod` target reads the host, warehouse path and token from `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH` and `DATABRICKS_TOKEN`.

## Publish the manifest

On a push to `main`, `publish-prod-manifest-databricks.yml` publishes the manifest. Run it by hand with **Actions → Publish Prod Manifest (Databricks) → Run workflow** once the workflow is on `main`. It opens no Databricks connection and needs no secret beyond the workflow's own `GITHUB_TOKEN`.

The workflow's steps also run from a workstation, at a commit that is on GitHub. From the repository root, with `gh auth login` done, in a virtualenv that holds only the workflow's packages (the provenance step refuses a second dbt adapter):

```bash
python3 -m venv /tmp/publish && /tmp/publish/bin/pip install -c .github/managed-constraints.txt dbt-core dbt-databricks pyyaml
export PATH=/tmp/publish/bin:$PATH PROD_DB_NAME=nyctaxi_prod PROD_SCHEMA_NAME=main GH_TOKEN=$(gh auth token)
dbt deps --project-dir transformation
dbt parse --project-dir transformation --profiles-dir .github/profiles --profile dbt_databricks_compile --target compile
dbt docs generate --project-dir transformation --profiles-dir .github/profiles --profile dbt_databricks_compile --target compile --static --empty-catalog --no-compile
PYTHONPATH=.github/scripts python3 .github/scripts/publish_manifest_release.py transformation/target "$(git rev-parse HEAD)" manifest.json
PYTHONPATH=.github/scripts python3 .github/scripts/publish_dbt_docs_release.py transformation/target static_index.html manifest.json manifest-source.json
```

A clone made from another model-answer repo carries its release tags; `gh release create` refuses a tag that exists only locally, so delete those first (`git tag -l 'dbt-*'`).

## What it costs

Measured on 2026-10-28 on a serverless 2X-Small SQL warehouse and serverless job compute (environment 4), for Q1 2024:

| Step | Time |
| --- | --- |
| `bundle deploy`: about 320 files | under 1 min |
| `nyc_taxi_refresh`: `tlc`, `ops` and `mdm` in parallel, 2.5 to 3 min each; then `dbt build`, 219 nodes, 4 min | about 7 min |

Serverless compute is billed per DBU while the tasks run, and the warehouse stops after 10 idle minutes.

## Check the seed

- `intermediate.int_trips_conformed` and `core.fct_trip` hold 9,722,362 rows, `bronze.yellow_tripdata` 9,554,778 and `bronze.green_tripdata` 167,585: the DuckDB repo's full Q1 figures.
- `docs/setup/parity.py` compares every table in the Domain catalog with a DuckDB build of the same three months: row counts, column types, non-null counts, the distinct count and range of every text and time column, and numeric sums. It exits non-zero on a difference it does not list as known, and on a known one that no longer appears:

```bash
python3 docs/setup/parity.py <reference.duckdb> --profile <profile> --warehouse-id <warehouse id> --catalog nyctaxi_prod
```

  Build the reference from the DuckDB model-answer repo with `docs/setup/seed_domain_duckdb.py --months 2024-01 2024-02 2024-03`. As committed, that build does not fit a 9 GB workstation: [the seed record](../verify/2026-10-28-vd-7386-databricks-seed.md#s4-parity-with-duckdb) lists what the copy that built the 2026-10-28 reference changed. The script lists its known differences with their causes.

## Limits

- `ops` and `mdm` are generated from the TLC window the run loads. The window is `[sources.tlc] months` (default 2024-01 to 2024-03).
- The Domain's coordinates are committed, so a second Domain from this repo means editing both files above, not copying the repository unchanged.
