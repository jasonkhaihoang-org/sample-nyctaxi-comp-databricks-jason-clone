# Domain skills

A domain skill is a multi-step procedure this repo has and no plugin skill covers. It is the one kind of skill in `.agents/skills/` that is a procedure; the others are convention skills (a must or never that holds for every change of a kind), written from `templates/skills/`. Example: "add a reporting month": change the config months, run ingestion, rebuild an incremental fact with `--full-refresh`.

Never a candidate: adding or changing a source, pipeline, model, test or semantic model. Plugin skills cover those; what is specific to this repo becomes a convention skill.

## Finding candidates

- README and CONTRIBUTING sections that read as steps.
- Runbooks, wiki exports, `docs/`.
- Makefile targets, run scripts and CI jobs that chain commands.
- Comments in `dbt_project.yml` and config files that say "when you change X, also do Y".
- Git history: files that change together in commit after commit.

## Rules

- Present each candidate with its name and steps in the grilling. Write only the ones the user confirms.
- If a plugin skill covers the task (add a source, add a model), the repo-specific part is a convention skill, not a procedure skill.
- Write a handful at most. An uncertain candidate is a `gap` finding in the review.
- Each skill gets a narrow description that names the procedure, so a build task does not pick it up by accident.
