import importlib.util
import re
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("parity", ROOT / "docs/setup/parity.py")
parity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parity)


def test_numeric_types_on_both_engines():
    assert all(parity.is_numeric(t) for t in ("BIGINT", "DOUBLE", "DECIMAL(18,2)", "INT", "LONG", "decimal(10,2)", "UBIGINT"))
    assert not any(parity.is_numeric(t) for t in ("VARCHAR", "STRING", "BOOLEAN", "DATE", "TIMESTAMP"))


def test_sums_compare_at_a_cent_or_a_relative_tolerance():
    assert not parity.sums_differ(10.004, 10.0)
    assert parity.sums_differ(10.02, 10.0)
    assert not parity.sums_differ(1e12, 1e12 + 100)
    assert parity.sums_differ(None, 0.0)
    assert not parity.sums_differ(None, None)


def test_a_row_count_difference_hides_the_sums():
    assert parity.compare("s.t", (3, 4), [("x", 1.0, 2.0)]) == ["s.t: rows duckdb=3 databricks=4"]
    assert parity.compare("s.t", (3, 3), [("x", 1.0, 2.0), ("y", 1.0, 1.0)]) == ["s.t.x: sum duckdb=1.0 databricks=2.0"]


def test_type_families_line_up_across_engines():
    assert parity.family("BIGINT") == parity.family("INT") == "numeric"
    assert parity.family("VARCHAR") == parity.family("STRING") == "text"
    assert parity.family("TIMESTAMP") == parity.family("TIMESTAMP_NTZ") == "temporal"
    assert parity.family("TIMESTAMP WITH TIME ZONE") == parity.family("TIMESTAMP") == "temporal"
    assert parity.family("DATE") == "temporal"
    assert parity.family("BOOLEAN") == "boolean"
    assert parity.family("ARRAY<STRING>") == "array<string>"


def test_column_differences_are_reported():
    duck = {"a": "BIGINT", "b": "VARCHAR", "c": "DOUBLE"}
    dbx = {"a": "INT", "b": "INT", "d": "DOUBLE"}
    assert parity.column_diffs("s.t", duck, dbx) == [
        "s.t.b: type duckdb=VARCHAR databricks=INT",
        "s.t.c: missing on databricks",
        "s.t.d: missing on duckdb",
    ]


def test_profiles_compare_counts_and_the_text_range():
    assert parity.compare_profiles("s.t", [("x", (5, 3, "a", "c"), (5, 3, "a", "c")), ("y", (5, 2, "a", "b"), (5, 2, "A", "b"))]) == [
        "s.t.y: profile duckdb=(5, 2, 'a', 'b') databricks=(5, 2, 'A', 'b')"]


def test_a_known_difference_is_matched_by_its_whole_line():
    known = {"s.t.x: sum duckdb=1.0 databricks=2.0": "why", "s.t.z: sum duckdb=1.0 databricks=3.0": "fixed since"}
    diffs = ["s.t.x: sum duckdb=1.0 databricks=2.0", "s.t.x: sum duckdb=1.0 databricks=9.0", "s.t: rows duckdb=1 databricks=2"]
    unexplained, seen, stale = parity.split_known(diffs, known)
    assert seen == [diffs[0]]
    assert unexplained == diffs[1:]
    assert stale == ["s.t.z: sum duckdb=1.0 databricks=3.0"]


def test_the_profile_query_speaks_each_engine():
    cols = [("fare", "numeric"), ("zone", "text"), ("at", "temporal")]
    assert parity._profile_sql(cols, "`c`.`s`.`t`", "databricks") == (
        "select count(*), count(`fare`), 0, null, null, count(`zone`), count(distinct `zone`), "
        "min(cast(`zone` as string)), max(cast(`zone` as string)), count(`at`), count(distinct `at`), "
        "date_format(min(`at`), 'yyyy-MM-dd HH:mm:ss'), date_format(max(`at`), 'yyyy-MM-dd HH:mm:ss'), "
        "cast(sum(`fare`) as double) from `c`.`s`.`t`")
    assert "strftime(cast(min(\"at\") as timestamp), '%Y-%m-%d %H:%M:%S')" in parity._profile_sql(cols, "t", "duckdb")


