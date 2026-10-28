# Databricks best practices

What the Databricks port relies on, with where each fact comes from:
- **plugin:** vde `origin/main` `5ec5dbe5f`, `_shared/platforms/databricks/*.md` and `templates/`, `scripts/platforms/databricks.py`. Studio's vde pin (`2cde8ea14`) predates the Databricks dlt notebook and orchestration work (VD-7389, VD-7390, VD-7412), so live runs need a pin that has them.
- **Studio:** `origin/main` of 2026-10-28;
- **domain-cicd:** `domain-ci-databricks-bundle`;
- **P1–P7:** the [probe record](../verify/2026-10-28-vd-7384-databricks-probe.md).

The decisions for VD-7385 come last. Repo maintenance only: build agents do not read this file.

## 1. Data types

- dlt lands a Python or DuckDB `DATE` as `date`, timestamps as `timestamp` (UTC), floats as `double`, booleans as `boolean` and integers as `bigint` (P7). The `ops` generator computes its dates as `DATE '…' + INTERVAL … DAY`, which DuckDB types as `TIMESTAMP`, so those land as timestamps at UTC midnight; `mdm`'s literal `DATE`s land as `date` (P7). The warehouse session time zone is UTC (P7).
- dlt folds column names to lower case: `VendorID` lands as `vendorid` (P7). Spark SQL resolves identifiers case-insensitively, so a model may keep `VendorID`; YAML that names columns (tests, contracts) should use the landed lower-case name.
- `/` is always fractional: `7/3600` is `0.00194…` (P7). Integer truncation, which Redshift needed a cast for, does not happen.
- `cast(timestamp as string)` trims trailing fractional zeros, and `cast(double as string)` gives the shortest form (`3.1`) (P7). This is Spark's behaviour on Fabric too, so the trip key renders the same way it did there.

## 2. Table design

- Tables are Delta. Layout is liquid clustering (`liquid_clustered_by`) or `partition_by`, not `sort`/`dist` (P1, P7).
- A view over a production source builds and reads in the Ephemeral catalog (P1). The Lakehouse ban on views (its SQL analytics endpoint could not read a Spark view) has no reason here.

## 3. dbt-databricks 1.12.6

