# Fabric Sample Lakehouse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Fabric-managed `src/` tree, retargeted dbt project, dlt notebooks, pipelines, and functional specs in `sample-nyctaxi-comp-fabric` on branch `feature/fabric-tailoring`.

**Architecture:** Scaffold Fabric item folders (each `<Name>.<Type>/` + `.platform`) beside shared sources under `src/`; port DuckDB builders to dlt/PySpark notebooks 1:1; retarget the single dbt project to `dbt-fabricspark`; three one-activity-per-item pipelines; five functional specs.

**Tech Stack:** Fabric items (Lakehouse, Notebook `notebook-content.py`, DataBuildToolJob `dbt-content.json`, DataPipeline `pipeline-content.json`), dbt (`dbt-fabricspark`), dlt/PySpark notebooks, markdown specs.

**Spec:** `docs/design/fabric-sample-lakehouse.md` (this repo, committed `8f4e7b2`); README.md (`f479cba`) for narrative; source behavior from sibling clone `../sample-nyctaxi-comp` (`tools/*.py`, `transformation/dbt_project.yml`, `docs/data-provenance.md`, `CONTEXT.md`).

## Global Constraints

- Branch is `feature/fabric-tailoring`; never commit to `main`.
- `src/` is the Fabric-connected folder: never place human-authored files inside any `*.<ItemType>/` except that item's own definition files.
- New item folders ship `.platform` WITHOUT `logicalId` (Fabric assigns on first sync); `metadata.type` + `metadata.displayName` MUST equal folder `<Name>.<Type>`.
- `tools/` is frozen: read it, never modify it.
- Full-volume landing everywhere; no `SAMPLE`/`TABLESAMPLE` clause in any loader.
- dlt seam: loaders land raw + enrichment with `_load_id`, `_source_file`, `_loaded_at` on every row; no SCD2/conformance logic in notebooks (that stays dbt).
- One pipeline activity per item; agg parallelism via dbt `threads` (4), never pipeline fan-out.
- Every task ends with a commit on the branch; verify with the stated command before committing.

## Review Focus

- An item folder whose name and `.platform:metadata` disagree will fail Fabric import silently pairing the wrong identity — every task re-runs the validator on its files.
- A loader that drops `_load_id`/`_source_file`/`_loaded_at` breaks M1/M3 evidence — the validator asserts the stamp strings exist in each notebook.
- A `SAMPLE` clause or `sample_trips`-style flag reintroduces the rejected downsampling — grep for it in the owning task's test.
- A dbt `vars` database still set to `domain` (DuckDB file) points the project at a database that does not exist here — retarget task asserts the string `domain` appears nowhere as a database value.
- A pipeline `.schedules` committed enabled would schedule runs on sync — assert `disabled` in the pipeline task.

---

### Task 1: Tree validator script

**Files:**
- Create: `scripts/validate_tree.py`
- Test: run `python3 scripts/validate_tree.py` (exit 0 = pass)

**Interfaces:**
- Consumes: nothing (first task; conventions from spec §3, §10).
- Produces: `validate_tree.py` — later tasks run it after adding files. Checks: every `*.<ItemType>/` under `src/` has `.platform` (valid JSON; `metadata.type`/`displayName` match folder name; NO `logicalId` key); every `*.Notebook/` has `notebook-content.py`; every `*.DataBuildToolJob/` has `dbt-content.json`; every `*.DataPipeline/` has `pipeline-content.json`; no `SAMPLE` (case-insensitive) in `src/dlt/`; `_load_id` + `_source_file` + `_loaded_at` strings present in each `src/dlt/*.Notebook/notebook-content.py`.

- [ ] **Step 1: Write `scripts/validate_tree.py`** implementing the checks above (stdlib only: `os`, `json`, `re`, `sys`). Empty tree passes (no items yet = no violations).
- [ ] **Step 2: Run it**

Run: `python3 scripts/validate_tree.py`
Expected: PASS (exit 0, prints `tree OK: 0 items` or similar)

