# Sample NYC Taxi Analytics — Fabric

A brownfield Fabric Lakehouse for NYC taxi analytics and intent-driven data
work. It combines genuine NYC TLC trip records with deterministically
generated fleet-operations and master-data systems.

The project tests joins, sessionization, SCD2 dimensions, quality rules, and
aggregate design without pretending that generated driver, vehicle, garage, or
weather data is real.

## Data provenance

| Layer | Contents | Provenance |
| --- | --- | --- |
| `bronze` | Yellow/Green trips and TLC zone lookup | Trips are landed from official TLC Parquet files; the zone lookup is CSV. Source columns are preserved and ingestion metadata is added. |
| `silver` | Conformed trips, zones, payment types, and rate codes | Derived from Bronze; Yellow and Green are unioned, renamed, keyed, and deduplicated. |
| `ops_raw` | Garages, vehicles, drivers, leases, shifts, assignments, status events, maintenance | Fully synthetic and deterministic, generated from landed TLC trips. |
| `mdm_raw` | Zone/vendor/payment/rate/borough/calendar/POI/weather data | Mixed: some labels/rates are hand-transcribed; enriched attributes and weather are generated. |
| dbt models | Staging, intermediate, dimensions, facts, marts, and aggregates | Derived transformations and business rules. |

All layers live as schemas in one Lakehouse (`nyc_taxi_lakehouse`).

The TLC trip window is January–June 2024. Read the full tier-by-tier notes in
[`docs/data-provenance.md`](docs/data-provenance.md) before treating a result
as a real-world claim. Trip-level TLC facts are genuine; Harbour Point
identities and operational outcomes are not.

## Architecture

```text
TLC Parquet + CSV in Lakehouse Files
           │
           ▼
src/dlt/landing.Notebook ───► bronze ───► silver
                                     │
           ┌─────────────────────────┘
           ▼
src/dlt/mdm.Notebook ───────► mdm_raw
src/dlt/fleet_ops.Notebook ─► ops_raw
                                     │
                                     ▼
              nyc_taxi_analytics DataBuildToolJob
              staging → intermediate → marts (core + agg)
                                     │
                    ┌────────────────┴───────────────┐
                    ▼                                ▼
              finance marts                     ops marts
```

Landing is full-volume: every TLC file, verbatim plus loader stamps
(`_load_id`, `_source_file`, `_loaded_at`). There is no sampling step; a
downsampled dev copy is a target concern, never part of the landing
contract. Enrichment (MDM masters, fleet entities and event streams) is
deterministic from landed data. Conforming and SCD2 assembly happen in dbt,
not in the loaders.

Orchestration is three Fabric Data Pipelines, one activity per item:

- `main`: landing → mdm + fleet_ops (parallel) → staging → marts.
- `finance`: finance marts, after `main`.
- `ops`: ops marts and scorecards, after `main`.

Model-level parallelism inside a dbt run comes from dbt `threads`, not from
pipeline fan-out. Schedules live in the workspace and are never committed
(Fabric deletes committed `.schedules` on sync); the estate's standing
cadence is nightly at 03:00 ET once enabled.

## Repository layout

`src/` is the Fabric-connected folder: everything under it is workspace
items, mirrored by Git integration. `tools/` and `docs/` live at the repo
root, outside Fabric management.

```text
src/
  nyc_taxi_lakehouse.Lakehouse/
  dbt/nyc_taxi_analytics.DataBuildToolJob/  # job + embedded project (Code/dbt/)
  dbt/<staging|marts|finance|ops>_dbt.Notebook/  # drivers: run slice, assert it
  dlt/<landing|mdm|fleet_ops>.Notebook/     # dlt ingestion + enrichment
  pipelines/<main|finance|ops>.DataPipeline/
tools/          # frozen DuckDB-era builders: reference only, never run here
docs/
  data-provenance.md
  functional/   # per-flow specs: ingestion, mdm-enrichment, fleet-ops,
                #   transformation, orchestration
  adr/
CONTEXT.md      # domain context and analytical vocabulary
```

## Prerequisites

- A Fabric workspace with a Lakehouse (`nyc_taxi_lakehouse`) and dbt-job
  support enabled in the tenant.
- The workspace connected to this repo with `src/` as its Git folder.
- TLC source files staged in the Lakehouse Files section (13 files,
  ~336 MB, January–June 2024).

No local Python environment, no DuckDB, no committed warehouse file. There
is nothing to rebuild locally.

## Deploy and run

1. Connect the workspace to this repo (`src/` folder) and sync.
2. Run the `main` pipeline: landing → mdm + fleet_ops → staging → marts.
3. Run `finance` and `ops` pipelines for their marts.
4. Each driver notebook (`*_dbt.Notebook`) runs its dbt slice
   (`--select <group>.*`) and asserts it: row-count reconciliation,
   grain and join evidence, billable-trip and reporting-window rules,
   SCD2 overlap checks.

## dbt targets and model layers

The project (`nyc_taxi_analytics`, profile `nyc_taxi_analytics`) builds
against the Lakehouse via the `dbt-fabricspark` adapter:

- **staging**: source-shaped views over `bronze`, `silver`, `ops_raw`, and `mdm_raw`.
- **intermediate**: conformed trip, status, occupancy, fare, and quality logic.
- **core marts**: dimensions, bridges, and facts.
- **aggregates**: driver, vehicle, zone, OD, weather, and occupancy summaries.
- **finance marts**: daily revenue, monthly summaries, and revenue bridges.
- **operations marts**: driver, vehicle, and trip-quality scorecards.
- **seeds**: four analyst-owned banding tables.

The reporting window (`2024-01-01` through `2024-07-01`) and billable-trip
definition (`total_amount > 0`) live in dbt models and project variables.

## Important limitations

- `ops_raw` driver, vehicle, garage, lease, maintenance, and weather records
  are synthetic and are not real NYC operations.
- Generated zone coordinates, population, area, demand tiers, and version
  histories are plausible-looking test attributes, not authoritative geography.
- `weather_daily` is a seasonal curve plus noise, not NOAA data.
- `tools/` documents how the DuckDB original was built; it is not executed
  in this repo. Do not point it at the Lakehouse.

## Source and license

Trip records and the zone lookup are downloaded from the official NYC Taxi &
Limousine Commission trip-record-data page:
<https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>

Check the source terms and attribution requirements before redistributing the
downloaded data. This repository publishes build logic and metadata; the large
source files are intentionally not published with it.
