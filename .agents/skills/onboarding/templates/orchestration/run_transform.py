"""Run the dbt project: `dbt deps`, then `dbt build` against the `dev` target, writing domain.duckdb by default."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(command, cwd, env):
    return subprocess.run(command, cwd=cwd, env=env, check=False)


DEFAULT_DB = ROOT / "domain.duckdb"


def run_transform(runner: Callable = _run, target: str = "dev", db_path: Path = DEFAULT_DB) -> int:
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(ROOT / "transformation")
    env["DBT_PROFILE_NAME"] = "<project_name>"
    # The profile reads the database path from the same variable the Studio sandbox sets.
    env["VD_EPHM_DUCKDB_LOCAL_PATH"] = str(db_path)
    dbt = [sys.executable, "-m", "dbt.cli.main"]
    # packages.yml lists dbt_project_evaluator; a fresh checkout does not have it installed.
    deps = runner([*dbt, "deps"], cwd=ROOT / "transformation", env=env).returncode
    if deps != 0:
        return deps
    return runner([*dbt, "build", "--target", target], cwd=ROOT / "transformation", env=env).returncode


def main() -> int:
    return run_transform()


if __name__ == "__main__":
    raise SystemExit(main())
