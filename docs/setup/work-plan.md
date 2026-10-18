# Set up sample-nyctaxi-comp as a Vibedata brownfield repo: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn this repo into the model answer for a Vibedata-worked data product: dlt ingestion, silver in dbt, conventions in `AGENTS.md` and `.agents/rules/`, locations in `repo-map.json`, and a conformed set of ADRs, design records and context.

**Architecture:** Three dlt pipelines (`tlc`, `ops`, `mdm`) load every raw source into DuckDB; dbt builds staging, intermediate and gold, including the silver logic that `tools/build_domain.py` holds today. Operators' conventions live in `.agents/rules/` and `repo-map.json`; the platform's live in the skills. Docs are written last, so each claim is checked against built code.

**Tech Stack:** dlt 1.31 with `vibedata-dlt-duckdb-studio` 0.11.0, dbt-duckdb on dbt 1.11, DuckDB 1.5, pytest 9, Python 3.

**Spec:** `docs/setup/requirements.md` (R-01 to R-23, and the decisions table). Supporting files in the same folder: `conventions-inventory.md`, `repo-map-design.md`, `rules-docs-draft.md`, `domain-terms.md`, `skill-change-notes.md`.

## Global Constraints

- Work in worktree `~/src/worktrees/setup/nyctaxi-comp-repo`, branch `setup/nyctaxi-comp-repo`. Target repo `accelerate-data/sample-nyctaxi-comp`; the branch ends as a PR there.
- Data: TLC yellow and green trips and the zone lookup for 2024-01 to 2024-03 only, fetched by dlt from `https://d37ci6vzurychx.cloudfront.net` (`/trip-data/<fleet>_tripdata_2024-0N.parquet`, `/misc/taxi_zone_lookup.csv`). No sampling.
- `report_start` = `2024-01-01`, `report_end` = `2024-04-01`, set once in `transformation/dbt_project.yml`.
- Pipelines follow `_shared/platforms/duckdb_local/templates/dlt-pipeline.py` in the plugin and import `from vibedata.dlt.duckdb import setup_environment, finalize`. Destination literal `"duckdb"`; dataset names `bronze`, `ops_raw`, `mdm_raw`.
- No transformation, casts, joins or filters in bronze; never drop `_dlt_*` columns.
- `trip_key` is produced only by the `trip_natural_key` macro in `transformation/macros/trip_keys.sql`.
- Reference tables `payment_type_ref`, `rate_code_ref`, `vendor_ref` and `silver.zones`/`payment_types`/`rate_codes` are dropped.
- Docs: `CONTEXT.md` is vocabulary only. ADR numbers 0003 to 0016 are new; 0001 and 0002 change only frontmatter. Cite ADRs as `ADR NNNN`. Design records name no consumers or audiences. Dates in new ADRs are the day written.
- Stage named files only; never `git add .`; one concern per commit; never force-push.
- Never commit `domain.duckdb`, downloaded files, `secrets.toml` or `.agents_tmp/`.

## Review Focus

- Re-running a pipeline must not duplicate rows (`replace` per resource); a second run changes no counts.
- The `ops` pipeline loads only `ops_raw` tables, never trips; the hidden TLC parent must not land in `ops_raw`.
- `trip_key` computed in dbt from natural columns must equal the key the old script produced for the same trips (compared on a 3-month, unsampled baseline).
- A trip with no fleet match keeps null keys and `is_fleet_attributed = false`; no placeholder member appears.
- Every ADR claim, every design-record statement and every `CONTEXT.md` term traces to code or a model in this branch; a superseded ADR is edited only in its frontmatter.

## File Structure

