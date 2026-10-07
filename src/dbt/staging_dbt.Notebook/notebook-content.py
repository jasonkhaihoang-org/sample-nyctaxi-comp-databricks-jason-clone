# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# staging_dbt: assert the staging slice after the dbt build.
# Assumes the default lakehouse is nyc_taxi_lakehouse and the staging
# models are built. Assert-only: no dbt invocation, no trigger API.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# A1: per-fleet reconciliation. The yellow/green extras are deduplicated to
# one row per trip_key so the rejoin cannot multiply the fact (sibling:
# stg_tlc__yellow_trip_extras / stg_tlc__green_trip_extras descriptions in
# src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/models/staging/_staging.yml; multiplication hazard from
# src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/models/intermediate/int_trips_enriched description and
# src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/tests/assert_airport_fee_only_on_yellow.sql).
yellow = spark.sql("""
    SELECT
        (SELECT COUNT(*) FROM staging.stg_tlc__trips WHERE service_type = 'yellow') AS trips,
        (SELECT COUNT(*) FROM staging.stg_tlc__yellow_trip_extras) AS extras
""").collect()[0]
assert yellow.trips == yellow.extras, (
    f"yellow reconciliation failed: {yellow.trips} trips vs {yellow.extras} extras"
)
print(f"PASS yellow reconciliation: {yellow.trips} trips = {yellow.extras} extras")

green = spark.sql("""
    SELECT
        (SELECT COUNT(*) FROM staging.stg_tlc__trips WHERE service_type = 'green') AS trips,
        (SELECT COUNT(*) FROM staging.stg_tlc__green_trip_extras) AS extras
""").collect()[0]
assert green.trips == green.extras, (
    f"green reconciliation failed: {green.trips} trips vs {green.extras} extras"
)
print(f"PASS green reconciliation: {green.trips} trips = {green.extras} extras")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# A2: null-key checks. Copies the unique + not_null data tests on trip_key
# in src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/models/staging/_staging.yml (stg_tlc__trips,
# stg_tlc__yellow_trip_extras, stg_tlc__green_trip_extras).
for table in (
    "staging.stg_tlc__trips",
    "staging.stg_tlc__yellow_trip_extras",
    "staging.stg_tlc__green_trip_extras",
):
    bad = spark.sql(f"""
        SELECT
            SUM(CASE WHEN trip_key IS NULL THEN 1 ELSE 0 END) AS null_keys,
            COUNT(*) - COUNT(DISTINCT trip_key) AS duplicate_keys
        FROM {table}
    """).collect()[0]
    assert bad.null_keys == 0, f"{table}: {bad.null_keys} null trip_key"
    assert bad.duplicate_keys == 0, f"{table}: {bad.duplicate_keys} duplicate trip_key"
    print(f"PASS null-key check: {table}")
