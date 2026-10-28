#!/usr/bin/env python3
"""Compare every table of the Databricks Domain with a DuckDB build of the same months.

Repo maintenance, not an agent task. For each table both sides hold it compares the row count; the
column names and type families; the non-null count of every column; the distinct count, minimum and
maximum (as text) of every non-numeric one; and the sum of every numeric column, equal at 0.01 or a
relative 1e-9 for large sums. It prints one line per difference and a summary, and exits non-zero on
any difference it cannot match to KNOWN, on a KNOWN line it no longer sees, or when nothing was
compared. The DuckDB file comes from the DuckDB model-answer repo's
`docs/setup/seed_domain_duckdb.py --months 2024-01 2024-02 2024-03`. The Databricks side is the
Domain catalog, read through a SQL warehouse with a Databricks CLI profile's credentials.

    python3 docs/setup/parity.py path/to/reference.duckdb --profile <cli-profile> \
        --warehouse-id <id> --catalog nyctaxi_prod
"""
from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Iterable

SYSTEM_SCHEMAS = ("information_schema", "pg_catalog")
# Every Unity Catalog catalog has an empty `default` schema; DuckDB has none.
DATABRICKS_ONLY_SCHEMAS = ("default",)
FAMILIES = {
    "numeric": ("int", "bigint", "smallint", "tinyint", "integer", "hugeint", "ubigint", "uinteger", "usmallint",
                "utinyint", "uhugeint", "double", "float", "real", "decimal", "numeric", "long", "short", "byte"),
    "text": ("varchar", "char", "text", "string"),
    "temporal": ("date", "timestamp", "timestamp_ntz", "timestamptz", "timestamp with time zone", "time"),
    "boolean": ("boolean", "bool"),
}
# dlt's own bookkeeping and the plugin's audit tables differ by construction.
SKIP_PREFIXES = ("_dlt", "audit_")
# Differences explained and owned elsewhere, as the exact line the comparison prints: printed, but they
# do not fail the run. A line that changes, or stops appearing, fails it, so a cause cannot hide drift.
POI_ORDER = ("the DuckDB reference's string_agg(distinct) has no order; this repo sorts the set, and the sorted "
             "reference has the same 54 distinct values (VD-7201)")
KNOWN: dict[str, str] = {
    "intermediate.int_zone_attributes.poi_categories: profile duckdb=(173, 59, 'AIRPORT,HOSPITAL', 'UNIVERSITY,RAIL') "
    "databricks=(173, 54, 'AIRPORT,HOSPITAL', 'UNIVERSITY')": POI_ORDER,
    "core.dim_zone.poi_categories: profile duckdb=(176, 59, 'AIRPORT,HOSPITAL', 'UNIVERSITY,RAIL') "
    "databricks=(176, 54, 'AIRPORT,HOSPITAL', 'UNIVERSITY')": POI_ORDER,
    "agg.agg_trip_zone_daily.revenue_rank_that_day: sum duckdb=2382195.0 databricks=2382193.0": (
        "this repo ranks revenue rounded to the cent, so summed doubles that differ in the last bits do not "
        "break a tie; the reference ranked at the cent gives the same sum"),
}


