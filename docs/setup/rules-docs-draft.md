# Draft rules: context, ADRs, design records

Draft text for three files in `.agents/rules/`: `context.md`, `adr.md`, `design-records.md`. Operator-owned: the skills (`domain-modeling`, `designing`) read these instead of carrying their own copies. Formats that CI scripts read (ADR frontmatter, design-record section names) stay with the skill; these rules are about content.

## context.md: what goes into `CONTEXT.md`

`CONTEXT.md` is the vocabulary of the data product. Nothing else.

**Belongs**
- A business term: what the domain means by a word, in one or two sentences.
- An abbreviation this domain uses.
- A rejected synonym, as a `_Not_:` line with the reason.

**Does not belong**
- Schemas, layers, owners or file locations: `repo-map.json`.
- Columns, types, row counts, lineage: the catalog.
- A decision about how something is handled: an ADR.
- Implementation detail: the design record.
- Example values, ids, dates or numbers the code can change.
- Consumers, teams, reports or audiences. The product can be used by anyone.
- Platform or agent terms, such as the medallion layering. They are defined elsewhere.

**Entries**
- Format: `**Term**:` then the meaning, then `_Not_:` where a synonym was rejected.
- Add a term when it resolves, never speculatively. Every term is used by a model, an ADR or a design record.
- Changes: create, sharpen, split, merge or deprecate. A deprecated entry stays, marked, and names its replacement.

## adr.md: what goes into an ADR

**Write an ADR when all three hold**
- It is hard to reverse.
- It is surprising without context.
- It is the result of a real trade-off between named alternatives.

A business definition of a measure, population, threshold or grain also qualifies, and cites its source. A decision the code already makes, with no ADR, qualifies if it passes the three tests.

**Content**
- One decision per ADR, titled as a decision.
- `## Considered options`: each alternative and why it was or was not chosen.
- `## Consequences`: what later work must respect.
- `## Affected designs`: relative links to the design records the decision changes.
- No consumers, teams or audiences. No example values.
- Every claim is checked against the code or data at the time of writing. The date is the day it is written, never copied from another ADR.

**Lifecycle**
- Number: the next in sequence.
- A decision that still holds is left alone.
- A decision that no longer holds is superseded by a new ADR; the old ADR changes only its frontmatter, `status: rejected` and `rejected-note`.
- Cite ADRs as `ADR NNNN` so the CI citation check finds them.

## design-records.md: what goes into a design record

**Scope**
- One record per model or pipeline, amended by later changes, never one per change.
- Record only what the code and catalog cannot tell a reader.

**Decisions**
- `D-NN`, append-only, each with its source: a requirement, an answer or a convention.
- Where an ADR governs a decision, cite it as `ADR NNNN` with a link. When that ADR is superseded, cite its successor.
- Pipeline records: per resource, the write disposition, incremental cursor, the three schema-contract axes (`columns`, `tables`, `data_type`) and the duplicate-key handling.

**Consumers**
- Lists dependents only: the models and pipelines in this repo that depend on this one, taken from lineage (`dbt ls --select <model>+`).
- No teams, reports, packs or audiences.
- When nothing in the repo depends on it, write "None in this repo".

**Evidence**
- What settled the decisions: profiling, reconciliation, the slice used. One line each, with the query or path.
