# Which tables get a concept

Read this before declaring or omitting a concept, and when `validating-ontology` reviews coverage. The ontology is neither a mirror of the star schema nor the glossary alone: every dimension and fact the Ossie documents register is classified first, and the reason a table gets no concept is written where a reader will look for it — the table's own description, or the Ossie document that carries it. No tool enforces this classification; the review reads it.

| Table kind, read from the name and the SQL | Concept? | What it becomes instead |
| --- | --- | --- |
| Conformed dimension: the same meaning and key in more than one document | Yes, an `EntityType` | — |
| Reference dimension: one meaningful attribute, a name or a code | Yes, an `EntityType` | — |
| Transactional fact: one row per event the business names | Yes, an `EntityType` | its numbers are metrics, not concepts |
| Event-derived interval fact: one row per derived interval the business names, with its own id | Yes, an `EntityType` | its durations are metrics; the derivation is the Ossie document's |
| Transferable entity: a licence, contract or membership whose holder changes over time | Yes, an `EntityType` of its own | the current holding as a `ManyToOne`; the transfers a gap in the Ossie documents |
| Junk dimension: a bundle of unrelated low-cardinality flags | No | attributes of the concept that owns them |
| Degenerate dimension: an identifier with no table, a key on the fact | No | an identity component or a relationship |
| Rebuilt state snapshot: a state recomputed as of a date, no interval of its own | No | the rule that derives it, in an ADR |
| Effective-dated rule table: rates, thresholds, bands | No | the rule, in an ADR |
| Bridge: two concepts many-to-many, with a weight | No | the relationship's `weight` in the Ossie document |
| Aggregate or report mart: a rollup or a report shape | No | metrics on the concepts it rolls up |

- **A classification is not a vocabulary.** A missing `CONTEXT.md` term blocks a concept whatever the table is; add the term in the same change.
- **A classification is not an identity.** A reference dimension whose only key is a surrogate still gets a concept when the business names it, but its identity is that key and the mapping's description says the natural code is absent. Do not invent a code.

## When in doubt, ask — never skip

A silent gap reads as coverage. Each of these is a question to the user through `grilling`, one at a time, with the options and a recommendation, before a concept is declared or omitted:

- **The table fits no row.** A junk dimension with one meaningful flag, an interval fact rebuilt from events, a rule table joined as if it were a dimension: name the two readings and ask which the business means.
- **The standard cannot state the relation.** A many-to-many over time, a validity window, a transfer: declare what the standard can hold and say what it cannot, never widening one concept to absorb another.
- **Identity cannot be proven from the SQL.** A `*_key` with no code beside it, a name that might change, a column that might be a surrogate.
- **A term is missing.** Add it in the same change, or ask whether the business names the thing at all.
- **Two concepts seem to name one object,** or one concept seems to name two.

Record the ruling where the artifact lives — the concept's description, the mapping's description or the table's note — and list the table in the report as ruled or blocked. A blocked table is a finding, never an omission.
