# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# fleet_ops: Harbour Point Taxi Management dispatch/telematics feed (ops_raw.*).
# Mirrors the brownfield builder tools/build_fleet_ops.py in the sibling clone
# (garage 6 -> vehicle 420 -> driver 760 -> lease -> shift ~73k ->
# trip_assignment ~978k -> status events ~3.8M -> maintenance), staged here as
# dlt resources in dependency order. The timing skeleton reads the Task 6
# silver_trips table via spark.table: it is landed by the landing notebook's
# pipeline run, so dlt.read (same-run only) cannot see it.
# Deterministic, NO rng: every pseudo-random choice is hb() of a key, and
# generate_series/unnest become spark.range / explicit small frames.
# All four deliberate imperfections are KEPT (flagged downstream, not cleaned),
# each marked below with its downstream flag. Every write stamps _load_id,
# _source_file, _loaded_at.
#
# DuckDB -> Spark SQL notes (values stay deterministic per key; exact
# cross-engine equality is NOT required):
# - hb(x) = CAST(hash(x) % 100000000 AS BIGINT) in DuckDB. Spark hash() is a
#   different function over the UTF-8 bytes, so bits differ per key; pmod
#   keeps the remainder non-negative where DuckDB % can go negative.
# - Per-row variable intervals (sign-on offsets, clock skew) use unix-second
#   arithmetic: a dynamic INTERVAL literal is not expressible per row.
# - Cumulative shift_seq uses rowsBetween (ROWS semantics): the default RANGE
#   frame would merge rows sharing a pickup timestamp.
# - QUALIFY is rewritten as a lead() subquery plus filter.

import dlt
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Fixed load stamp: build_fleet_ops.py carries no stamp of its own, so the
# notebook owns one. Fixed (never current_timestamp) to keep reruns identical.
LOADED_AT = "2024-07-02 04:10:00"
SOURCE_FILE = "build_fleet_ops.py"

N_VEHICLES = 420
N_DRIVERS = 760
N_GARAGES = 6


def hb(col):
    """DuckDB hb(x) macro port: deterministic pseudo-random int per key."""
    return F.pmod(F.hash(col), F.lit(100000000))


def _stamp(frame, load_id):
    """Loader stamps on every write: fixed _loaded_at keeps reruns identical."""
    return (
        frame.withColumn("_load_id", F.lit(load_id))
        .withColumn("_source_file", F.lit(SOURCE_FILE))
        .withColumn("_loaded_at", F.to_timestamp(F.lit(LOADED_AT)))
    )


def _minus_minutes(ts_col, minutes_col):
    """ts_col minus a per-row minute offset (no dynamic INTERVAL literal)."""
    return F.from_unixtime(ts_col.cast("long") - minutes_col * 60).cast("timestamp")


def _plus_minutes(ts_col, minutes_col):
    """ts_col plus a per-row minute offset (no dynamic INTERVAL literal)."""
    return F.from_unixtime(ts_col.cast("long") + minutes_col * 60).cast("timestamp")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Reference entities. Copies build_fleet_ops.py:40-125: garage VALUES (6 rows),
# vehicle (420 medallions off spark.range), driver (760 hack licences), lease
# (one row per driver off dlt.read of the driver table; the source's count(*)
# over vehicle is the N_VEHICLES constant, 420 by construction). Range ids are
# long; string keys are cast before any concat/modulo so types never mix.
@dlt.table(name="ops_raw_garage", comment="Fleet garage master, 6 rows")
def garage():
    return _stamp(
        spark.createDataFrame(
            [(1, "Long Island City Depot", "Queens", 140, "2011-04-01"),
             (2, "Sunset Park Yard", "Brooklyn", 110, "2013-09-15"),
             (3, "Hunts Point Garage", "Bronx", 80, "2015-06-01"),
             (4, "Willets Point Annex", "Queens", 60, "2019-02-11"),
             (5, "Bay Ridge Overflow", "Brooklyn", 40, "2021-08-30"),
             (6, "Harbour Point HQ Lot", "Manhattan", 30, "2009-01-01")],
            ["garage_id", "garage_name", "borough", "bay_capacity", "opened_date"],
        ).withColumn("opened_date", F.to_date("opened_date")),
        "ops_garage_v1",
    )


