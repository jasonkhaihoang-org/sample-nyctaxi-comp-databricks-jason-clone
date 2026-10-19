import importlib.util
from pathlib import Path

import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("seed_domain", ROOT / "docs/setup/seed_domain.py")
seed_domain = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_domain)

WS = "w" * 8
ITEM = "i" * 8


def test_job_url_names_the_pipeline_item():
    assert seed_domain.job_url(WS, ITEM) == (
        f"https://api.fabric.microsoft.com/v1/workspaces/{WS}/items/{ITEM}/jobs/instances?jobType=Pipeline"
    )


@pytest.mark.parametrize("terminal", ["Completed", "Failed", "Cancelled", "Deduped"])
def test_wait_stops_on_each_terminal_state(terminal):
    states = iter(["NotStarted", "InProgress", terminal])
    result = seed_domain.wait("loc", get=lambda url: {"status": next(states)}, sleep=lambda s: None,
                              clock=iter(range(0, 10**6, 30)).__next__, deadline_s=3600)
    assert result["status"] == terminal


def test_wait_gives_up_after_the_deadline():
    with pytest.raises(TimeoutError):
        seed_domain.wait("loc", get=lambda url: {"status": "InProgress"}, sleep=lambda s: None,
                         clock=iter(range(0, 10**6, 600)).__next__, deadline_s=3600)


def test_item_id_finds_the_pipeline_by_name():
    items = [{"type": "Notebook", "displayName": "nyc_taxi_refresh", "id": "nb"},
             {"type": "DataPipeline", "displayName": "nyc_taxi_refresh", "id": ITEM}]
    assert seed_domain.item_id(items, "nyc_taxi_refresh") == ITEM
    with pytest.raises(SystemExit):
        seed_domain.item_id(items[:1], "nyc_taxi_refresh")


def _stub(monkeypatch, final_status, location_header="location"):
    calls = []

    def request(method, url):
        calls.append((method, url))
        if method == "POST":
            return {}, {location_header: "https://jobs/1"}
        if url.endswith("/items"):
            return {"value": [{"type": "DataPipeline", "displayName": "nyc_taxi_refresh", "id": ITEM}]}, {}
        return {"status": final_status}, {}

    monkeypatch.setattr(seed_domain, "_request", request)
    monkeypatch.setattr(seed_domain, "_domain", lambda: {"workspaceid": WS})
    monkeypatch.setattr(seed_domain.time, "sleep", lambda s: None)
    return calls


@pytest.mark.parametrize("status,code", [("Completed", 0), ("Failed", 1)])
def test_run_exits_on_the_job_status(monkeypatch, status, code):
    calls = _stub(monkeypatch, status)
    monkeypatch.setattr(sys, "argv", ["seed_domain.py", "--run"])
    assert seed_domain.main() == code
    assert ("POST", seed_domain.job_url(WS, ITEM)) in calls
    assert ("GET", "https://jobs/1") in calls


def test_run_reads_the_location_header_in_any_case(monkeypatch):
    _stub(monkeypatch, "Completed", location_header="Location")
    monkeypatch.setattr(sys, "argv", ["seed_domain.py", "--run"])
    assert seed_domain.main() == 0
