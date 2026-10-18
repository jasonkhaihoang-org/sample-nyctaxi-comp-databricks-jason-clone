---
kinds: [project-config]
---

# Requirement: Set up sample-nyctaxi-comp as a Vibedata brownfield repo

## Ask

Make this repo look like one a Vibedata agent has already worked on, using the
`vibedata-data-engineering` plugin skills as the reference for what such a repo
holds (`~/src/studio/ext/vd-data-engineering/plugins/vibedata-data-engineering`).
Then add a `repo-map.json` and an `AGENTS.md` with `.agents/rules/` (modelled on
`~/src/studio/ext/vd-data-engineering`) so conventions live in the repo and the
skills can be lighter. Consumers: Vibedata agents and skill authors testing
against a realistic brownfield domain.

## Requirements

- [x] `R-01` Domain glossary matches the plugin template — accept when `CONTEXT.md` has a `## Language` section of `**Term**:` entries with `_Not_:` lines and no example values — source: domain-modeling skill
- [x] `R-02` ADRs follow the plugin template and the supersession rule — accept when every ADR carries `status:`/`date:` frontmatter; each ADR whose decision no longer holds has `status: rejected` and `rejected-note: Superseded by docs/adr/<new>.md` and no other change except removing its old `**Status:**` line; and each ADR that still holds keeps its original date — source: domain-modeling skill, user answer
- [x] `R-03` Existing design records match the model-design template — accept when each of the 3 records under `docs/design/models/` has `artifacts:` frontmatter and Grain, Decisions (`D-NN` with source), Rejected, Consumers, Evidence and History sections, and every statement still matches the built model — source: designing skill
- [x] `R-04` `AGENTS.md` exists at the repo root — accept when it follows `agents-md-template.md` sections and declares the Artifact Paths overrides this repo needs (layered `docs/design/models/<layer>/`, flat `models/staging/`, no `orchestration/`) — source: init skill, artifact-paths convention
- [x] `R-05` `.agents/rules/` holds the conventions the skills currently restate — accept when each rule file is one topic and `AGENTS.md` links to it — source: request
- [x] `R-06` `repo-map.json` exists — accept when it validates against the schema used by `vd-data-engineering` (`.claude/repo-map.schema.json`) and every path it lists exists — source: request
- [x] `R-07` CI bundle is installed — accept when `.github/` and `.workflow/ci-config.yml` come from `domain-cicd` for `duckdb_local` and `validate_ci_config.py` exits 0 — source: install-ci skill
- [x] `R-08` `.gitignore` carries the plugin fragments — accept when it ignores `**/secrets.toml`, `.agents_tmp/`, `*.log`, `*/target/`, `*/logs/` — source: add-or-update-source, dbt fragment
- [x] `R-09` `transformation/dbt_project.yml` profile uses the env-var form — accept when `profile:` is `"{{ env_var('DBT_PROFILE_NAME', 'nyc_taxi_analytics') }}"` and `dbt parse` still passes — source: generating-dbt-model skill
- [x] `R-10` All raw sources are loaded by dlt (TLC bronze, `ops_raw`, `mdm_raw`) — accept when `ingestion/` holds dlt pipelines, `.dlt/config.toml` `[sources.<name>]` sections and `docs/<connection>.yml` per the plugin layout, the dbt sources point at the dlt-loaded datasets, and `dbt build` still passes on the converted bronze — source: user answer, generating-dlt-pipeline and add-or-update-source skills
- [x] `R-11` Skill-change document is written — accept when `skill-changes.md` in this folder has one row per change with the skill name, the reference (file and section in the plugin), and the suggested change, covering everything pulled out of skills into `AGENTS.md`, `.agents/rules/` and `repo-map.json` and every gap in `skill-change-notes.md`, with a section on what `init` must do for greenfield and brownfield repos, derived from what this repo needed — source: user answer
- [x] `R-12` Silver is built in dbt — accept when `silver.*` is no longer produced by `tools/build_domain.py`; `stg_tlc__yellow_tripdata` and `stg_tlc__green_tripdata` are 1:1 with bronze; `int_trips_conformed` does the union, key and dedup the old `silver.trips` did with identical row count and `trip_key` set; downstream refs, sources, tests, `CONTEXT.md` and design records are updated; and a new ADR records that bronze is loaded by dlt and silver is built in dbt — source: user answer, ADR 0001
- [x] `R-13` Conventions inventory is settled — accept when every row in `conventions-inventory.md` has a Decision of skill, rule, or default-in-skill-override-in-rule, and the rule files in `.agents/rules/` contain exactly the ones decided as rule — source: user answer
- [x] `R-14` Domain terms added to `CONTEXT.md` and non-language sections removed — accept when the layers table, the known-data-characteristics section and the consumers section are gone, and each agreed term from the silver and gold models is a `## Language` entry with a business meaning and, where a synonym was rejected, a `_Not_:` line; no entry names a column, value or design decision; and each term can be traced to a model or design record — source: user answer, domain-modeling skill
- [x] `R-15` Architecture decisions are recorded as ADRs — accept when each ADR in the agreed list exists in `docs/adr/` at the next number in sequence, follows the plugin template with `status: decided` and today's date, names its considered options, and cites the model or file it governs; and no ADR still in force contradicts the code — source: user answer
- [x] `R-16` ADRs and design records link both ways — accept when every ADR still in force lists the design records it affects, every design record cites the ADRs behind its decisions as `ADR NNNN` with a link, the two sides agree (a design record that cites an ADR appears in that ADR's list, and the reverse), a design record that cited a superseded ADR now cites its successor, and `adr_lint.py` finds no dangling citation — source: user answer, studio ADR convention
- [x] `R-17` Content rules exist for context, ADRs and design records — accept when `.agents/rules/context.md`, `adr.md` and `design-records.md` state what belongs and what does not (including that design-record Consumers lists dependents only), `AGENTS.md` links to them, and `CONTEXT.md`, every ADR and every design record in the repo conform to them — source: user answer; draft in `rules-docs-draft.md`
- [x] `R-18` Intent requirement documents exist for demo and context — accept when each of the three agreed intents has a `requirement.md` under `intents/<slug>/` in the plugin format, each claim in it traceable to a real file, model or commit in this repo, and any reconstructed approval marked as reconstructed — source: user answer
- [x] `R-19` Repo documents are updated — accept when `AGENTS.md`, the contributor guide and `README.md` describe the repo as it is after the build (dlt ingestion, dbt silver, `repo-map.json`, `test-map.json` if added, `.agents/rules/`, the docs layout, where ADRs and design records live), and no document points at removed files such as `tools/download_bronze_data.py` — source: user answer
- [x] `R-20` Test map and unit tests exist — accept when `test-map.json` maps each layer or model group to its narrow `dbt build --select` command and the singular tests that guard it, every path and selector it names exists, and dbt unit tests cover `int_status_intervals` (tie-break and negative floor), `int_trips_enriched` (the three airport-fee states) and `int_trips_conformed` (dedup and key), passing under `dbt test --select test_type:unit` — source: user answer
- [x] `R-23` Python scripts have unit tests — accept when the orchestration scripts and the ingestion pipeline and generator code have pytest unit tests that run offline (network and DuckDB downloads stubbed or served from small fixtures), pass under one documented command, and are mapped in `test-map.json` beside the dbt lanes, with pytest listed in `repo-map.json` `test_frameworks` — source: user answer
- [x] `R-21` Semantic model exists — accept when MetricFlow YAML for the agreed metrics sits beside the gold marts with a `metricflow_time_spine`, every measure points at a committed gold column, and `dbt parse` passes — source: user answer, generating-semantic-model skill
- [x] `R-22` Orchestration scripts exist — accept when the agreed scripts run ingestion and `dbt build` end to end from a clean checkout, and `repo-map.json` `entrypoints` and `commands` name each one — source: user answer

## Business decisions

| Decision | Value | Source |
| --- | --- | --- |
| Run records | `plan.md`, `verify.md` and `case.md` are ignored. Only `requirement.md` is kept for intents, for demo and context | user answer |
| `requirements.md` location | `docs/setup/` | user answer |
| Purpose of this repo | The model answer: it reflects every convention and preference decision, so it shows what the Vibedata skills should produce when they do the right thing | user answer |
| Role of studio and `ext/vd-data-engineering` | Reference only: studio shows how agents get bearing (`AGENTS.md`, rules, `repo-map.json`, `test-map.json`); the plugin skills show how skills work today. Neither is modified | user answer |
| Where conventions live | Conventions and customer preferences (dbt/dlt paths, naming, testing, SQL style) move out of skills into this repo's `AGENTS.md` and `.agents/rules/`, so skills get lighter and per-customer preferences are a repo change, not a skill change | user answer |
| Rules path | `.agents/rules/` (the user's wording; studio's `.claude/rules/` is only an example) | user answer |
| Ownership principle | Skill = decided by the platform; rule (`AGENTS.md`, `.agents/rules/`) = decided by the operator. Each convention is listed in `conventions-inventory.md` and assigned an owner there | user answer |
| Two owners only | A convention belongs to the skill (platform) or to the operator (rules, repo-map). "Default in skill, override in rule" is not allowed: anything an operator can replace lives in the repo | user answer |
| Repo-map vs rules | Folders and artifact locations live in `repo-map.json`; other conventions live in `.agents/rules/` | user answer |
| Repo-map shape | Modelled on studio's `repo-map.json`, tailored for data engineering: adds `layers`, `sources`, `artifact_paths`; drops web-app fields and `conventions`. Each schema (`core`, `agg`, `finance`, `ops`, ...) has its own `layers` entry. Sketch in `repo-map-design.md` | user answer |
| Domain terms | `CONTEXT.md` gains domain terms drawn from the silver and gold models; the term list is agreed in brainstorm before writing | user answer |
| ADR supersession | An ADR whose decision no longer holds is superseded by a new ADR at the next number; the old ADR changes only its frontmatter. An ADR that still holds is left alone | user answer |
| ADR 0001 | Superseded: the conform decision is restated for the dbt build (`int_trips_conformed`), because it names `silver.trips`, built by a script | user answer (rule); application is mine |
| ADR 0002 | Superseded: it says every gold mart applies the billable rule, but only `mart_daily_zone_revenue`, `mart_monthly_service_summary`, `mart_revenue_component_bridge` and `agg_od_flow_matrix` filter on it. `fct_trip` exposes the flag; two aggregates and the quality scorecard report billable and non-billable counts; fleet-operations marts do not use it. `CONTEXT.md` already describes this correctly | user answer (rule); finding is from the SQL |
| ADRs to write (first set) | 0003 billable trip as applied (supersedes 0002); 0004 implausible trips are flagged, not deleted (closes the citation in `dbt_project.yml`); 0005 raw sources loaded by dlt; 0006 silver built in dbt (supersedes 0001); 0007 one `trip_key` definition, natural columns in the operator source; 0008 simulated sources as a dlt transformer; 0009 Type 2 only where the source versions history; 0010 driver ranking and utilisation definitions | user answer |
| ADR and design links | Design records cite their ADRs; ADRs list the design records they affect. Both sides are kept in the same commit. The ADR side is a body section, `## Affected designs`, with relative links; no frontmatter key | user answer |
| Pipeline design records | Each dlt pipeline (`tlc`, `ops`, `mdm`) gets a design record at `docs/design/pipelines/<pipeline>.md`, using the same template as model design records. Each resource's write disposition, incremental cursor and the three schema-contract axes are recorded as `D-NN` decisions, and the dbt sources it feeds are listed under Consumers. Models the build adds or changes (`int_trips_conformed`, the two new staging models, `stg_ops__trip_assignments`) also get design records | user answer; format from the plugin's `designing` skill and pipeline inventory template |
| Domain slug | `nyc-taxi-duckdb-demo` (`VD_DOMAIN_SLUG` in `.workflow/ci-config.yml`) | user answer |
| TLC source registration | Custom source under `ingestion/`, registered by hand-following the `add-or-update-source` section format; the gap is recorded in `skill-change-notes.md` | user answer |
| Domain terms | All candidate terms listed in `domain-terms.md` go into `CONTEXT.md` | user answer |
| Layers table | Dropped from `CONTEXT.md`: layout and ownership belong in `repo-map.json` `layers` and `docs/setup/data-provenance.md` | user answer |
| Data characteristics | Each entry in `CONTEXT.md`'s "Known data characteristics" becomes its own ADR, and the section is removed. Each ADR records the handling decision the code already makes, with the alternatives, and is checked against the SQL before it is written | user answer; mapping to ADRs proposed below |
| Data product, no audience | The repo describes a data product that anyone can use. `CONTEXT.md` and ADRs name no consumers or consuming teams; the repo reflects the product through its terms, ADRs, design records and requirements | user answer |
| ADRs for data characteristics | 0004 quality verdicts flag trips and never delete them (refunds, zero-distance, implausible); 0011 tips are measured only over payment methods that record them; 0012 unknown zones are retained and flagged, and each mart chooses whether to exclude them; 0013 no-charge and dispute payments are not excluded by the billable rule, and each metric decides | user answer |
| Terms for data characteristics | Refund, Zero-distance trip, Unknown zone, Unmeasured tip, and No-charge and dispute payments stay in `CONTEXT.md` as short terms; the ADR holds the decision | user answer |
| Consumers wording | Model descriptions name no audience; each design record's `## Consumers` lists dependents only (models and pipelines, from lineage) | user answer |
| Draft rules accepted | The text in `rules-docs-draft.md` for `context.md`, `adr.md` and `design-records.md` is accepted as written; `adr.md` also says business definitions qualify as ADRs | user answer |
| Content rules for docs | Three operator-owned rules: what goes into `CONTEXT.md`, what goes into an ADR, and what goes into a design record (including that Consumers lists dependents only). The skills read these rules instead of carrying their own copies | user answer |
| Skill-changes document | `skill-changes.md` lives in `docs/setup/` | user answer |
| Repo documents | `AGENTS.md`, the contributor guide and `README.md` are updated as a deliverable in the work plan | user answer |
| Open questions | Worked through with the `grill-with-docs` skill | user answer |
| Target repo | The work is built on branch `setup/nyctaxi-comp-repo` in `accelerate-data/sample-nyctaxi-comp` and raised as a PR there. Porting to `vibedata-showcase/nyc-taxi-duckdb` is a separate decision after checking whether it diverged. The README's "archived" note is corrected to match what GitHub shows | user answer |
| Pipeline form | Pipelines follow the plugin template and import `from vibedata.dlt.duckdb import setup_environment, finalize`. The package `vibedata-dlt-duckdb-studio` (0.11.0, pinned in the plugin's constraints, downloads from the configured index) is installed in a throwaway venv for local runs, with the sandbox variable pointing at a local DuckDB file. If `setup_environment()` cannot run outside Studio, local runs fall back to plain dlt and the pipeline design records say so | user answer |
| Design record layout | Layered: `docs/design/models/{layer}/{model}.md`, with `{layer}` taken from the `repo-map.json` `layers` keys; pipelines at `docs/design/pipelines/{pipeline}.md` | user answer (confirmed with the `artifact_paths` keys) |
| Test map and unit tests | Add `test-map.json` and dbt unit tests for `int_status_intervals`, `int_trips_enriched` and `int_trips_conformed` | user answer |
| Script unit tests | The orchestration scripts and the ingestion pipeline and generator code get pytest unit tests, mapped in `test-map.json`. "The scripts" read as those two groups; to be confirmed | user answer; scope provisional |
| Intent requirement documents | Three: `intents/trip-fact` (`fct_trip`, `int_trips_enriched`, `int_trips_conformed`; ADRs 0001 to 0004), `intents/status-occupancy` (`int_status_intervals`, `fct_status_interval`, occupancy; ADR 0010), and `intents/setup-dlt-ingestion` (this branch's `R-10` and `R-12`; ADRs 0005 to 0008). Reconstructed approval lines are marked as reconstructed, with no invented quotes. The old `intent/` folders in history stay there | user answer |
| Convention owners | Every row in `conventions-inventory.md` has a Decision. Overrides to my proposals: G1 (work branch) is skill; no transformation, casts, joins or filters in bronze is a rule; never dropping `_dlt_*` columns is a rule (now its own row, D8b); `access: public` requires an enforced contract stays a skill. All other rows as proposed | user answer |
| Repo-map `artifact_paths` | Keys: `design_record_model` (`docs/design/models/{layer}/{model}.md`), `design_record_pipeline`, `context`, `adr`, `dbt_project`, `dbt_sources`, `singular_tests`, `ingestion_root`, `pipeline`, `resource_docs`, `orchestration`, `test_map`. Intent paths are not in the repo-map: they are skill-owned (Studio sets the root). Skills read `layers.<x>.built_by` to choose a procedure; recorded as a skill change | user answer |
| Rule files | Eight files in `.agents/rules/`: `dbt-models.md`, `sql-style.md`, `dbt-testing.md`, `dlt.md`, `context.md`, `adr.md`, `design-records.md`, `git-and-prs.md`. Staging stays flat, declared in `repo-map.json` `layers.staging` | user answer |
| ADRs for business defaults | 0014 weeks start on Monday and `dim_date.week_start_date` is the single week boundary; 0015 a trip with no dimension match keeps a null key and an explicit flag, never a placeholder member; 0016 rates are rebuilt from summed numerators and denominators, and a zero denominator yields null. Each is checked against the SQL before it is written | user answer |
| Business defaults | Standing business answers (week boundary, null and unmatched-key handling, null aggregation) are ADRs, not rules. `capturing-requirements` asks only when no ADR answers the question | user answer |
| Decision capture | Every decision made during this setup is recorded in this file as it is made | user answer |
| Working branch | Isolated worktree `~/src/worktrees/setup/nyctaxi-comp-repo` (worktrees live in `~/src/worktrees/<branch name>`), branch `setup/nyctaxi-comp-repo` off `main` | user answer |
| dlt | Convert bronze loading from `tools/*.py` to dlt (`ingestion/`), so the repo is a full dlt + dbt model answer | user answer |
| Download | dlt pipelines fetch the TLC files themselves from the public TLC source; `tools/download_bronze_data.py` and the `raw/` pre-step are removed, so the repo looks like a real domain | user answer |
| Fleet ops source | `ops_raw` is built as a dlt transformer on the TLC trips, in the same pipeline run. It needs neither the warehouse nor a dbt model. The generated numbers will differ from today's | user answer |
| Trip key | `ops_raw.trip_assignment` carries the trip's natural columns, not `trip_key`. dbt derives `trip_key` in `stg_ops__trip_assignments` with the `trip_natural_key` macro, which is the only definition (`silver.trips` in `build_domain.py` goes away with silver) | user answer |
| Sampling | The 5% Bernoulli sample is dropped. Volume is limited only by loading 3 months | user answer |
| Data volume | TLC data limited to 3 months, 2024-01 to 2024-03, to keep the repo small | user answer |
| Reporting window | `report_start`/`report_end` change to the loaded months (2024-01-01 to 2024-04-01). ADR 0002, `CONTEXT.md`, README, provenance doc and the generators' hardcoded dates are updated to match | user answer |
| Reference data | If it is needed to load raw data, it is a dlt resource; if it is used in staging, it is a dbt seed. `payment_type_ref`, `rate_code_ref`, `vendor_ref` and `silver.zones`/`payment_types`/`rate_codes` are used by no dbt model, so they are dropped. The zone lookup CSV is loaded by dlt because the mdm generator needs it | user answer |
| Massaging in dlt | The preparation steps in the build scripts (sampling, hand-maintained reference tables, synthetic ops and mdm generation, load metadata) become part of the dlt pipelines, not separate scripts | user answer |
| dlt scope | dlt loads every external source: TLC bronze (trips Parquet, zone lookup), and the generated `ops_raw` and `mdm_raw`. Generators stop writing into the warehouse and become source simulators that write landing files for dlt to load | user answer |
| Silver in dbt | Convention-faithful: 1:1 staging per bronze table, then `int_trips_conformed` for union, key and dedup. `stg_tlc__trips` is renamed or reworked and downstream refs change | user answer |
| Orchestration | Scripts (possibly notebooks), described in `repo-map.json` `entrypoints` and `commands`, so agents can run ingestion and the dbt models. Form: scripts only, in `orchestration/` (`run_ingest.py` runs the dlt pipelines in order, `run_transform.py` runs `dbt build`, `run_all.py` chains them). No notebooks, no MotherDuck Flights or Fabric pipelines. This is how a DuckDB lakehouse is run, and `generating-orchestration` has no route for it today (recorded in `skill-change-notes.md`) | user answer |
| Semantic model | Included: MetricFlow YAML beside the gold marts and a `metricflow_time_spine`, per `generating-semantic-model`. Two semantic models: `fct_trip` (trip count, billable trip count, billable revenue per ADR 0003, fare residual summed) and `fct_shift` (shift count, online hours, occupancy rate from summed numerators and denominators, revenue per online hour per ADR 0010). Measurable tip rate and the mart-level aggregates are left out | user answer |
| Docs conformance | `CONTEXT.md`, ADRs and design records are updated to the plugin templates | user answer |
| Second deliverable | After the repo is built, reverse-engineer a list of skill changes, with a focus on what `init` must do for greenfield and brownfield setup so the other skills work efficiently | user answer |
| Order of work | Brainstorm and capture decisions, then define the plan, then build the repo, then derive the skill-change list | user answer |
| Semantic model / time spine | Not created | recommended, not yet confirmed |

## Out of scope

- Run records: `plan.md`, `verify.md`, `case.md`, execution evidence, `Ship-Step` history.
- dbt model, seed, macro and test changes beyond `R-09`.
- Design records for the other ~60 models (decide below).
- MotherDuck Flights and any `orchestration/` directory.
- Local git hooks under `.git/hooks`.

## Open questions

- dlt stamps `_dlt_load_id` and `_dlt_id`, which replace the current `_load_id`, `_source_file` and `_loaded_at`. Staging models and freshness checks that use the old columns need updating. Holds `R-10`.
- Execution method for the work plan: subagent-driven or native.

## Approvals

<!-- append-only; none recorded yet -->

## Verification

Checked on a clean clone of the branch on 2026-10-14. `python3 orchestration/run_all.py` exits 0 (about 56 s); `python3 -m pytest tests -q` 39 passed; `dbt test --exclude test_type:unit` 143 passed; `dbt test --select test_type:unit` 6 passed; `dbt parse` exits 0; `validate_ci_config.py` valid; `adr_lint.py` clean.

| Requirement | Evidence |
| --- | --- |
| R-01, R-14 | `CONTEXT.md` has only a `## Language` section with 34 terms and no digits-led values; layers, data characteristics and consumers are gone |
| R-02, R-15 | 16 ADRs; 0001 and 0002 `status: rejected` with `rejected-note`; 0003 to 0016 have Considered options, Consequences, Affected designs and today's date; checked by script |
| R-03 | 17 design records have `artifacts:` frontmatter and all six sections; Consumers lists dependents only |
| R-04 | `AGENTS.md` follows the template sections. The artifact-path overrides (layered design records, flat staging, no `orchestration/` Flights) are declared in `repo-map.json`, not `AGENTS.md`, per the later decision that locations live in the repo-map |
| R-05, R-17 | eight rule files, each one topic, indexed in `AGENTS.md`; every Rule row in `conventions-inventory.md` is in exactly one |
| R-06, R-20, R-23 | `tests/test_maps.py` (12 tests) validates the repo-map, its paths and every test-map selector |
| R-07 | `.github/` and `.workflow/ci-config.yml`; `validate_ci_config.py` valid. The local git hooks the bundle also writes were not installed (out of scope) |
| R-08, R-09 | `git check-ignore` confirms `**/secrets.toml`, `.agents_tmp/`, `*.log`, `target/`, `logs/`; profile uses `env_var('DBT_PROFILE_NAME', ...)` and `dbt parse` passes |
| R-10, R-12, R-22 | three pipelines run from a clean clone; second runs leave counts unchanged; `int_trips_conformed` equals the replaced silver (9,722,362 rows, identical key set); `run_all.py` runs end to end |
| R-11 | `skill-changes.md`: 45 table rows, every skill covered, every quoted path exists |
| R-13 | all 82 rows of `conventions-inventory.md` have a Decision |
| R-16 | 0 dangling `ADR NNNN` citations; ADR and design-record links agree both ways; `adr_lint.py` clean |
| R-18 | three `intents/*/requirement.md`; every path, model and test they name exists; approvals marked reconstructed |
| R-19 | `README.md`, `AGENTS.md`, `CONTRIBUTING.md` updated; no reference to the removed scripts; relative links resolve |
| R-21 | `dbt parse` passes with 2 semantic models and 10 metrics (eight agreed plus two helper metrics MetricFlow ratios need) |

Not met: none. Deferred: column-level descriptions and `access:`/`contract:` on gold models were not audited against the plugin's `generating-dbt-model` rules.
