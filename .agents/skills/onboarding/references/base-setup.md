# Base setup

What every onboarded repo has, so the first build intent does not spend its calls discovering the environment. It comes from how agents, the sandbox and the CI bundle work, not from the repo's code.

## Empty Domain catalog

Check the Domain catalog first. An Intent builds only what it changes and defers everything else to the Domain's released models (`--defer --state /cache/prod-target`). When the Domain has no released model, there is nothing to defer to: every unselected `ref()` fails, every source the Intent did not load reads an empty Domain, and the base commands, data tests and dry run have nothing to read.

Releasing the Domain is not a sandbox step: a release writes the Domain catalog, and the CI bundle publishes its production manifest; the sandbox never writes the Domain. Write a proposal under `docs/proposal/` for seeding it (the sources, their size, the steps, what blocks it), and run the base commands on a sample load of every source (`run_notebook.py --limit <N>`, the plugin's `databricks/dlt.md` § Sandbox run) into this Intent's schemas in the Ephemeral catalog, building without `--defer`. `macros/source_defer.sql` reads the Intent's own load of a source before the Domain's.

That data stays in this Intent: the Domain is still empty for later Intents. Say so in the PR description.

## Existing Domain views

When the Domain holds data, check its existing views before the base commands. No Intent can repair a Domain view, so a broken one stays broken for every later Intent until a release fixes it. Include views outside the dbt project and views without tests. The check is read-only: never create, replace or drop a view, and never write the Domain.

An Intent reads a Domain view the way it reads a table: a dbt view through `--defer`, any other by its three-part name. Read them with `lakehouse_query` on the `domain` target.

1. Take the Domain catalog from `VD_DOMAIN_DATABRICKS_CATALOG`, never from a file. List its views from the catalog's `information_schema` with `lakehouse_query` (`target=domain`), without the `information_schema` schema itself.
2. Bind each view without reading rows: `select * from <catalog>.<schema>.<view> where 1 = 0`. To save calls, bind up to 50 in one statement, `select 1 from <view a> where 1 = 0 union all select 1 from <view b> where 1 = 0 ...` (`select 1`, because views with different columns cannot be unioned as `select *`), and bind one by one only the views of a batch that fails.
3. Record the views checked, failed and unchecked, and each failing view with the object or column it cannot find, in this Intent's verification record. A timeout, an unavailable tool or a truncated list makes the check incomplete, never a pass.
4. In the `onboarding` review, file each failure as a `bug` finding, naming the view and the missing object or column, not raw SQL. Say that no Intent repairs the Domain: the fix is a release that rebuilds or drops the view.

A Domain with no views makes the check not applicable; record that.

## Base commands

Put these in `repo-map.json` `commands`, using the repo's own paths: `dbt_deps`, `dbt_parse`, `dbt_build`, `python_tests`, `python_lint`, plus the run scripts if the repo has them, and one entry per CI check script an agent should run rather than read (for example `adr_lint` for `.github/scripts/vibedata_domain_ci/adr_lint.py`).

In the design phase, after the Domain view check and before the inventory, run each once in the sandbox: plain `dbt` with `--target databricks_sandbox` and `--defer --state /cache/prod-target` (as the plugin's `databricks/dbt.md` § Sandbox run and § Defer give it), after `dbt deps` when `packages.yml` exists. dbt needs the `profile:` line from [Changes the build needs](#changes-the-build-needs) first. Record every result. A failure you cannot fix with a change from the two lists below is a review finding, `platform` or `bug`.

## Changes the build needs

The only edits to existing files. List each in the PR description.

| File | Change | Why |
| --- | --- | --- |
| `dbt_project.yml` | `profile: dbt_databricks` | The name Studio exports as `DBT_PROFILE_NAME` for a Databricks Intent, so the sandbox finds it. Write it literally: with `env_var(...)` there, the bundle job's dbt task fails with `Could not find profile named ...`. `transformation/profiles.yml` keeps the same name for local runs. |
| `_sources.yml` (every sources file) | Set each source's `database:` to `"{{ env_var('VD_DOMAIN_DATABRICKS_CATALOG', target.database) }}"`, remove any var that feeds it or its `schema:`, and give the schema as a literal. Remove the then-unused vars from `dbt_project.yml`. | In an Intent the target catalog is the Ephemeral catalog, so a source without a `database` reads only that. The env var names the Domain's catalog in an Intent without writing it into the file; in a release the `prod` target's catalog is the Domain's. `macros/source_defer.sql` reads the Intent's prefixed copy of a source in the Ephemeral catalog when the Intent loaded it, and otherwise the Domain table the YAML names. |
| `profiles.yml` (the repo's own) | A `prod` target on the Domain's production catalog and Primary Schema, as in [templates/dbt/profiles.yml](../templates/dbt/profiles.yml). Never an Ephemeral catalog, a mirror schema or a workspace host. If `prod` already differs, ask the user to fix it rather than rewriting it. | Studio ignores this file in an Intent, which runs on its own `dbt_databricks` profile; the map tests parse and list with it. |
| `dbt_project.yml` | Under `models:` and `seeds:`, `dbt_project_evaluator: +enabled: "{{ var('dbt_project_evaluator_enabled', false) }}"` | Keeps the evaluator out of normal builds; the repo's quality workflow, where it has one, and `verifying` switch it on. Only with the `packages.yml` entry below. |

## Behaviour-free cleanups

Make the base parse clean, so agents have no warnings to chase. Prove each change leaves the test list and the compiled SQL of every test identical (`dbt ls --resource-type test` and `dbt compile --select resource_type:test`, before and after), and list it in the PR.

- Generic-test arguments nested under `arguments:` (`- relationships: {arguments: {to: ..., field: ...}}`), which removes `MissingArgumentsPropertyInGenericTestDeprecation`.
- `dbt_project.yml` config paths that apply to no resource (for example a `snapshots:` block with no snapshots) removed.

Any other warning the parse shows is a `style` finding.

## Files onboarding adds

Only when the repo has none. When the repo has its own that conflicts, leave it and file the difference.

| File | Content |
| --- | --- |
| `macros/source_defer.sql` (dbt) | Copy the plugin's `_family/shared-container/templates/source_defer.sql` into the project's macro path unchanged. If the project already overrides `source()`, merge and say so in the PR. dbt's `--defer` rewrites `ref()` but never `source()`; without the macro a source always reads the Domain's table, never the Intent's own load. Part of setting up the dbt models, not a review finding. |
| `macros/generate_schema_name.sql` (dbt) | Copy the plugin's `_family/shared-container/templates/generate_schema_name.sql` unchanged. dbt's built-in builds `<target schema>_<custom>`; the macro lands a `+schema:` node in `<VD_EPHM_SCHEMA_PREFIX><name>` in a sandbox and in `<name>` in prod. Without it Studio's sandbox guard refuses every schema the build creates. |
| `packages.yml` entry | `dbt-labs/dbt_project_evaluator`, `version: [">=1.1.0", "<2.0.0"]`, added to an existing `packages.yml` or a new one. The repo's quality workflow builds it where it has one; the Databricks CI bundle installs none. |
| `tests/test_adr_links.py` | Copy [templates/tests/test_adr_links.py](../templates/tests/test_adr_links.py): every design record that cites an ADR is in that ADR's `## Affected designs`, and every record listed there exists and cites it. `adr_lint` checks only numbering and dangling citations. |
| `tests/test_maps.py` | Every map path exists; every source is registered; every `test-map.json` dbt selector resolves to a test. Its dbt calls name the repo's own profile (`--profiles-dir <dbt project> --profile <name>`) and run `dbt deps` once when `dbt_packages/` is missing, so they pass locally, in the sandbox and in CI. |
| `ruff.toml` | `[lint] select = ["E4", "E7", "E9", "F"]`, and `extend-exclude` with any paths the repo's documented lint command or CI already excludes (for example `--extend-exclude ingestion/sources`). Ruff's default selection changes between releases. Fix nothing it reports; file the findings as `style`. |
| `.gitignore` lines | Appended to the existing `.gitignore` (or a new one), only the lines missing from [`gitignore-fragment`](../templates/repo/gitignore-fragment), with the repo's own dlt preview path. If `.user.yml` files are tracked, `git rm --cached` them. |

## Repo checks

The map tests and the ADR link test are the Domain's own checks; the CI bundle does not run them. Ask the user where they run, as one grilling question. Recommended: a repo workflow, [templates/repo/repo-checks.yml](../templates/repo/repo-checks.yml) at `.github/workflows/repo-checks.yml`, which installs `requirements-dev.txt` and runs `python_tests` on every pull request. A pre-commit hook is the other option; if the user wants one, say that setting `core.hooksPath` stops git reading `.git/hooks`, where the CI bundle installs its own hooks, so the repo hook must call them.

## Convention skills

Copy these from [templates/skills/](../templates/skills/) as they are, each `<name>.md` becoming `.agents/skills/<name>/SKILL.md` (the templates are not named `SKILL.md`, so the agent does not load them as skills); only examples may change to the repo's own. When the repo's confirmed inventory says otherwise (its own commit format, for example), the inventory wins for that line.

| Skill | What it holds |
| --- | --- |
| `context` | What goes in `CONTEXT.md` and what does not. |
| `design-records` | What goes in a design record: decisions with sources, consumers from lineage; no evidence (that is for verification). |
| `adr` | The three tests, what is not an ADR, content, supersession. |
| `git-and-prs` | Commit format, staging named files (never `git add .`), the four PR-body sections the `shipping` skill fills. |
| `workarounds` | The open platform gaps, each with what removes it: `plan.md` and `verify.md` written once per phase, large files changed by script, verify from the landed table and saved profile, the Tier-1 dev dataset, sample loads that land whole yields. |

Write these into the repo's own convention skills beside its conventions:

| Skill | Rule |
| --- | --- |
| `dlt` | Sample loads (`run_notebook.py --limit <N>`) while a pipeline is written; one full load at most per intent, at the end, only when the requirement asks for loaded data. `replace` is proven with two sample loads (the limit's row count and one load package), never a second full load. |
| `dlt` | Profile a remote source file once per intent into `.agents_tmp/<source>-profile.json`, and take every later figure from it. |
| `dlt` | To see whether a source exists, read `repo-map.json` `sources`; query the catalog with `lakehouse_query` only for data questions. |
| `dbt-models` | Sources name the Domain's catalog as their `database` through `"{{ env_var('VD_DOMAIN_DATABRICKS_CATALOG', target.database) }}"`, never a literal catalog, a literal schema and tables, and no var feeds the schema or tables. |
| `dlt` | Mirror the repo's existing source of the same kind for batching and file handling. |
| `adr` | Check citations with the `adr_lint` command (or the repo's equivalent) and the two-way links with `tests/test_adr_links.py`; run them, do not read the scripts. |
| `dbt-models` | dlt lands timestamps as `timestamp` in UTC, and a date as whatever type the source yields (a `DATE` as `date`; a date the source computes as a timestamp lands as one at UTC midnight): staging carries every dlt-loaded timestamp as the wall-clock value the source recorded, casts a `date` column with `cast(... as date)`, and turns a midnight timestamp into its calendar day without letting the session's zone move it; a sample load shows whether bronze already holds the wall-clock value, and the skill names a conversion only if one is needed. |
| `dbt-models` | YAML (tests, contracts, `columns:`) names a bronze column by its landed name: dlt folds column names to lower case on Databricks, so `VendorID` lands as `vendorid`. |
| `dbt-testing` | A left join on a derived key gets a singular test that every left row finds its match, or that the unmatched rows are the expected ones. |
| `dbt-testing` | Rebuilt values are compared at the cent for money and at a stated tolerance otherwise, never by hashing raw doubles: Spark float aggregation is not reproducible bit for bit. |

## Agent entry points

- `AGENTS.md` starts with a Startup section: before a task, invoke the convention skill for the task (`dlt` to add a source, `dbt-models` for a model); do not read README, CONTRIBUTING or other human documents for a pipeline or model change. Read `repo-map.json` whole, once: its `modules`, `artifact_paths` and `sources` are the index of the repo, so do not list directories or read it again in parts.
- The Startup section also says not to read the installed source of dbt, dlt or any other library: the repo's own models, pipelines and tests are the reference, and the library's documentation covers the rest. Agents otherwise read dbt's package source to answer questions such as how a unit test overrides a var.
- Material that is not for build tasks (setup or maintenance notes, demo or evaluation prompts, answer keys) is declared in `key_directories` and `notes_for_agents` as not read. Prompts used to test agents are an answer key: file a `gap` finding recommending a move into the maintenance folder.
- Artifact paths: no `## Artifact Paths` table in `AGENTS.md`. The plugin has no default locations, so `repo-map.json` `artifact_paths` declares every class it writes: `requirement`, `plan`, `verification` and `case_record` (each with the `{intent}` name the plugin gives an intent), `design_record_model`, `design_record_pipeline` and `design_record_area`. A repo without them makes the build agent stop and ask for onboarding.
- `repo-map.json` `notes_for_agents` has at least: `startup`; `new_source` (a new source mirrors an existing `sources` entry and creates every artifact it lists); `reviews_and_proposals`; and, when pipelines use the Vibedata dlt package, the environment variables they need outside Studio.

## Checks for the onboarding review

File each as a finding when it fails; change nothing.

| Check | Kind when it fails |
| --- | --- |
| Parquet or Arrow sources stamp `_dlt_load_id` and `_dlt_id` (`[normalize.parquet_normalizer] add_dlt_load_id`, `add_dlt_id`) | `platform` |
| Staging reads bronze only through `source()` | `platform` |
| Staging carries dlt-loaded timestamps as the source's wall-clock value | `bug` if a key or join depends on them, else `convention` |
| Each Lakeflow job's dbt task runs `dbt deps` before building when the project has a `packages.yml` | `bug` |
| Each pipeline notebook has every widget and cell of the plugin's `databricks/templates/dlt-pipeline.ipynb` | `platform` |
| The plugin's `validate-job.py` exits 0 on the committed bundle (`databricks.yml`, `orchestration/*.job.yml`) | `platform` |
| `.sqlfluff` (or the SQL lint config) uses the `databricks` dialect and the jinja templater, with every macro but `source_defer.sql` loaded | `gap` |

## Verify

The base commands pass, or each failure is a filed finding. `tests/test_maps.py` passes in the sandbox. A sandbox build of one model with `--defer --state /cache/prod-target` resolves every unselected `ref()` and `source()` against the Domain.
