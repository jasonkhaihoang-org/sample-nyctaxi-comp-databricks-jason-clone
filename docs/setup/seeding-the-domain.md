# Seeding the Studio Domain database

Repo maintenance. Build agents do not read this document.

Studio copies the Domain DuckDB file into every Intent's sandbox when the Intent starts. An empty Domain gives every Intent an empty sandbox, so the first build has to load every source and build every model before it can do its own work. Seed the Domain before creating it.

## Build the file

From the repo root, with dlt, `vibedata-dlt-duckdb-studio` and `dbt-duckdb` installed (`pip install -c .github/managed-constraints.txt ...`):

```bash
python3 docs/setup/seed_domain_duckdb.py --out nyc_taxi.duckdb --months 2024-01
```

The script:

1. Loads the TLC trips for the given months, the zone lookup, and the simulated ops and mdm systems.
2. Runs `dbt deps` and `dbt build` (217 nodes) into the same file.
3. Copies the file under another name, as Studio does for a sandbox, and runs every data test on the copy without rebuilding anything. A view that stored a catalog name would fail here.
4. Compacts the file and prints its schemas and size.

January 2024 gives a file of about 560 MiB. Studio's Domain-create upload accepts up to 1 GiB; the script warns above that.

## Create the Domain

1. In Studio, create a Domain on the DuckDB-local platform.
2. Upload `nyc_taxi.duckdb` as the Domain database and pick `main` as the Domain schema.
3. Start Intents as usual. Each one's sandbox is a copy of this file under the name `ephm_<domain>_<intent>`.

A Domain's database cannot be changed after creation. To refresh the data, seed a new file and create a new Domain.

## What makes the project work in a renamed copy

- Sources name a schema, never a database (`.agents/rules/dbt-models.md` B18).
- `transformation/macros/relations.sql` renders `ref()` and `source()` as `schema.table`, so the views dbt stores carry no catalog name.
- The repo's `profiles.yml` reads its path from `VD_EPHM_DUCKDB_LOCAL_PATH`, the variable the sandbox sets.

## Limits

- The reporting window (`report_start`, `report_end`) stays Q1 2024. A January seed fills one month of it, so quarterly marts in the seeded Domain cover January only.
- `--months 2024-01 2024-02 2024-03` seeds the whole quarter, but the file is then over the upload limit.
