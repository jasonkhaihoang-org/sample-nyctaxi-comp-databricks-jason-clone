# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   }
# META }

# MARKDOWN ********************

# # Vibedata dbt job — nyc_taxi_build_dbt
#
# Runs this job's dbt commands on the Domain's dbt project, delivered to
# `Files/nyc-taxi-fabric-demo/transformation` in the attached Lakehouse. Production builds with
# the project's own `prod` profile; an Intent's upload delivers its own profile beside
# it, `ephemeral_platform`, and the run defers to production.
#
# `DBT_OUTPUT_DIR` names this run's folder, `Files/nyc-taxi-fabric-demo/runs/<DBT_OUTPUT_DIR>/`,
# where dbt writes `target/` and `dbt.log`; the invoking activity passes its run id.

# PARAMETERS CELL ********************

DBT_OUTPUT_DIR = "manual"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 1. Install

# CELL ********************

# MAGIC %%sh
# MAGIC cat > /tmp/managed-constraints.txt <<'EOF'
# MAGIC dbt-core==1.12.5
# MAGIC dbt-fabric==1.11.1
# MAGIC dbt-fabricspark==1.13.8
# MAGIC dbt-duckdb==1.11.0
# MAGIC dbt-redshift==1.11.1
# MAGIC dbt-bigquery==1.12.1
# MAGIC dlt==1.30.0
# MAGIC sqlfluff==4.4.0
# MAGIC sqlfluff-templater-dbt==4.4.0
# MAGIC dbt-databricks==1.12.6
# MAGIC databricks-sdk==0.117.0
# MAGIC databricks-sql-connector==4.4.0
# MAGIC dbt-snowflake==1.12.1
# MAGIC snowflake-connector-python==4.8.0
# MAGIC vibedata-dbt-fabric-notebook==0.2.1
# MAGIC vibedata-dlt-core==0.10.0
# MAGIC vibedata-dlt-fabric-notebook==0.11.0
# MAGIC vibedata-dlt-fabric-studio==0.19.1
# MAGIC vibedata-dlt-fabric-warehouse-studio==0.7.0
# MAGIC vibedata-dlt-duckdb-core==0.3.0
# MAGIC vibedata-dlt-duckdb-studio==0.13.0
# MAGIC vibedata-motherduck-flight==0.1.0
# MAGIC vibedata-dlt-studio-secrets==0.5.0
# MAGIC vibedata-studio-azure-cred-broker==0.2.0
# MAGIC vibedata-dlt-redshift-studio>=0.3.0
# MAGIC duckdb>=1.5.5
# MAGIC EOF
# MAGIC pip install -q -c /tmp/managed-constraints.txt vibedata-dbt-fabric-notebook dbt-core dbt-fabricspark

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 2. Prerequisites

# CELL ********************

from vibedata.dbt.fabric import (
    enable_defer_if_not_prod, set_dbt_env_vars, stage_dbt_project_locally, use_intent_profile_if_present,
)

project = stage_dbt_project_locally(domain_slug="nyc-taxi-fabric-demo")
set_dbt_env_vars(project, domain_slug="nyc-taxi-fabric-demo", output_dir=DBT_OUTPUT_DIR)
use_intent_profile_if_present(domain_slug="nyc-taxi-fabric-demo")
enable_defer_if_not_prod(project, manifest_dir="prod-target")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 3. Run

# CELL ********************

# MAGIC %%sh
# MAGIC set -e
# MAGIC cd "$DBT_PROJECT_DIR"
# MAGIC dbt deps
# MAGIC dbt build

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
