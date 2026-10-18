---
name: dlt
description: "Use when adding or changing a dlt source or pipeline in ingestion/, or when running a sample or full load."
---

# dlt ingestion
<!-- onboarding
ask: no
reason: Index text; sections below carry the decisions.
-->

Operator conventions for the pipelines in `ingestion/`. Where files live is declared in `repo-map.json`.

## Datasets (D5)
<!-- onboarding
ask: yes
question: Which dataset does each pipeline load?
recommended: The raw schema of its source system.
alternatives: `src_<connection>` per connection.
fills: <raw schemas>
-->

A pipeline's dataset is the raw schema it feeds, one per source system: <raw schemas>. Not `src_<connection>`.

## Write disposition (D6)
<!-- onboarding
ask: yes
question: How is write disposition chosen?
recommended: Per resource: `append` for immutable events, `replace` for a fixed window, `merge` for mutable records with a key.
alternatives: one disposition for every resource.
-->

Set per resource, never per run: `append` for immutable events that arrive once, `replace` for a full reload of a fixed window, `merge` for mutable records with a key.

## Schema contract (D7)
<!-- onboarding
ask: yes
question: Which schema contract?
recommended: `columns: freeze`, `tables: evolve` while new then `freeze`, `data_type: freeze`.
alternatives: `evolve` throughout.
-->

`columns: freeze`, `tables: evolve` while a pipeline is new then `freeze` once every resource has loaded into a database that persists, `data_type: freeze`. Any other value carries a `# why:` line in the pipeline and a decision in its design record.

## Bronze carries no logic (D8)
<!-- onboarding
ask: no
reason: The medallion guardrail: bronze is what the source sent.
-->

No transformation, casts, joins or filters in a pipeline. A pipeline loads what the source gives it. Source column names are kept verbatim (`[schema] naming = "direct"`).

## `_dlt_*` columns (D8b)
<!-- onboarding
ask: no
reason: Audit surfaces read them.
-->

Never drop or alias them.

## Sample loads (D10)
<!-- onboarding
ask: no
reason: How the sandbox is used; learned from Studio runs.
-->

A safety run or sample load sets `DLT_INGEST_LIMIT` (default 1,000 rows); a full load leaves it unset. No committed limit.

In an intent, every run while the pipeline is being written is a sample load. A full load runs at most once, after the pipeline and its docs are final, and only when the requirement asks for loaded data. Prove `replace` with two sample loads at the same `DLT_INGEST_LIMIT`, never a second full load.

## Profiling a remote file (D16)
<!-- onboarding
ask: no
reason: How the sandbox is used; learned from Studio runs.
-->

Profile a remote source file once per intent into `.agents_tmp/<source>-profile.json`, with the URL and the time read, and take every later figure (design record, resource docs, verify) from that file.

## Adding a source
<!-- onboarding
ask: no
reason: Follows from the repo-map and the map tests.
-->

- The first source sets the pattern; every later source mirrors an existing entry in `repo-map.json` `sources` and creates every artifact it lists (module, config section, pipeline, resource docs, tests, design record).
- The pipeline is a notebook, `ingestion/<name>_pipeline.Notebook/`, scaffolded by the plugin's generator (`fabric_lakehouse/pipeline-notebook.md`). Add it as an activity to the Domain's Data Pipeline in `orchestration/`, and add the source to `repo-map.json` and `test-map.json`. `tests/test_maps.py` fails when a source's listed paths or its config section are missing.
- To see whether a source exists, read `repo-map.json` `sources`; query the lakehouse only for data questions.
- Mirror the existing source of the same kind for batching and file handling.