- [ ] **Step 3: Commit**

```bash
git add scripts/validate_tree.py
git commit -m "Add src tree validator for Fabric item conventions"
```

### Task 2: Lakehouse item folder

**Files:**
- Create: `src/nyc_taxi_lakehouse.Lakehouse/.platform`, `src/nyc_taxi_lakehouse.Lakehouse/lakehouse.metadata.json`, `src/nyc_taxi_lakehouse.Lakehouse/alm.settings.json`, `src/nyc_taxi_lakehouse.Lakehouse/shortcuts.metadata.json`
- Test: `python3 scripts/validate_tree.py`

**Interfaces:**
- Consumes: `validate_tree.py` from Task 1.
- Produces: Lakehouse item other tasks reference by display name `nyc_taxi_lakehouse`. Reference shape: sibling-verified `dude/axfabriclakehouse.Lakehouse/` (files `.platform`, `alm.settings.json`, `lakehouse.metadata.json`, `shortcuts.metadata.json`).

- [ ] **Step 1: Create the four files.** `.platform`: `metadata.type` = `Lakehouse`, `metadata.displayName` = `nyc_taxi_lakehouse`, `config.version` = `2.0`, no `logicalId`. `lakehouse.metadata.json`: display name + description (one line: NYC taxi brownfield sample). `alm.settings.json` + `shortcuts.metadata.json`: minimal valid JSON (`{}` with a `_comment` field is NOT valid to Fabric — use the smallest real shapes: `alm.settings.json` = `{"version": "1.0"}`; `shortcuts.metadata.json` = `{"shortcuts": []}`). If the reference shapes differ, match the reference.
- [ ] **Step 2: Run the validator**

Run: `python3 scripts/validate_tree.py`
Expected: PASS, reports 1 item

- [ ] **Step 3: Commit**

```bash
git add src/nyc_taxi_lakehouse.Lakehouse scripts/validate_tree.py
git commit -m "Add nyc_taxi_lakehouse Lakehouse item folder"
```

### Task 3: Retargeted single dbt project at `src/dbt/dbt/`

**Files:**
- Create: full tree under `src/dbt/dbt/` copied from `../sample-nyctaxi-comp/transformation/` (`dbt_project.yml`, `models/`, `seeds/`, `macros/`, `tests/`, plus `profiles.yml` retargeted)
- Test: `python3 -c` yaml-parse + grep checks (below)

**Interfaces:**
- Consumes: source tree `../sample-nyctaxi-comp/transformation/` (read-only; never modify the sibling clone).
- Produces: `src/dbt/dbt/` — the one project the job (Task 4) points at via `folderPath: "dbt"`. Schemas kept (`staging`, `intermediate`, `core`, `agg`, `finance`, `ops`, `seeds`); databases retargeted to the Lakehouse.

- [ ] **Step 1: Copy the project** (`cp -r`, excluding `target/`, `logs/`, `dbt_packages/` if present).
- [ ] **Step 2: Retarget.** `profiles.yml`: replace `dbt-duckdb`/path targets with a `dbt-fabricspark` profile for the Lakehouse (no secrets in the file — placeholders `<workspace-id>`, `<lakehouse-id>` with a comment pointing at driver-notebook runtime binding). `dbt_project.yml` `vars`: `bronze_database`, `silver_database`, `ops_database`, `mdm_database` from `domain` to the Lakehouse database value; schemas untouched. Keep `name: nyc_taxi_analytics`, version, model materializations, seeds config byte-identical.
- [ ] **Step 3: Verify**

Run: `python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('src/dbt/dbt/**/*.yml', recursive=True)]" && ! grep -riw --include='*.yml' --include='*.sql' '\bdomain\.duckdb\b\|dbt-duckdb' src/dbt/dbt/ && grep -q 'nyc_taxi_lakehouse\|<lakehouse' src/dbt/dbt/profiles.yml`
Expected: PASS (no output = no DuckDB residue; last grep matches)

