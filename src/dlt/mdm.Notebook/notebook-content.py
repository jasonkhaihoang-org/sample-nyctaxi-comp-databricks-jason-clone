# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

# Runtime libraries (dlt, deltalake, pyarrow) come from the attached
# dlt.Environment, NOT pip: %pip fails instantly in job sessions here.

# CELL ********************

# mdm: master-data platform raw landing (mdm_raw.*) for nyc_taxi_lakehouse.
# Mirrors the brownfield builder tools/build_mdm.py in the sibling clone
# (versioned zone/vendor masters + static reference masters + POI bridge +
# calendar + weather).
# NO SCD2 assembly here: raw versions land side by side and dbt owns
# conforming + SCD2 downstream. Every write stamps _load_id, _source_file,
# _loaded_at.
#
# Engine split (same as landing): dlt-hub resources yield the STATIC masters
# as records into Delta on the Lakehouse Files mount (ADLS-backed, no
# credentials); plain Spark SQL builds every derived master from Delta and
# writes it back. dlt owns extract+load of static rows; Spark owns transforms.
#
# DuckDB -> Spark SQL notes (values stay deterministic per key; exact
# cross-engine equality is NOT required):
# - hb(x) = CAST(hash(x) % 100000000 AS BIGINT) in DuckDB. Spark hash() is a
#   different function over the UTF-8 bytes, so bits differ per key; pmod
#   keeps the remainder non-negative where DuckDB % can go negative.
# - Spark dayofweek() returns 1 (Sunday)..7 (Saturday); DuckDB dayofweek()
#   returns 0..6, so the weekend test becomes IN (1, 7).
# - strftime(obs_date, '%Y%m%d') becomes date_format(obs_date, 'yyyyMMdd').

import dlt
import tempfile as _tf
from dlt.destinations import filesystem
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Fixed load stamp, mirroring TIMESTAMP '2024-07-02 02:40:00' in build_mdm.py.
LOADED_AT = "2024-07-02 02:40:00"

# dlt landing zone: local Lakehouse Files mount (ADLS-backed, no credentials).
DLT_ROOT = "/lakehouse/default/Files/dlt/mdm"
DATASET = "mdm"
# Bronze lives in the landing notebook's dataset (pipelines run landing first).
LANDING_DS = "/lakehouse/default/Files/dlt/landing/landing"

# Explicit table -> schema map for registration. Nothing is inferred.
TABLE_SCHEMAS = {
    "zone_master": "mdm_raw.zone_master",
    "vendor_master": "mdm_raw.vendor_master",
    "payment_method_master": "mdm_raw.payment_method_master",
    "rate_plan_master": "mdm_raw.rate_plan_master",
    "fare_regime_master": "mdm_raw.fare_regime_master",
    "borough_master": "mdm_raw.borough_master",
    "zone_poi": "mdm_raw.zone_poi",
    "calendar_master": "mdm_raw.calendar_master",
    "weather_daily": "mdm_raw.weather_daily",
}


def delta_path(table):
    """Delta directory dlt wrote for one landed table. Single knob: if a
    first run shows dlt laying Delta out differently, change it here."""
    return "%s/%s/%s" % (DLT_ROOT, DATASET, table)


def hb(col):
    """DuckDB hb(x) macro port: deterministic pseudo-random int per key."""
    return F.pmod(F.hash(col), F.lit(100000000))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Static reference masters. Values copied verbatim from build_mdm.py:97-182
# (VALUES lists; the team keeps these in the warehouse because the TLC code
# lists are bare codes and labels). Yielded as dlt records with the source's
# _load_id / _source_file plus the fixed _loaded_at.
# VENDOR MASTER -- versioned. Copies build_mdm.py:97-110: VendorID 2 traded
# as VeriFone until the Curb Mobility rebrand; the contract tier changed too.
@dlt.resource(table_name="vendor_master", write_disposition="replace", table_format="delta")
def vendor_master():
    rows = [(1, "Creative Mobile Technologies LLC", "CMT", "gold", "2011-01-01", "2099-12-31", 1, True),
            (2, "VeriFone Inc", "VTS", "silver", "2011-01-01", "2023-07-01", 1, True),
            (2, "Curb Mobility LLC", "CURB", "gold", "2023-07-01", "2099-12-31", 2, True),
            (6, "Myle Technologies Inc", "MYLE", "bronze", "2022-03-01", "2099-12-31", 1, True),
            (7, "Helix Technologies", "HELIX", "bronze", "2021-06-01", "2023-01-15", 1, False)]
    cols = ["vendor_id", "vendor_legal_name", "vendor_short_code", "contract_tier",
            "valid_from_date", "valid_to_date", "source_version", "is_approved"]
    for row in rows:
        rec = dict(zip(cols, row))
        rec["_load_id"] = "mdm_vendor_v2"
        rec["_source_file"] = "vendor_master.csv"
        rec["_loaded_at"] = LOADED_AT
        yield rec


