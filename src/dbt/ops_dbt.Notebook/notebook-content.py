# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# ops_dbt: assert the ops slice after the dbt build.
# Assumes the default lakehouse is nyc_taxi_lakehouse and the ops models
# are built. Assert-only: no dbt invocation, no trigger API.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# O1: status-interval validity. Copies transformation/tests/
# assert_no_negative_status_intervals.sql verbatim in intent: the interval
# model floors at zero, and the floor must never have had to bite widely
# (threshold: 5000).
negative = spark.sql("""
    SELECT COUNT(*) AS negative_intervals
    FROM intermediate.int_status_intervals
    WHERE is_negative_interval
""").collect()[0].negative_intervals
assert negative <= 5000, f"int_status_intervals: {negative} negative intervals (cap 5000)"
print(f"PASS status intervals: {negative} negative (cap 5000)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# O2: shift-time reconciliation. Copies transformation/tests/
# assert_shift_time_budget_reconciles.sql verbatim in intent: on-trip,
# available and break seconds must not exceed the shift's online seconds
# (60-second tolerance); exceeding it means overlapping intervals.
over_budget = spark.sql("""
    SELECT COUNT(*) AS over_budget_shifts
    FROM intermediate.int_shift_occupancy
    WHERE on_trip_seconds + available_seconds + break_seconds > online_seconds + 60
""").collect()[0].over_budget_shifts
assert over_budget == 0, f"int_shift_occupancy: {over_budget} shifts over time budget"
print("PASS shift reconciliation: accounted seconds within online budget")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# O3: trip-quality flag presence. Every fact row carries a quality verdict
# through the junk dimension (sibling: relationships test on
# fct_trip.trip_quality_key to dim_trip_quality in
# transformation/models/marts/core/_core.yml; junk-dimension description on
# dim_trip_quality). A null or dangling key means a trip escaped verdicts.
flagless = spark.sql("""
    SELECT COUNT(*) AS flagless_rows
    FROM core.fct_trip f
    LEFT JOIN core.dim_trip_quality q ON f.trip_quality_key = q.trip_quality_key
    WHERE f.trip_quality_key IS NULL OR q.trip_quality_key IS NULL
""").collect()[0].flagless_rows
assert flagless == 0, f"fct_trip: {flagless} rows without a trip-quality verdict"
print("PASS quality flags: every fact row has a dim_trip_quality verdict")
