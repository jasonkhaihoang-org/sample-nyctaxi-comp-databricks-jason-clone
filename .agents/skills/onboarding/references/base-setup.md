# Base setup

What every onboarded repo has, so the first build intent does not spend its calls discovering the environment. It comes from how agents, the sandbox and the CI bundle work, not from the repo's code.

## Empty Domain Lakehouse

Check the Domain Lakehouse first. An Intent builds only what it changes and defers everything else to the Domain's released models (`--defer --state /cache/prod-target`). When the Domain has no released model, there is nothing to defer to: every unselected `ref()` and `source()` fails, and the base commands, data tests and dry run have nothing to read.

Releasing the Domain is not a sandbox step: a release writes the Domain Lakehouse and publishes its production manifest, and the sandbox never writes the Domain. Write a proposal under `docs/proposal/` for seeding it (the sources, their size, the steps, what blocks it), and run the base commands on a sample load of every source (`DLT_INGEST_LIMIT`) in this Intent's Ephemeral Lakehouse, building without `--defer`.

That data stays in this Intent: the Domain is still empty for later Intents. Say so in the PR description.

## Existing Domain views

When the Domain holds data, check its existing views before the base commands. No Intent can repair a Domain view, so a broken one stays broken for every later Intent until a release fixes it. Include views outside the dbt project and views without tests. The check is read-only: never create, replace or drop a view, and never write the Domain.

A Lakehouse holds two kinds of view, and each tool sees only one:

- **Spark views**, which dbt's `view` materialisation and notebooks create. An Intent's build reads them through `--defer`, so a broken one fails each Intent that selects a model reading it. In a schema-enabled Lakehouse, Spark stores each one's references expanded to `` `workspace`.`lakehouse`.`schema`.table ``, so the Intent's same-named Ephemeral Lakehouse never captures them. Renaming the Domain's workspace breaks every one, as does dropping an object or column a view reads. `lakehouse_query` cannot see them; reach them with `dbt show` in the sandbox.
- **SQL analytics endpoint views** (T-SQL). The build never reads them, but agents and users do, through `lakehouse_query`, the only tool that sees them.

The check needs a schema-enabled Domain Lakehouse. Its released manifest's relation names are then four-part, which `macros/source_defer.sql` also requires. In a Lakehouse without schemas, `SHOW VIEWS` from another Lakehouse's session returns nothing even when views exist, so record the Spark half as unchecked, never as no views, and file it as a `platform` finding.