@dlt.table(name="ops_raw_vehicle", comment="Fleet vehicle master, 420 medallions")
def vehicle():
    n = F.col("n")
    return _stamp(
        spark.range(1, N_VEHICLES + 1).withColumnRenamed("id", "n")
        .withColumn("vehicle_id", n)
        .withColumn("medallion_number",
                    F.format_string("%d%s%02d", 1 + (n % 9),
                                    F.chr((65 + (n * 7) % 26).cast("int")),
                                    1 + (n % 99)))
        .withColumn("vin", F.concat(F.lit("HPT"),
                                    F.lpad((100000 + n * 37).cast("string"), 8, "0")))
        .withColumn("make", F.when(n % 5 == 0, "Toyota")
                    .when(n % 5 == 1, "Nissan")
                    .when(n % 5 == 2, "Toyota")
                    .when(n % 5 == 3, "Ford").otherwise("Chevrolet"))
        .withColumn("model", F.when(n % 5 == 0, "Camry Hybrid")
                    .when(n % 5 == 1, "NV200")
                    .when(n % 5 == 2, "Sienna")
                    .when(n % 5 == 3, "Escape Hybrid").otherwise("Malibu"))
        .withColumn("model_year", 2016 + (n % 8))
        .withColumn("fuel_type", F.when((n % 5).isin(0, 3), "hybrid")
                    .when(n % 23 == 0, "electric").otherwise("gasoline"))
        .withColumn("wheelchair_accessible", n % 9 == 0)
        .withColumn("garage_id", 1 + (n % N_GARAGES))
        .withColumn("in_service_date",
                    F.date_add(F.to_date(F.lit("2016-01-01")),
                               F.pmod(n * 11, F.lit(2900)).cast("int")))
        .withColumn("retired_date",
                    F.when(n % 47 == 0,
                           F.date_add(F.to_date(F.lit("2024-01-01")),
                                      (n % 150).cast("int"))))
        .select("vehicle_id", "medallion_number", "vin", "make", "model",
                "model_year", "fuel_type", "wheelchair_accessible", "garage_id",
                "in_service_date", "retired_date"),
        "ops_vehicle_v1",
    )


@dlt.table(name="ops_raw_driver", comment="Fleet driver master, 760 hack licences")
def driver():
    n = F.col("n")
    return _stamp(
        spark.range(1, N_DRIVERS + 1).withColumnRenamed("id", "n")
        .withColumn("driver_id", n)
        .withColumn("hack_licence_no",
                    F.concat(F.lit("5"),
                             F.lpad((400000 + n * 13).cast("string"), 6, "0")))
        .withColumn("driver_ref", F.concat(F.lit("DRV-"), F.lpad(n.cast("string"), 4, "0")))
        .withColumn("engagement_type", F.when(n % 4 == 0, "owner_operator")
                    .when(n % 4 == 1, "lease_daily")
                    .when(n % 4 == 2, "lease_weekly").otherwise("lease_daily"))
        .withColumn("home_garage_id", 1 + (n % N_GARAGES))
        .withColumn("hire_date",
                    F.date_add(F.to_date(F.lit("2012-01-01")),
                               F.pmod(n * 19, F.lit(4300)).cast("int")))
        .withColumn("termination_date",
                    F.when(n % 31 == 0,
                           F.date_add(F.to_date(F.lit("2024-02-01")),
                                      (n % 120).cast("int"))))
        .withColumn("is_wav_certified", n % 6 == 0)
        .withColumn("driver_status",
                    F.when(n % 31 == 0, "terminated").otherwise("active"))
        .select("driver_id", "hack_licence_no", "driver_ref", "engagement_type",
                "home_garage_id", "hire_date", "termination_date",
                "is_wav_certified", "driver_status"),
        "ops_driver_v1",
    )


