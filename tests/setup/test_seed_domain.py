import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("seed_domain_duckdb", ROOT / "docs/setup/seed_domain_duckdb.py")
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


class Recorder:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def __call__(self, command, cwd, env):
        self.calls.append((list(command), env))
        return SimpleNamespace(returncode=1 if self.fail_on and self.fail_on in " ".join(command) else 0)


def test_seed_loads_the_chosen_months_into_the_output_file_then_builds_it(tmp_path):
    out = tmp_path / "nyc_taxi.duckdb"
    runner = Recorder()
    assert seed.build(out, ["2024-01"], runner) == 0
    commands = [" ".join(c) for c, _ in runner.calls]
    assert [c.rsplit(" ", 1)[-1] for c in commands[:3]] == ["tlc_pipeline.py", "ops_pipeline.py", "mdm_pipeline.py"]
    assert commands[-1].endswith("build --target dev")
    assert {env["VD_EPHM_DUCKDB_LOCAL_PATH"] for _, env in runner.calls} == {str(out)}
    assert {env["SOURCES__TLC__MONTHS"] for _, env in runner.calls} == {'["2024-01"]'}


def test_seed_stops_before_dbt_when_ingestion_fails(tmp_path):
    runner = Recorder(fail_on="ops_pipeline.py")
    assert seed.build(tmp_path / "x.duckdb", ["2024-01"], runner) == 1
    assert not any("dbt.cli.main" in " ".join(c) for c, _ in runner.calls)
