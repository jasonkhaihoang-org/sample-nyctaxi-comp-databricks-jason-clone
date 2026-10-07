# Fabric Sample Lakehouse — Design

> Status: agreed in conversation 2026-10-07; README committed on
> `feature/fabric-tailoring` (`f479cba`). This doc is the spec the
> implementation plan argues from.

## Goal

Tailor the `sample-nyctaxi-comp` estate for Microsoft Fabric as a reference
customer estate for Agent Readiness: every object provably built from code an
agent can act on.

## Decisions

1. **Repo**: new repo `sample-nyctaxi-comp-fabric` (this repo), branched
   `feature/fabric-tailoring`. `tools/` (DuckDB builders) frozen reference.
2. **Target**: Fabric Lakehouse (`dbt-fabricspark`), single Lakehouse item
   `src/nyc_taxi_lakehouse.Lakehouse/` holding all schemas.
3. **`src/` is the Fabric-connected folder.** Workspace subfolders mirror as
   subfolders. Nothing human-authored lives inside any
   `*.<ItemType>/` (Fabric wipes strays there on commit); shared sources sit
   beside item folders and Fabric preserves them.
4. **Single dbt project** `nyc_taxi_analytics` (v2.1.0, from
   `transformation/dbt_project.yml:1`) embedded in the job at
   `src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/` (native
   Fabric shape: `dbt-content.json` `folderPath: "dbt"` resolves inside
   `Code/`). Retarget:
   adapter `dbt-duckdb` → `dbt-fabricspark`, `profiles.yml` to Lakehouse
   coords, `vars` databases `domain` → Lakehouse (schemas unchanged).
   Full-volume landing; no sample clause (dev slicing is a target concern).
5. **One `DataBuildToolJob`** `src/dbt/nyc_taxi_analytics.DataBuildToolJob/`
   (folder + `.platform:displayName` match project name; `logicalId`
   pre-assigned in Git so imports resolve on first sync). `dbt-content.json` `folderPath` points at the
   shared `dbt/` project — no copies.
6. **Four driver notebooks** `src/dbt/<staging|marts|finance|ops>_dbt.Notebook/`:
   assert slices, one layer each (staging views; marts = intermediate+core+agg;
   finance; ops). Seeds live once, in `staging`.
7. **Three dlt notebooks** `src/dlt/<landing|mdm|fleet_ops>.Notebook/`,
   replacing `tools/build_domain.py`, `build_mdm.py`, `build_fleet_ops.py`
   1:1. Seam preserved: dlt lands raw + enrichment with loader stamps
   (`_load_id`, `_source_file`, `_loaded_at`); SCD2/conformance stays in dbt.
   Order: `landing` → `mdm` + `fleet_ops` in parallel (`fleet_ops` reads
   `silver.trips` timestamps).
8. **Three pipelines** `src/pipelines/<main|finance|ops>.DataPipeline/`,
   one activity per item. `main`: landing → mdm + fleet_ops → staging →
   marts. `finance`/`ops` after `main`. Agg parallelism via dbt `threads`,
   not pipeline fan-out. Schedules live in the workspace, never in Git
   (standing cadence
   nightly 03:00 ET).
9. **`docs/functional/`**: five specs (ingestion, mdm-enrichment, fleet-ops,
   transformation, orchestration), each stating behavior + provenance tier,
   so this estate scores as the "explained" reference.
10. **Placement rule**: `docs/functional/`, `tools/`, design docs at repo
    root — never inside `src/` item folders.

## Non-goals

Running against a live workspace (no capacities or credentials in scope);
CI bundle (`install-ci` drift check) — later, after the tree exists; Jev or
semantic classification — the deterministic catalog only.