@dlt.resource(table_name="payment_method_master", write_disposition="replace", table_format="delta")
def payment_method_master():
    rows = [(0, "Flex Fare trip", "electronic", True, 1, 0.0250, True),
            (1, "Credit card", "electronic", True, 2, 0.0290, True),
            (2, "Cash", "cash", False, 0, 0.0000, True),
            (3, "No charge", "waived", False, 0, 0.0000, False),
            (4, "Dispute", "contested", False, 30, 0.0000, False),
            (5, "Unknown", "unknown", False, 0, 0.0000, False),
            (6, "Voided trip", "voided", False, 0, 0.0000, False)]
    cols = ["payment_type_code", "payment_method_name", "settlement_class",
            "tip_is_captured", "settlement_days", "processor_fee_pct", "counts_as_revenue"]
    for row in rows:
        rec = dict(zip(cols, row))
        rec["_load_id"] = "mdm_pay_v1"
        rec["_source_file"] = "payment_method_master.csv"
        rec["_loaded_at"] = LOADED_AT
        yield rec


@dlt.resource(table_name="rate_plan_master", write_disposition="replace", table_format="delta")
def rate_plan_master():
    rows = [(1, "Standard metered", False, None, False, True, "meter"),
            (2, "JFK flat fare", True, 70.00, True, True, "flat"),
            (3, "Newark", False, None, True, True, "meter_plus"),
            (4, "Nassau or Westchester", False, None, False, True, "meter_plus"),
            (5, "Negotiated fare", False, None, False, False, "negotiated"),
            (6, "Group ride", True, None, False, False, "flat"),
            (99, "Undocumented code", False, None, False, False, "unknown")]
    cols = ["rate_code", "rate_plan_name", "is_flat_fare", "flat_fare_amount",
            "is_airport_plan", "is_metered_baseline", "pricing_model"]
    for row in rows:
        rec = dict(zip(cols, row))
        rec["_load_id"] = "mdm_rate_v1"
        rec["_source_file"] = "rate_plan_master.csv"
        rec["_loaded_at"] = LOADED_AT
        yield rec


@dlt.resource(table_name="fare_regime_master", write_disposition="replace", table_format="delta")
def fare_regime_master():
    rows = [("IMP-2015", "improvement_surcharge", 0.30, "all", "2015-01-01", "2023-12-01"),
            ("IMP-2023", "improvement_surcharge", 1.00, "all", "2023-12-01", "2099-12-31"),
            ("MTA-2009", "mta_tax", 0.50, "all", "2009-11-01", "2099-12-31"),
            ("CON-2019Y", "congestion_surcharge", 2.50, "yellow", "2019-02-01", "2099-12-31"),
            ("CON-2019G", "congestion_surcharge", 2.75, "green", "2019-02-01", "2099-12-31"),
            ("APT-2022", "airport_access_fee", 1.25, "yellow", "2022-09-01", "2023-12-01"),
            ("APT-2023", "airport_access_fee", 1.75, "yellow", "2023-12-01", "2099-12-31")]
    cols = ["regime_code", "fare_component", "rate_amount", "applies_to_fleet",
            "valid_from_date", "valid_to_date"]
    for row in rows:
        rec = dict(zip(cols, row))
        rec["_load_id"] = "mdm_regime_v1"
        rec["_source_file"] = "fare_regime_master.csv"
        rec["_loaded_at"] = LOADED_AT
        yield rec


