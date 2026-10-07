# Ingestion — TLC landing and conforming

Full-volume landing of the TLC trip-record feed into `nyc_taxi_lakehouse`
(`bronze` + `silver` schemas), executed by
`src/dlt/landing.Notebook/notebook-content.py` (dlt pipeline `landing`,
destination `lakehouse`).

## What lands

**Bronze — verbatim plus stamps.** Every bronze write preserves source columns
and adds `_load_id`, `_source_file`, `_loaded_at` (fixed
`2024-07-02 03:14:00`, so reruns are identical):

| Table | Source | Stamp |
| --- | --- | --- |
| `bronze_yellow_tripdata` | `Files/raw/yellow_tripdata_2024-*.parquet` (Jan–Jun 2024) | `load_2024h1_yellow` |
| `bronze_green_tripdata` | `Files/raw/green_tripdata_2024-*.parquet` (Jan–Jun 2024) | `load_2024h1_green` |
| `bronze_taxi_zone_lookup` | `Files/raw/taxi_zone_lookup.csv`, explicit 4-column select | `load_2024h1_ref` |
| `bronze_payment_type_ref` | Hand-maintained static values (7 payment-type labels) | `load_2024h1_ref` |
| `bronze_rate_code_ref` | Hand-maintained static values (6 rate-code labels) | `load_2024h1_ref` |
| `bronze_vendor_ref` | Hand-maintained static values (4 vendor names) | `load_2024h1_ref` |

**Full volume, no sampling.** Every row in the source files lands. The load
stamps distinguish the three source batches; they are not sample markers.

**Silver — conformed, one trip grain.** `silver_trips` unions yellow and green
onto shared names (`VendorID`/`RatecodeID`/`PULocationID`/`DOLocationID` renamed,
pickup/dropoff columns unified per fleet, `service_type` tag added), keys each
row with `trip_key` (md5 over service type, vendor, timestamps, zones, distance,
total), and dedupes to one row per key (`row_number` ordered by `_source_file`).
`silver_zones`, `silver_payment_types`, `silver_rate_codes` are rename-only
conforms of their bronze counterparts; stamps pass through.

**Dropped, not nulled.** Columns existing on only one fleet do not survive into
silver: yellow's `Airport_fee` and green's `ehail_fee` / `trip_type` are dropped
rather than carried as mostly-null columns. Anything needing them reads bronze.

## Provenance

Tier 1 (real, downloaded from TLC): the two trip tables and the zone lookup —
all ~20.67M trips, every timestamp, fare, tip, zone id, and the mess (negative
totals, zero-distance trips, `RatecodeID` 99). Tier 2 (real-world facts,
hand-transcribed): the three ref tables, typed from the TLC data dictionary and
carrying transcription risk Tier 1 does not. `silver_trips` is real data,
transformed — union, rename, type, deduplicate.

## Checks

Stamps on every write (fixed `_loaded_at` catches clock-dependent reruns);
`trip_key` grain enforced downstream by the staging-dbt null/duplicate-key
asserts and the `fct_trip`-matches-silver-rowcount test.