| Path | Responsibility |
| --- | --- |
| `ingestion/tlc_pipeline.py`, `ops_pipeline.py`, `mdm_pipeline.py` | One dlt pipeline each; `main()` only runs under `__main__` |
| `ingestion/sources/` | Source code shared by pipelines: `tlc.py` (downloads and yields), `ops.py` (fleet generator as transformer), `mdm.py` (master-data generators) |
| `ingestion/.dlt/config.toml`, `ingestion/docs/<name>.yml`, `ingestion/requirements.txt` | Connection sections, resource docs, dependencies |
| `orchestration/run_ingest.py`, `run_transform.py`, `run_all.py` | Run order: tlc, ops, mdm, then dbt |
| `tests/ingestion/`, `tests/orchestration/` | pytest unit tests, offline |
| `transformation/…` | dbt changes listed per task |
| `.agents/rules/*.md` (8), `AGENTS.md`, `CONTRIBUTING.md`, `README.md` | Conventions and entry documents |
| `repo-map.json`, `test-map.json` | Locations and test lanes |
| `docs/adr/`, `docs/design/`, `CONTEXT.md`, `intents/<slug>/requirement.md` | Domain documents |
| `docs/setup/skill-changes.md` | Deliverable R-11 |

---

### Task 1: Baseline and environment

**Files:** none committed. Scratch only, under the session scratchpad.

**Interfaces:**
- Produces: a venv with `dlt`, `dbt-duckdb`, `pytest`, `vibedata-dlt-duckdb-studio==0.11.0`; a baseline file `baseline_trip_keys.parquet` and `baseline_counts.json` (row counts of the old `silver.trips`, built unsampled from Jan to Mar 2024).

- [ ] **Step 1: Create the venv and install** the four packages; pass if `python -c "from vibedata.dlt.duckdb import setup_environment, finalize"` exits 0.
- [ ] **Step 2: Probe `setup_environment()` outside Studio.** Run it with `VD_EPHM_DUCKDB_LOCAL_PATH` set to a scratch file. Record whether it succeeds. If it raises `DuckdbSandboxMissingError`, set the variables it names and retry; if it still fails, record "plain dlt for local runs" in `requirements.md` decisions.
- [ ] **Step 3: Build the baseline.** In scratch, copy `tools/build_domain.py`, remove the `USING SAMPLE` clause and the 2024-04 to 2024-06 files, run it against downloaded Jan to Mar files, and write the distinct `trip_key` set and `count(*)` of `silver.trips` to the baseline files. Pass if both files exist and the count is above zero.

### Task 2: Project configuration and ignore rules

**Files:**
- Modify: `.gitignore`, `transformation/dbt_project.yml`
- Create: `ingestion/requirements.txt`

**Interfaces:** Produces: `profile:` as `"{{ env_var('DBT_PROFILE_NAME', 'nyc_taxi_analytics') }}"`; vars `report_start: '2024-01-01'`, `report_end: '2024-04-01'`.

- [ ] **Step 1: Edit `.gitignore`:** add `**/secrets.toml`, `.agents_tmp/`, `*.log`, `*/logs/`, `dbt_packages/`; remove `raw/` and `*.parquet` comments that mention `tools/build_domain.py`.
- [ ] **Step 2: Edit `dbt_project.yml`:** profile and window as above; the ADR 0004 comment stays (the ADR is written in Task 14).
- [ ] **Step 3: Create `ingestion/requirements.txt`** listing `dlt`, `duckdb`, `pyarrow`, `requests` unpinned (managed packages bare).
- [ ] **Step 4: Verify:** `cd transformation && dbt parse` exits 0.
- [ ] **Step 5: Commit** `chore: window, profile and ignore rules`.

### Task 3: Rules and AGENTS.md

**Files:**
- Create: `.agents/rules/{dbt-models,sql-style,dbt-testing,dlt,context,adr,design-records,git-and-prs}.md`, `AGENTS.md`

**Interfaces:** Consumes the Decision column of `conventions-inventory.md` (rows whose Decision is Rule); `rules-docs-draft.md` for the three doc rules. Produces: eight rule files, each one topic; `AGENTS.md` with sections Medallion Layers, Model Naming, File Organization, Testing, SQL Style as short pointers, a Rules index linking all eight, an Artifact Paths pointer to `repo-map.json`, and the command list.

