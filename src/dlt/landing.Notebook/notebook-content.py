# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# Setup: dlt-hub is not in the Fabric Spark runtime. Run once per session,
# then restart the session before the cells below.
# %pip install "dlt[deltalake]" "pyarrow>=17.0.0"
# Durable fix (not this cell): an Environment item carrying dlt, attached
# to this notebook.

# CELL ********************

# landing: bronze + silver conformed tables for nyc_taxi_lakehouse.
# Mirrors the brownfield builder tools/build_domain.py in the sibling clone
# (bronze landing + silver conforming), staged here with Lakehouse Files
# local raw/ paths build_domain.py reads. FULL-VOLUME landing: every row lands.
# Every write stamps _load_id, _source_file, _loaded_at.
#
# Engine split (dlt-hub has no lakehouse target and Fabric has no
# Delta-Live-Tables runtime, so each engine does what it is for):
# - dlt-hub resources yield RAW inputs (parquet files, zone CSV, static
#   ref rows) as record batches into Delta on the Lakehouse Files mount
#   (ADLS-backed OneLake; local path needs no credentials and no GUIDs --
#   swap DLT_ROOT for an abfss:// OneLake URL if an external account is
#   ever wanted).
# - Plain Spark SQL builds every derived table from that Delta and writes
#   it back as Delta; the registration cell publishes schemas + tables.
# dlt owns extract+load of raw (with state); Spark owns every transform.

import dlt
import datetime as dt
import glob as pyglob
import os
import pyarrow as pa
import pyarrow.csv as pa_csv
import pyarrow.parquet as pq
from dlt.destinations import filesystem
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Fixed load stamp, mirroring TIMESTAMP '2024-07-02 03:14:00' in build_domain.py.
LOADED_AT = "2024-07-02 03:14:00"
LOAD_YELLOW = "load_2024h1_yellow"
LOAD_GREEN = "load_2024h1_green"
LOAD_REF = "load_2024h1_ref"

# dlt landing zone: local Lakehouse Files mount (ADLS-backed, no credentials).
DLT_ROOT = "/lakehouse/default/Files/dlt/landing"
RAW_DIR = "/lakehouse/default/Files/raw"
DATASET = "landing"

# Explicit table -> schema map for registration. Nothing is inferred.
TABLE_SCHEMAS = {
    "bronze_yellow_tripdata": "bronze.yellow_tripdata",
    "bronze_green_tripdata": "bronze.green_tripdata",
    "bronze_taxi_zone_lookup": "bronze.taxi_zone_lookup",
    "bronze_payment_type_ref": "bronze.payment_type_ref",
    "bronze_rate_code_ref": "bronze.rate_code_ref",
    "bronze_vendor_ref": "bronze.vendor_ref",
    "silver_trips": "silver.trips",
    "silver_zones": "silver.zones",
    "silver_payment_types": "silver.payment_types",
    "silver_rate_codes": "silver.rate_codes",
}


def _stamp_batch(batch, load_id, source_file):
    """Append the three loader stamps to one Arrow batch."""
    n = batch.num_rows
    ts = pa.array(
        [dt.datetime.strptime(LOADED_AT, "%Y-%m-%d %H:%M:%S")] * n,
        type=pa.timestamp("us"),
    )
    return (
        batch.append_column("_load_id", pa.array([load_id] * n))
        .append_column("_source_file", pa.array([source_file] * n))
        .append_column("_loaded_at", ts)
    )


def delta_path(table):
    """Delta directory dlt wrote for one landed table. Single knob: if a
    first run shows dlt laying Delta out differently, change it here."""
    return "%s/%s/%s" % (DLT_ROOT, DATASET, table)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Bronze trip tables. Copies build_domain.py land() (build_domain.py:35-52):
# source columns preserved verbatim plus _load_id / _source_file / _loaded_at.
# Paths substituted: local raw/yellow_tripdata_2024-*.parquet (Jan-Jun 2024,
# per download_bronze_data.py DEFAULT_MONTHS) -> Lakehouse Files.
# Streamed per file in 100k-row batches: the driver never holds the load.


@dlt.resource(table_name="bronze_yellow_tripdata", write_disposition="replace", table_format="delta")
def yellow_tripdata():
    for path in sorted(pyglob.glob(RAW_DIR + "/yellow_tripdata_2024-*.parquet")):
        name = os.path.basename(path)
        reader = pq.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=100000):
            yield _stamp_batch(batch, LOAD_YELLOW, name)


