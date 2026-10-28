"""A DuckDB result as an Arrow table, on whichever DuckDB the runtime has loaded.

A notebook runtime can import a DuckDB of its own before the install cell runs, and then
upgrading it there cannot change the loaded module. 1.4 has only fetch_arrow_table; 1.5 adds
to_arrow_table and deprecates the old name. Both return the same table.
"""
import pyarrow as pa


def arrow_table(result) -> pa.Table:
    if hasattr(result, "to_arrow_table"):
        return result.to_arrow_table()
    return result.fetch_arrow_table()
