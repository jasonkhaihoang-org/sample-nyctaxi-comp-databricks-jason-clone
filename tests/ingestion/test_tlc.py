import io

import pyarrow as pa
import pyarrow.parquet as pq
from sources import tlc


def _parquet_bytes(rows: int) -> bytes:
    table = pa.table({"VendorID": list(range(rows)), "total_amount": [1.5] * rows})
    sink = io.BytesIO()
    pq.write_table(table, sink)
    return sink.getvalue()


def _fetch(url: str) -> bytes:
    if url.endswith("taxi_zone_lookup.csv"):
        return b"LocationID,Borough,Zone,service_zone\n1,EWR,Newark Airport,EWR\n2,Queens,Jamaica Bay,Boro Zone\n"
    return _parquet_bytes(4)


def test_trip_url_format():
    assert (
        tlc.trip_url("yellow", "2024-01")
        == "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet"
    )


def test_months_cover_the_three_month_window():
    assert tlc.MONTHS == ["2024-01", "2024-02", "2024-03"]


def test_source_yields_one_table_per_month():
    source = tlc.tlc_source(fetch=_fetch)
    for resource in ("yellow_tripdata", "green_tripdata"):
        tables = list(source.resources[resource])
        assert len(tables) == 3
        assert all(isinstance(t, pa.Table) for t in tables)


def test_no_rows_dropped_or_changed():
    source = tlc.tlc_source(fetch=_fetch)
    tables = list(source.resources["yellow_tripdata"])
    assert sum(t.num_rows for t in tables) == 12
    assert tables[0].column_names == ["VendorID", "total_amount"]


def test_zone_rows_keep_the_types_the_csv_reader_infers():
    rows = tlc.zone_rows(fetch=_fetch)
    assert rows == [
        {"LocationID": 1, "Borough": "EWR", "Zone": "Newark Airport", "service_zone": "EWR"},
        {"LocationID": 2, "Borough": "Queens", "Zone": "Jamaica Bay", "service_zone": "Boro Zone"},
    ]


def test_source_loads_only_the_months_it_is_given():
    fetched = []

    def fetch(url):
        fetched.append(url)
        return _fetch(url)

    source = tlc.tlc_source(fetch=fetch, months=["2024-01"])
    assert len(list(source.resources["yellow_tripdata"])) == 1
    assert [u for u in fetched if "tripdata" in u] == [tlc.trip_url("yellow", "2024-01")]


def test_months_can_be_set_from_the_environment(monkeypatch):
    monkeypatch.setenv("SOURCES__TLC__MONTHS", '["2024-01"]')
    source = tlc.tlc_source.clone(name="tlc", section="tlc")(fetch=_fetch)
    assert len(list(source.resources["green_tripdata"])) == 1


def test_yellow_trips_reads_the_months_tlc_loads(monkeypatch):
    """The ops generator re-reads the yellow trips: it must read the window tlc loaded, no more."""
    monkeypatch.setenv("SOURCES__TLC__MONTHS", '["2024-01"]')
    asked = []

    def fetch(url: str) -> bytes:
        asked.append(url)
        return _parquet_bytes(2)

    assert len(list(tlc.yellow_trips(fetch))) == 1
    assert asked == [tlc.trip_url("yellow", "2024-01")]


def test_yellow_trips_defaults_to_the_three_month_window(monkeypatch):
    monkeypatch.delenv("SOURCES__TLC__MONTHS", raising=False)
    assert len(list(tlc.yellow_trips(lambda url: _parquet_bytes(1)))) == 3
