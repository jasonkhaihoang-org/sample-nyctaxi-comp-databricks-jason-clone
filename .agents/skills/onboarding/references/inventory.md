# Convention inventory

One row per convention the repo follows. Build it from the code and documents before asking anything.

| Column | Content |
| --- | --- |
| ID | `C-n` |
| Convention | One sentence, as a rule would state it |
| Evidence | Paths, and a count where it matters: "41 of 44 staging models are `stg_<source>__<table>`" |
| Consistent | `yes`, or the exceptions by name |
| Destination | `repo-map`, `convention skill: <name>`, `domain skill: <name>`, `ADR`, `CONTEXT`, `design record: <model>`, `review` |
| Status | `inferred`, `confirmed`, `changed by user`, `dropped` |

## Where to look

- dbt: `dbt_project.yml` (paths, `+schema`, `+materialized`, vars), model folders and names, properties files, `packages.yml`, macros, singular and unit tests, seeds, `profiles.yml` targets.
- dlt: pipelines, sources, `.dlt/config.toml`, write dispositions, schema contracts, naming, incremental cursors.
- SQL style: `.sqlfluff`, and what the models actually do where the two differ.
- Orchestration and CI: run scripts, Makefile, CI jobs.
- Documents: README, CONTRIBUTING, runbooks, agent instruction files, existing ADRs or design notes, model YAML descriptions.

## Destination test

Ask in this order and stop at the first yes:

1. Can a script check it against the file tree? `repo-map`.
2. Is it something that should change? `review`.
3. Does it hold for every change of a kind? `convention skill`.
4. Is it an ordered procedure only this repo has? `domain skill`, after confirmation.
5. Does it record a choice someone made for a reason? `ADR`.
6. Is it a business term? `CONTEXT`.
7. Does it belong to one model or pipeline only? `design record`.

A convention a plugin skill already states is not a convention skill. Drop it.