1. Take the Domain's workspace and Lakehouse names from the four-part relation names in `/cache/prod-target/manifest.json`. List its schemas with `lakehouse_query` (`target=domain`): `SELECT name FROM sys.schemas`, without `sys`, `INFORMATION_SCHEMA`, `guest`, `queryinsights` and the `db_` roles. Add any schema the manifest names that the list lacks.
2. `dbt show` needs the `profile:` line from [Changes the build needs](#changes-the-build-needs) and, when `packages.yml` exists, `dbt deps` through the wrapper; make that edit and run that first. List each schema's Spark views from the dbt project directory, quoted exactly as below (the wrapper re-parses its argument, so the backticks stay escaped):

   ```bash
   cd <dbt project> && dbt show --inline "SHOW VIEWS IN \`<workspace>\`.\`<lakehouse>\`.\`<schema>\`" --limit -1 --target ephemeral_dev
   ```

   Keep `--limit -1`: without it dbt appends a `limit`, which `SHOW` rejects.
3. Bind each Spark view without reading rows:

   ```bash
   cd <dbt project> && dbt show --inline "select * from \`<workspace>\`.\`<lakehouse>\`.\`<schema>\`.\`<view>\` where 1 = 0" --target ephemeral_dev
   ```

   Leave the `limit` to dbt; a second one is a syntax error. Each `dbt show` starts its own Spark session, so bind up to 50 views in one statement, `select 1 from <view a> where 1 = 0 union all select 1 from <view b> where 1 = 0 ...` (`select 1`, because views with different columns cannot be unioned as `select *`), and bind one by one only the views of a batch that fails.
4. List the endpoint views with `lakehouse_query` (`target=domain`): `sys.views` joined to `sys.schemas`, without the system schemas above. Bind each with `SELECT TOP 0 * FROM [<schema>].[<view>]`. The endpoint lags the Lakehouse by minutes, so a table dropped just before the check can still bind.
5. Record, for each kind, the views checked, failed and unchecked, and each failing view with the object or column it cannot find, in this Intent's verification record. A timeout, an unavailable tool or a truncated list makes the check incomplete, never a pass.
6. In the `onboarding` review, file each failure as a `bug` finding, naming the view and the missing object or column, not raw SQL. Say that no Intent repairs the Domain: the fix is a release that rebuilds or drops the view. When the Domain holds Spark views, also file one `platform` finding: renaming its workspace breaks all of them.

A Domain with no views of either kind makes the check not applicable; record that.

## Base commands

Put these in `repo-map.json` `commands`, using the repo's own paths: `dbt_deps`, `dbt_parse`, `dbt_build`, `python_tests`, `python_lint`, plus the run scripts if the repo has them, and one entry per CI check script an agent should run rather than read (for example `adr_lint` for `.github/scripts/adr_lint.py`).

In the design phase, after the Domain view check (which runs `dbt deps` first) and before the inventory, run each once in the sandbox: plain `dbt` with `--target ephemeral_dev` and `--defer --state /cache/prod-target` (as the `workarounds` skill says), after `dbt deps` when `packages.yml` exists. Record every result. A failure you cannot fix with a change from the two lists below is a review finding, `platform` or `bug`.

## Changes the build needs

The only edits to existing files. List each in the PR description.

| File | Change | Why |
| --- | --- | --- |
| `dbt_project.yml` | `profile: "{{ env_var('DBT_PROFILE_NAME', '<current name>') }}"` | The sandbox selects its profile through `DBT_PROFILE_NAME`; a fixed name means no dbt command runs in the sandbox. Local and CI runs keep the current name. |
| `_sources.yml` (every sources file) | Remove each source's `database:` and any var that feeds it or its `schema:`; give the schema as a literal. Remove the then-unused vars from `dbt_project.yml`. | In an Intent, `macros/source_defer.sql` resolves a source in the Ephemeral Lakehouse and, under `--defer`, in the Domain's; a source that names a database is pinned to one Lakehouse. Schemas are the same in both. |
| `profiles.yml` (the repo's own, read by the Domain's dbt job notebooks and its release) | A `prod` target holding the Domain's literal coordinates, as in [templates/dbt/profiles.yml](../templates/dbt/profiles.yml); never an `env_var()`. If `prod` already uses one or a placeholder, ask the user to fix it rather than rewriting it. | A Fabric notebook has none of the agent's environment, so an `env_var()` cannot resolve there; Studio ignores this file in an Intent. |
| `dbt_project.yml` | Under `models:` and `seeds:`, `dbt_project_evaluator: +enabled: "{{ var('dbt_project_evaluator_enabled', false) }}"` | Keeps the evaluator out of normal builds; the CI quality workflow and `verifying` switch it on. Only with the `packages.yml` entry below. |

## Behaviour-free cleanups

Make the base parse clean, so agents have no warnings to chase. Prove each change leaves the test list and the compiled SQL of every test identical (`dbt ls --resource-type test` and `dbt compile --select resource_type:test`, before and after), and list it in the PR.

- Generic-test arguments nested under `arguments:` (`- relationships: {arguments: {to: ..., field: ...}}`), which removes `MissingArgumentsPropertyInGenericTestDeprecation`.
- `dbt_project.yml` config paths that apply to no resource (for example a `snapshots:` block with no snapshots) removed.

Any other warning the parse shows is a `style` finding.

## Files onboarding adds

Only when the repo has none. When the repo has its own that conflicts, leave it and file the difference.

| File | Content |
| --- | --- |
| `macros/source_defer.sql` (dbt) | Copy the plugin's `fabric_lakehouse/templates/source_defer.sql` into the project's macro path unchanged. If the project already overrides `source()`, merge and say so in the PR. dbt's `--defer` rewrites `ref()` but never `source()`; without it every source fails in a sandbox that holds only what the Intent builds. Part of setting up the dbt models, not a review finding. |
| `macros/generate_schema_name.sql` (dbt) | Copy [templates/dbt/generate_schema_name.sql](../templates/dbt/generate_schema_name.sql) (the plugin's `fabric_lakehouse` template). Delete any `fabricspark_generate_schema_name_for_env.sql`: the adapter never calls it. `dbt-fabricspark` honours a custom `+schema` only on a target named `prod`; without the override a sandbox build puts every model in one schema and defer breaks. |
| `packages.yml` entry | `dbt-labs/dbt_project_evaluator`, `version: [">=1.1.0", "<2.0.0"]`, added to an existing `packages.yml` or a new one. The CI quality workflow builds it. |
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
| `workarounds` | The open platform gaps, each with what removes it: the sandbox dbt command (and never opening `profiles.yml`), `plan.md` and `verify.md` written once per phase, large files changed by script, verify from the landed table and saved profile, the Tier-1 dev dataset, sample loads that land whole pages. |

Write these into the repo's own convention skills beside its conventions:

| Skill | Rule |
| --- | --- |
| `dlt` | Sample loads (`DLT_INGEST_LIMIT`) while a pipeline is written; one full load at most per intent, at the end, only when the requirement asks for loaded data. `replace` is proven with two sample loads (the limit's row count and one load package), never a second full load. |
| `dlt` | Profile a remote source file once per intent into `.agents_tmp/<source>-profile.json`, and take every later figure from it. |
| `dlt` | To see whether a source exists, read `repo-map.json` `sources`; query the lakehouse only for data questions. |
| `dbt-models` | Sources name a schema and tables, never a database, and no var feeds either. |
| `dlt` | Mirror the repo's existing source of the same kind for batching and file handling. |
| `adr` | Check citations with the `adr_lint` command (or the repo's equivalent) and the two-way links with `tests/test_adr_links.py`; run them, do not read the scripts. |
| `dbt-models` | dlt lands timestamps tagged UTC and the session time zone is not always UTC: staging converts every dlt-loaded timestamp to the wall-clock value the source recorded, and the skill names the function once a sample load proves it. |
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
| Staging converts dlt-loaded timestamps to UTC | `bug` if a key or join depends on them, else `convention` |
| The dbt job notebook runs `dbt deps` before building when the project has a `packages.yml` | `bug` |
| `.sqlfluff` (or the SQL lint config) resolves its profile and project paths | `gap` |

## Verify

The base commands pass, or each failure is a filed finding. `tests/test_maps.py` passes in the sandbox. A sandbox build of one model with `--defer --state /cache/prod-target` resolves every unselected `ref()` and `source()` against the Domain.