@dlt.resource(table_name="borough_master", write_disposition="replace", table_format="delta")
def borough_master():
    rows = [("Manhattan", "MN", "Manhattan Core", 1694251, 22.83, True, True),
            ("Brooklyn", "BK", "Outer Boroughs", 2736074, 69.50, True, False),
            ("Queens", "QN", "Outer Boroughs", 2405464, 108.10, True, False),
            ("Bronx", "BX", "Outer Boroughs", 1472654, 42.10, True, False),
            ("Staten Island", "SI", "Outer Boroughs", 495747, 58.37, True, False),
            ("EWR", "NJ", "Out of State", 0, 0.00, False, False),
            ("Unknown", "XX", "Unresolved", 0, 0.00, False, False),
            ("N/A", "XX", "Unresolved", 0, 0.00, False, False)]
    cols = ["borough_name", "borough_code", "reporting_region", "resident_population",
            "area_sq_mi", "is_nyc", "is_core_market"]
    for row in rows:
        rec = dict(zip(cols, row))
        rec["_load_id"] = "mdm_boro_v1"
        rec["_source_file"] = "borough_master.csv"
        rec["_loaded_at"] = LOADED_AT
        yield rec


# Run static ingestion: dlt streams the five resources above into Delta.
# dlt state lives in an ephemeral local dir (full-replace loads keep no state).
pipeline = dlt.pipeline(
    pipeline_name="mdm",
    destination=filesystem(bucket_url="file://%s" % DLT_ROOT,
                           kwargs={"auto_mkdir": True}),
    dataset_name=DATASET,
    pipelines_dir=_tf.mkdtemp(prefix="dlt-"),
)
load_info = pipeline.run([vendor_master, payment_method_master,
                          rate_plan_master, fare_regime_master,
                          borough_master])