class FakeWarehouse:
    """A DuckDB file standing in for the Databricks catalog: Databricks SQL in, rows as strings out."""

    def __init__(self, path: Path, catalog: str):
        self.con, self.catalog = duckdb.connect(), catalog
        self.con.execute("set TimeZone = 'UTC'")
        self.con.execute(f"attach '{path}' as {catalog} (read_only)")

    def rows(self, sql: str) -> list[list]:
        sql = sql.replace("`", '"')
        sql = re.sub(r"date_format\((.+?\)), 'yyyy-MM-dd HH:mm:ss'\)", r"strftime(cast(\1 as timestamp), '%Y-%m-%d %H:%M:%S')", sql)
        info = re.match(rf'select (.+) from "{self.catalog}"\.information_schema\.(\w+)(?: where (.*))?$', sql)
        if info:
            column = "catalog_name" if info.group(2) == "schemata" else "table_catalog"
            where = f"{column} = '{self.catalog}'" + (f" and {info.group(3)}" if info.group(3) else "")
            sql = f"select {info.group(1)} from information_schema.{info.group(2)} where {where}"
        return [[None if v is None else str(v) for v in row] for row in self.con.execute(sql).fetchall()]


def _catalog(path: Path, statements: list[str]) -> Path:
    con = duckdb.connect(str(path))
    for statement in statements:
        con.execute(statement)
    con.close()
    return path


BASE = [
    "create schema core",
    "create table core.trips (id integer, fare double, zone varchar, picked_up timestamptz, service_date date)",
    "insert into core.trips values (1, 10.5, 'Astoria', '2024-01-01 00:10:00+00', '2024-01-01'),"
    " (2, 4.0, 'Bronx', '2024-01-02 08:00:00+00', '2024-01-02')",
]


@pytest.fixture()
def reference(tmp_path):
    return str(_catalog(tmp_path / "ref.duckdb", BASE))


def test_matching_catalogs_have_no_difference(tmp_path, reference, capsys):
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", BASE), "prod")
    assert parity.main(reference, dbx, "prod", {}) == 0
    assert "checked 1 tables, 0 differences, 0 known, 0 stale" in capsys.readouterr().out


def test_a_shifted_timestamp_and_a_renamed_label_are_differences(tmp_path, reference):
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", BASE + [
        "update core.trips set picked_up = picked_up + interval 7 hour, zone = upper(zone)"]), "prod")
    diffs, checked = parity.compare_catalogs(duckdb.connect(reference, read_only=True), dbx, "prod")
    assert checked == 1
    assert [d.split(":")[0] for d in diffs] == ["core.trips.picked_up", "core.trips.zone"]


def test_a_row_count_difference_is_the_only_line_for_its_table(tmp_path, reference):
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", BASE + ["delete from core.trips where id = 2"]), "prod")
    diffs, _ = parity.compare_catalogs(duckdb.connect(reference, read_only=True), dbx, "prod")
    assert diffs == ["core.trips: rows duckdb=2 databricks=1"]


def test_a_schema_only_the_catalog_holds_is_reported(tmp_path, reference):
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", BASE + [
        "create schema extra", "create table extra.t (x integer)", "create schema \"default\""]), "prod")
    diffs, _ = parity.compare_catalogs(duckdb.connect(reference, read_only=True), dbx, "prod")
    assert diffs == ["extra.t: missing on duckdb"]


def test_a_stale_known_line_fails_the_run(tmp_path, reference, capsys):
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", BASE), "prod")
    assert parity.main(reference, dbx, "prod", {"core.trips.fare: sum duckdb=1.0 databricks=2.0": "fixed"}) == 1
    assert "known difference no longer seen" in capsys.readouterr().out


def test_nothing_compared_is_an_error(tmp_path):
    empty = str(_catalog(tmp_path / "ref.duckdb", []))
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", []), "prod")
    assert parity.main(empty, dbx, "prod", {}) == 2


def test_a_date_matches_a_midnight_timestamp_in_any_host_zone(tmp_path):
    """dlt lands some dates as DATE on Databricks and as midnight-UTC timestamptz in DuckDB."""
    ref = _catalog(tmp_path / "ref.duckdb", ["set TimeZone = 'Asia/Ho_Chi_Minh'", "create schema s",
                                              "create table s.t (d timestamptz)", "insert into s.t values ('2024-01-02 00:00:00+00')"])
    dbx = FakeWarehouse(_catalog(tmp_path / "dbx.duckdb", ["create schema s", "create table s.t (d date)",
                                                           "insert into s.t values ('2024-01-02')"]), "prod")
    assert parity.compare_catalogs(duckdb.connect(str(ref), read_only=True), dbx, "prod") == ([], 1)