@dlt.resource(table_name="bronze_green_tripdata", write_disposition="replace", table_format="delta")
def green_tripdata():
    for path in sorted(pyglob.glob(RAW_DIR + "/green_tripdata_2024-*.parquet")):
        name = os.path.basename(path)
        reader = pq.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=100000):
            yield _stamp_batch(batch, LOAD_GREEN, name)


# Bronze taxi_zone_lookup. Copies build_domain.py:54-63 (explicit column
# list + stamps; path raw/taxi_zone_lookup.csv -> Lakehouse Files).
# The CSV read leaves LocationID a string; downstream casts before any
# numeric test.
@dlt.resource(table_name="bronze_taxi_zone_lookup", write_disposition="replace", table_format="delta")
def taxi_zone_lookup():
    tbl = pa_csv.read_csv(
        RAW_DIR + "/taxi_zone_lookup.csv",
        read_options=pa_csv.ReadOptions(
            column_names=[
                "LocationID", "Borough", "Zone", "service_zone"],
            skip_rows=1),
    )
    for batch in tbl.to_batches(max_chunksize=100000):
        yield _stamp_batch(batch, LOAD_REF, "taxi_zone_lookup.csv")


# Hand-maintained refs. Static values copied verbatim from
# build_domain.py:67-93 (the team keeps these in the warehouse because the
# TLC data dictionary is a PDF). Stamped like every other write: the source
# SQL carries no stamps, but stamp-every-write wins.
@dlt.resource(table_name="bronze_payment_type_ref", write_disposition="replace", table_format="delta")
def payment_type_ref():
    rows = [(0, "Flex Fare trip"), (1, "Credit card"), (2, "Cash"),
            (3, "No charge"), (4, "Dispute"), (5, "Unknown"), (6, "Voided trip")]
    for payment_type, payment_type_desc in rows:
        yield {"payment_type": payment_type,
               "payment_type_desc": payment_type_desc,
               "_load_id": LOAD_REF,
               "_source_file": "payment_type_ref.csv",
               "_loaded_at": LOADED_AT}


@dlt.resource(table_name="bronze_rate_code_ref", write_disposition="replace", table_format="delta")
def rate_code_ref():
    rows = [(1, "Standard rate"), (2, "JFK"), (3, "Newark"),
            (4, "Nassau or Westchester"), (5, "Negotiated fare"), (6, "Group ride")]
    for rate_code_id, rate_code_desc in rows:
        yield {"rate_code_id": rate_code_id,
               "rate_code_desc": rate_code_desc,
               "_load_id": LOAD_REF,
               "_source_file": "rate_code_ref.csv",
               "_loaded_at": LOADED_AT}


@dlt.resource(table_name="bronze_vendor_ref", write_disposition="replace", table_format="delta")
def vendor_ref():
    rows = [(1, "Creative Mobile Technologies"), (2, "Curb Mobility"),
            (6, "Myle Technologies"), (7, "Helix")]
    for vendor_id, vendor_name in rows:
        yield {"vendor_id": vendor_id,
               "vendor_name": vendor_name,
               "_load_id": LOAD_REF,
               "_source_file": "vendor_ref.csv",
               "_loaded_at": LOADED_AT}


# Run raw ingestion: dlt streams the six resources above into Delta under
# DLT_ROOT/DATASET. dlt state lives in the pipeline working dir on the
# same mount (no credentials anywhere in this notebook).
pipeline = dlt.pipeline(
    pipeline_name="landing",
    destination=filesystem(bucket_url="file://%s" % DLT_ROOT,
                           kwargs={"auto_mkdir": True}),
    dataset_name=DATASET,
    pipelines_dir="/lakehouse/default/Files/dlt/pipelines",
)
load_info = pipeline.run([yellow_tripdata, green_tripdata, taxi_zone_lookup,
                          payment_type_ref, rate_code_ref, vendor_ref])
