# VD-7386 Databricks seed (2026-10-28)

The Domain's first release: the `nyc_taxi_refresh` bundle job deployed to `prod` and run once, which loads Q1 2024 and builds every model in `nyctaxi_prod`; the production manifest; a driving user's grants, checked with a principal that holds only those grants; and parity with the DuckDB Q1 reference.

**Estate:** workspace `uk-vd-spike-dbx`, SQL warehouse `nyctaxi-wh` (serverless 2X-Small), Domain catalog `nyctaxi_prod` (empty before the run), Ephemeral catalog `nyctaxi_ephm`.

**Tools:** Databricks CLI 1.21.0; serverless environment 4; dbt-core 1.12.5 + dbt-databricks 1.12.6 in the job; dlt 1.30.0; domain-cicd `22f9069` (`domain-ci-databricks-bundle`); plugin vde `fix/vd-7442-vd-7466-…` (`run_notebook.py`); DuckDB repo `87e4904` for the reference.

**The notebook package.** Runs 1 to 3 were made before vibedata-dlt-databricks-notebook 0.2.1 (VD-7465) was published, while `.github/managed-constraints.txt` pinned 0.1.0, which cannot load. They ran from a copy of this repository whose only differences were the pin at 0.2.1 and a `--find-links` line in `ingestion/requirements.txt` naming a locally built 0.2.1 wheel uploaded with the bundle, as in [VD-7385 runs R5](2026-10-28-vd-7385-databricks-runs.md#r5-rerun-with-the-plugin-fixes). Run 4 was deployed from a clean checkout of `eb993b5`, which pins 0.2.1 from PyPI (`release-2026-10-28-d`).

## S1 Release and run

`databricks bundle deploy -t prod` with `catalog=nyctaxi_prod`, `schema=main` and the warehouse id, then `databricks bundle run -t prod nyc_taxi_refresh`, from the repository root, as the deploying user (`mode: production`).

| Run | Tasks | Result |
| --- | --- | --- |
| 1 | `dlt_tlc_pipeline` 213 s, `dlt_ops_pipeline` 208 s, `dlt_mdm_pipeline` 203 s: SUCCESS. `dbt`: FAILED | `Could not find profile named 'dbt_databricks'` |
| 2 | `dlt_tlc_pipeline` 185 s, `dlt_ops_pipeline` 170 s, `dlt_mdm_pipeline` 147 s, then `dbt` 237 s: SUCCESS | `dbt build`: `PASS=219 WARN=0 ERROR=0 SKIP=0`; the run took 424 s |
| 3 | the same job again, unchanged: every task SUCCESS, 408 s | `PASS=219`; `core.fct_trip` still 9,722,362 rows, 9,722,362 distinct `trip_key`: repeating a seed with the same window adds nothing |
| 4 | deployed from a clean checkout of `eb993b5` (the committed repository, 0.2.1 from PyPI): `dlt_tlc_pipeline` 200 s, `dlt_ops_pipeline` 186 s, `dlt_mdm_pipeline` 170 s, then `dbt` 243 s: SUCCESS, 444 s | `PASS=219`; the deploy removed the copy's wheel folder, and the deployed `requirements.txt` has no `--find-links`; `core.fct_trip` 9,722,362 rows, all distinct |

- **Run 1's dbt task.** `dbt_project.yml` named its profile `"{{ env_var('DBT_PROFILE_NAME', 'dbt_databricks') }}"`, inherited from the Lakehouse repo. The job's dbt task writes its own profiles directory and could not find `dbt_databricks` in it. Run 2 changed only that line, to `profile: dbt_databricks`, which the repo now commits. Studio exports `DBT_PROFILE_NAME=dbt_databricks` to a Databricks Intent, the same name.
- **Where the loads landed.** Each notebook wrote to `nyctaxi_prod` through the job's default `dlt_env` (VD-7442): `bronze`, `ops_raw` and `mdm_raw`. dbt wrote `staging`, `intermediate`, `core`, `agg`, `finance`, `ops`, `seeds` and `main`.
- **Counts.** `core.fct_trip` and `intermediate.int_trips_conformed` hold 9,722,362 rows, `bronze.yellow_tripdata` 9,554,778 and `bronze.green_tripdata` 167,585: the DuckDB repo's full Q1 figures.

Run 4 is the job's run proof (DBX-D11): the committed repository, deployed and run as it stands.

The same checkout's `mdm_pipeline.ipynb`, unchanged from the template, also loaded as an Intent's sandbox run on 0.2.1 from PyPI: the plugin's `run_notebook.py` (vde `integration/nyctaxi-databricks`) with `--limit 1 --dev-mode`, TERMINATED SUCCESS, `destination-identity` `nyctaxi_ephm`. Its dev-mode schema and synced folder were deleted afterwards.

## S2 The production manifest

`publish-prod-manifest-databricks.yml` runs on a push to `main`, where it is not yet, so its steps ran from a workstation at `e8c4ff2` (this branch, pushed), in a virtualenv holding only `dbt-core` and `dbt-databricks` under the managed constraints, as the workflow installs them. The provenance step refuses a second adapter (`ambiguous dbt adapter: … ['dbt-databricks', 'dbt-duckdb']`).

- `ci_config_runner.py prod-db-name`: `PROD_DB_NAME=nyctaxi_prod`, `PROD_SCHEMA_NAME=main`.
- `dbt parse` and `dbt docs generate --static` with the offline `dbt_databricks_compile` profile.
- `publish_manifest_release.py` created `dbt-manifest-e8c4ff2…`; `publish_dbt_docs_release.py` created `dbt-docs-latest` with `manifest.json`, `manifest-source.json` and `static_index.html`. That is the release Studio stages into an Intent's `/cache/prod-target`.
- The published manifest's adapter is `databricks`, and every one of its 88 relations is in `nyctaxi_prod` (`` `nyctaxi_prod`.`core`.`fct_trip` ``). They are the same relation names as the manifest S3's deferred build used.
- `manifest-source.json`: `build_sha` `e8c4ff2…`, dbt 1.12.5, dbt-databricks 1.12.6.

The clone carried four tags from the Lakehouse repo (`dbt-docs-latest` and three `dbt-manifest-*`), and `gh release create` refused to create a release over the local `dbt-docs-latest` tag. Deleting the local tags cleared it; this repository's remote had none.

## S3 A driving user's grants

No Studio Intent can run on this Domain yet (Studio's vde pin, `skill-changes.md`), so a service principal, `nyctaxi-vd7386-intent-user`, stood in for the driving user. It held exactly what Studio's Databricks design gives a user (Studio `docs/proposals/databricks/permissions.md` §3 and §6, `databricks-ephemeral-grant.ts`):

- `USE CATALOG`, `USE SCHEMA`, `SELECT` on `nyctaxi_prod`; `USE CATALOG`, `CREATE SCHEMA` on `nyctaxi_ephm`; `CAN_USE` on the warehouse.
- On the Intent's mirror `<prefix>main` and its `<prefix>main_staging`, created by the owner as Studio's service principal creates them (with the `_vd_dlt_staging` volume), Studio's own two `GRANT` statements.

Intent `vd7386`, prefix `ephm__nyc_taxi_databricks__vd7386__`. A second schema, `ephm__nyc_taxi_databricks__vd7386other__main` with one table, stood for another Intent.

| As the user | Result |
| --- | --- |
| `select` from `nyctaxi_prod.core.fct_trip` and `nyctaxi_prod.bronze.yellow_tripdata` | succeeded (9,722,362 and 9,554,778) |
| `create table` in `nyctaxi_prod.main` | refused: no `CREATE TABLE` on the schema |
| `create schema` in `nyctaxi_prod` | refused: no `CREATE SCHEMA` on the catalog |
| `delete from nyctaxi_prod.seeds.fare_bands` | refused: no `MODIFY` |
| `drop table nyctaxi_prod.core.dim_zone` | refused: no `MANAGE` |
| create and drop a table in the mirror | succeeded |
| create `<prefix>probe`, a table in it, and drop it | succeeded |
| read, insert into, or drop the other Intent's schema | refused |
| `show schemas in nyctaxi_ephm` | the user's two schemas only |

So a principal holding the grants Studio's design gives a driving user can read production and change nothing there, and can create schemas in `nyctaxi_ephm`, own them and see nothing else there. That the grants were applied by hand, not by Studio, is the limit of this check: Studio's own grant code runs on its first Intent (VD-7387).

**An Intent's build, as that user.** dbt in Studio's sandbox shape (`dbt_databricks`, target `databricks_sandbox` on `nyctaxi_ephm` and the mirror, `VD_EPHM_SCHEMA_PREFIX`, `VD_DOMAIN_DATABRICKS_CATALOG=nyctaxi_prod`), signed in as the user, with `--defer --state` on the production manifest:

- `dbt build --select mart_daily_zone_revenue`: `PASS=4`. The user created `<prefix>finance` (its `CREATE SCHEMA`) and built the mart there, reading `nyctaxi_prod.core.fct_trip` and `nyctaxi_prod.core.dim_zone` through the deferred refs.
- The Intent's mart and the Domain's have the same 20,770 rows on (`trip_date`, `pickup_location_id`), with equal counts and labels; the revenue sums differ by at most 3.6e-9, the order a `double` sum is added in.

**An Intent's load, as that user.** The plugin's `run_notebook.py --notebook ingestion/mdm_pipeline.ipynb --limit 1000`, with the CLI signed in as the user and the Intent context as [VD-7385 runs](2026-10-28-vd-7385-databricks-runs.md) gave it: TERMINATED SUCCESS, `destination-identity` `nyctaxi_ephm`. dlt created `<prefix>mdm_raw`, which the user owns, and loaded its ten tables there.

## S4 Parity with DuckDB

`docs/setup/parity.py` (as committed with this record) against a DuckDB build of the same three months, after run 3: **88 tables checked, 0 differences, 3 known, 0 stale.** For each table it compares the row count, the column type families, every column's non-null count, every text and time column's distinct count and minimum and maximum (times as UTC text, a date as its midnight), and every numeric sum. A known difference is matched by its exact line, so any drift in it fails the run.

| Known difference | Cause |
| --- | --- |
| `intermediate.int_zone_attributes.poi_categories`, `core.dim_zone.poi_categories`: 59 distinct values in DuckDB, 54 here | DuckDB's `string_agg(distinct …)` has no order; this repo sorts the set. Sorting the reference's lists gives the same 54 (VD-7201). |
| `agg.agg_trip_zone_daily.revenue_rank_that_day`: sum 2,382,195 in DuckDB, 2,382,193 here | This repo ranks revenue rounded to the cent, because summed doubles differ in their last bits between engines. Ranking the reference at the cent gives 2,382,193. |

Everything else matches, `fct_trip` included. Before times were compared as UTC text, 38 lines differed only in rendering: DuckDB printed timestamps in the workstation's +07 zone and Databricks in UTC, and dlt landed some dates as `DATE` on Databricks and as midnight-UTC timestamps in DuckDB. As UTC text, every one of them matched.

**The reference.** The DuckDB model-answer repo at `87e4904` with its ops fix (as the Redshift parity used), `seed_domain_duckdb.py`'s load of 2024-01 to 2024-03, then `dbt build`. A Q1 build does not fit this 9 GB workstation as committed, so the throwaway copy that built it changed how, not what:

- the DuckDB profile capped at 5.5 GB with one dbt thread;
- `int_trips_conformed`, `int_trips_enriched`, `int_trip_fare_components` and `int_trip_quality_flags` as tables rather than views (this repo builds them as tables);
- `fct_trip`, which is incremental, loaded a month at a time (pickups before February, then before March, then the rest), the quality and fare-component rows narrowed to the same trips.

The finished file then passed a full `dbt build`: `PASS=219`, 5.7 GB peak.

## Cleanup

The seeded Domain and the deployed `nyc_taxi_refresh` job stay: they are what this ticket delivers. Everything S3 made is gone: the Intent's schemas and the other Intent's, the stand-in principal's grants on both catalogs and the warehouse, and the principal itself. `nyctaxi_ephm` holds only `default` and `information_schema`. Its workspace home folder is protected, so Databricks keeps it for a deleted principal.