- [ ] **Step 4: Commit**

```bash
git add src/dbt/dbt
git commit -m "Add retargeted nyc_taxi_analytics dbt project for Lakehouse"
```

### Task 4: `nyc_taxi_analytics.DataBuildToolJob` item

**Files:**
- Create: `src/dbt/nyc_taxi_analytics.DataBuildToolJob/.platform`, `src/dbt/nyc_taxi_analytics.DataBuildToolJob/dbt-content.json`
- Test: `python3 scripts/validate_tree.py`

**Interfaces:**
- Consumes: `src/dbt/dbt/` (Task 3); validator (Task 1).
- Produces: job other tasks reference by display name `nyc_taxi_analytics`. Reference shape: `dude/dbtJob_1.DataBuildToolJob/` (`.platform` with `type: DataBuildToolJob`; `dbt-content.json` with `project.projectType: OneLake`, `project.folderPath: "dbt"`, `profile.profileType: Lakehouse`, `profile.schema`, `command.operation: build`, `command.arguments.threads: 4`).

- [ ] **Step 1: Create `.platform`** (`type: DataBuildToolJob`, `displayName: nyc_taxi_analytics`, no `logicalId`) and **`dbt-content.json`** with `folderPath: "dbt"`, Lakehouse profile (connection name `nyc_taxi_lakehouse`, schema per group default — use `staging`; per-slice schemas come from `dbt_project.yml` model configs, not the profile), `operation: build`, `threads: 4`.
- [ ] **Step 2: Run the validator**

Run: `python3 scripts/validate_tree.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/dbt/nyc_taxi_analytics.DataBuildToolJob
git commit -m "Add nyc_taxi_analytics dbt job item pointing at shared dbt/ project"
```

### Task 5: Four driver notebooks (assert slices)

**Files:**
- Create: `src/dbt/staging_dbt.Notebook/`, `src/dbt/marts_dbt.Notebook/`, `src/dbt/finance_dbt.Notebook/`, `src/dbt/ops_dbt.Notebook/` (each: `.platform` + `notebook-content.py`)
- Test: `python3 scripts/validate_tree.py` + `python3 -m py_compile` on each `notebook-content.py`

**Interfaces:**
- Consumes: dbt groups from Task 3 (staging; marts = intermediate+core+agg; finance; ops); validator (Task 1).
- Produces: drivers the pipelines (Task 7) invoke after each dbt slice. Each notebook assumes its slice is built and asserts it with `spark.sql` — no dbt invocation, no trigger API.

- [ ] **Step 1: Write the four notebooks.** `staging`: row-count reconciliation source→staging per fleet + null-key checks. `marts`: grain checks (one row per `trip_key` in `core.fct_trip`; uniqueness of `dim_zone`/`dim_vendor` natural keys incl. SCD2 non-overlap) + zone-join zero-unmatched assertion. `finance`: billable-trip definition (`total_amount > 0`) + reporting-window bounds + revenue-bridge tie-out. `ops`: status-interval validity + shift-time reconciliation + trip-quality flag presence. Real thresholds from the sibling repo's dbt tests (`transformation/models/**/schema.yml`, `transformation/tests/`) — copy the predicate, not a placeholder. Each file keeps the `# Fabric notebook source` header style from the reference notebook format.
- [ ] **Step 2: Verify**

Run: `python3 scripts/validate_tree.py && python3 -m py_compile src/dbt/*_dbt.Notebook/notebook-content.py`
Expected: PASS (validator clean; no compile output)

- [ ] **Step 3: Commit**

```bash
git add src/dbt/*_dbt.Notebook
git commit -m "Add four dbt driver notebooks asserting staging/marts/finance/ops slices"
```

### Task 6: dlt `landing` notebook (bronze + silver)

**Files:**
- Create: `src/dlt/landing.Notebook/.platform`, `src/dlt/landing.Notebook/notebook-content.py`
- Test: validator + `py_compile` + stamp/sample grep checks

