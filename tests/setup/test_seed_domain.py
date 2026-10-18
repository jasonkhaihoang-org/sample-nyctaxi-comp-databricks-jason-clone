import importlib.util
from pathlib import Path

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
