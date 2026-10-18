# Contributing

## Set up

Follow the prerequisites in [`README.md`](README.md). Data lives only in the
Domain Lakehouse; to stand up a Domain of your own, follow
`docs/setup/seeding-the-domain.md`.

## Before you push

```bash
python3 -m pytest tests -q
ruff check . --extend-exclude .github,ingestion/sources
sqlfluff lint transformation/models
```

The dbt data and unit tests need a Lakehouse: run them in an Intent's sandbox,
or against a Domain after a release.

`test-map.json` names the narrow command for each layer, so a change to one model
needs only its layer's tests until the final run.

## Conventions

The operator conventions are skills in [`.agents/skills/`](.agents/skills/), indexed by
[`AGENTS.md`](AGENTS.md):

- model and file naming, layers and materialisation: [`dbt-models`](.agents/skills/dbt-models/SKILL.md)
- SQL formatting: [`sql-style`](.agents/skills/sql-style/SKILL.md)
- tests: [`dbt-testing`](.agents/skills/dbt-testing/SKILL.md)
- pipelines: [`dlt`](.agents/skills/dlt/SKILL.md)
- commits and pull requests: [`git-and-prs`](.agents/skills/git-and-prs/SKILL.md)

`repo-map.json` says where each kind of file lives. Update it, and `test-map.json`,
when a layer, entrypoint, command or location changes; `tests/test_maps.py`
fails when either names something that does not exist.

## Decisions and designs

- A decision that is hard to reverse, surprising without context and a real
  trade-off is an ADR in `docs/adr/`. Standing business answers are ADRs too.
  See [`adr`](.agents/skills/adr/SKILL.md). Never edit a decision that still holds;
  supersede one that does not.
- Each model and pipeline has a design record under `docs/design/`, and an ADR
  lists the design records it affects. See
  [`design-records`](.agents/skills/design-records/SKILL.md).
- New terms go in `CONTEXT.md` only when a model, ADR or design record uses them.
  See [`context`](.agents/skills/context/SKILL.md).
- Requirements for a piece of work go in `docs/requirement/`, plans in `docs/plans/` and verifications in `docs/verify/`, as `repo-map.json` `artifact_paths` declares.

## Pull requests

Use the four sections in [`git-and-prs`](.agents/skills/git-and-prs/SKILL.md): Summary,
Verification, Approved contract changes, Remaining manual checks.