print(load_info)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# silver.trips. Copies the conforming transform at build_domain.py:105-157:
# yellow + green unioned onto one grain (renamed, typed), deduped to one row
# per trip_key via row_number ordered by _source_file. Reads the Delta dlt
# landed above -- plain Spark owns this transform, not dlt.
#
# Conforming note (build_domain.py:99-102): columns that exist on only one of
# the two fleets are dropped rather than carried as a mostly-null column --
# yellow's Airport_fee and green's ehail_fee / trip_type do not survive into
# silver. Anything needing them reads bronze.
CONFORMED_COLS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "passenger_count",
    "trip_distance", "rate_code_id", "store_and_fwd_flag",
    "pickup_location_id", "dropoff_location_id", "payment_type",
    "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "congestion_surcharge", "total_amount",
    "_load_id", "_source_file", "_loaded_at",
]


def _conform(frame, service_type, pickup_col, dropoff_col):
    return (
        frame.withColumn("service_type", F.lit(service_type))
        .withColumnRenamed("VendorID", "vendor_id")
        .withColumnRenamed(pickup_col, "pickup_datetime")
        .withColumnRenamed(dropoff_col, "dropoff_datetime")
        .withColumnRenamed("RatecodeID", "rate_code_id")
        .withColumnRenamed("PULocationID", "pickup_location_id")
        .withColumnRenamed("DOLocationID", "dropoff_location_id")
        .select("service_type", *CONFORMED_COLS)
    )


yellow = spark.read.format("delta").load(delta_path("bronze_yellow_tripdata"))
green = spark.read.format("delta").load(delta_path("bronze_green_tripdata"))
unioned = _conform(yellow, "yellow",
                   "tpep_pickup_datetime", "tpep_dropoff_datetime").unionByName(
    _conform(green, "green",
             "lpep_pickup_datetime", "lpep_dropoff_datetime")
)
key_cols = ["service_type", "vendor_id", "pickup_datetime", "dropoff_datetime",
            "pickup_location_id", "dropoff_location_id", "trip_distance", "total_amount"]
keyed = unioned.withColumn(
    "trip_key",
    F.md5(F.concat_ws("|", *[F.col(c).cast("string") for c in key_cols])),
).withColumn(
    "_dup_rank",
    F.row_number().over(Window.partitionBy(*key_cols).orderBy("_source_file")),
)
trips = keyed.filter(F.col("_dup_rank") == 1).drop("_dup_rank")
trips.write.format("delta").mode("overwrite").save(delta_path("silver_trips"))

# silver.zones / silver.payment_types / silver.rate_codes. Copies
# build_domain.py:159-180 (rename-only conform from bronze). The source SQL
# carries no stamps; stamp columns pass through from bronze so every write
# stays stamped. gold.* (dim_zone and the marts) is deliberately NOT ported:
# superseded by the dbt project.
zones = spark.read.format("delta").load(delta_path("bronze_taxi_zone_lookup")).select(
    F.col("LocationID").alias("location_id"),
    F.col("Borough").alias("borough"),
    F.col("Zone").alias("zone_name"),
    "service_zone", "_load_id", "_source_file", "_loaded_at",
)
zones.write.format("delta").mode("overwrite").save(delta_path("silver_zones"))

payment_types = spark.read.format("delta").load(delta_path("bronze_payment_type_ref")).select(
    "payment_type", "payment_type_desc", "_load_id", "_source_file", "_loaded_at",
)
payment_types.write.format("delta").mode("overwrite").save(delta_path("silver_payment_types"))

rate_codes = spark.read.format("delta").load(delta_path("bronze_rate_code_ref")).select(
    "rate_code_id", "rate_code_desc", "_load_id", "_source_file", "_loaded_at",
)
rate_codes.write.format("delta").mode("overwrite").save(delta_path("silver_rate_codes"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Registration: publish every landed + derived Delta directory as a
# <schema>.<table> in nyc_taxi_lakehouse per TABLE_SCHEMAS. dlt _state and
# _dlt_* directories are never tables. Rerun-safe (IF NOT EXISTS); to
# rebuild a table, drop it first and rerun this notebook.
for table, dotted in TABLE_SCHEMAS.items():
    schema, name = dotted.split(".")
    spark.sql("CREATE SCHEMA IF NOT EXISTS %s" % schema)
    spark.sql("CREATE TABLE IF NOT EXISTS %s.%s USING DELTA LOCATION '%s'"
              % (schema, name, delta_path(table)))
print("registered %d tables" % len(TABLE_SCHEMAS))