**Interfaces:**
- Consumes: behavior from `../sample-nyctaxi-comp/tools/build_domain.py` + `download_bronze_data.py` (land verbatim + stamps; yellow+green union → `silver.trips`, dropping single-fleet-only columns `Airport_fee`, `ehail_fee`, `trip_type`); validator (Task 1).
- Produces: `bronze.*` + `silver.trips` in the Lakehouse; `mdm`/`fleet_ops` notebooks (Tasks 7–8) read them.

- [ ] **Step 1: Write the notebook** as a dlt pipeline (PySpark): resources `yellow_tripdata`, `green_tripdata` (full TLC files from Lakehouse Files — no sample clause), `taxi_zone_lookup`, hand-maintained refs (`payment_type_ref`, `rate_code_ref`, `vendor_ref` as static values, copied verbatim from `build_domain.py:67-93`), then `silver.trips` conforming transform (union, rename, dedupe; single-fleet-only columns dropped with a comment citing the conforming note). Every write stamps `_load_id`, `_source_file`, `_loaded_at`.
- [ ] **Step 2: Verify**

Run: `python3 scripts/validate_tree.py && python3 -m py_compile src/dlt/landing.Notebook/notebook-content.py && grep -c '_load_id\|_source_file\|_loaded_at' src/dlt/landing.Notebook/notebook-content.py && ! grep -ri 'sample' src/dlt/landing.Notebook/notebook-content.py`
Expected: PASS, stamp count ≥ 3, final grep finds nothing

- [ ] **Step 3: Commit**

```bash
git add src/dlt/landing.Notebook
git commit -m "Add dlt landing notebook: bronze + silver.trips"
```

### Task 7: dlt `mdm` notebook (masters + enrichment)

**Files:**
- Create: `src/dlt/mdm.Notebook/.platform`, `src/dlt/mdm.Notebook/notebook-content.py`
- Test: validator + `py_compile` + stamp grep

**Interfaces:**
- Consumes: `../sample-nyctaxi-comp/tools/build_mdm.py` (zone_master versioned incl. `location_id % 37` second versions; vendor_master rebrand; rate/fare/calendar/borough/POI/weather masters; hash macro `hb(x)`); `bronze.taxi_zone_lookup` from Task 6.
- Produces: `mdm_raw.*` tables.

- [ ] **Step 1: Write the notebook** as dlt resources, one per master, translating the DuckDB SQL to Spark SQL function-for-function (hash via `hash()`/`md5` with a comment where bit-behavior differs from DuckDB — values stay deterministic per zone, exact cross-engine equality is NOT required). No SCD2 assembly here (dbt owns it — cite in a header comment). Loader stamps on every row.
- [ ] **Step 2: Verify**

Run: `python3 scripts/validate_tree.py && python3 -m py_compile src/dlt/mdm.Notebook/notebook-content.py && grep -c '_load_id' src/dlt/mdm.Notebook/notebook-content.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/dlt/mdm.Notebook
git commit -m "Add dlt mdm notebook: versioned masters + enrichment"
```

### Task 8: dlt `fleet_ops` notebook (synthetic source system)

**Files:**
- Create: `src/dlt/fleet_ops.Notebook/.platform`, `src/dlt/fleet_ops.Notebook/notebook-content.py`
- Test: validator + `py_compile` + stamp grep

**Interfaces:**
- Consumes: `../sample-nyctaxi-comp/tools/build_fleet_ops.py` (garage 6 → vehicle 420 → driver 760 → lease → shift 73k → trip_assignment → status events → maintenance; deterministic, no RNG; deliberate imperfections KEPT: missing LOGOUTs, out-of-order events, mis-windowed assignments, missing odometers — flagged downstream, not cleaned); `silver.trips` timestamps from Task 6.
- Produces: `ops_raw.*` tables.

