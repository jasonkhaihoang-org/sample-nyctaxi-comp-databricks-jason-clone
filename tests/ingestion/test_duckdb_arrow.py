import pyarrow as pa
from sources.duckdb_arrow import arrow_table


class _Result:
    """A DuckDB result as older DuckDB (1.4) exposes it: no to_arrow_table."""

    def fetch_arrow_table(self):
        return pa.table({"a": [1]})


def test_arrow_table_falls_back_to_fetch_arrow_table_on_duckdb_1_4():
    assert arrow_table(_Result()).column("a").to_pylist() == [1]


def test_arrow_table_reads_a_real_duckdb_result():
    import duckdb

    assert arrow_table(duckdb.connect().execute("select 2 as a")).column("a").to_pylist() == [2]
