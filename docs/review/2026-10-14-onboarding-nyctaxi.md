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