- [ ] **Step 1: Write the notebook** translating entity-by-entity in dependency order, preserving counts (6/420/760), the no-RNG determinism, and all four deliberate imperfections (each with a comment naming the downstream flag that catches it). Loader stamps on every row.
- [ ] **Step 2: Verify**

Run: `python3 scripts/validate_tree.py && python3 -m py_compile src/dlt/fleet_ops.Notebook/notebook-content.py && grep -c '_load_id' src/dlt/fleet_ops.Notebook/notebook-content.py`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/dlt/fleet_ops.Notebook
git commit -m "Add dlt fleet_ops notebook: deterministic synthetic source system"
```

### Task 9: Three pipelines (main, finance, ops)

**Files:**
- Create: `src/pipelines/main.DataPipeline/`, `src/pipelines/finance.DataPipeline/`, `src/pipelines/ops.DataPipeline/` (each: `.platform` + `pipeline-content.json` + `.schedules` committed disabled)
- Test: validator + JSON parse + disabled-schedule assert

**Interfaces:**
- Consumes: items from Tasks 2, 4–8 by display name. Reference activity JSON shape from the `dude/` example (`pipeline-content.json` with activities + `dependsOn`; fetch `pipeline3.DataPipeline/pipeline-content.json` from `stream-lit-hellp` `dude/Dude2/` as the shape reference if reachable, else mirror `dbt-content.json`-style minimal valid structure and note the deviation in the commit message).
- Produces: `main` = landing → mdm + fleet_ops (parallel `dependsOn`) → staging slice + driver → marts slice + driver; `finance` = finance slice + driver (after main); `ops` = ops slice + driver (after main). dbt slices invoked as DataBuildToolJob activities with `--select <group>.*`; asserts as Notebook activities.

- [ ] **Step 1: Write the three `pipeline-content.json` files**, one activity per item, `dependsOn` chains as above, `.schedules` present and disabled in each.
- [ ] **Step 2: Verify**

Run: `python3 scripts/validate_tree.py && python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('src/pipelines/*/*.json')]" && grep -ri 'enabled' src/pipelines/*/.schedules | grep -vi 'disabled\|false' ; test $? -eq 1`
Expected: PASS (validator clean; JSON parses; no enabled schedule)

- [ ] **Step 3: Commit**

```bash
git add src/pipelines
git commit -m "Add main/finance/ops pipelines, one activity per item"
```

### Task 10: `docs/functional/` specs (five flows)

**Files:**
- Create: `docs/functional/ingestion/README.md`, `docs/functional/mdm-enrichment/README.md`, `docs/functional/fleet-ops/README.md`, `docs/functional/transformation/README.md`, `docs/functional/orchestration/README.md`
- Test: markdownlint if available, else file-presence + cross-link check

**Interfaces:**
- Consumes: behavior+provenance from `../sample-nyctaxi-comp/docs/data-provenance.md` (tiers 1–4), `CONTEXT.md` (layers, ubiquitous language), and Tasks 2–9 (names must match: item names, schemas, selectors).
- Produces: the "explained" reference the readiness catalog scores against.

- [ ] **Step 1: Write the five specs** at behavior altitude (what is built, from what, with what stamps/checks — never how Fabric executes it): ingestion (full-volume landing, stamps, silver conforming + dropped columns); mdm-enrichment (per-master real-vs-invented column contract, versioning rule `% 37`, SCD2-in-dbt boundary); fleet-ops (counts, determinism, four imperfections + downstream flags); transformation (single project, per-group selectors, billable-trip + window rules, threads); orchestration (three pipelines, activity chains, disabled schedules, 03:00 ET standing cadence).
- [ ] **Step 2: Verify**

Run: `ls docs/functional/*/README.md && ! grep -ril 'TBD\|TODO' docs/functional/`
Expected: PASS (5 files, no placeholders)

- [ ] **Step 3: Commit**

```bash
git add docs/functional
git commit -m "Add five functional specs for the Fabric sample lakehouse"
```
