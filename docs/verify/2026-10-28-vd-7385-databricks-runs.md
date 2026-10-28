# VD-7385 Databricks runs (2026-10-28)

The live runs behind VD-7385: each pipeline notebook loaded on serverless compute as an Intent's sandbox run, and the whole dbt project built in an Intent's shape. Setup, what ran and what came back.

**Estate:** workspace `uk-vd-spike-dbx`, SQL warehouse `nyctaxi-wh`, Ephemeral catalog `nyctaxi_ephm`, Domain catalog `nyctaxi_prod` (empty: the Domain is seeded in VD-7386). The Intent is named as Studio names one: prefix `ephm__nyc_taxi_databricks__vd7385__`, mirror schema `ephm__nyc_taxi_databricks__vd7385__main`, created first as Studio does at activation. Every run was as one user who owns both catalogs, so nothing here shows what an Intent's grants allow (VD-7386).

**Tools:** plugin vde `origin/main` `5ec5dbe5f` (`run_notebook.py`, `validate-job.py`, the templates), Databricks CLI 1.21.0, dbt-core 1.12.5 + dbt-databricks 1.12.6, dlt 1.30.0, vibedata-dlt-databricks-notebook 0.1.0 on serverless environment 4, the repo at `28c5ab1` plus this ticket's `config.toml`.

**How it ran from a workstation:** the plugin's own `run_notebook.py`, with only `load_intent_context` replaced by the four keys Studio would hand it (`VD_EPHM_DATABRICKS_CATALOG`, `VD_DOMAIN_DATABRICKS_HTTP_PATH`, `VD_EPHM_SCHEMA_PREFIX`, `DESTINATION__STAGING_DATASET_NAME_LAYOUT=%s_dlt_staging`), the CLI authenticating through a profile. No Studio Intent ran: Studio's vde pin predates the Databricks notebook work.

## R1 The template notebook cannot load (VD-7465)

`run_notebook.py --notebook ingestion/mdm_pipeline.ipynb --limit 1 --dev-mode`, the notebook exactly as the template builds it:

- From the repo root: exit 2, `RUN_NOT_STARTED: databricks current-user me: Error: please specify target`. The CLI loads the repo's `databricks.yml`, which has no default target by the plugin's rule, for every command (VD-7466). Every later run started from outside the repo, with absolute paths.
- From outside: the run started and failed, `INTERNAL_ERROR`: `ConfigFieldMissingException ... credentials ... tried (ExplicitValues, credentials)`.

The same, resolving the destination's configuration on a workstation with the catalog and warehouse in the environment:

| Destination | `config.toml` | Result |
| --- | --- | --- |
| `databricks_files_api()` 0.1.0 or 0.2.0 | none, or `keep_staged_files` only, or the template's credentials section | `ConfigFieldMissingException`, explicit values only |
| dlt's `databricks()` | none | resolved |
| `databricks_files_api()` with `__orig_base__ = databricks` | `keep_staged_files` only | resolved |
| the same | the template's credentials section | `ValueNotSecretException` (P6) |
| the same | `keep_staged_files` only, no catalog in the environment | `ConfigFieldMissingException`: `catalog` |

dlt reads a factory's argument defaults from `__orig_base__`, else the class's own `__init__`; `databricks_files_api.__init__` declares no `credentials`, so `credentials=None` stays an explicit value and no provider is consulted. The last two rows show, off compute, what VD-7442 turns on: the template's section is refused, and with none a run has no catalog unless something supplies it (`dlt_env`). No compute run used the template's section: it waits for VD-7465.

## R2 Loads, with the one-line fix

An uncommitted copy of the repo whose notebooks add `databricks_files_api.__orig_base__ = databricks` to the setup cell, and the committed `config.toml` (no credentials section):

| Run | Result | Evidence |
| --- | --- | --- |
| `mdm` safety run, `--limit 1 --dev-mode` | TERMINATED SUCCESS | `destination-identity: {"type": "dlt.destinations.databricks", "database": "nyctaxi_ephm"}`; loaded `<prefix>mdm_raw_20261028113737` |
| `tlc` full load, `--limit -1` | TERMINATED SUCCESS, same identity | `audit_runs`: `first_run` true, `total_rows_extracted` 9,722,628 = yellow 9,554,778 + green 167,585 + zones 265 |
| `ops` full load | TERMINATED SUCCESS, same identity | `audit_runs`: `first_run` true, 2,311,964 rows, 8 tables |
| `mdm` full load | TERMINATED SUCCESS, same identity | `audit_runs`: `first_run` true, 1,521 rows |