- [ ] **Step 1: Write the eight rule files**, one row set each: `dbt-models` B1 B2 B3 B6 B8 B12 B15; `sql-style` B7; `dbt-testing` C1 C2 C4 (naming) C5; `dlt` D5 D6 D7 D8 D8b D10 D14 (D14 marked not applicable until a local-files feed exists); `context` E1 E10; `adr` E3 E11 and the business-definition clause; `design-records` E9; `git-and-prs` G4 G5.
- [ ] **Step 2: Write `AGENTS.md`** with the title `# NYC Taxi Analytics (nyc-taxi-duckdb-demo): Agent Conventions`.
- [ ] **Step 3: Verify:** every rule row in the inventory appears in exactly one rule file (`grep -c` per row id in a scratch script); every relative link in `AGENTS.md` resolves.
- [ ] **Step 4: Commit** `docs: agent rules and AGENTS.md`.

### Task 4: TLC pipeline

**Files:**
- Create: `ingestion/sources/tlc.py`, `ingestion/tlc_pipeline.py`, `ingestion/.dlt/config.toml`, `ingestion/docs/tlc.yml`, `tests/ingestion/test_tlc.py`

**Interfaces:**
- Produces in `ingestion/sources/tlc.py`: `MONTHS: list[str]` (`["2024-01","2024-02","2024-03"]`); `def tlc_source(fetch=requests_get) -> dlt.sources.DltSource` with resources `yellow_tripdata`, `green_tripdata` (one yielded `pyarrow.Table` per month file) and `taxi_zone_lookup` (CSV); `def trip_url(fleet: str, month: str) -> str`.
- Produces in `tlc_pipeline.py`: `CONNECTION_NAME = "tlc"`, `PIPELINE_NAME = "tlc"`, dataset `bronze`; per resource `apply_hints(write_disposition="replace", schema_contract={"columns":"freeze","tables":"evolve","data_type":"freeze"})`.

- [ ] **Step 1: Write failing tests** in `test_tlc.py`: `test_trip_url_format` asserts `trip_url("yellow","2024-01") == "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"`; `test_source_yields_one_table_per_month` injects a stub `fetch` returning a small Parquet and asserts 3 tables per fleet; `test_no_rows_dropped` asserts row counts equal the stub's.
- [ ] **Step 2: Run** `pytest tests/ingestion/test_tlc.py -q`; expect FAIL (module missing).
- [ ] **Step 3: Implement `tlc.py`:** download each file with `fetch`, read with `pyarrow.parquet`, yield unchanged; the zone lookup yields CSV rows unchanged. No casts, filters or sampling.
- [ ] **Step 4: Implement `tlc_pipeline.py`** from the plugin template; `[sources.tlc]` in `config.toml` with `connector="custom"`, `connector_source="local"`, `entry_point="tlc_source"`.
- [ ] **Step 5: Write `ingestion/docs/tlc.yml`:** one entry per emitted field using `source_ref:`; `_dlt_id` and `_dlt_load_id` with the fixed control-column descriptions.
- [ ] **Step 6: Run tests; expect PASS.** Then a real load: `cd ingestion && VD_EPHM_DUCKDB_LOCAL_PATH=$PWD/../domain.duckdb python tlc_pipeline.py`; expect `bronze.yellow_tripdata`, `green_tripdata`, `taxi_zone_lookup` non-empty; run it a second time and expect unchanged counts.
- [ ] **Step 7: Commit** `feat: dlt pipeline for TLC bronze`.

### Task 5: MDM pipeline

**Files:**
- Create: `ingestion/sources/mdm.py`, `ingestion/mdm_pipeline.py`, `ingestion/docs/mdm.yml`, `tests/ingestion/test_mdm.py`
- Modify: `ingestion/.dlt/config.toml` (adds `[sources.mdm]`)

