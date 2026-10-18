---
name: context
description: "Use when adding, changing or removing a term in CONTEXT.md."
---

# What goes into CONTEXT.md (E1, E10)

`CONTEXT.md` is the vocabulary of the data product. Nothing else.

## Belongs

- A business term: what the domain means by a word, in one or two sentences.
- An abbreviation this domain uses.
- A rejected synonym, as a `_Not_:` line with the reason.

## Does not belong

- Schemas, layers, owners or file locations: `repo-map.json`.
- Columns, types, row counts, lineage: the catalog.
- A decision about how something is handled: an ADR.
- Implementation detail: the design record.
- Example values, ids, dates or numbers the code can change.
- Consumers, teams, reports or audiences. The product can be used by anyone.
- Platform or agent terms, such as the medallion layering. They are defined elsewhere.

## Entries

- Format: `**Term**:` then the meaning, then `_Not_:` where a synonym was rejected.
- Add a term when it resolves, never speculatively. Every term is used by a model, an ADR or a design record.
- Changes: create, sharpen, split, merge or deprecate. A deprecated entry stays, marked, and names its replacement.
