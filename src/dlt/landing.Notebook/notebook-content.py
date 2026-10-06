# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# landing: bronze + silver.trips for nyc_taxi_lakehouse.
# Mirrors the brownfield builder tools/build_domain.py in the sibling clone
# (bronze landing + silver conforming), staged here with Lakehouse Files
# local raw/ paths build_domain.py reads. FULL-VOLUME landing: every row lands.
# Every write stamps _load_id, _source_file, _loaded_at.

import dlt
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Fixed load stamp, mirroring TIMESTAMP '2024-07-02 03:14:00' in build_domain.py.
LOADED_AT = "2024-07-02 03:14:00"
LOAD_YELLOW = "load_2024h1_yellow"
LOAD_GREEN = "load_2024h1_green"
LOAD_REF = "load_2024h1_ref"

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
@dlt.table(name="bronze_yellow_tripdata", comment="Bronze yellow trips, landed verbatim")
def yellow_tripdata():
    return (
        spark.read.parquet("Files/raw/yellow_tripdata_2024-*.parquet")
        .withColumn("_load_id", F.lit(LOAD_YELLOW))
        .withColumn("_source_file", F.regexp_extract(F.input_file_name(), "[^/]+$", 0))
        .withColumn("_loaded_at", F.to_timestamp(F.lit(LOADED_AT)))
    )


@dlt.table(name="bronze_green_tripdata", comment="Bronze green trips, landed verbatim")
def green_tripdata():
    return (
        spark.read.parquet("Files/raw/green_tripdata_2024-*.parquet")
        .withColumn("_load_id", F.lit(LOAD_GREEN))
        .withColumn("_source_file", F.regexp_extract(F.input_file_name(), "[^/]+$", 0))
        .withColumn("_loaded_at", F.to_timestamp(F.lit(LOADED_AT)))
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Bronze taxi_zone_lookup. Copies build_domain.py:54-63 (explicit column
# list + stamps; path raw/taxi_zone_lookup.csv -> Lakehouse Files).
@dlt.table(name="bronze_taxi_zone_lookup", comment="Bronze TLC zone lookup")
def taxi_zone_lookup():
    return (
        spark.read.option("header", True).csv("Files/raw/taxi_zone_lookup.csv")
        .select("LocationID", "Borough", "Zone", "service_zone")
        .withColumn("_load_id", F.lit(LOAD_REF))
        .withColumn("_source_file", F.lit("taxi_zone_lookup.csv"))
        .withColumn("_loaded_at", F.to_timestamp(F.lit(LOADED_AT)))
    )


# Hand-maintained refs. Static values copied verbatim from
# build_domain.py:67-93 (the team keeps these in the warehouse because the
# TLC data dictionary is a PDF).
@dlt.table(name="bronze_payment_type_ref", comment="Hand-maintained payment-type descriptions")
def payment_type_ref():
    return spark.createDataFrame(
        [(0, "Flex Fare trip"), (1, "Credit card"), (2, "Cash"),
         (3, "No charge"), (4, "Dispute"), (5, "Unknown"), (6, "Voided trip")],
        ["payment_type", "payment_type_desc"],
    )


@dlt.table(name="bronze_rate_code_ref", comment="Hand-maintained rate-code descriptions")
def rate_code_ref():
    return spark.createDataFrame(
        [(1, "Standard rate"), (2, "JFK"), (3, "Newark"),
         (4, "Nassau or Westchester"), (5, "Negotiated fare"), (6, "Group ride")],
        ["rate_code_id", "rate_code_desc"],
    )


@dlt.table(name="bronze_vendor_ref", comment="Hand-maintained vendor names")
def vendor_ref():
    return spark.createDataFrame(
        [(1, "Creative Mobile Technologies"), (2, "Curb Mobility"),
         (6, "Myle Technologies"), (7, "Helix")],
        ["vendor_id", "vendor_name"],
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# silver.trips. Copies the conforming transform at build_domain.py:105-157:
# yellow + green unioned onto one grain (renamed, typed), deduped to one row
# per trip_key via row_number ordered by _source_file.
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
    "_load_id", "_source_file",
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


@dlt.table(name="silver_trips", comment="Conformed yellow+green union, deduped")
def trips():
    unioned = _conform(dlt.read("bronze_yellow_tripdata"), "yellow",
                       "tpep_pickup_datetime", "tpep_dropoff_datetime").unionByName(
        _conform(dlt.read("bronze_green_tripdata"), "green",
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
    return keyed.filter(F.col("_dup_rank") == 1).drop("_dup_rank")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Run the pipeline against the default lakehouse (nyc_taxi_lakehouse).
pipeline = dlt.pipeline(pipeline_name="landing", destination="lakehouse", dataset_name="default")
load_info = pipeline.run([yellow_tripdata(), green_tripdata(), taxi_zone_lookup(),
                          payment_type_ref(), rate_code_ref(), vendor_ref(), trips()])
print(load_info)