**Interfaces:** Produces `def mdm_source(zone_lookup: Callable[[], Iterable[dict]]) -> DltSource` with one resource per table that `tools/build_mdm.py` creates in `mdm_raw` (`zone_master`, `vendor_master`, `payment_method_master`, `rate_plan_master`, `fare_regime_master`, `borough_master`, `zone_poi`, `calendar_master`, `weather_daily`); same column names and the same deterministic `hb()` hash values; dataset `mdm_raw`. Dates: calendar and weather cover `2024-01-01` to `2024-03-31`.

- [ ] **Step 1: Write failing tests:** `test_hash_matches_duckdb` asserts the Python port of `hb(x)` equals DuckDB's `hash(x) % 100000000` for 20 sample strings; `test_zone_master_has_versioned_zones` asserts at least one location has two versions with `valid_from < valid_to`; `test_calendar_window` asserts min and max dates.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Port each generator** from `tools/build_mdm.py` into `mdm.py` as dlt resources yielding dicts; replace the `_load_id`, `_source_file`, `_loaded_at` metadata with nothing (dlt stamps its own). Use DuckDB in memory only to evaluate the same SQL where a port would change the values.
- [ ] **Step 4: Implement `mdm_pipeline.py`** (template; `write_disposition="replace"`); write `docs/mdm.yml` with `source_fields:` and `transformation:` for synthesised fields.
- [ ] **Step 5: Run tests; expect PASS.** Then load and assert the nine `mdm_raw` tables are non-empty and a second run leaves counts unchanged.
- [ ] **Step 6: Commit** `feat: dlt pipeline for mdm_raw`.

### Task 6: Ops pipeline

**Files:**
- Create: `ingestion/sources/ops.py`, `ingestion/ops_pipeline.py`, `ingestion/docs/ops.yml`, `tests/ingestion/test_ops.py`
- Modify: `ingestion/.dlt/config.toml` (adds `[sources.ops]`)

**Interfaces:**
- Consumes `tlc_source` resource `yellow_tripdata` from Task 4.
- Produces `def ops_source(trips: DltResource) -> DltSource` with `garage`, `vehicle`, `driver`, `lease_agreement` (reference), and transformers `shift`, `trip_assignment`, `driver_status_event`, `maintenance_event`; dataset `ops_raw`. The trips parent is set `selected = False` so it is never written. `trip_assignment` carries the natural columns (`service_type, vendor_id, pickup_datetime, dropoff_datetime, pickup_location_id, dropoff_location_id, trip_distance, total_amount`) and not `trip_key`. Attribution hashes `hb(<natural columns joined with '|'>)` in place of `hb(trip_key)`.

- [ ] **Step 1: Write failing tests:** `test_no_trip_rows_loaded` runs the source over a small fixture and asserts the resource names written exclude `yellow_tripdata`; `test_no_vehicle_overlap` asserts no two attributed trips overlap on one vehicle; `test_assignment_has_no_trip_key` asserts the column set; `test_status_events_reconcile` asserts every assignment has a bracketing login and logout unless it is in the documented defect share.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Port the generator** from `tools/build_fleet_ops.py` into `ops.py`, keeping the deliberate defects (missing logout, out-of-order events, out-of-window assignments, missing odometer). Window `2024-01-01` to `2024-04-01`; replace `silver.trips` with the in-memory trips table.
- [ ] **Step 4: Implement `ops_pipeline.py`** (template; `replace`); write `docs/ops.yml`.
- [ ] **Step 5: Run tests; expect PASS.** Load after Task 4 and assert the eight `ops_raw` tables are non-empty and `bronze` is untouched by this run.
- [ ] **Step 6: Commit** `feat: dlt pipeline for ops_raw`.

### Task 7: Orchestration scripts

**Files:**
- Create: `orchestration/run_ingest.py`, `run_transform.py`, `run_all.py`, `tests/orchestration/test_run.py`

