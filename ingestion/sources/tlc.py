"""NYC TLC open data: yellow and green trip files and the zone lookup.

Fetched from the public TLC CDN for the three-month window below, or the months
given in `[sources.tlc] months` (env `SOURCES__TLC__MONTHS`). Nothing is cast,
filtered or sampled: each resource yields what the source file holds.
"""

from __future__ import annotations

import io
from typing import Callable, Iterator

import dlt
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import requests

BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
MONTHS = ["2024-01", "2024-02", "2024-03"]
FLEETS = ("yellow", "green")

Fetch = Callable[[str], bytes]


def trip_url(fleet: str, month: str) -> str:
    return f"{BASE_URL}/trip-data/{fleet}_tripdata_{month}.parquet"


def zone_url() -> str:
    return f"{BASE_URL}/misc/taxi_zone_lookup.csv"


def http_get(url: str) -> bytes:
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    return response.content


def zone_rows(fetch: Fetch = http_get) -> list[dict]:
    """The TLC zone lookup, one dict per row, with the types the CSV reader infers."""
    return pacsv.read_csv(io.BytesIO(fetch(zone_url()))).to_pylist()


def trip_tables(fleet: str, fetch: Fetch = http_get, months: list[str] = MONTHS) -> Iterator:
    for month in months:
        yield pq.read_table(io.BytesIO(fetch(trip_url(fleet, month))))


def configured_months() -> list[str]:
    """The months `[sources.tlc] months` names (env `SOURCES__TLC__MONTHS`), else the default window."""
    return dlt.config.get("sources.tlc.months", list) or MONTHS


def yellow_trips(fetch: Fetch = http_get) -> Iterator:
    """The yellow trips of the window the tlc pipeline loads, for a generator that derives from them."""
    return trip_tables("yellow", fetch, configured_months())


@dlt.source(name="tlc")
def tlc_source(fetch: Fetch = http_get, months: list[str] | None = None):
    months = months or MONTHS

    @dlt.resource(name="yellow_tripdata")
    def yellow_tripdata():
        yield from trip_tables("yellow", fetch, months)

    @dlt.resource(name="green_tripdata")
    def green_tripdata():
        yield from trip_tables("green", fetch, months)

    @dlt.resource(name="taxi_zone_lookup")
    def taxi_zone_lookup():
        yield zone_rows(fetch)

    return yellow_tripdata, green_tripdata, taxi_zone_lookup