@dlt.table(name="ops_raw_lease_agreement", comment="Driver lease terms, one row per driver")
def lease_agreement():
    d = dlt.read("ops_raw_driver")
    lease_type = F.col("lease_type")
    driver_id = F.col("driver_id")
    return _stamp(
        d.withColumn("lease_id", F.row_number().over(Window.orderBy("driver_id")))
        .withColumn("primary_vehicle_id",
                    1 + F.pmod(driver_id * 3, F.lit(N_VEHICLES)))
        .withColumnRenamed("engagement_type", "lease_type")
        .withColumn("lease_rate",
                    F.when(lease_type == "owner_operator", F.lit(0.00))
                    .when(lease_type == "lease_weekly", 830.00 + (driver_id % 7) * 10)
                    .otherwise(129.00 + (driver_id % 5) * 6))
        .withColumn("revenue_share_pct",
                    F.when(lease_type == "owner_operator", F.lit(0.12))
                    .otherwise(F.lit(0.00)))
        .withColumn("lease_start_date",
                    F.greatest(F.col("hire_date"), F.to_date(F.lit("2022-01-01"))))
        .withColumnRenamed("termination_date", "lease_end_date")
        .select("lease_id", "driver_id", "primary_vehicle_id", "lease_type",
                "lease_rate", "revenue_share_pct", "lease_start_date", "lease_end_date"),
        "ops_lease_v1",
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Attribution + shift shaping. Copies build_fleet_ops.py:127-243: Harbour Point
# runs ~420 medallions, so it sees an hb-bucketed slice of yellow trips, made
# temporally consistent per vehicle by the overlap drop; consecutive trips
# <5h apart share a shift. The three TEMP stages stay plain helpers so only
# ops_raw.* tables land in the dataset. Skeleton columns off silver_trips:
# trip_key, pickup_datetime, dropoff_datetime, pickup_location_id,
# dropoff_location_id, trip_distance (total_amount carried, service_type cut).
def _candidate_trips():
    t = spark.table("silver_trips")
    duration_s = (F.col("dropoff_datetime").cast("long")
                  - F.col("pickup_datetime").cast("long"))
    return (
        t.filter(F.col("service_type") == "yellow")
        .filter(F.pmod(hb(F.concat(F.col("trip_key"), F.lit("harbourpoint"))),
                       F.lit(100)) < 6)
        .filter(F.col("pickup_datetime") >= F.to_timestamp(F.lit("2024-01-01")))
        .filter(F.col("pickup_datetime") < F.to_timestamp(F.lit("2024-07-01")))
        .filter((duration_s > 0) & (duration_s < 6 * 3600))
        .withColumn("vehicle_id", 1 + F.pmod(hb(F.col("trip_key")), F.lit(N_VEHICLES)))
        .select("trip_key", "pickup_datetime", "dropoff_datetime",
                "pickup_location_id", "dropoff_location_id",
                "total_amount", "trip_distance", "vehicle_id")
    )


def _fleet_trips():
    w = Window.partitionBy("vehicle_id").orderBy("pickup_datetime")
    return (
        _candidate_trips()
        .withColumn("prev_dropoff", F.lag("dropoff_datetime").over(w))
        .filter(F.col("prev_dropoff").isNull()
                | (F.col("pickup_datetime") >= F.col("prev_dropoff")))
        .drop("prev_dropoff")
    )


def _trip_shift():
    w = Window.partitionBy("vehicle_id").orderBy("pickup_datetime")
    prev_dropoff = F.lag("dropoff_datetime").over(w)
    gap_s = F.col("pickup_datetime").cast("long") - prev_dropoff.cast("long")
    seq = (Window.partitionBy("vehicle_id").orderBy("pickup_datetime")
           .rowsBetween(Window.unboundedPreceding, Window.currentRow))
    return (
        _fleet_trips()
        .withColumn("is_shift_start",
                    F.when(prev_dropoff.isNull() | (gap_s > 5 * 3600), 1).otherwise(0))
        .withColumn("shift_seq", F.sum("is_shift_start").over(seq))
    )


@dlt.table(name="ops_raw_shift", comment="Driver sign-ons with telematics imperfections kept")
def shift():
    agg = (
        _trip_shift().groupBy("vehicle_id", "shift_seq")
        .agg(F.min("pickup_datetime").alias("first_trip_ts"),
             F.max("dropoff_datetime").alias("last_trip_ts"),
             F.count("*").alias("trip_count"),
             F.sum("trip_distance").alias("shift_miles"))
    )
    keyed = agg.withColumn(
        "shift_id",
        F.concat(F.lit("SH-"),
                 F.lpad(F.row_number()
                        .over(Window.orderBy("vehicle_id", "shift_seq"))
                        .cast("string"), 8, "0")))
    vkey = F.concat(F.col("vehicle_id").cast("string"), F.col("shift_seq").cast("string"))
    skey = F.concat(F.col("shift_seq").cast("string"), F.col("vehicle_id").cast("string"))
    shift_id = F.col("shift_id")
    return _stamp(
        keyed.withColumn("shift_start_ts",
                         _minus_minutes(F.col("first_trip_ts"),
                                        7 + F.pmod(hb(vkey), F.lit(38))))
        .withColumn("_full_end_ts",
                    _plus_minutes(F.col("last_trip_ts"),
                                  4 + F.pmod(hb(skey), F.lit(26))))
        .withColumn("driver_id",
                    F.when(F.pmod(hb(shift_id), F.lit(5)) < 4,
                           1 + F.pmod(F.col("vehicle_id") * 7, F.lit(N_DRIVERS)))
                    .otherwise(1 + F.pmod(hb(F.concat(shift_id, F.lit("cover"))),
                                          F.lit(N_DRIVERS))))
        # IMPERFECTION 1 (missing LOGOUTs): the tablet died mid-shift, so the
        # end stays null; downstream stg_ops__shifts flags is_unclosed_shift
        # and substitutes derived_end_ts. Not cleaned here.
        .withColumn("shift_end_ts",
                    F.when(F.pmod(hb(F.concat(shift_id, F.lit("close"))),
                                   F.lit(200)) < 3,
                           F.lit(None).cast("timestamp"))
                    .otherwise(F.col("_full_end_ts")))
        .withColumn("derived_end_ts", F.col("_full_end_ts"))
        .withColumnRenamed("trip_count", "reported_trip_count")
        .withColumn("odometer_start",
                    F.round(12000 + F.pmod(hb(shift_id), F.lit(180000)) / F.lit(1.0), 0))
        # IMPERFECTION 4 (missing odometers): ~1-in-50 shifts carry a null
        # odometer_end; downstream odometer_miles goes null and fct_shift's
        # nullif-guarded paid_mile_ratio stays null instead of dividing.
        .withColumn("odometer_end",
                    F.when(F.pmod(hb(F.concat(shift_id, F.lit("odo"))),
                                   F.lit(50)) == 0,
                           F.lit(None).cast("double"))
                    .otherwise(F.round(12000 + F.pmod(hb(shift_id), F.lit(180000))
                                       + F.col("shift_miles"), 0)))
        .withColumn("telematics_source",
                    F.when(F.pmod(hb(F.concat(shift_id, F.lit("src"))),
                                   F.lit(100)) < 92, "tablet")
                    .otherwise("driver_app"))
        .select("shift_id", "vehicle_id", "driver_id", "shift_start_ts",
                "shift_end_ts", "derived_end_ts", "reported_trip_count",
                "odometer_start", "odometer_end", "telematics_source"),
        "ops_shift_v1",
    )


# Copies build_fleet_ops.py:245-263: each fleet trip joins its own shift
# window (start <= pickup, coalesce(end, derived) >= dropoff); the windows are
# gap-built per vehicle, so the join is exactly one row per trip. Any
# window-containment drift would surface in the ops shift-time reconciliation
# assert (assert_shift_time_budget_reconciles over int_shift_occupancy), so
# nothing is cleaned here.
@dlt.table(name="ops_raw_trip_assignment", comment="Trip-to-shift attribution")
def trip_assignment():
    ts = _trip_shift().alias("ts")
    sh = dlt.read("ops_raw_shift").alias("sh")
    j = (
        ts.join(sh,
                (F.col("sh.vehicle_id") == F.col("ts.vehicle_id"))
                & (F.col("sh.shift_start_ts") <= F.col("ts.pickup_datetime"))
                & (F.coalesce(F.col("sh.shift_end_ts"), F.col("sh.derived_end_ts"))
                   >= F.col("ts.dropoff_datetime")))
        .select(F.col("ts.trip_key").alias("trip_key"),
                F.col("sh.shift_id").alias("shift_id"),
                F.col("sh.driver_id").alias("driver_id"),
                F.col("ts.vehicle_id").alias("vehicle_id"),
                F.col("ts.pickup_datetime").alias("pickup_datetime"))
    )
    return _stamp(
        j.withColumn("assignment_id",
                     F.concat(F.lit("TA-"),
                              F.lpad(F.row_number()
                                     .over(Window.orderBy("vehicle_id", "pickup_datetime"))
                                     .cast("string"), 9, "0")))
        .withColumnRenamed("pickup_datetime", "assigned_ts")
        .withColumn("assignment_method",
                    F.when(F.pmod(hb(F.concat(F.col("trip_key"), F.lit("mtr"))),
                                   F.lit(500)) == 0, "manual")
                    .otherwise("auto"))
        .select("assignment_id", "trip_key", "shift_id", "driver_id",
                "vehicle_id", "assigned_ts", "assignment_method"),
        "ops_assign_v1",
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Status event stream. Copies build_fleet_ops.py:265-334: LOGIN -> AVAILABLE
# -> DISPATCHED -> ON_TRIP -> AVAILABLE ... -> LOGOUT per shift, BREAK on
# >25min fare gaps (QUALIFY rewritten as a lead() subquery plus filter).
# Location ids are cast to int up front: the CSV/parquet read can leave them
# strings, which would break the union and any numeric test downstream.
@dlt.table(name="ops_raw_driver_status_event", comment="Driver occupancy event stream")
def driver_status_event():
    ta = dlt.read("ops_raw_trip_assignment")
    ts = _trip_shift()
    sh = dlt.read("ops_raw_shift")
    base = ta.join(ts, ["trip_key", "vehicle_id"])
    cols = ["shift_id", "driver_id", "vehicle_id", "event_ts",
            "status_code", "zone_id", "ord"]
    trip_events = (
        base.select("shift_id", "driver_id", "vehicle_id",
                    F.expr("pickup_datetime - INTERVAL 3 MINUTES").alias("event_ts"),
                    F.lit("DISPATCHED").alias("status_code"),
                    F.col("pickup_location_id").cast("int").alias("zone_id"),
                    F.lit(2).alias("ord")).select(*cols).unionByName(
            base.select("shift_id", "driver_id", "vehicle_id",
                        F.col("pickup_datetime").alias("event_ts"),
                        F.lit("ON_TRIP").alias("status_code"),
                        F.col("pickup_location_id").cast("int").alias("zone_id"),
                        F.lit(3).alias("ord")).select(*cols)).unionByName(
            base.select("shift_id", "driver_id", "vehicle_id",
                        F.col("dropoff_datetime").alias("event_ts"),
                        F.lit("AVAILABLE").alias("status_code"),
                        F.col("dropoff_location_id").cast("int").alias("zone_id"),
                        F.lit(4).alias("ord")).select(*cols))
    )
    bookend = (
        sh.select("shift_id", "driver_id", "vehicle_id",
                  F.col("shift_start_ts").alias("event_ts"),
                  F.lit("LOGIN").alias("status_code"),
                  F.lit(None).cast("int").alias("zone_id"),
                  F.lit(1).alias("ord")).select(*cols).unionByName(
            sh.select("shift_id", "driver_id", "vehicle_id",
                      F.expr("shift_start_ts + INTERVAL 1 MINUTE").alias("event_ts"),
                      F.lit("AVAILABLE").alias("status_code"),
                      F.lit(None).cast("int").alias("zone_id"),
                      F.lit(1).alias("ord")).select(*cols)).unionByName(
            sh.filter(F.col("shift_end_ts").isNotNull())
            .select("shift_id", "driver_id", "vehicle_id",
                    F.col("shift_end_ts").alias("event_ts"),
                    F.lit("LOGOUT").alias("status_code"),
                    F.lit(None).cast("int").alias("zone_id"),
                    F.lit(9).alias("ord")).select(*cols))
    )
    bw = Window.partitionBy("shift_id").orderBy("pickup_datetime")
    breaks = (
        base.select("shift_id", "driver_id", "vehicle_id", "pickup_datetime",
                    "dropoff_datetime", "dropoff_location_id")
        .withColumn("next_pickup", F.lead("pickup_datetime").over(bw))
        .filter(F.col("next_pickup").cast("long")
                - F.col("dropoff_datetime").cast("long") > 25 * 60)
        .select("shift_id", "driver_id", "vehicle_id",
                F.expr("dropoff_datetime + INTERVAL 1 MINUTE").alias("event_ts"),
                F.lit("BREAK").alias("status_code"),
                F.col("dropoff_location_id").cast("int").alias("zone_id"),
                F.lit(5).alias("ord")).select(*cols)
    )
    allev = trip_events.unionByName(bookend).unionByName(breaks)
    return _stamp(
        allev.withColumn("event_id",
                         F.concat(F.lit("EV-"),
                                  F.lpad(F.row_number()
                                         .over(Window.orderBy("shift_id", "event_ts", "ord"))
                                         .cast("string"), 10, "0")))
        # IMPERFECTION 2 (out-of-order status events): ~1-in-333 events carry
        # a received_ts skewed +2min past event_ts, enough to invert against
        # the neighbour; downstream stg_ops__status_events exposes skew_seconds
        # and int_status_intervals orders on event_ts (never received_ts),
        # flagging is_negative_interval (assert_no_negative_status_intervals).
        .withColumn("received_ts",
                    F.when(F.pmod(hb(F.concat(F.col("shift_id"),
                                              F.col("event_ts").cast("string"))),
                                   F.lit(333)) == 0,
                           F.expr("event_ts + INTERVAL 2 MINUTES"))
                    .otherwise(F.col("event_ts")))
        .withColumn("source_system",
                    F.when(F.pmod(hb(F.col("shift_id")), F.lit(100)) < 92, "tablet")
                    .otherwise("driver_app"))
        .select("event_id", "shift_id", "driver_id", "vehicle_id", "event_ts",
                "status_code", "zone_id", "received_ts", "source_system"),
        "ops_status_v1",
    )


# Copies build_fleet_ops.py:336-351: up to 3 dated work orders per vehicle,
# hb-gated to keep ~2/3 (unnest([1, 2, 3]) as an explicit small frame).
@dlt.table(name="ops_raw_maintenance_event", comment="Vehicle maintenance work orders")
def maintenance_event():
    v = (dlt.read("ops_raw_vehicle")
         .select("vehicle_id", F.col("vehicle_id").cast("string").alias("vstr")))
    n = spark.createDataFrame([(1,), (2,), (3,)], ["d"])
    dkey = F.col("d").cast("string")
    x = v.crossJoin(n).filter(
        F.pmod(hb(F.concat(F.col("vstr"), dkey, F.lit("has"))), F.lit(3)) < 2)
    return _stamp(
        x.withColumn("maintenance_id",
                     F.concat(F.lit("MX-"),
                              F.lpad(F.row_number()
                                     .over(Window.orderBy("vehicle_id", "d"))
                                     .cast("string"), 7, "0")))
        .withColumn("started_date",
                    F.date_add(F.to_date(F.lit("2024-01-01")),
                               F.pmod(hb(F.concat(F.col("vstr"), dkey)),
                                       F.lit(180)).cast("int")))
        .withColumn("down_days",
                    1 + F.pmod(hb(F.concat(F.col("vstr"), dkey, F.lit("dur"))),
                               F.lit(4)))
        .withColumn("maintenance_type",
                    F.when(F.col("d") % 4 == 0, "scheduled_service")
                    .when(F.col("d") % 4 == 1, "brake_repair")
                    .when(F.col("d") % 4 == 2, "tlc_inspection")
                    .otherwise("collision_repair"))
        .withColumn("cost_usd",
                    F.round(120 + F.pmod(hb(F.concat(F.col("vstr"), dkey,
                                                    F.lit("cost"))),
                                          F.lit(2400)), 2))
        .select("maintenance_id", "vehicle_id", "started_date", "down_days",
                "maintenance_type", "cost_usd"),
        "ops_maint_v1",
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Run the pipeline against the default lakehouse (nyc_taxi_lakehouse).
# Lazy references: dlt owns execution, so pass the functions un-called.
pipeline = dlt.pipeline(pipeline_name="fleet_ops", destination="lakehouse", dataset_name="default")
load_info = pipeline.run([garage, vehicle, driver, lease_agreement,
                          shift, trip_assignment, driver_status_event,
                          maintenance_event])
print(load_info)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