- **Studio's profile:** name `dbt_databricks`, one target `databricks_sandbox`. Its catalog is `VD_EPHM_DATABRICKS_CATALOG` and its schema `VD_EPHM_DATABRICKS_MIRROR_SCHEMA`; the token is minted per dbt process by the shim (Studio `templates/databricks-dbt-profiles.yml`, plugin `dbt.md` § Sandbox run).
- **Schema resolution:** the plugin's `generate_schema_name` (copied verbatim from `_family/shared-container/templates/`) lands a `+schema:` node in `<VD_EPHM_SCHEMA_PREFIX><name>` in a sandbox and in `<name>` in prod (P1). Every layer of this repo sets `+schema:`, so a sandbox writes `<prefix>staging`, `<prefix>core`, … and never the mirror itself.
- **Source reads:** the plugin's `source_defer.sql` (same template folder) reads `<prefix><schema>` in the Ephemeral catalog when the Intent loaded that table, else the Domain's (P1). It needs no unit-test guard (P1).
- **Defer:** a `ref()` to a model the Intent did not build resolves to the Domain's released model through `--defer --state /cache/prod-target` (P1). Without `--defer` it fails with `TABLE_OR_VIEW_NOT_FOUND` (P1). Studio stages the one manifest the CI bundle publishes (`databricks.descriptor.ts` `deferManifest: 'none'`; `intent-prod-manifest-publication.ts`), and the plugin's `dbt.md` § Defer gives the command and the path selection.
- **Incremental:** `merge` and `delete+insert` (`fct_trip`'s strategy), each with a `unique_key`, run twice on Delta without duplicating a key (P1).
- **sqlfluff:** `dialect = databricks` with the jinja templater and every macro but `source_defer.sql` parses all models (P4).
- **Evaluator:** `dbt_project_evaluator` on dbt-duckdb still parses and builds with Databricks configs and the plugin's macros (P5).

## 4. dlt on Databricks

- **Pipeline file:** a notebook, `ingestion/<name>_pipeline.ipynb`, from the plugin's `templates/dlt-pipeline.ipynb`. The destination is `databricks_files_api()` from `vibedata-dlt-databricks-notebook`, and the notebook names no host, catalog, warehouse, schema or secret (plugin `dlt.md` § Authoring).
- **Runs:** a sandbox run uploads the committed repo and runs the notebook on serverless compute with `run_notebook.py`, overriding the catalog, warehouse, prefix and staging layout through `dlt_env` (plugin `dlt.md` § Sandbox run). A full load is the same command with `--limit -1` and no `--dev-mode` (plugin `dlt.md` § Full load).
- **Override precedence:** in dlt's resolver an environment key beats `ingestion/.dlt/config.toml` for every key it sets, so a sandbox run lands in the Ephemeral catalog whatever the file names (P6).
- **`databricks_files_api()` resolves no credentials:** vibedata-dlt-databricks-notebook 0.1.0 and 0.2.0 keep `credentials=None` as an explicit value, so dlt never reads the environment, `config.toml` or the secret scope for them, and the template notebook fails at load on compute (VD-7465, [`../verify/2026-10-28-vd-7385-databricks-runs.md`](../verify/2026-10-28-vd-7385-databricks-runs.md)).
- **The template's credentials section:** dlt 1.30 refuses `[destination.databricks.credentials]` in `config.toml` (`ValueNotSecretException`), with or without an override (P6); with VD-7465's fix, the same holds when `databricks_files_api()`'s configuration is resolved on a workstation ([`../verify/2026-10-28-vd-7385-databricks-runs.md`](../verify/2026-10-28-vd-7385-databricks-runs.md)). With no section, a run with no `dlt_env` catalog has none (VD-7442).
- **Datasets:** a load lands in `<prefix><dataset_name>` (the `dataset()` helper; P2).

## 5. Cross-catalog reads and writes

- An Intent writes the Domain's shared Ephemeral catalog; every Intent schema starts with `ephm__<domain>__<intent>__` (Studio `databricks-mirror-names.ts`). It reads production by three-part name.
- What stops a sandbox write to production is Unity Catalog grants: the driving user holds only `SELECT` there (Studio `databricks-dbt-profiles.yml`). The probes ran as an owner of both catalogs, so they show nothing about that boundary.
- Dev-mode cleanup lists and drops only in the Ephemeral catalog (P2). The bronze preview reads every table under the Intent's prefix, dbt-built ones included (P3).

## 6. Contradictions with the plugin and Studio

| Statement | Finding |
| --- | --- |
| Plugin `templates/dlt-config.toml` commits `[destination.databricks.credentials]` with `catalog` and `http_path`. | dlt 1.30's resolver refuses that section in `config.toml` with `ValueNotSecretException` (P6), even when the environment overrides both keys; confirmed for `databricks_files_api()` once VD-7465 is fixed (VD-7442). |
| Plugin `dbt.md` § Defer: copy `source_defer.sql` "unchanged; never overwrite one that exists". | The Lakehouse repo carries its own Fabric `source_defer.sql`; a port has to replace it with the shared template, which the rule's wording forbids an agent from doing. A repo decision (DBX-D1), not a plugin defect. |
| Studio `templates/databricks-dbt-project.yml`: "Every model builds into the Intent's one mirror schema regardless of the schema it configures (see databricks-generate-schema-name.sql)". | That macro is a reference Studio does not deliver; the plugin's macro lands `+schema:` in `<prefix><name>` (P1). The comment describes behaviour that does not happen. |
| Plugin `dlt.md` § Bronze preview. | Accurate, but it previews dbt-built tables too once the Intent has built any (P3). Worth one sentence; not a defect. |

## 7. What Studio does with a Databricks Intent

- **Opening an Intent:** the driving user creates the mirror schema `ephm__<domain>__<intent>__<primary>` in the Ephemeral catalog, and the service principal (the catalog owner) grants on it (Studio `databricks-dbt-profiles.yml`, `databricks-mirror-names.ts`).
- **Environment:** `VD_DOMAIN_DATABRICKS_{HOST,HTTP_PATH,CATALOG,PRIMARY_SCHEMA,PROD_HOST,PROD_HTTP_PATH}`, `VD_EPHM_DATABRICKS_{CATALOG,MIRROR_SCHEMA}`, `VD_EPHM_SCHEMA_PREFIX`, `DESTINATION__STAGING_DATASET_NAME_LAYOUT` (plugin `lib/contracts/studio/runtime-contract.json`).
- **Production manifest:** staged into `/cache/prod-target` from the release the CI bundle publishes (`deferManifest: 'none'`: one manifest).
- **CI:** `ciMode: 'gha'`; `domain-ci-databricks-bundle` installs `publish-prod-manifest-databricks.yml`, an offline `dbt_databricks_compile` profile, and `.workflow/ci-config.yml` (`VD_DOMAIN_DATABRICKS_CATALOG`, `VD_DOMAIN_DATABRICKS_PRIMARY_SCHEMA`). It runs no PR gates.
- **Secrets:** a Databricks-backed secret scope as the Domain's secret store (`databricks_secret_scope`; Studio `docs/adr/0221-a-databricks-secret-scope-is-listed-as-the-identity-that-reads-it-and-studio-grants-that-identity-read.md`).

## Decisions for VD-7385

- **DBX-D1 Macros.** Replace `transformation/macros/source_defer.sql` and `generate_schema_name.sql` with the plugin's `_family/shared-container/templates/` copies, unchanged (P1).
- **DBX-D2 Materialisation.** Keep every model a table, by choice (one rule for the project, as on Fabric); the Fabric reason (the SQL endpoint cannot read a Spark view) goes from the skills, and `test_dbt_project_is_fabricspark`'s no-view assertion with it.
- **DBX-D3 Dates.** `utc_date()` stays for the `ops` dates, which land as timestamps at UTC midnight (P7); it keeps their calendar day whatever the session's zone, although the warehouse session is UTC. A `date` column (`mdm`, TLC) is cast with `cast(... as date)`.
- **DBX-D4 Division and keys.** `safe_divide` and `trip_natural_key` stay as they are (P7).
- **DBX-D5 Column names.** Bronze column names are lower case on Databricks (P7). YAML column names (tests, contracts, `columns:`) use the landed name.
- **DBX-D6 Layout.**
  - Pipelines become `ingestion/<name>_pipeline.ipynb` from the plugin template; the `.Notebook` folders go. Pipeline names stay `tlc_pipeline`, `ops_pipeline`, `mdm_pipeline`.
  - Orchestration becomes `databricks.yml` and `orchestration/nyc_taxi_refresh.job.yml` from the plugin templates (three notebook tasks, then the dbt task), validated by `validate-job.py`; the `.DataPipeline` and the dbt notebook go. Tag the job `project=nyctaxi-databricks`.
  - `.sqlfluff`: `dialect = databricks`, jinja templater, every macro but `source_defer.sql` (P4).
  - `requirements-dev.txt`: `dbt-databricks`.
  - `transformation/profiles.yml`: `dbt_databricks` with a `prod` target on `nyctaxi_prod`; `dbt_project.yml` names `profile: dbt_databricks` literally. The Lakehouse repo's `env_var('DBT_PROFILE_NAME', …)` failed the bundle job's dbt task in the first release run with `Could not find profile named 'dbt_databricks'` ([seed run](../verify/2026-10-28-vd-7386-databricks-seed.md)). The literal name passed the second; Studio exports `DBT_PROFILE_NAME=dbt_databricks`, the same name.
- **DBX-D7 dlt config.** `ingestion/.dlt/config.toml` carries no credentials section: dlt refuses one there (P6, VD-7442). The catalog and warehouse reach the notebooks through `dlt_env`: a sandbox run passes the Ephemeral ones, and the job's `dlt_env` variable defaults to the catalog and warehouse it is deployed with (the plugin's fixed `databricks.yml` template). The notebooks stay exactly as the template builds them, and load on vibedata-dlt-databricks-notebook 0.2.1 (VD-7465), which this repo pins: seed run 4, from the committed repository.
- **DBX-D8 CI.** The Fabric six-gate workflows (`ci.yml`, `deploy-orchestration.yml`, `workspace-cleanup.yml`, `publish-prod-manifest.yml` and their profiles) gave way to the Databricks bundle in VD-7386 (domain-cicd `22f9069`, installed with its own `bundle_deploy.py`). `repo-checks.yml` and `dbt-project-quality.yml` stay.
- **DBX-D9 Domain.** Slug `nyc-taxi-databricks`; production catalog `nyctaxi_prod`; Ephemeral catalog `nyctaxi_ephm`; Primary Schema `main` (no model writes it, since every layer sets `+schema:`).
- **DBX-D10 Sources.** Each source's `database` is `"{{ env_var('VD_DOMAIN_DATABRICKS_CATALOG', target.database) }}"`. The shared `source()` resolves an unloaded source to the relation the sources YAML names, so that relation must carry the Domain catalog: with no `database`, dbt fills in the target's, which in a sandbox is the Ephemeral catalog (P1 named `database: nyctaxi_prod` literally). In a release the `prod` target *is* the Domain catalog, and no catalog name is written into a file.
- **DBX-D11 Orchestration proof.** The job never runs in a sandbox: every layer sets `+schema:`, and plugin `orchestration.md` § Sandbox run has `validate-job.py --sandbox` refuse that and says such a job is proven by its CI run. VD-7385 proves the job with `validate-job.py` (exit 0) and VD-7386 with the release's job run (seed S1: `PASS=219`).

## Still to probe

- A Studio Intent's grants. A principal holding only a driving user's grants behaved as Studio's design says (seed S3), but no Studio Intent, and so no Domain service principal of Studio's, has run on this Domain yet (VD-7387).
- Whether `VD_DOMAIN_DATABRICKS_CATALOG` reaches the dbt process DBX-D10 reads. The runtime contract carries it in the Intent context file only (`carrier: file-only`), and Studio's dbt shim (`src/agent-server/shims/vd-dbt.sh`) exports that file's values (`vd context export`) before it runs dbt; no Studio Intent has run this repo yet (VD-7387's journey is the first).

## Settled in VD-7386

- The production job's `dlt_env` default wrote all three loads to `nyctaxi_prod` in a real deploy and run (seed S1).
- The bundle job's run: run 4 of the release, deployed from the committed repository with 0.2.1 from PyPI, passed with `PASS=219`; run 1 had failed on a templated `profile:` (DBX-D6, VD-7488).
