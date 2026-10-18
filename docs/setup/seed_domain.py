#!/usr/bin/env python3
"""Release and seed the Fabric Lakehouse Domain from this repository. See seeding-the-domain.md.

--release runs the CI bundle's own deploy (.github/scripts/deploy_orchestration.py), as the
Deploy Orchestration workflow does on merge: it delivers ingestion/ and transformation/ to
the Domain Lakehouse's Files/<slug>/, with the production manifest an Intent defers to, and
applies the notebooks and the nyc_taxi_refresh Data Pipeline.
--run starts nyc_taxi_refresh once and waits for it: the run loads every source and builds
every model.

Signs in with the operator's `az login`; the Domain's ids come from transformation/profiles.yml.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
API = "https://api.fabric.microsoft.com/v1"
PIPELINE = "nyc_taxi_refresh"
TERMINAL = {"Completed", "Failed", "Cancelled", "Deduped"}
# A full Q1 seed took about half an hour; anything far past that is stuck, not slow.
DEADLINE_S = 3 * 3600


def job_url(workspace_id: str, item_id: str) -> str:
    return f"{API}/workspaces/{workspace_id}/items/{item_id}/jobs/instances?jobType=Pipeline"


def item_id(items: list[dict], name: str) -> str:
    matches = [i["id"] for i in items if i["type"] == "DataPipeline" and i["displayName"] == name]
    if len(matches) != 1:
        raise SystemExit(f"expected one DataPipeline named {name}, found {len(matches)}: run --release first")
    return matches[0]


def wait(location: str, get: Callable[[str], dict], sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.monotonic, deadline_s: float = DEADLINE_S, poll_s: float = 30) -> dict:
    """Poll a job instance until it reaches a terminal state."""
    start = clock()
    while True:
        job = get(location)
        if job["status"] in TERMINAL:
            return job
        if clock() - start > deadline_s:
            raise TimeoutError(f"{location} still {job['status']} after {deadline_s}s")
        sleep(poll_s)


def _token() -> str:
    return subprocess.run(["az", "account", "get-access-token", "--resource", "https://api.fabric.microsoft.com",
                           "--query", "accessToken", "-o", "tsv"], check=True, capture_output=True, text=True).stdout.strip()


def _request(method: str, url: str) -> tuple[dict, dict]:
    req = urllib.request.Request(url, method=method, headers={"Authorization": f"Bearer {_token()}"},
                                 data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        return (json.loads(body) if body else {}), dict(resp.headers)


def _domain() -> dict:
    import yaml

    return yaml.safe_load((ROOT / "transformation/profiles.yml").read_text())["nyc_taxi_analytics"]["outputs"]["prod"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", action="store_true", help="deliver the code and apply the items")
    ap.add_argument("--run", action="store_true", help=f"run {PIPELINE} once and wait for it")
    args = ap.parse_args()
    if not (args.release or args.run):
        ap.error("pass --release, --run or both")
    workspace = _domain()["workspaceid"]
    if args.release:
        subprocess.run([sys.executable, ".github/scripts/deploy_orchestration.py", "--repo-root", ".",
                        "--workspace-id", workspace], cwd=ROOT, check=True)
    if args.run:
        items, _ = _request("GET", f"{API}/workspaces/{workspace}/items")
        _, headers = _request("POST", job_url(workspace, item_id(items["value"], PIPELINE)))
        location = headers["Location"]
        print(f"started {PIPELINE}: {location}", flush=True)
        job = wait(location, get=lambda url: _request("GET", url)[0])
        print(json.dumps(job, indent=2))
        return 0 if job["status"] == "Completed" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
