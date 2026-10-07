# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# marts_dbt: assert the marts slice (intermediate + core + agg) after the
# dbt build. Assumes the default lakehouse is nyc_taxi_lakehouse and the
# slice is built. Assert-only: no dbt invocation, no trigger API.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# M1: grain. One row per trip_key in core.fct_trip. Copies the unique +
# not_null tests on fct_trip.trip_key in
# src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/models/marts/core/_core.yml ("One row per TLC trip").
grain = spark.sql("""
    SELECT
        SUM(CASE WHEN trip_key IS NULL THEN 1 ELSE 0 END) AS null_keys,
        COUNT(*) - COUNT(DISTINCT trip_key) AS duplicate_keys
    FROM core.fct_trip
""").collect()[0]
assert grain.null_keys == 0, f"fct_trip: {grain.null_keys} null trip_key"
assert grain.duplicate_keys == 0, f"fct_trip: {grain.duplicate_keys} duplicate trip_key"
print("PASS grain: one row per trip_key in core.fct_trip")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# M2: dimension natural-key uniqueness and SCD2 non-overlap.
# Uniqueness copies the unique tests on dim_zone.zone_key and
# dim_vendor.vendor_key in src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/models/marts/core/_core.yml.
# Non-overlap copies src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/tests/
# assert_scd2_zone_intervals_do_not_overlap.sql verbatim in intent: the
# half-open intervals must tile cleanly per natural key.
for dim, surrogate in (("core.dim_zone", "zone_key"), ("core.dim_vendor", "vendor_key")):
    dupes = spark.sql(f"""
        SELECT COUNT(*) - COUNT(DISTINCT {surrogate}) AS duplicate_keys
        FROM {dim}
    """).collect()[0].duplicate_keys
    assert dupes == 0, f"{dim}: {dupes} duplicate {surrogate}"
    print(f"PASS uniqueness: {dim}.{surrogate}")

overlap = spark.sql("""
    WITH ranked AS (
        SELECT zone_natural_key, valid_from_date, valid_to_date,
               LEAD(valid_from_date) OVER (
                   PARTITION BY zone_natural_key ORDER BY valid_from_date
               ) AS next_from
        FROM core.dim_zone
    )
    SELECT COUNT(*) AS overlapping_intervals
    FROM ranked
    WHERE next_from IS NOT NULL AND valid_to_date > next_from
""").collect()[0].overlapping_intervals
assert overlap == 0, f"dim_zone: {overlap} overlapping SCD2 intervals"
print("PASS SCD2 non-overlap: core.dim_zone")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# M3: zone-join zero-unmatched. Copies the relationships tests on
# fct_trip.pickup_zone_key / dropoff_zone_key to dim_zone.zone_key in
# src/dbt/nyc_taxi_analytics.DataBuildToolJob/Code/dbt/models/marts/core/_core.yml: every fact-side key must
# resolve in the dimension.
unmatched = spark.sql("""
    SELECT COUNT(*) AS unmatched_rows
    FROM core.fct_trip f
    LEFT JOIN core.dim_zone zp ON f.pickup_zone_key = zp.zone_key
    LEFT JOIN core.dim_zone zd ON f.dropoff_zone_key = zd.zone_key
    WHERE (f.pickup_zone_key IS NOT NULL AND zp.zone_key IS NULL)
       OR (f.dropoff_zone_key IS NOT NULL AND zd.zone_key IS NULL)
""").collect()[0].unmatched_rows
assert unmatched == 0, f"fct_trip: {unmatched} zone keys unmatched in dim_zone"
print("PASS zone-join: zero unmatched zone keys")
