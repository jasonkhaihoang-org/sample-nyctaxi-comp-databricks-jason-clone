import random
from datetime import datetime, timedelta
from itertools import pairwise

import pyarrow as pa
import pytest
from sources import ops

TABLES = [
    "garage", "vehicle", "driver", "lease_agreement", "shift",
    "trip_assignment", "driver_status_event", "maintenance_event",
]
NATURAL = [
    "service_type", "vendor_id", "pickup_datetime", "dropoff_datetime",
    "pickup_location_id", "dropoff_location_id", "trip_distance", "total_amount",
]


def _trips(n=200_000):
    """Dense yellow trips over three days, so vehicles would overlap without the generator's guard."""
    rng = random.Random(7)
    start = datetime(2024, 1, 10)
    pickups = [start + timedelta(seconds=rng.randrange(3 * 86400)) for _ in range(n)]
    dropoffs = [p + timedelta(minutes=rng.randrange(5, 60)) for p in pickups]
    return pa.table(
        {
            "VendorID": [rng.choice([1, 2]) for _ in range(n)],
            "tpep_pickup_datetime": pickups,
            "tpep_dropoff_datetime": dropoffs,
            "PULocationID": [rng.randrange(1, 264) for _ in range(n)],
            "DOLocationID": [rng.randrange(1, 264) for _ in range(n)],
            "trip_distance": [round(rng.uniform(0.2, 12), 2) for _ in range(n)],
            "total_amount": [round(rng.uniform(4, 80), 2) for _ in range(n)],
        }
    )


@pytest.fixture(scope="module")
def tables():
    source = ops.ops_source(trips=lambda: [_trips()])
    return {name: pa.concat_tables(list(source.resources[name])) for name in TABLES}


def test_source_has_exactly_the_eight_ops_tables():
    source = ops.ops_source(trips=list)
    assert sorted(source.resources) == sorted(TABLES)


def test_assignment_carries_natural_columns_and_no_trip_key(tables):
    cols = tables["trip_assignment"].column_names
    assert "trip_key" not in cols and "trip_ref" not in cols
    assert set(NATURAL) <= set(cols)


def test_only_yellow_trips_are_attributed(tables):
    assert set(tables["trip_assignment"].column("service_type").to_pylist()) == {"yellow"}


def test_no_two_attributed_trips_overlap_on_one_vehicle(tables):
    rows = sorted(
        tables["trip_assignment"].to_pylist(), key=lambda r: (r["vehicle_id"], r["pickup_datetime"])
    )
    assert rows, "no trips were attributed"
    for prev, cur in pairwise(rows):
        if prev["vehicle_id"] == cur["vehicle_id"]:
            assert cur["pickup_datetime"] >= prev["dropoff_datetime"]


def test_every_assignment_sits_inside_its_shift(tables):
    shifts = {r["shift_id"]: r for r in tables["shift"].to_pylist()}
    for a in tables["trip_assignment"].to_pylist():
        s = shifts[a["shift_id"]]
        end = s["shift_end_ts"] or s["derived_end_ts"]
        assert s["shift_start_ts"] <= a["pickup_datetime"] and a["dropoff_datetime"] <= end


def test_every_shift_has_a_login_and_a_logout_unless_it_never_closed(tables):
    events = tables["driver_status_event"].to_pylist()
    by_shift = {}
    for e in events:
        by_shift.setdefault(e["shift_id"], set()).add(e["status_code"])
    for s in tables["shift"].to_pylist():
        codes = by_shift[s["shift_id"]]
        assert "LOGIN" in codes
        assert ("LOGOUT" in codes) == (s["shift_end_ts"] is not None)


def test_generation_is_deterministic():
    one = ops.ops_source(trips=lambda: [_trips(20_000)])
    two = ops.ops_source(trips=lambda: [_trips(20_000)])
    for name in ("shift", "trip_assignment"):
        assert pa.concat_tables(list(one.resources[name])).equals(pa.concat_tables(list(two.resources[name])))
