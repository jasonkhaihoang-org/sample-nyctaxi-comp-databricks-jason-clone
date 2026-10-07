# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# finance_dbt: assert the finance slice after the dbt build.
# Assumes the default lakehouse is nyc_taxi_lakehouse and the finance
# models are built. Assert-only: no dbt invocation, no trigger API.

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# F1: billable-trip definition. Copies transformation/models/intermediate/
# int_trip_quality_flags.sql: is_billable is total_amount > 0, applied in
# gold and nowhere upstream (ADR 0002). Every mart row must satisfy it.
mismatch = spark.sql("""
    SELECT COUNT(*) AS mismatched_rows
    FROM core.fct_trip
    WHERE is_billable != (total_amount > 0)
""").collect()[0].mismatched_rows
assert mismatch == 0, f"fct_trip: {mismatch} rows where is_billable != (total_amount > 0)"
print("PASS billable definition: is_billable = (total_amount > 0)")

non_billable_revenue = spark.sql("""
    SELECT SUM(trip_count) AS leaked_trips
    FROM finance.mart_daily_zone_revenue
    WHERE total_revenue <= 0
""").collect()[0].leaked_trips
assert (non_billable_revenue or 0) == 0, (
    f"mart_daily_zone_revenue: {non_billable_revenue} trips with non-positive revenue"
)
print("PASS billable definition: no non-positive revenue rows in mart_daily_zone_revenue")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# F2: reporting-window bounds. Copies the in_report_window macro in
# transformation/macros/trip_keys.sql with the ADR 0002 vars from
# dbt_project.yml (report_start 2024-01-01, report_end 2024-07-01).
out_of_window = spark.sql("""
    SELECT COUNT(*) AS out_of_window_rows
    FROM finance.mart_daily_zone_revenue
    WHERE trip_date < DATE '2024-01-01' OR trip_date >= DATE '2024-07-01'
""").collect()[0].out_of_window_rows
assert out_of_window == 0, f"mart_daily_zone_revenue: {out_of_window} rows outside report window"
print("PASS reporting window: all trip_date in [2024-01-01, 2024-07-01)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# F3: revenue-bridge tie-out. Copies the construction of
# transformation/models/marts/finance/mart_revenue_component_bridge.sql:
# each group's unpivoted components (fare through residual) must walk back
# to the group's total_amount. The residual is its own component, so a
# non-zero walk is a finding about the source, not rounding to absorb.
unbalanced = spark.sql("""
    SELECT COUNT(*) AS unbalanced_groups
    FROM (
        SELECT trip_month, service_type_key, borough_name, MAX(total_amount) AS total_amount,
               SUM(component_amount) AS component_sum
        FROM finance.mart_revenue_component_bridge
        GROUP BY trip_month, service_type_key, borough_name
    )
    WHERE ABS(component_sum - total_amount) > 0.01
""").collect()[0].unbalanced_groups
assert unbalanced == 0, f"mart_revenue_component_bridge: {unbalanced} groups do not tie out"
print("PASS revenue bridge: components tie to total_amount per group")
