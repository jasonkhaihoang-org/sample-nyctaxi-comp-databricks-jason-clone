# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.12"
# META   }
# META }

# PARAMETERS CELL ********************

DOMAIN_SLUG = "nyc-taxi-fabric-demo"
PIPELINE_NAME = "mdm_pipeline"
CONNECTION_NAME = "mdm"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import os

LAKEHOUSE_FILES = "/lakehouse/default/Files"
if os.path.isdir(LAKEHOUSE_FILES):
    os.chdir(os.path.join(LAKEHOUSE_FILES, DOMAIN_SLUG, "ingestion"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

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
# MAGIC pip install -q -c /tmp/managed-constraints.txt vibedata-dlt-fabric-notebook vibedata-dlt-core
# MAGIC pip install -q -c /tmp/managed-constraints.txt -r requirements.txt

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

from vibedata.dlt.fabric import setup_environment

setup_environment()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import os

import dlt
from vibedata.dlt.core import dataset
from vibedata.dlt.fabric import finalize

from sources.mdm import mdm_source
from sources.tlc import zone_rows

# DLT_INGEST_LIMIT limits the rows of a safety run or sample load; unset loads everything.
NO_LIMIT = -1
LIMIT = int(os.environ.get("DLT_INGEST_LIMIT", NO_LIMIT))

# Each run regenerates the whole master, so every resource is a full replace.
# `tables` stays evolve: every Intent's Ephemeral Lakehouse starts empty (design record D-09/D-14).
CONTRACT = {"columns": "freeze", "tables": "evolve", "data_type": "freeze"}

pipeline = dlt.pipeline(
    pipeline_name=PIPELINE_NAME,
    destination="filesystem",
    dataset_name=dataset("mdm_raw"),
)

source = mdm_source.clone(name=CONNECTION_NAME, section=CONNECTION_NAME)(zone_lookup=zone_rows)
source.add_limit(LIMIT, count_rows=True)

# apply_hints is per-resource; a source-level call fails at run time.
for resource in source.selected_resources.values():
    resource.apply_hints(write_disposition="replace", schema_contract=CONTRACT)

try:
    load_info = pipeline.run(source, table_format="delta")
except Exception as exc:
    finalize(pipeline, error_message=str(exc))
    raise
print(load_info)
print("audit:", finalize(pipeline))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
