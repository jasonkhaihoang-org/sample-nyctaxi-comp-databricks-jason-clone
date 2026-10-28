---
type: onboarding
date: 2026-10-14
commit: 00e3d48
source: setup/nyctaxi-comp-repo
---

# Onboarding review: nyc-taxi-duckdb-demo

## Scope

The dbt project in `transformation/`, the three dlt pipelines in `ingestion/`, the run scripts in `orchestration/`, the pytest suite and the repository documents. A full build on the local target, the dbt tests, and queries against the built warehouse. Not reviewed: the simulated data generators beyond what the staging models read.

## Findings

| ID | Kind | Finding | Evidence | Suggested action | Status |
| --- | --- | --- | --- | --- | --- |
| R-1 | bug | Every yellow trip reports `airport_fee_status = 'missing'`: the extras models hash the trip key from TIMESTAMPTZ columns, the trip models from naive timestamps, so the rejoin matches nothing while the build stays green. | `stg_tlc__yellow_trip_extras.sql`; `select airport_fee_status, count(*) from fct_trip group by 1` → only `missing` | Convert in the extras models as in the trip models, and add a singular test that every trip rejoins its extras. | intent |
| R-2 | platform | Staging models read bronze tables by name instead of through `source()`, so lineage and freshness stop at staging. | `grep -L "source(" transformation/models/staging/*.sql` | Read bronze only through `source()`; declare every bronze table in `_sources.yml`. | intent |
| R-3 | convention | dlt loads naive Arrow timestamps as TIMESTAMPTZ; on a session in another time zone the values shift. | `describe bronze.yellow_tripdata` → `TIMESTAMP WITH TIME ZONE`; session time zone Asia/Singapore | Convert with `timezone('UTC', col)` in staging and state it in `dlt.md`. | intent |
| R-4 | bug | A fresh checkout cannot build: `packages.yml` is present but `orchestration/run_transform.py` never runs `dbt deps`. | Fresh worktree: 7 dbt-selector tests fail, `dbt_project_evaluator` not found | Run `dbt deps` before `dbt build` in `run_transform.py`. | intent |
| R-5 | gap | No CI job runs the pytest suite, so a stale `repo-map.json` or `test-map.json` is never caught. | `grep -l pytest .github/workflows/*.yml` → none | Add a job that installs pytest and dbt-duckdb together and runs `python3 -m pytest tests -q`. | open |
| R-6 | style | sqlfluff's default rules disagree with how the models are written (keyword case, implicit aliases, `values` column lists). | `sqlfluff lint transformation/models` → violations across most models | Keep the project's style and record the exceptions in `.sqlfluff` and `sql-style.md`. | declined: mass reformatting risks behaviour changes (`sqlfluff fix` dropped a `values` column list); exceptions recorded instead |
| R-7 | gap | High-volume for-hire (HVFHV) trips are outside the conformed trip grain, so trip counts and revenue cover yellow and green only. | `int_trips_conformed.sql` unions yellow and green only | Decide whether and how HVFHV joins the conformed grain. | proposal → P-0001 |
| R-8 | gap | `transformation/profiles.yml` has `domain` and `slice` targets and no `dev`; sandbox runs depend on the runtime profile. | `transformation/profiles.yml` | Document the sandbox command for agents; keep the repo profile for local and CI use. | deferred |
| R-9 | gap | `transformation/.user.yml` is tracked although `.gitignore` lists it. | `git ls-files transformation/.user.yml`; `.gitignore:23` | `git rm --cached transformation/.user.yml`. | open |

## Notes after the Fabric Lakehouse port (2026-10-18)

The findings above were made on the DuckDB Domain this repo was ported from. On the Fabric Lakehouse:

- R-4: the run scripts are gone; the `nyc_taxi_build_dbt` notebook runs `dbt deps` before `dbt build` when the project has a `packages.yml`.
- R-5: `.github/workflows/repo-checks.yml` runs the pytest suite; on Fabric it installs `dbt-fabricspark`, which the map tests' `dbt ls` needs.

## Notes after the Databricks port (2026-10-28)

This repo was then ported from the Fabric Lakehouse repo to Databricks, per `docs/setup/databricks-best-practices.md`. On Databricks:

- R-3: dlt lands timestamps as `timestamp` in UTC and a source `DATE` as `date` (the `ops` generator's computed dates land as midnight timestamps), and the warehouse session time zone is UTC (P7), so the shift this finding describes does not occur; DBX-D3 retires `utc_date()`'s reason.
- R-4: the dbt notebook goes; the Lakeflow job's dbt task, from the plugin's `orchestration.job.yml`, runs `dbt deps` before `dbt build` (DBX-D6).
- R-5: `.github/workflows/repo-checks.yml` stays (DBX-D8) and installs `dbt-databricks` for the map tests' `dbt ls`, once `requirements-dev.txt` moves to it (DBX-D6).
- R-6: under the `databricks` dialect with the jinja templater every model parses, with one `LT02` hit (P4).
- R-8: an Intent runs on Studio's `dbt_databricks` profile, target `databricks_sandbox`; the repo's own profile becomes `dbt_databricks` with a `prod` target on the Domain catalog (DBX-D6).
