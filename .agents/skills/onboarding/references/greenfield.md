# Greenfield

The repo has no dbt project and no pipelines, and the Domain catalog is empty. Onboarding sets up an empty, working project so the first intent is a plain "add a source".

## Requirement

Ask what the domain is for and where its data will come from. Scope: the whole repo.

## Design: grill by file and section

Use the `grilling` skill. Every template under [templates/](../templates/) marks each section with an `<!-- onboarding -->` block:

- `ask: yes`: a question, a recommended answer and the alternatives. Ask these.
- `ask: no`: platform-driven, with the reason. Show them, do not ask.

Go file by file, in this order: `AGENTS.md`, then the `dbt-models`, `dlt`, `dbt-testing`, `sql-style` and `git-and-prs` skills, then the content skills and `workarounds`. For each file, show every section's recommended text in one message and ask its `ask: yes` sections one at a time, recommendation first; the user may also override an `ask: no` section. A section answered once (for example the layers, in `AGENTS.md` and `dbt-models.md`) is not asked again.

Also ask the dbt project name (recommended: the domain slug with underscores), and pass the first business terms to `domain-modeling` for `CONTEXT.md`.

## Build

Write from [templates/](../templates/), filling the confirmed answers:

| Write | From |
| --- | --- |
| `transformation/dbt_project.yml`, `packages.yml`, `profiles.yml` | `templates/dbt/` |
| `transformation/macros/generate_schema_name.sql`, `transformation/macros/source_defer.sql` | the plugin's `_family/shared-container/templates/`, unchanged |
| `transformation/models/<layer>/` per confirmed layer, `models/staging/_sources.yml` (`version: 2`, no sources), `transformation/tests/` | empty, with a `.gitkeep` where a folder would be empty |
| `ingestion/.dlt/config.toml`, `ingestion/sources/`, `ingestion/requirements.txt` | `templates/dlt/` |
| `tests/conftest.py` | `templates/tests/` |
| `tests/test_maps.py`, `tests/test_adr_links.py` | `templates/tests/` |
| Where the repo checks run | The Repo checks question in [base-setup.md](base-setup.md); recommended `.github/workflows/repo-checks.yml` from `templates/repo/` |
| `repo-map.json`, `repo-map.schema.json`, `test-map.json` | `templates/repo/`, layers from the answers, `sources` empty |
| `AGENTS.md`, `ruff.toml`, `requirements-dev.txt`, `.gitignore` (`gitignore-fragment`) | `templates/repo/`, `<!-- onboarding -->` blocks removed |
| `.sqlfluff` | `templates/repo/sqlfluff.cfg`: the `databricks` dialect and the jinja templater, with every macro but `source_defer.sql` loaded, so it needs no profile or credential |
| `docs/adr/`, `docs/review/`, `docs/proposal/` | empty, with a `.gitkeep` |
| `.agents/skills/<name>/SKILL.md`, one per convention skill | `templates/skills/<name>.md`, with the confirmed answers in place of the placeholders and every `<!-- onboarding -->` block removed |
| `CONTEXT.md` and any ADR a confirmed decision earns | `domain-modeling` |
| CI, `.github/profiles/`, `.github/scripts/vibedata_domain_ci/adr_lint.py` | `install-ci`, which installs the Databricks CI bundle: the production-manifest publish workflow, its offline `dbt_databricks_compile` profile, `.workflow/ci-config.yml` and the shared scripts. Not optional: Studio stages `/cache/prod-target` from the manifest it publishes, and the `adr_lint` command depends on it. It runs no PR gates |

Fill the placeholders:

| Placeholder | Value |
| --- | --- |
| `<project_name>` | The confirmed dbt project name, in `dbt_project.yml` |
| `<VD_DOMAIN_…>` in `profiles.yml` | That Domain setting's value, written out as a literal |
| `<Domain name>`, `<domain paragraph>` | The requirement answer |
| `<domain slug>`, `<one line>` | `repo-map.json` `applications`: the slug and the domain paragraph's first sentence |
| `<raw schema>`, `<source system>` | `repo-map.json` `layers`: one entry per confirmed raw schema, keyed by its name, `path` `ingestion/` |
| mart areas | One `layers` entry and one `dbt_project.yml` block under `marts` per confirmed area, path `transformation/models/marts/<area>/` |
| `<UTC timestamp>` | The time of writing, in both maps |

Write no source, pipeline, model or design record: the first intent adds them. Write no orchestration either: the plugin's `generating-orchestration` authors `databricks.yml` and the Lakeflow job (`orchestration/<job>.job.yml`) once there is a pipeline and a model to run. Write no review file: there is nothing to review.

## Verify

Install `requirements-dev.txt`. The base commands pass on the empty project: `dbt deps`, `dbt parse`, `python3 -m pytest tests -q`, `ruff check .`. `dbt parse` warns that the layer config paths match no models: expected until each layer has its first model; do not remove the blocks. Then the dry run, with one task: add the first source.

## Ship

One PR. The commit body and the PR description list the confirmed answers, one line per section, and recommend the next intent: add the first source.
