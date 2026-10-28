---
name: workarounds
description: "Use after a conversation is condensed, and before editing plan.md or verify.md, linting Python, running Tier-1 tests or doing a sample load."
---

# Workarounds

Temporary rules that cover a gap in a platform skill or document. Each names the change that makes it redundant. When that change ships, delete the rule and its row in `AGENTS.md`. Track whether a rule helped in `docs/setup/skill-changes.md`.

## Write `plan.md` and `verify.md` once per phase

Draft the file once. Keep progress and evidence in your head or in a scratch note, and write them into the file in a single edit at the end of the phase. Do not edit the file after each task or check. Each edit echoes a snippet of the file back, and these files are large. When the work comes back on a return, rewrite the file whole in one write; do not patch it section by section.

Remove when: the `planning`, `executing-the-plan` and `verifying` skills write these files once per phase (`skill-changes.md`).

## Change large files with a script, not the file editor

The file editor echoes the file back after every edit; for `repo-map.json`, YAML properties files, `plan.md` and `verify.md` that is 15K to 27K characters per edit. Change them with a script and print only what you need to confirm:

- `repo-map.json`, `test-map.json`: load with Python `json`, change, dump with `indent=2`, then validate (`python3 -m pytest tests/test_maps.py -q`).
- `plan.md`, `verify.md`: append with a heredoc, or replace one block with a short Python `str.replace`.
- YAML properties files (`_sources.yml`, `_staging.yml`): a short Python `str.replace` on a unique anchor.

Never make two edits to the same file in parallel.

Remove when: the editor caps its echo (`skill-changes.md`, platform file editor).

## Verify from the landed table and the saved profile

An independent recount at verify reads the landed table and `.agents_tmp/<source>-profile.json`. It never reads the remote source file again.

Remove when: `verifying` says where independent figures come from for an ingestion change (`skill-changes.md`).

## Tier-1 tests after a safety run

A `--dev-mode` safety run (the `generating-dlt-pipeline` skill's) loads into a timestamped dev dataset in the Ephemeral catalog, `<VD_EPHM_SCHEMA_PREFIX>bronze_<timestamp>`; the plugin's bronze preview lists it with every other schema under the Intent's prefix. Pass that full schema name to the plugin's `scripts/run_bronze_tier1_tests.py --dataset`, which adds no prefix of its own; not `bronze`. After the full load, pass `<VD_EPHM_SCHEMA_PREFIX>bronze`. A Tier 2 or 3 pytest suite cannot reach the Ephemeral catalog: record its execution as deferred, as the plugin's `databricks/dlt.md` § Bronze tests says.

Remove when: the Tier-1 runner finds the dev dataset itself (`skill-changes.md`).

## A sample load lands whole yields, not N rows

The pipeline notebooks count the `dlt_ingest_limit` widget in rows (`add_limit(..., count_rows=True)`, from the plugin's template), but dlt stops only after the first yield that reaches the limit and does not trim it. `tlc` yields one table per monthly Parquet file, so a TLC sample load with a limit of 1,000 lands the whole first month. Do not write "N rows" for a sample load into a Requirement or Plan, and do not read a larger count as a failed limit. Check the landed count against what one yield of the source holds instead.

Remove when: `databricks/dlt.md` and `generating-dlt-pipeline` state that the limit stops after a whole yield (`skill-changes.md`).
