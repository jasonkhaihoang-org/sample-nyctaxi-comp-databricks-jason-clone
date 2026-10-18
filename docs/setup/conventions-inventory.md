# Conventions inventory

Every convention, preference and default found in the `vibedata-data-engineering` skills, with who should own it.

- **Skill** = decided by the platform. Same for every customer; changing it changes how Vibedata works.
- **Rule** = decided by the operator. Lives in `.agents/rules/`; each customer can differ.
- **Repo-map** = where things live. Folders and artifact locations are declared in `repo-map.json`, which skills read; rules hold the other conventions.

There is no "default in skill, override in rule" category: if an operator can replace it, it is not the skill's. A skill may still ask when the repo declares nothing, but it does not own a default.

The **Proposed** column is my starting point for the brainstorm. Nothing here is decided until the **Decision** column says so. Source skill names are the plugin skills that state or enforce the convention today.

## Decided

- No "default in skill, override in rule". A convention is owned by the skill or by the operator, not both.
- Folders and artifact locations go in `repo-map.json`. Rules hold the other conventions.

## Principle (to confirm)

Operator-owned when it is a preference that does not change whether the platform's loop is correct or safe: names, layout, style, thresholds, business defaults. Platform-owned when the loop, a safety property, or a CI check depends on it.

**Tension (still open):** several formats (design-record sections, ADR frontmatter, plan and verify tables) are read by CI scripts (`design_drift.py`, `adr_lint.py`, `gate_sweep.py`). If an operator can change them, those scripts must read the rule instead of assuming the default.

## A. Artifact locations

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| A1 | Requirement / plan / certification / case live at the plugin defaults: `docs/requirement/`, `docs/plans/`, `docs/verify/`, `docs/cases/`, named `<date>-<title>-<slug suffix>.md` (artifact-paths convention, `c5c4ba7`) | artifact-paths (all stage skills) | Skill | Skill; no `AGENTS.md` override table (`skill-changes.md`) |
| A2 | Model design record at `docs/design/models/<model>.md`; layered `<layer>/<model>.md` is an override | designing, artifact-paths | Repo-map | Repo-map |
| A3 | Pipeline design at `docs/design/pipelines/<pipeline>.md`; area design at `docs/design/<area>/<subject>.md` | designing | Repo-map | Repo-map |
| A4 | One durable design record per model, amended by later intents, never per intent | designing, planning | Skill | Skill |
| A5 | `CONTEXT.md` at repo root; ADRs at `docs/adr/NNNN-<slug>.md`, numbered sequentially | domain-modeling | Repo-map | Repo-map |
| A6 | Scratch in `.agents_tmp/`, never committed | executing-the-plan, planning | Skill | Skill |
| A7 | Locations come from `repo-map.json`; an existing artifact is continued where it lives, never moved | artifact-paths | Skill (reads repo-map) | Skill (reads repo-map) |

## B. dbt

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| B1 | Medallion mapping: bronze = raw ingest, silver = staging + intermediate, gold = marts | init template | Rule | Rule |
| B2 | Model prefixes `stg_` / `int_` / `fct_` / `dim_`; no `_fact`/`_dimension` suffix | init template | Rule | Rule |
| B3 | Staging named `stg_<source>__<entity>`; staging is 1:1 with a source table | init template | Rule | Rule |
| B4 | Folder layout: `staging/<source>/`, `intermediate/`, `marts/<area>/` | init template | Repo-map | Repo-map |
| B5 | Every model has a colocated schema YAML with description and tests | init template, generating-dbt-model | Skill (a bare model fails verification) | Skill (a bare model fails verification) |
| B6 | YAML file naming (`_<folder>.yml` vs `<model>.yml`) | not specified | Rule | Rule |
| B7 | SQL style: lowercase keywords, snake_case, explicit joins, one clause per line | init template | Rule | Rule |
| B8 | Explicit column list in models; no `select *` in marts | generating-dbt-model | Rule | Rule |
| B9 | `access:` set explicitly; `access: public` requires `contract: {enforced: true}` and a `data_type` on every column | generating-dbt-model, shipping | Skill (shipping depends on it) | Skill (shipping depends on it) |
| B10 | Mart states its grain in a comment on the `final` CTE; description opens with the grain | generating-dbt-model | Skill | Skill |
| B11 | No empty / TBD / placeholder descriptions (halts `DOCS_PLACEHOLDER_FOUND`) | generating-dbt-model | Skill | Skill |
| B12 | Audit columns (`_loaded_at`, `_dbt_invocation_id`, `_git_sha`) only if required; marts only; all-or-none | generating-dbt-model | Rule | Rule |
| B13 | `profile:` set as `env_var('DBT_PROFILE_NAME', '<name>')` | generating-dbt-model | Skill (sandbox targeting) | Skill (sandbox targeting) |
| B14 | No dbt `versions:` / `deprecation_date`; breaking change = new model beside the old (dual-write) | designing, shipping | Skill | Skill |
| B15 | Default materialisation per layer (view / table / incremental) | not specified | Rule | Rule |
| B16 | `.gitignore` fragments for dbt (`*/target/`, `*/logs/`, `dbt_packages/`, `.user.yml`) | generating-dbt-model | Skill | Skill |
| B17 | dlt-loaded timestamps are converted with `timezone('UTC', col)` in staging | trip-key bug in setup | Rule | Rule |
| B18 | Sources name a schema, never a database | Studio sandbox is a renamed copy of the Domain file | Rule | Rule |