**Interfaces:** Produces `def run_ingest(runner=subprocess.run) -> list[str]` (runs `tlc`, `ops`, `mdm` in that order from `ingestion/` with `VD_EPHM_DUCKDB_LOCAL_PATH` set to `<repo>/domain.duckdb`); `def run_transform(runner=subprocess.run, target="domain") -> int` (`dbt build --target <target>` from `transformation/`); `run_all()` chains them and stops at the first non-zero exit.

- [ ] **Step 1: Write failing tests** with a recording `runner`: `test_ingest_order`, `test_env_points_at_repo_database`, `test_all_stops_on_first_failure`.
- [ ] **Step 2: Run; expect FAIL.**
- [ ] **Step 3: Implement the three scripts**; each has a `main()` and `__main__` guard.
- [ ] **Step 4: Run tests; expect PASS.**
- [ ] **Step 5: Commit** `feat: orchestration scripts`.

### Task 8: Silver into dbt, and the new bronze sources

**Files:**
- Modify: `transformation/models/staging/_sources.yml`, `_staging.yml`, `intermediate/_intermediate.yml`, `intermediate/int_shift_economics.sql`, `intermediate/int_trips_enriched.sql`, `tests/assert_fct_trip_matches_silver_rowcount.sql` (renamed `assert_fct_trip_matches_conformed_rowcount.sql`)
- Create: `staging/stg_tlc__yellow_tripdata.sql`, `staging/stg_tlc__green_tripdata.sql`, `intermediate/int_trips_conformed.sql`
- Delete: `staging/stg_tlc__trips.sql`; remove the `silver` source and the three dropped reference tables from `_sources.yml`

**Interfaces:**
- Produces: `stg_tlc__yellow_tripdata`, `stg_tlc__green_tripdata` (1:1 with bronze: renamed and cast only, `_dlt_load_id` kept); `int_trips_conformed` with the columns of the old `stg_tlc__trips`, keyed by `{{ trip_natural_key(...) }}`, deduplicated on the natural columns keeping the first row by `_dlt_load_id`, `service_type` discriminator, derived duration, speed and date keys.
- Consumes: `bronze` source tables from Task 4.

- [ ] **Step 1: Run `dbt build --select int_trips_enriched+`** on the Task 4 warehouse before changes; record the failing refs (they fail because `silver` is gone). Expect errors.
- [ ] **Step 2: Write the two staging models and `int_trips_conformed`;** move the derived measures from the deleted `stg_tlc__trips` into `int_trips_conformed`; point `int_shift_economics`, `int_trips_enriched` and the row-count test at it.
- [ ] **Step 3: Update `_sources.yml`:** `bronze` source lists the dlt tables; freshness uses `_dlt_load_id`'s `_dlt_loads.inserted_at` where available, else is removed with a note in the design record.
- [ ] **Step 4: Verify equivalence:** compare `int_trips_conformed` to `baseline_trip_keys.parquet`; pass if the row count and the distinct `trip_key` set are identical.
- [ ] **Step 5: Commit** `refactor: silver built in dbt`.

### Task 9: Ops and mdm staging for dlt, and the derived trip key

**Files:**
- Modify: `transformation/models/staging/stg_ops__*.sql` (8 files), `stg_mdm__*.sql` (9 files), `_sources.yml`, `_staging.yml`

**Interfaces:** `stg_ops__trip_assignments` computes `trip_key` with `{{ trip_natural_key(service_type, vendor_id, pickup_datetime, dropoff_datetime, pickup_location_id, dropoff_location_id, trip_distance, total_amount) }}` and passes `fct_trip`'s join unchanged. All staging models read `_dlt_load_id` where they read `_load_id` today.

