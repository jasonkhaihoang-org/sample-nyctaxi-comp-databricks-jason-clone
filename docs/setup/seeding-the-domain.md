# Seeding the Studio Domain

Repo maintenance. Build agents do not read this document.

A Studio Intent builds only the models it changes. Every other `ref()` and `source()` defers to the Domain's released models: `--defer --state /cache/prod-target`, plus `macros/source_defer.sql` for sources. A Domain with no released model gives an Intent nothing to defer to, so seed the Domain before creating it in Studio.

Seeding a Fabric Lakehouse Domain is a release followed by one run:

1. The **release** delivers `ingestion/` and `transformation/` to the Domain Lakehouse's `Files/<slug>/`, with the production manifest an Intent defers to (`Files/<slug>/transformation/prod-target/manifest.json`), and applies the pipeline notebooks, the dbt job notebook and the `nyc_taxi_refresh` Data Pipeline.
2. **One run of `nyc_taxi_refresh`** loads every source (`tlc`, then `ops` and `mdm`) and builds every model, so the Domain holds the full Q1 2024 window.

On merge to `main`, the CI bundle repeats the release (Deploy Orchestration) and publishes the manifests as a GitHub release (Publish Prod Manifest). `docs/setup/seed_domain.py` does the same release from a workstation and starts the run.

## Create the Domain's Fabric resources

You need a Fabric capacity and an `az login` identity that can create workspaces on it.

1. Create a workspace on the capacity (this repo's is `nyc-taxi-fabric-demo`).
2. Create a Lakehouse in it **with schemas enabled** (`creationPayload: {"enableSchemas": true}` over the REST API, or the "Lakehouse schemas" box in the portal). dlt writes `Tables/<dataset>/<table>`, which a Lakehouse without schemas shows as Unidentified.
3. Choose a Key Vault the notebook identity can read. No source here reads a secret, but the Fabric notebook unit always registers the vault as dlt's secret provider.
4. Write the coordinates where the plugin reads them, and nowhere else:
   - `transformation/profiles.yml`, `prod` target: `workspaceid`, `lakehouse`, `lakehouseid`, `schema: dbo`.
   - `ingestion/.dlt/config.toml`: `[destination.filesystem]` (the workspace and Lakehouse ids, and the `abfss://` `bucket_url`, as the plugin's `fabric_lakehouse/destination-staging.md` writes them) and `[providers.azure_key_vault] vault_url`.
   - `.workflow/ci-config.yml`: the slug, the workspace and Lakehouse ids and names, and `VD_DOMAIN_SCHEMA: dbo`. Check it with `python3 .github/scripts/validate_ci_config.py`. That validator accepts a template still holding `<guid>`, so read the file too.

## Release and run

From the repository root, with `requirements-dev.txt` installed and `az login` done:

```bash
python3 docs/setup/seed_domain.py --release --run
```

`--release` alone redeploys without running. `--run` alone runs what is already released. The run replaces every bronze table (`replace`) and rebuilds every model except `fct_trip`, which is incremental: it adds only trips picked up after the latest one it holds. Repeating a seed with the same window is therefore safe. Seeding a Domain whose `fct_trip` was built from a different window is not: the run fails `assert_fct_trip_matches_conformed_rowcount`, because TLC files carry trips dated before that watermark. Rebuild it once before the run, over Livy. The committed `prod` target signs in as a Fabric notebook, so from a workstation use a profile outside the repository that copies `prod` with `authentication: CLI`:

```bash
cd transformation && dbt build --full-refresh --select fct_trip+ --target prod --profiles-dir <that profile's directory>
```


Afterwards, merging to `main` publishes the release manifests on GitHub. Studio's GitHub Actions sync provisions the CI variables (`CD_TENANT_ID`, `CD_SPN_CLIENT_ID`, `VD_PROD_WORKSPACE_ID`, …) that the merge-time deploy needs.

## What it costs

Measured on 2026-10-19 on an FTL64 trial capacity:

| Step | Time |
| --- | --- |
| Release (`deploy_orchestration.py`): 9 ingestion files, 97 transformation files, 5 items | about 4 min |
| `nyc_taxi_refresh`, full Q1: `tlc` 2.7 min, then `ops` 2.4 and `mdm` 2.1 in parallel, then `nyc_taxi_build_dbt` 13.2 | about 19 min |

A trial capacity is not billed; the run's capacity-unit use was not measured. Each notebook starts in 2 to 3 minutes on a cold capacity, which is most of the load steps' time.

## Check the seed

- `intermediate.int_trips_conformed` and `core.fct_trip` hold 9,722,362 rows, `bronze.yellow_tripdata` 9,554,778 and `bronze.green_tripdata` 167,585: the DuckDB repo's full Q1 figures (measured 2026-10-19).
- An Intent-shaped build defers to the Domain. From a scratch Lakehouse, `dbt build --select mart_daily_zone_revenue --defer --state <dir>` built that mart alone, read `core.fct_trip` and `core.dim_zone` from the Domain, and matched the Domain's mart row for row (measured 2026-10-19). The state is the release's `manifest_prod.json` (4-part names, `+workspace_name` injected). The `prod-target/manifest.json` the deploy writes to `Files/` has 3-part names, which `source_defer.sql` refuses (`skill-changes.md`).

## Limits

- `ops` and `mdm` are generated from the TLC window the run loads; the window is `[sources.tlc] months` (default 2024-01 to 2024-03).
- The SQL analytics endpoint lists freshly written tables a few minutes after the run. Query over Spark (Livy, a notebook) to read them at once.
- The Domain's coordinates are committed; a second Domain from this repo means editing all three files above, not copying the repository unchanged.
