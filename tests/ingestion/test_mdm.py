import pyarrow as pa
from sources import mdm

TABLES = [
    "zone_master", "vendor_master", "payment_method_master", "rate_plan_master",
    "fare_regime_master", "borough_master", "zone_poi", "calendar_master", "weather_daily",
]
BOROUGHS = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island", "EWR"]


def _zones(n=80):
    return [
        {"LocationID": i, "Borough": BOROUGHS[i % 6], "Zone": f"Zone {i}", "service_zone": "Boro Zone"}
        for i in range(1, n + 1)
    ]


def _table(name, zones=None):
    source = mdm.mdm_source(zone_lookup=lambda: zones or _zones())
    (table,) = list(source.resources[name])
    assert isinstance(table, pa.Table)
    return table


def test_source_has_the_nine_master_tables():
    assert sorted(mdm.mdm_source(zone_lookup=_zones).resources) == sorted(TABLES)


def test_no_table_carries_old_load_metadata():
    for name in TABLES:
        assert not {"_load_id", "_source_file", "_loaded_at"} & set(_table(name).column_names), name


def test_zone_master_versions_every_37th_zone():
    rows = _table("zone_master").to_pylist()
    versions = {}
    for row in rows:
        versions.setdefault(row["location_id"], []).append(row)
    assert {loc for loc, v in versions.items() if len(v) == 2} == {37, 74}
    expired, current = sorted(versions[37], key=lambda r: r["source_version"])
    assert expired["valid_to_date"] == current["valid_from_date"]


def test_weather_covers_the_three_month_window():
    rows = _table("weather_daily")
    dates = rows.column("obs_date").to_pylist()
    assert min(dates).isoformat() == "2024-01-01" and max(dates).isoformat() == "2024-03-31"
    assert rows.num_rows == 91 * 6


def test_calendar_marks_new_years_day_a_holiday():
    rows = {r["calendar_date"].isoformat(): r for r in _table("calendar_master").to_pylist()}
    assert rows["2024-01-01"]["is_holiday"] is True
    assert rows["2024-01-02"]["is_holiday"] is False


def test_generation_is_deterministic():
    assert _table("zone_poi").equals(_table("zone_poi"))
    assert _table("weather_daily").equals(_table("weather_daily"))