print(load_info)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ZONE MASTER -- versioned. Copies build_mdm.py:36-91: TLC zones enriched
# with pseudo-geography, a congestion flag and a demand tier; zones with
# location_id % 37 = 0 carry an expired first version (demand tier stepped
# down one level) plus the replacing second version. Reads the landing
# notebook's bronze_taxi_zone_lookup Delta (pipelines run landing first).
# The CSV read leaves LocationID a string, so cast before any numeric test.
# Plain Spark owns this transform, not dlt: it reads prior Delta.
zone_lookup = spark.read.format("delta").load(
    "%s/%s/%s" % ("/lakehouse/default/Files/dlt/landing", "landing",
                   "bronze_taxi_zone_lookup")).select(
    F.col("LocationID").cast("int").alias("location_id"),
    F.col("Borough").alias("borough_name"),
    F.col("Zone").alias("zone_label"),
    F.col("service_zone").alias("tlc_service_zone"),
)
tier_idx = F.pmod(hb(F.concat(F.col("zone_label"), F.lit("tier"))), F.lit(4))
base = (
    zone_lookup.withColumn("centroid_lat",
                 F.round(40.55 + F.pmod(hb(F.col("zone_label")), F.lit(42000)) / 100000.0, 6))
    .withColumn("centroid_lon",
                F.round(-74.05 + F.pmod(hb(F.concat(F.col("zone_label"), F.lit("lon"))),
                                        F.lit(38000)) / 100000.0, 6))
    .withColumn("area_sq_mi",
                F.round(0.4 + F.pmod(hb(F.concat(F.col("zone_label"), F.lit("area"))),
                                     F.lit(850)) / 100.0, 3))
    .withColumn("resident_population",
                F.pmod(hb(F.concat(F.col("zone_label"), F.lit("pop"))), F.lit(92000)) + 1800)
    .withColumn("is_airport_zone", F.col("location_id").isin(1, 132, 138))
    .withColumn("is_congestion_zone",
                (F.col("borough_name") == "Manhattan")
                & (F.pmod(hb(F.concat(F.col("zone_label"), F.lit("cz"))), F.lit(100)) < 62))
    .withColumn("zone_class",
                F.when(F.col("location_id").isin(1, 132, 138), "airport")
                .when(F.col("borough_name") == "Manhattan", "core")
                .when(F.col("borough_name").isin("Unknown", "N/A"), "unresolved")
                .otherwise("boro"))
    .withColumn("demand_tier",
                F.when(tier_idx == 0, "very_high")
                .when(tier_idx == 1, "high")
                .when(tier_idx == 2, "moderate")
                .otherwise("low"))
)
current = (
    base.filter(F.col("location_id") % 37 != 0)
    .withColumn("valid_from_date", F.to_date(F.lit("2019-01-01")))
    .withColumn("valid_to_date", F.to_date(F.lit("2099-12-31")))
    .withColumn("source_version", F.lit(1))
)
expired = (
    base.filter(F.col("location_id") % 37 == 0)
    .withColumn("demand_tier",
                F.when(F.col("demand_tier") == "very_high", "high")
                .when(F.col("demand_tier") == "high", "moderate")
                .otherwise("low"))
    .withColumn("valid_from_date", F.to_date(F.lit("2019-01-01")))
    .withColumn("valid_to_date", F.to_date(F.lit("2023-09-01")))
    .withColumn("source_version", F.lit(1))
)
replaced = (
    base.filter(F.col("location_id") % 37 == 0)
    .withColumn("valid_from_date", F.to_date(F.lit("2023-09-01")))
    .withColumn("valid_to_date", F.to_date(F.lit("2099-12-31")))
    .withColumn("source_version", F.lit(2))
)
zone_master = (
    current.unionByName(expired).unionByName(replaced)
    .withColumn("_load_id", F.lit("mdm_zone_v3"))
    .withColumn("_source_file", F.lit("zone_master.csv"))
    .withColumn("_loaded_at", F.to_timestamp(F.lit(LOADED_AT)))
)
zone_master.write.format("delta").mode("overwrite").save(delta_path("zone_master"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# ZONE POINTS OF INTEREST -- a genuine many-to-many. Copies
# build_mdm.py:189-214: each zone holds ~11% of the non-airport categories
# (hb-gated) plus the AIRPORT category on the three airport zones, so the
# dimensional model gets a bridge, not a flattened column. poi_id numbers rows
# ordered by (location_id, poi_category) exactly like the source.
cats = spark.createDataFrame(
    [("AIRPORT", "Airport terminal", 5), ("RAIL", "Rail terminal", 5),
     ("SUBWAY", "Subway interchange", 2), ("STADIUM", "Stadium or arena", 4),
     ("HOSPITAL", "Hospital", 3), ("UNIVERSITY", "University campus", 3),
     ("HOTEL", "Hotel cluster", 4), ("NIGHTLIFE", "Nightlife district", 4),
     ("PARK", "Major park", 1), ("FERRY", "Ferry terminal", 3)],
    ["poi_category", "poi_category_name", "demand_weight"],
)
z = spark.read.format("delta").load(delta_path("bronze_taxi_zone_lookup")).select(
    F.col("LocationID").cast("int").alias("location_id"),
    F.col("Zone").alias("zone_label"),
)
zone_poi = (
    z.crossJoin(cats)
    .filter(((F.col("location_id").isin(1, 132, 138)) & (F.col("poi_category") == "AIRPORT"))
            | ((F.pmod(hb(F.concat(F.col("zone_label"), F.col("poi_category"))),
                        F.lit(100)) < 11)
               & (F.col("poi_category") != "AIRPORT")))
    .withColumn("poi_id",
                F.concat(F.lit("POI-"),
                         F.lpad(F.row_number()
                                .over(Window.orderBy("location_id", "poi_category"))
                                .cast("string"), 5, "0")))
    .withColumn("poi_name",
                F.concat(F.col("zone_label"), F.lit(" "), F.col("poi_category_name")))
    .select("poi_id", "location_id", "poi_category", "poi_category_name",
            "demand_weight", "poi_name",
            F.lit("mdm_poi_v1").alias("_load_id"),
            F.lit("zone_poi.csv").alias("_source_file"),
            F.to_timestamp(F.lit(LOADED_AT)).alias("_loaded_at"))
)
zone_poi.write.format("delta").mode("overwrite").save(delta_path("zone_poi"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# CALENDAR MASTER -- real US federal holidays plus NYC demand events. Copies
# build_mdm.py:220-252: every date 2023-12-01..2024-12-31 left-joined to the
# holiday list. sequence()+explode() stands in for generate_series().
dates = spark.sql(
    "SELECT explode(sequence(to_date('2023-12-01'), to_date('2024-12-31'), interval 1 day))"
    " AS calendar_date"
)
holidays = (
    spark.createDataFrame(
        [("2024-01-01", "New Year's Day", "federal"),
         ("2024-01-15", "Martin Luther King Jr. Day", "federal"),
         ("2024-02-19", "Presidents' Day", "federal"),
         ("2024-03-17", "St Patrick's Day Parade", "city_event"),
         ("2024-04-08", "Solar eclipse", "city_event"),
         ("2024-05-27", "Memorial Day", "federal"),
         ("2024-06-19", "Juneteenth", "federal"),
         ("2024-07-04", "Independence Day", "federal"),
         ("2024-09-02", "Labor Day", "federal"),
         ("2024-11-28", "Thanksgiving Day", "federal"),
         ("2024-12-25", "Christmas Day", "federal")],
        ["holiday_date", "holiday_name", "holiday_class"],
    )
    .withColumn("holiday_date", F.to_date("holiday_date"))
)
calendar_master = (
    dates.join(holidays, dates.calendar_date == holidays.holiday_date, "left")
    .select(
        "calendar_date", "holiday_name", "holiday_class",
        F.col("holiday_date").isNotNull().alias("is_holiday"),
        # Spark dayofweek: 1 = Sunday .. 7 = Saturday (DuckDB: 0..6).
        F.dayofweek("calendar_date").isin(1, 7).alias("is_weekend"),
        (F.month("calendar_date").between(1, 6)
         | F.month("calendar_date").between(9, 12)).alias("is_school_term"),
        F.lit("mdm_cal_v1").alias("_load_id"),
        F.lit("calendar_master.csv").alias("_source_file"),
        F.to_timestamp(F.lit(LOADED_AT)).alias("_loaded_at"),
    )
)
calendar_master.write.format("delta").mode("overwrite").save(delta_path("calendar_master"))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# WEATHER -- daily observation per borough. Copies build_mdm.py:258-280: a
# seasonal curve through H1 2024 plus per-key hb noise; rain lifts short-hop
# demand and snow suppresses everything downstream. The snow-noise key uses
# the date alone (hb(obs_date || 'sn')), quirk preserved from the source.
dates = spark.sql(
    "SELECT explode(sequence(to_date('2024-01-01'), to_date('2024-06-30'), interval 1 day))"
    " AS obs_date"
)
boroughs = spark.createDataFrame(
    [("Manhattan",), ("Brooklyn",), ("Queens",),
     ("Bronx",), ("Staten Island",), ("EWR",)],
    ["borough_name"],
)
obs = dates.crossJoin(boroughs)
# DuckDB obs_date::VARCHAR renders 'YYYY-MM-DD', same as the Spark cast.
key = F.concat(F.col("obs_date").cast("string"), F.col("borough_name"))
weather_daily = (
    obs.withColumn("observation_id",
                   F.concat(F.lit("WX-"),
                            F.date_format("obs_date", "yyyyMMdd"),
                            F.lit("-"),
                            F.regexp_replace("borough_name", " ", "")))
    .withColumn("temp_avg_f",
                F.round(34 + 26 * F.sin((F.dayofyear("obs_date") - 100) * 3.14159 / 182.0)
                        + F.pmod(hb(key), F.lit(900)) / 100.0, 1))
    .withColumn("precip_inches",
                F.round(F.greatest(F.lit(0),
                                   F.pmod(hb(F.concat(key, F.lit("p"))), F.lit(100)) - 68)
                        / 22.0, 2))
    .withColumn("snow_inches",
                F.when(F.month("obs_date").isin(1, 2)
                       & (F.pmod(hb(F.concat(key, F.lit("s"))), F.lit(100)) > 88),
                       F.round(F.pmod(hb(F.concat(F.col("obs_date").cast("string"),
                                                  F.lit("sn"))),
                                       F.lit(700)) / 100.0, 1))
                .otherwise(0.0))
    .withColumn("wind_mph",
                F.round(3 + F.pmod(hb(F.concat(key, F.lit("w"))), F.lit(1800)) / 100.0, 1))
    .select("observation_id", "obs_date", "borough_name", "temp_avg_f",
            "precip_inches", "snow_inches", "wind_mph",
            F.lit("mdm_wx_v1").alias("_load_id"),
            F.lit("weather_daily.csv").alias("_source_file"),
            F.to_timestamp(F.lit(LOADED_AT)).alias("_loaded_at"))
)
weather_daily.write.format("delta").mode("overwrite").save(delta_path("weather_daily"))

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