## C. Testing and quality

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| C1 | PK gets `unique` + `not_null`; FK to a conformed dimension gets `relationships` | init template, generating-dbt-model | Rule | Rule |
| C2 | Source freshness where the source lands on a schedule | init template | Rule | Rule |
| C3 | Data tests and unit tests run as separate commands (`--exclude test_type:unit`, then `test_type:unit`) | verifying | Skill | Skill |
| C4 | Where singular tests live; naming `assert_*` | not specified | Repo-map (location); rule (naming) | Repo-map (location); rule (naming) |
| C5 | When a unit test is required (which models) | not specified | Rule | Rule |
| C6 | `dbt_project_evaluator` advisory run, or `not applicable` if absent | verifying | Skill | Skill |
| C7 | Never loosen a test to pass (weakening needs a design decision plus an approval) | verifying | Skill | Skill |
| C8 | Docs must match data: every number/rule in descriptions, design records, ADRs, `CONTEXT.md` matches the built relation | verifying | Skill | Skill |
| C9 | Dev-artifact scan (no `dev_mode`, `.add_limit()`, edited profile target committed) | verifying | Skill | Skill |
| C10 | A left join on a derived key gets a rejoin test | trip-key bug in setup | Rule | Rule |

## D. dlt and bronze

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| D1 | dlt project is flat at `ingestion/`; no `pipelines/<name>/` or `connections/<name>/` | generating-dlt-pipeline | Repo-map | Repo-map |
| D2 | Connections only as `[sources.<name>]` in `ingestion/.dlt/config.toml`, written by `add-or-update-source` | add-or-update-source | Skill | Skill |
| D3 | Source name matches `^[a-z][a-z0-9_]*$` | add-or-update-source | Skill | Skill |
| D4 | Secrets: never read, echoed or written; secret-store name shape depends on store kind | add-or-update-source | Skill | Skill |
| D5 | Dataset name `src_<connection>` unless the section sets `schema` | generating-dlt-pipeline | Rule | Rule |
| D6 | Write disposition per resource: append for events, replace for snapshots, merge for mutable records | generating-dlt-pipeline | Rule | Rule |
| D7 | Schema contract defaults: columns freeze, tables evolve then freeze, data_type freeze | generating-dlt-pipeline | Rule | Rule |
| D8 | No transformation, casts, joins or filters in bronze | generating-dlt-pipeline | Rule | Rule |
| D8b | Never drop or alias `_dlt_*` columns | generating-dlt-pipeline | Rule | Rule |
| D9 | Pipeline calls `setup_environment()` / `finalize()`; never hand-written otherwise | generating-dlt-pipeline | Skill | Skill |
| D10 | Sample load default of 1,000 rows, or `Load: full` | planning, generating-dlt-pipeline | Rule | Rule |
| D11 | `ingestion/docs/<connection>.yml` per connection, one field entry per emitted column | generating-dlt-pipeline | Skill | Skill |
| D12 | Preview file written only by `vd-dlt-preview.sh` | generating-dlt-pipeline | Skill | Skill |
| D13 | Source registration committed alone | add-or-update-source | Skill | Skill |
| D14 | Local-files feeds are a one-off load, not scheduled | add-or-update-source | Rule | Rule |
| D15 | Reference data needed to load raw is a dlt resource; reference data used in staging is a dbt seed | user answer | Skill | Skill |
| D16 | Profile a remote source file once per intent and reuse the saved profile | HVFHV run analysis (9 to 12 reads of the same file per run) | Rule | Rule |