- [ ] **Step 1: Run `dbt build --select staging`;** expect failures on the renamed load columns.
- [ ] **Step 2: Update each staging model** for the dlt columns; compute the key in `stg_ops__trip_assignments`.
- [ ] **Step 3: Run `dbt build`** end to end on the full warehouse built by `orchestration/run_ingest.py`; expect all models and tests pass, and `fct_trip` fleet-attributed share is within the same order as before (record the figure in the pipeline design record's Evidence).
- [ ] **Step 4: Commit** `refactor: staging reads dlt bronze and derives trip_key`.

### Task 10: Unit tests and singular tests

**Files:**
- Create: `transformation/models/intermediate/_unit_tests.yml`
- Modify: `transformation/tests/assert_fct_trip_matches_conformed_rowcount.sql`

**Interfaces:** Unit tests on `int_status_intervals` (event order tie-break by `event_id`, negative duration floored to zero with `is_negative_interval`, terminal event closed at the shift's effective end), `int_trips_enriched` (`airport_fee_status` is `present`, `missing` or `not_applicable`), `int_trips_conformed` (two identical rows yield one; yellow and green rows with the same natural columns yield two).

- [ ] **Step 1: Write the unit tests** with `given` and `expect` fixtures.
- [ ] **Step 2: Run `dbt test --select test_type:unit`;** expect PASS after any fixture fixes; separately `dbt test --exclude test_type:unit` also passes.
- [ ] **Step 3: Commit** `test: unit tests for logic-heavy models`.

### Task 11: Semantic model

**Files:**
- Create: `transformation/models/marts/core/_semantic.yml`, `transformation/models/metricflow_time_spine.sql`, `transformation/models/metricflow_time_spine.yml`
- Modify: the design records for `fct_trip` and `fct_shift` (a `## Semantic Model` section, written in Task 14)

**Interfaces:** Semantic models `trips` (on `fct_trip`) and `shifts` (on `fct_shift`) with metrics `trip_count`, `billable_trip_count`, `billable_revenue`, `fare_residual_total`, `shift_count`, `online_hours`, `occupancy_rate` (ratio of summed numerator and denominator), `revenue_per_online_hour`. Spec chosen by `dbt --version`; time spine from `_shared/platforms/duckdb_local/templates/metricflow_time_spine.sql` unchanged.

- [ ] **Step 1: Run `dbt --version`** and record the spec chosen.
- [ ] **Step 2: Write the YAML and copy the time spine;** every measure points at an existing gold column.
- [ ] **Step 3: Verify:** `cd transformation && dbt parse` exits 0; `dbt ls --resource-type metric` lists all eight.
- [ ] **Step 4: Commit** `feat: semantic model`.

### Task 12: Repo map and test map

**Files:**
- Create: `repo-map.json`, `test-map.json`, `tests/test_maps.py`

**Interfaces:** `repo-map.json` is the sketch in `repo-map-design.md`, completed with `modules`, `key_directories`, `entrypoints` (the three `orchestration/` scripts), `commands`, `key_references`, `notes_for_agents`. `test-map.json` maps `ingestion`, `orchestration`, `staging`, `intermediate`, `core`, `agg`, `finance`, `ops` and `semantic` to `{command, paths, singular_tests}`.

- [ ] **Step 1: Write `tests/test_maps.py`:** `test_repo_map_paths_exist` (every path in `layers`, `artifact_paths` without placeholders, `entrypoints`, `key_directories` exists); `test_test_map_selectors_resolve` (each `dbt` selector returns at least one node via `dbt ls`); `test_repo_map_validates` against `~/src/studio/.claude/repo-map.schema.json` extended with the added fields.
- [ ] **Step 2: Run; expect FAIL.** Write both files; run; expect PASS.
- [ ] **Step 3: Commit** `docs: repo-map and test-map`.

### Task 13: CI bundle

**Files:**
- Create: `.github/**`, `.workflow/ci-config.yml`

- [ ] **Step 1: Read** `~/src/studio/ext/domain-cicd/shared/scripts/bundle_deploy.py` and the duckdb bundle's `bundle-deploy.json` before running anything.
- [ ] **Step 2: Deploy** with `python3 ~/src/studio/ext/domain-cicd/shared/scripts/bundle_deploy.py --platform duckdb_local --target <worktree>`; set `VD_DOMAIN_SLUG: nyc-taxi-duckdb-demo` in `.workflow/ci-config.yml`.
- [ ] **Step 3: Verify:** `python3 .github/scripts/validate_ci_config.py` exits 0.
- [ ] **Step 4: Commit** `ci: install domain CI bundle`.

### Task 14: ADRs, context and design records

**Files:**
- Modify: `docs/adr/0001-…md`, `docs/adr/0002-…md` (frontmatter only, plus removing the old `**Status:**` line), `CONTEXT.md`, `docs/design/models/core/fct_trip.md`, `docs/design/models/intermediate/int_status_intervals.md`, `docs/design/models/intermediate/int_trips_enriched.md`, model descriptions in `transformation/models/**/_*.yml` and `docs.md` that name audiences
- Create: ADRs 0003 to 0016 (`docs/adr/00NN-<slug>.md`); design records for `int_trips_conformed`, `stg_tlc__yellow_tripdata`, `stg_tlc__green_tripdata`, `stg_ops__trip_assignments`, `docs/design/pipelines/{tlc,ops,mdm}.md`

**Interfaces:** ADR list: 0003 billable as applied (supersedes 0002); 0004 quality verdicts flag and never delete; 0005 dlt for all raw sources; 0006 silver in dbt (supersedes 0001); 0007 one `trip_key` definition; 0008 simulated sources (`ops` uses TLC trips as a hidden parent and carries natural columns); 0009 Type 2 only where the source versions history; 0010 driver ranking and utilisation definitions; 0011 tips measured over payment methods that record them; 0012 unknown zones retained and flagged; 0013 no-charge and dispute payments not excluded by the billable rule; 0014 weeks start Monday; 0015 unmatched keys stay null with a flag; 0016 rates rebuilt from summed numerators and denominators. Each follows `.agents/rules/adr.md` and has `## Affected designs`. Design records follow `.agents/rules/design-records.md`; pipeline records carry per-resource `D-NN` decisions for write disposition, cursor, the three contract axes and duplicate-key handling, and record the `setup_environment()` outcome from Task 1.

- [ ] **Step 1: Verify each ADR claim against the SQL before writing it** (grep or `dbt show`); write down the evidence in the ADR's consequences or the design record's Evidence.
- [ ] **Step 2: Write ADRs 0003 to 0016,** then edit 0001 and 0002 frontmatter (`status: rejected`, `date:` original, `rejected-note: Superseded by docs/adr/<new>.md`).
- [ ] **Step 3: Rewrite `CONTEXT.md`** per `domain-terms.md`: drop Layers, Known data characteristics and Consumers; keep vocabulary only.
- [ ] **Step 4: Conform and write the design records;** replace consumer wording in model descriptions.
- [ ] **Step 5: Verify:** a scratch script asserts (a) every `ADR NNNN` citation under `docs/` has a file, (b) symmetry: a design record that cites an ADR appears in that ADR's Affected designs and the reverse, (c) no `CONTEXT.md` or ADR line contains a team name, a digit-led example value or a column name; run `python3 .github/scripts/adr_lint.py` locally without `--pr-number`; expect no findings.
- [ ] **Step 6: Commit** in two commits: `docs: ADRs 0003 to 0016` and `docs: context, design records and descriptions`.

### Task 15: Repo documents

**Files:**
- Modify: `README.md`, `AGENTS.md`
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Update `README.md`:** architecture diagram (dlt, dbt, orchestration), layout, commands, data window; replace the "archived" note with what GitHub shows; remove every reference to `tools/download_bronze_data.py`, `build_domain.py`, `build_mdm.py`, `build_fleet_ops.py`.
- [ ] **Step 2: Write `CONTRIBUTING.md`:** how to run ingestion, dbt and tests, branch and commit format (link `.agents/rules/git-and-prs.md`), where ADRs and design records go.
- [ ] **Step 3: Delete `tools/`** scripts replaced by pipelines (`download_bronze_data.py`, `build_domain.py`, `build_mdm.py`, `build_fleet_ops.py`, `build_synthetic_sources.py`); keep `dq.py` and `build_dbt_and_docs.py` if still referenced, else delete.
- [ ] **Step 4: Verify:** `grep -rn "tools/build\|download_bronze" README.md AGENTS.md CONTRIBUTING.md docs repo-map.json` returns nothing.
- [ ] **Step 5: Commit** `docs: README, AGENTS.md, CONTRIBUTING`.

### Task 16: Intent requirement documents

**Files:**
- Create: `intents/trip-fact/requirement.md`, `intents/status-occupancy/requirement.md`, `intents/setup-dlt-ingestion/requirement.md`

**Interfaces:** Each follows `_shared/templates/intent-template.md` (`kinds:` frontmatter, Ask, Requirements with `R-NN`, Business decisions, Out of scope, Open questions, Approvals). Design records cite these `R-NN` as `D-NN` sources.

- [ ] **Step 1: Write the three documents** from the design records, ADRs and this branch's `requirements.md` (R-10 and R-12 for `setup-dlt-ingestion`).
- [ ] **Step 2: Mark every approval line** `reconstructed`; no quoted answers.
- [ ] **Step 3: Verify:** every path or model named in each document exists (scratch script).
- [ ] **Step 4: Commit** `docs: intent requirements`.

### Task 17: Skill changes document

**Files:** Create `docs/setup/skill-changes.md`.

**Interfaces:** A table with columns Skill, Reference (plugin file and section), Suggested change; plus a section "What `init` must do" for greenfield and brownfield. Consumes `conventions-inventory.md` (Skill and Rule rows) and `skill-change-notes.md`.

- [ ] **Step 1: Build the rows** from every convention row that moved to rules, repo-map or ADRs (each names the skill that restates it today) and every note in `skill-change-notes.md`.
- [ ] **Step 2: Write the `init` section** from what this repo needed: scan for layout, write `repo-map.json`, write `AGENTS.md` and `.agents/rules/`, install CI, set `.gitignore`.
- [ ] **Step 3: Verify:** every `Today in` skill named in the inventory appears in at least one row.
- [ ] **Step 4: Commit** `docs: skill changes`.

### Task 18: Final verification and PR

- [ ] **Step 1: From a clean checkout,** run `python3 orchestration/run_all.py`; expect exit 0.
- [ ] **Step 2: Run** `python -m pytest tests -q`, `cd transformation && dbt test`, `dbt parse`; expect all pass.
- [ ] **Step 3: Walk R-01 to R-23** against `requirements.md`; mark each accept-when as met with its command or file; list any unmet one.
- [ ] **Step 4: Open the PR** on `accelerate-data/sample-nyctaxi-comp` with the PR template sections from `.agents/rules/git-and-prs.md`.

## Self-review notes

- **Coverage:** R-01 Task 14; R-02 Task 14; R-03 Task 14; R-04 Task 3; R-05 Task 3; R-06 Task 12; R-07 Task 13; R-08 and R-09 Task 2; R-10 Tasks 4 to 6, 9; R-11 Task 17; R-12 Task 8; R-13 recorded in `conventions-inventory.md`; R-14 Task 14; R-15 Task 14; R-16 Task 14; R-17 Task 3; R-18 Task 16; R-19 Task 15; R-20 Tasks 10, 12; R-21 Task 11; R-22 Task 7; R-23 Tasks 4 to 7, 12.
- **Interpretation to confirm:** requirements say `ops` is a transformer "in the same pipeline run" as TLC, while the repo-map lists three pipelines. This plan keeps three pipelines: `ops` re-reads the TLC trips as a hidden parent that is never written, so no data lands twice.
- **`replace` write disposition** on every resource is chosen because each run reloads the full fixed 3-month window; recorded as a `D-NN` per resource.
