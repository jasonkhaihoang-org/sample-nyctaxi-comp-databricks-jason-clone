"""Run ingestion, then the dbt build. Stops at the first failure."""

from __future__ import annotations

from collections.abc import Callable

import run_ingest
import run_transform


def run_all(runner: Callable | None = None) -> int:
    ingest = run_ingest.run_ingest(runner) if runner else run_ingest.run_ingest()
    if ingest != 0:
        return ingest
    return run_transform.run_transform(runner) if runner else run_transform.run_transform()


def main() -> int:
    return run_all()


if __name__ == "__main__":
    raise SystemExit(main())
