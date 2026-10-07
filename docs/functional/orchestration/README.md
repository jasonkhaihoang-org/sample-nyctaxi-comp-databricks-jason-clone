# Orchestration — three pipelines, one dbt job

Three Fabric data pipelines (`src/pipelines/`) fan out from one dbt job
(`src/dbt/nyc_taxi_analytics.DataBuildToolJob`, operation `build`,
`threads: 4`). Item references are placeholder logical IDs
(`<LANDING_LOGICAL_ID>`, `<NYC_TAXI_ANALYTICS_LOGICAL_ID>`, …) that rebind at
apply/sync time — never real GUIDs. Every activity is committed `Inactive`
(`onInactiveMarkAs: Succeeded`); nothing runs on deploy.

## Activity chains

**main** (end-to-end lakehouse build): `landing` → `mdm` + `fleet_ops` (both
after landing) → `BuildStagingSlice` (`staging.*`) → `staging_dbt` notebook →
`BuildMartsSlice` (`marts.*`) → `marts_dbt` notebook.

**finance** (revenue pack refresh): `BuildFinanceSlice` (`finance.*`) →
`finance_dbt` notebook.

**ops** (operations review refresh): `BuildOpsSlice` (`ops.*`) → `ops_dbt`
notebook.

The four `*_dbt` notebooks (`src/dbt/*.Notebook/notebook-content.py`) are
assert-only: they verify the slice their pipeline just built (staging key
uniqueness and yellow/green trip-vs-extras parity; marts grain checks and the
SCD2 no-overlap assert; finance/ops equivalents). No notebook invokes dbt and
none triggers another pipeline — sequencing is pipeline fan-in, not notebook
fan-out.

## Schedules and cadence

All three `.schedules` files read `{"schedules": [], "disabled": true}`:
schedules are committed disabled. The standing cadence is nightly 03:00 ET —
the Monday revenue pack, garage operations review, and data-quality review all
read from what the nightly run built.