Each load landed in `<prefix><dataset>` (`bronze`, `ops_raw`, `mdm_raw`) in `nyctaxi_ephm`; nothing reached `nyctaxi_prod`.

## R3 dbt build in the Intent's shape

Studio's profile shape (`dbt_databricks`, target `databricks_sandbox`: catalog `nyctaxi_ephm`, schema the mirror), `VD_EPHM_SCHEMA_PREFIX` and `VD_DOMAIN_DATABRICKS_CATALOG=nyctaxi_prod` in the environment, and `--defer --state` against a production manifest made as the CI bundle makes it (`dbt parse` with domain-cicd's offline `dbt_databricks_compile` profile, `PROD_DB_NAME=nyctaxi_prod`, `PROD_SCHEMA_NAME=main`).

- `dbt build`: **`PASS=219 WARN=0 ERROR=0 SKIP=0`**: 64 models, 4 seeds, 145 data tests, 6 unit tests (the project has no snapshots). `fct_trip` holds 9,722,362 trips, 9,604,535 billable.
- Every model landed in `<prefix><layer>` (`staging`, `intermediate`, `core`, `agg`, `finance`, `ops`, `seeds`); the catalogs then held only those, the loads and the mirror. `nyctaxi_prod` stayed empty.
- Sources read the Intent's own loads: `stg_tlc__yellow_tripdata` compiles to `` from `nyctaxi_ephm`.`<prefix>bronze`.`yellow_tripdata` ``.
- Defer: `dbt compile -s fct_trip --favor-state` resolves every upstream `ref()` to the Domain (`` `nyctaxi_prod`.`core`.`dim_zone` ``, `` `nyctaxi_prod`.`intermediate`.`int_trips_enriched` `` …) and `{{ this }}` to `<prefix>core.fct_trip`. A source the Intent has not loaded resolves to the Domain table the YAML names (P1).

## R4 The bundle job

- `validate-job.py --repo-root .`: `JOB_OK: databricks.yml and 1 job file(s)`, exit 0.
- `validate-job.py --repo-root . --sandbox`: exit 1, one finding per `+schema:` (six model layers and the seeds): a sandbox job run is refused by design (DBX-D11).
- `databricks bundle validate -t sandbox` with the three coordinate variables: `Validation OK!`.

## R5 Rerun with the plugin fixes

The three fixes, unmerged: vibedata-dlt-runtime-utils `fix/vd-7465-…` (`databricks_files_api.__init__` carries dlt's `databricks` signature; 0.2.1, built locally as a wheel) and vde `fix/vd-7442-vd-7466-…` (`run_notebook.py` runs its CLI calls outside the repository; the `databricks.yml` template's `dlt_env` defaults to the job's own catalog and warehouse; `dlt-config.toml` holds no credentials). A copy of this repo at `24f7885` with the notebooks **unchanged from the template**; the only differences were `.github/managed-constraints.txt` pinning `vibedata-dlt-databricks-notebook==0.2.1` and a `--find-links` line in `ingestion/requirements.txt` pointing at the synced wheel, since 0.2.1 is not on PyPI yet. Every run was launched from the repository root.

| Run | Result |
| --- | --- |
| `tlc` safety, `--limit 1 --dev-mode` | TERMINATED SUCCESS, identity `nyctaxi_ephm` |
| `tlc`, `ops`, `mdm` sample, `--limit 1000` | each TERMINATED SUCCESS, identity `nyctaxi_ephm`; `audit_runs` `first_run` true |
| `tlc`, `ops`, `mdm` full, `--limit -1` | each TERMINATED SUCCESS, identity `nyctaxi_ephm`; 9,722,628 / 2,311,964 / 1,521 rows, as R2 |
| `dbt build` in the Intent's shape (as R3) | `PASS=219 WARN=0 ERROR=0` |

- The sample loads read past their cap: `tlc` extracted 3,021,440 rows (a whole month) and `ops` and `mdm` everything, because `dlt_ingest_limit` stops only after the batch that reaches it (ledger row on `generating-dlt-pipeline`).
- Production's `dlt_env`: `databricks bundle validate -t prod` with only `catalog=nyctaxi_prod`, `warehouse_id` and `schema` resolves every notebook task's `dlt_env` to that catalog and warehouse. Not deployed; VD-7386's release runs it.
- `validate-job.py` from the fixed plugin: `JOB_OK`; it refuses the old `"{}"` default.

## Cleanup

After R2–R4 and again after R5, all `<prefix>` schemas in `nyctaxi_ephm` were dropped and the synced workspace folder `/Workspace/Users/<user>/.vibedata/ephm__nyc_taxi_databricks__vd7385` deleted; both catalogs hold only `default` and `information_schema`.
