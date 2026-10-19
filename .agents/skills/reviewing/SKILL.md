---
name: reviewing
description: "Use only when the user or the onboarding skill asks for a review of this repository (onboarding, security, performance, cost, data quality) whose findings go to docs/review/ for triage. Do not use for code review of a pull request or for verifying an intent."
user-invocable: true
triggers: [review this repo, security review, performance review, cost review, data quality review]
---

# Reviewing

A review records what is wrong or missing, with evidence, for someone to triage. It changes nothing else.

## Output

One file per run at `artifact_paths.review` in `repo-map.json` (`docs/review/{date}-{type}-{slug}.md`), from [templates/review.md](templates/review.md).

- Frontmatter: `type`, `date`, `commit` (the commit reviewed), `source` (the intent or person that ran it).
- Scope: one paragraph on what was and was not looked at.
- Findings: one row each, `R-n` numbered from 1 in this file.

| Column | Content |
| --- | --- |
| ID | `R-n` |
| Kind | `platform` (a plugin skill or audit surface needs it), `convention` (breaks the repo's own confirmed convention), `bug` (wrong data or a failing run), `gap` (missing test, document or check), `style` |
| Finding | One sentence |
| Evidence | Path and line, or a query and its result. Never a guess. |
| Suggested action | One sentence |
| Status | `open` when written |

## Triage

Triage edits only the status column; the rest of the file stays as written.

| Status | Meaning |
| --- | --- |
| `intent` | Small enough for an intent as it stands |
| `proposal → P-NNNN` | A major functional or design item that needs discussion first; write the proposal from [templates/proposal.md](templates/proposal.md) at `artifact_paths.proposal` and list the finding in its `findings` |
| `declined: <reason>` | Will not change |
| `deferred` | Not now |

A proposal does not need a finding. An intent that starts from one links it from `requirement.md` and sets its status when it ships.

## Common mistakes

- Fixing a finding while reviewing. File it.
- Evidence such as "probably" or "seems". Query or cite the line, or leave the finding out.
- Mixing review types in one file. One run, one type.