## E. Docs: glossary, ADRs, design records

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| E1 | `CONTEXT.md` is business language only: no columns, types, row counts, lineage, design decisions, example values | domain-modeling | Rule | Rule |
| E2 | Glossary entry format `**Term**:` + meaning + `_Not_:` line | domain-modeling | Skill (agents parse it) | Skill (agents parse it) |
| E3 | ADR bar: hard to reverse AND surprising AND a real trade-off between named alternatives | domain-modeling | Rule | Rule |
| E4 | ADR frontmatter `status: decided`, `date:`; sections Considered options, Consequences | domain-modeling | Skill (`adr_lint.py`) | Skill (`adr_lint.py`) |
| E5 | Supersede by writing a new ADR and changing only the old one's frontmatter | domain-modeling | Skill | Skill |
| E6 | Design record sections Grain, Decisions (`D-NN` with source), Rejected, Consumers, Evidence, History | designing | Skill (`design_drift.py`) | Skill (`design_drift.py`) |
| E7 | Dates and numbers recomputed at write time; ADR date is the day written | domain-modeling | Skill | Skill |
| E8 | Precedence when sources disagree: design record > `CONTEXT.md`/ADR > `.openhands/memory/` | domain-modeling | Skill | Skill |
| E9 | Design-record Consumers lists dependents only (from lineage); no teams, reports or audiences | user answer | Rule | Rule |
| E10 | `CONTEXT.md` excludes layers, columns, example values, consumers and platform terms | user answer | Rule | Rule |
| E11 | ADRs name no consumers or audiences and no example values; each lists its affected designs | user answer | Rule | Rule |

## F. Requirement capture and defaults

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| F1 | Thresholds, cut-offs, rank bases and population rules are asked, never picked from data | capturing-requirements | Skill | Skill |
| F2 | Grain stated as one sentence per mart | capturing-requirements | Skill | Skill |
| F3 | Reuse check: ask whether to build on an existing published model | capturing-requirements | Skill | Skill |
| F4 | Week boundary, null/unmatched-key handling and NULL aggregation are asked | transformation playbook | ADR (standing business answers); skill asks only if no ADR answers it | ADR (standing business answers); skill asks only if no ADR answers it |
| F5 | Approval wording limited to `approved`, `go ahead`, `proceed`, `yes`, `lgtm` | capturing-requirements | Skill | Skill |
| F6 | Maximum 5 investigation rounds in reconciliation; 1,000-row detail limit | reconciliation | Skill | Skill |

## G. Git, PRs and safety

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| G1 | Work branch `intent/<slug>`; push each turn that committed | git-workflow | Rule (branch naming) | Skill (Studio assigns the branch name) |
| G2 | Stage named files only; never `git add .`; one concern per commit | git-workflow | Skill | Skill |
| G3 | Never force-push, never skip hooks, never rebase | git-workflow, shipping | Skill | Skill |
| G4 | Commit message format | shipping | Rule (format) | Rule (format) |
| G4b | `Ship-Step:` trailer on ship commits | shipping | Skill | Skill |
| G5 | PR body sections Summary, Verification, Approved contract changes, Remaining manual checks | shipping | Rule | Rule |
| G6 | One PR per head ref; reuse an open one | shipping | Skill | Skill |
| G7 | Builds and tests only in the sandbox; never against the Domain/prod target; never open `profiles.yml` | executing-the-plan | Skill | Skill |
| G8 | No `--full-refresh` of a published model without recorded approval | executing-the-plan | Skill | Skill |
| G9 | Code only: never deploy, schedule or publish | generating-orchestration, generating-semantic-model | Skill | Skill |

## H. Semantic layer and orchestration

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| H1 | MetricFlow spec chosen by `dbt --version` (Fusion vs Core); never mix | generating-semantic-model | Skill | Skill |
| H2 | One semantic model per fact-grain mart; one primary entity; one time dimension | generating-semantic-model | Skill | Skill |
| H3 | Time spine ships with the first metric | generating-semantic-model | Skill | Skill |
| H4 | Orchestration at `orchestration/<Name>.Flight/` with `flight.py`, `requirements.txt`, `config.json` | generating-orchestration | Skill (platform-specific) | Skill (platform-specific) |
| H5 | Schedules are five-field UTC cron; local time converted with the arithmetic shown | generating-orchestration | Skill | Skill |

## I. CI

| # | Convention | Today in | Proposed | Decision |
| --- | --- | --- | --- | --- |
| I1 | CI bundle files are overwritten on refresh; `.workflow/ci-config.yml` is created once and owned by the repo | install-ci | Skill | Skill |
| I2 | Studio provisions CI variables and secrets; skills add none | install-ci | Skill | Skill |
