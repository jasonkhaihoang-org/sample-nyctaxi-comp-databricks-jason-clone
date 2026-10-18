"""Run the dlt pipelines: tlc, then ops, then mdm. Loads domain.duckdb at the repo root by default."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINES = ["tlc_pipeline.py", "ops_pipeline.py", "mdm_pipeline.py"]


def _run(command, cwd, env):
    return subprocess.run(command, cwd=cwd, env=env, check=False)


DEFAULT_DB = ROOT / "domain.duckdb"


def ingest_environment(db_path: Path = DEFAULT_DB) -> dict[str, str]:
    """The three variables vibedata's setup_environment() needs on a DuckDB-local domain."""
    env = os.environ.copy()
    env["VD_EPHM_DUCKDB_LOCAL_PATH"] = str(db_path)
    env["VD_DOMAIN_DATA_PLATFORM"] = "duckdb_local"
    env["VD_DOMAIN_SECRET_STORE_KIND"] = "local_toml"
    return env


def run_ingest(runner: Callable = _run, db_path: Path = DEFAULT_DB) -> int:
    """Run each pipeline from the ingestion root; stop at the first failure and return its code."""
    env = ingest_environment(db_path)
    for pipeline in PIPELINES:
        result = runner([sys.executable, pipeline], cwd=ROOT / "ingestion", env=env)
        if result.returncode != 0:
            return result.returncode
    return 0


def main() -> int:
    return run_ingest()


if __name__ == "__main__":
    raise SystemExit(main())
