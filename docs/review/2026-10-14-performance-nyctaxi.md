---
type: performance
date: 2026-10-14
commit: be81dc8
source: hb
---

# Performance review: dbt build

## Scope

The dbt build of `transformation/` on the local target, with attention to the incremental fact and the aggregates. Ingestion run times were not measured.

## Findings

| ID | Kind | Finding | Evidence | Suggested action | Status |
| --- | --- | --- | --- | --- | --- |
| R-1 | gap | `fct_trip` loads only rows newer than its maximum `pickup_datetime`, so corrected or late trips are never picked up, and any change upstream needs a `--full-refresh` to take effect. | `fct_trip.sql:28-30`; a relationships test failed after an upstream change until `dbt build --full-refresh` | Use a lookback window on the incremental filter, or rebuild `fct_trip` as a table while the data is one quarter. | open |
| R-2 | gap | Aggregates are not bit-for-bit reproducible: two builds with no code change give different content checksums for 19 aggregate tables. | Checksums of `agg_*` tables across two builds of the same commit | Compare aggregates with a tolerance; do not use exact checksums for parity. | declined: floating-point summation order; parity checks use a tolerance |
| R-3 | gap | Every run rebuilds the warehouse from scratch: `replace` write disposition and a fresh `domain.duckdb`. | `ingestion/.dlt/config.toml`; `orchestration/run_all.py` | None while the data is three months of open data. | declined: intended for a demo-sized dataset |

## Notes after the Fabric Lakehouse port (2026-10-18)

The findings above were made on the DuckDB Domain this repo was ported from. On the Fabric Lakehouse:

- R-2: Spark aggregation is not reproducible bit for bit either; the finding holds and compares at stated precision.
- R-3: there is no local database file. A release reloads the Domain Lakehouse in full (`replace`) and rebuilds every model; an Intent builds only what it changes and defers the rest to the Domain.
