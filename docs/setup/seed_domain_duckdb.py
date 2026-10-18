"""Build a seeded Domain DuckDB file to upload when creating the Domain in Studio.

Repo maintenance, not an agent task. Studio copies the Domain file into every
Intent's sandbox, so an empty Domain gives every Intent an empty sandbox. This
loads the chosen TLC months plus the simulated ops and mdm systems into a new
file, builds every dbt model in it, checks that a renamed copy (what the sandbox
is) still builds, compacts the file and reports what it holds. See seeding-the-domain.md.

    python3 docs/setup/seed_domain_duckdb.py --out nyc_taxi.duckdb --months 2024-01
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "orchestration"))

import run_ingest  # noqa: E402
import run_transform  # noqa: E402

UPLOAD_LIMIT_BYTES = 1024**3  # Studio's Domain-create upload limit.


def _run(command, cwd, env):
    return subprocess.run(command, cwd=cwd, env=env, check=False)


def build(out: Path, months: list[str], runner: Callable = _run) -> int:
    """Load the months into `out`, then dbt deps and build against it. Returns the first failing code."""

    def with_months(command, cwd, env):
        return runner(command, cwd, {**env, "SOURCES__TLC__MONTHS": json.dumps(months)})

    code = run_ingest.run_ingest(with_months, db_path=out)
    if code != 0:
        return code
    return run_transform.run_transform(with_months, db_path=out)


def check_renamed_copy(out: Path, runner: Callable = _run) -> int:
    """The sandbox is a byte copy under another name, so its catalog differs.

    Every stored view must still resolve there: run the data tests on the copy without rebuilding anything.
    """
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "ephm_seed_check.duckdb"
        shutil.copyfile(out, copy)
        env = {**run_ingest.ingest_environment(copy), "DBT_PROFILES_DIR": str(ROOT / "transformation")}
        command = [sys.executable, "-m", "dbt.cli.main", "test", "--target", "dev", "--exclude", "test_type:unit"]
        return runner(command, ROOT / "transformation", env).returncode


def compact(built: Path, out: Path) -> None:
    """Copy into a fresh file: DuckDB never shrinks a file that dlt and dbt have rewritten."""
    import duckdb

    with duckdb.connect() as con:
        con.sql(f"attach '{built}' as built (read_only)")
        con.sql(f"attach '{out}' as seeded")
        con.sql("copy from database built to seeded")


def report(out: Path) -> None:
    import duckdb

    with duckdb.connect(str(out), read_only=True) as con:
        rows = con.sql(
            "select table_schema, count(*) from information_schema.tables "
            "where table_catalog = current_database() group by 1 order by 1"
        ).fetchall()
    size = out.stat().st_size
    print(f"{out}: {size / 1024**2:,.0f} MiB")
    for schema, tables in rows:
        print(f"  {schema}: {tables} tables")
    if size > UPLOAD_LIMIT_BYTES:
        print("WARNING: larger than Studio's 1 GiB upload limit; seed fewer months.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "nyc_taxi.duckdb")
    parser.add_argument("--months", nargs="+", default=["2024-01"])
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error(f"{out} exists; remove it or choose another --out")
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        built = Path(tmp) / out.name
        code = build(built, args.months) or check_renamed_copy(built)
        if code == 0:
            compact(built, out)
    if code == 0:
        report(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
