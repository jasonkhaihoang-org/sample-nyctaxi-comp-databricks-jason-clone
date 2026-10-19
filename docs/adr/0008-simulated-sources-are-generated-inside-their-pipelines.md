---
status: decided
date: 2026-10-14
---

# The simulated sources are generated in memory inside their pipelines

`ops_raw` (the fleet operator's dispatch and telematics platform) and `mdm_raw` (the master-data platform) are simulated source systems. Each is generated deterministically by DuckDB in memory inside its own dlt pipeline, and loaded like any source. The operator's records are derived from the yellow trips, which the ops pipeline reads in memory and never writes: it loads the eight `ops_raw` tables only. The generators keep the imperfections a real feed has (shifts that never log out, events that arrive out of order, missing odometer readings) and leave them for dbt to flag.

## Considered options

- **Generators that write into the warehouse** (the earlier arrangement) — rejected: they bypass the load path every other source uses.
- **Generators that write landing files for dlt** — rejected: a second stage to run and keep in step.
- **A dlt transformer on the TLC trips resource** — rejected: shifts and vehicle overlaps span monthly files, so the generator needs every trip at once.
- **Generate inside the pipeline, from trips read in memory** — chosen.

## Consequences

- The ops pipeline downloads the yellow trips again; the pipelines stay independent.
- Generation is deterministic: the same inputs give the same rows.
- Overlapping trips on one vehicle are removed repeatedly until none remain; a single pass left some behind.

## Affected designs

- [`pipelines/ops.md`](../design/pipelines/ops.md)
- [`pipelines/mdm.md`](../design/pipelines/mdm.md)
- [`models/staging/stg_ops__trip_assignments.md`](../design/models/staging/stg_ops__trip_assignments.md)