def split_known(diffs: list[str], known: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """Unexplained differences, explained ones, and explained lines the run no longer prints."""
    seen = [d for d in diffs if d in known]
    return [d for d in diffs if d not in known], seen, [k for k in known if k not in diffs]


def family(data_type: str) -> str:
    base = data_type.split("(")[0].strip().lower()
    if base not in {m for members in FAMILIES.values() for m in members}:
        base = base.split(" ")[0]
    return next((name for name, members in FAMILIES.items() if base in members), base)


def is_numeric(data_type: str) -> bool:
    return family(data_type) == "numeric"


def sums_differ(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return (a is None) != (b is None)
    return abs(a - b) > max(0.01, abs(a) * 1e-9)


def column_diffs(name: str, duck: dict[str, str], dbx: dict[str, str]) -> list[str]:
    """A column on one side only, or of another type family, would otherwise drop out of the check."""
    diffs = []
    for col in sorted(duck.keys() | dbx.keys()):
        if col.startswith("_dlt"):
            continue
        if col not in dbx or col not in duck:
            diffs.append(f"{name}.{col}: missing on {'databricks' if col not in dbx else 'duckdb'}")
        elif family(duck[col]) != family(dbx[col]):
            diffs.append(f"{name}.{col}: type duckdb={duck[col]} databricks={dbx[col]}")
    return diffs


def compare(name: str, counts: tuple[int, int], sums: Iterable[tuple[str, float | None, float | None]]) -> list[str]:
    if counts[0] != counts[1]:
        return [f"{name}: rows duckdb={counts[0]} databricks={counts[1]}"]
    return [f"{name}.{col}: sum duckdb={a} databricks={b}" for col, a, b in sums if sums_differ(a, b)]


def compare_profiles(name: str, profiles: Iterable[tuple[str, tuple, tuple]]) -> list[str]:
    """Non-null counts for every column; distinct count, minimum and maximum for the non-numeric ones. A NULL
    where the other side has a value, a renamed label or a shifted timestamp leaves every sum unchanged."""
    return [f"{name}.{col}: profile duckdb={d} databricks={r}" for col, d, r in profiles if tuple(d) != tuple(r)]


PARTS_PER_COLUMN = 4


QUOTE = {"duckdb": '"', "databricks": "`"}


def _as_utc_text(expr: str, engine: str) -> str:
    """A date or timestamp as the same UTC wall-clock text on both engines: a timestamptz renders in the
    session's zone (UTC on both, see compare_catalogs), and a date reads as its midnight."""
    if engine == "duckdb":
        return f"strftime(cast({expr} as timestamp), '%Y-%m-%d %H:%M:%S')"
    return f"date_format({expr}, 'yyyy-MM-dd HH:mm:ss')"


def _profile_sql(cols: list[tuple[str, str]], name: str, engine: str) -> str:
    """`cols` pairs each column with its type family."""
    q = lambda c: f"{QUOTE[engine]}{c}{QUOTE[engine]}"  # noqa: E731
    parts = []
    for col, fam in cols:
        parts.append(f"count({q(col)})")
        if fam == "numeric":
            parts += ["0", "null", "null"]
        elif fam == "temporal":
            parts += [f"count(distinct {q(col)})", _as_utc_text(f"min({q(col)})", engine), _as_utc_text(f"max({q(col)})", engine)]
        else:
            text = f"cast({q(col)} as string)"
            parts += [f"count(distinct {q(col)})", f"min({text})", f"max({text})"]
    sums = [f"cast(sum({q(col)}) as double)" for col, fam in cols if fam == "numeric"]
    return "select count(*)" + "".join(f", {p}" for p in parts + sums) + f" from {name}"


def _number(value: object) -> float | None:
    return None if value is None else float(value)


def _profile(row: list, i: int) -> tuple:
    count, distinct, low, high = row[1 + PARTS_PER_COLUMN * i: 1 + PARTS_PER_COLUMN * (i + 1)]
    return int(count), int(distinct), low, high


class Warehouse:
    """One SQL warehouse, read through the Statement Execution API."""

    DEADLINE_S = 900

    def __init__(self, profile: str, warehouse_id: str):
        from databricks.sdk import WorkspaceClient

        self.client, self.warehouse_id = WorkspaceClient(profile=profile), warehouse_id

    def rows(self, sql: str) -> list[list]:
        from databricks.sdk.service.sql import StatementState

        api = self.client.statement_execution
        r = api.execute_statement(warehouse_id=self.warehouse_id, statement=sql, wait_timeout="50s")
        start, wait = time.monotonic(), 1.0
        while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.monotonic() - start > self.DEADLINE_S:
                raise TimeoutError(f"{sql}: still {r.status.state.value} after {self.DEADLINE_S}s")
            time.sleep(wait)
            wait = min(wait * 2, 10.0)
            r = api.get_statement(r.statement_id)
        if r.status.state != StatementState.SUCCEEDED:
            raise RuntimeError(f"{sql}: {r.status.state.value} {r.status.error.message if r.status.error else ''}")
        return (r.result.data_array or []) if r.result else []


def compare_catalogs(duck, dbx, catalog: str) -> tuple[list[str], int]:
    """Every difference between the DuckDB file and the catalog, and how many tables were compared.
    `dbx.rows(sql)` runs Databricks SQL (backtick quoting, `<catalog>.information_schema`)."""
    diffs, checked = [], 0
    # A Databricks SQL warehouse's session zone is UTC unless an admin sets another; DuckDB's is the host's.
    duck.execute("set TimeZone = 'UTC'")
    duck_schemas = {r[0] for r in duck.execute("select distinct table_schema from information_schema.tables").fetchall()}
    dbx_schemas = {r[0] for r in dbx.rows(f"select schema_name from `{catalog}`.information_schema.schemata")}
    for schema in sorted((duck_schemas | dbx_schemas) - set(SYSTEM_SCHEMAS) - set(DATABRICKS_ONLY_SCHEMAS)):
        duck_tables = {r[0].lower() for r in duck.execute(
            "select table_name from information_schema.tables where table_schema = ?", [schema]).fetchall()}
        dbx_tables = {r[0].lower() for r in dbx.rows(
            f"select table_name from `{catalog}`.information_schema.tables where table_schema = '{schema}'")}
        for table in sorted(duck_tables | dbx_tables):
            if table.startswith(SKIP_PREFIXES):
                continue
            if table not in dbx_tables or table not in duck_tables:
                diffs.append(f"{schema}.{table}: missing on {'databricks' if table not in dbx_tables else 'duckdb'}")
                continue
            checked += 1
            label = f"{schema}.{table}"
            d_cols = {c.lower(): t for c, t in duck.execute(
                "select column_name, data_type from information_schema.columns where table_schema = ? and table_name = ?",
                [schema, table]).fetchall()}
            r_cols = {c.lower(): t for c, t in dbx.rows(
                f"select column_name, data_type from `{catalog}`.information_schema.columns "
                f"where table_schema = '{schema}' and table_name = '{table}'")}
            diffs += column_diffs(label, d_cols, r_cols)
            cols = [(c, family(d_cols[c])) for c in sorted(d_cols.keys() & r_cols.keys())
                    if not c.startswith("_dlt") and family(d_cols[c]) == family(r_cols[c])]
            d_row = list(duck.execute(_profile_sql(cols, f'"{schema}"."{table}"', "duckdb")).fetchone())
            r_row = dbx.rows(_profile_sql(cols, f"`{catalog}`.`{schema}`.`{table}`", "databricks"))[0]
            n = PARTS_PER_COLUMN * len(cols)
            profiles = [(c, _profile(d_row, i), _profile(r_row, i)) for i, (c, _) in enumerate(cols)]
            numeric = [c for c, fam in cols if fam == "numeric"]
            sums = zip(numeric, map(_number, d_row[1 + n:]), map(_number, r_row[1 + n:]))
            row_counts = (int(d_row[0]), int(r_row[0]))
            if row_counts[0] != row_counts[1]:
                diffs += compare(label, row_counts, [])
            else:
                diffs += compare(label, row_counts, sums) + compare_profiles(label, profiles)
    return diffs, checked


def main(reference: str, dbx, catalog: str, known: dict[str, str]) -> int:
    import duckdb

    diffs, checked = compare_catalogs(duckdb.connect(reference, read_only=True), dbx, catalog)
    unexplained, seen, stale = split_known(diffs, known)
    for d in unexplained:
        print(d)
    for d in stale:
        print(f"known difference no longer seen: {d}")
    for d in seen:
        print(f"known: {d} ({known[d]})")
    print(f"checked {checked} tables, {len(unexplained)} differences, {len(seen)} known, {len(stale)} stale")
    if checked == 0:
        print("nothing was compared: check the reference file and the Databricks coordinates", file=sys.stderr)
        return 2
    return 1 if unexplained or stale else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("reference", help="the DuckDB reference file")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument("--warehouse-id", required=True)
    parser.add_argument("--catalog", default="nyctaxi_prod")
    args = parser.parse_args()
    sys.exit(main(args.reference, Warehouse(args.profile, args.warehouse_id), args.catalog, KNOWN))
