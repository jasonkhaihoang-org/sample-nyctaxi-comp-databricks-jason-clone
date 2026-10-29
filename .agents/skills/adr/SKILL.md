---
name: adr
description: "Use when recording a decision, when a choice might need an ADR, or when writing, superseding or reviewing a file in docs/adr/."
---

# What goes into an ADR (E3, E11)

## Write an ADR when all three hold

- It is hard to reverse.
- It is surprising without context.
- It is the result of a real trade-off between named alternatives.

A business definition of a measure, population, threshold or grain also qualifies, and cites its source. This includes the standing answers a requirement would otherwise ask about, such as the week boundary or how nulls are handled. A decision the code already makes, with no ADR, qualifies if it passes the three tests.

Not an ADR: a choice one model or pipeline makes that is easy to change later, such as which months a source loads, a write disposition or an incremental cursor. Record it as a decision in that artifact's design record.

## Content

- One decision per ADR, titled as a decision.
- `## Considered options`: each alternative and why it was or was not chosen.
- `## Consequences`: what later work must respect.
- `## Affected designs`: relative links to the design records the decision changes.
- No consumers, teams or audiences. No example values.
- Every claim is checked against the code or data at the time of writing. The date is the day it is written, never copied from another ADR.

## Lifecycle

- Number: the next in sequence, four digits.
- A decision that still holds is left alone.
- A decision that no longer holds is superseded by a new ADR. The old ADR changes only its frontmatter: `status: rejected` and `rejected-note: Superseded by docs/adr/<new>.md`.
- Cite ADRs as `ADR NNNN` so the CI citation check finds them.
- A design record that starts citing an ADR is added to that ADR's `## Affected designs` in the same commit, and a record that stops citing a decided ADR is removed from it. A rejected ADR's body, its `## Affected designs` included, stays as it was when the ADR was rejected.
- When an ADR is superseded, the design records it lists move their citations to the new ADR in the same commit, and the new ADR's `## Affected designs` lists them.
- Check citations with the `adr_lint` command in `repo-map.json` (numbering and dangling citations) and the two-way links with `tests/test_adr_links.py` (part of `python_tests`). Run them; do not read the scripts to work out what they check.
