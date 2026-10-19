from pathlib import Path

import pytest
import yaml

DOCS = sorted((Path(__file__).resolve().parents[2] / "ingestion" / "docs").glob("*.yml"))


def test_every_pipeline_has_a_docs_file():
    assert [p.stem for p in DOCS] == sorted(p.stem for p in DOCS)
    assert {"tlc", "mdm", "ops"} <= {p.stem for p in DOCS}


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.stem)
def test_fields_have_one_shape_and_a_real_description(path):
    doc = yaml.safe_load(path.read_text())
    assert doc["resources"], "no resources documented"
    for resource, body in doc["resources"].items():
        assert body["columns"], f"{resource} documents no columns"
        for column in body["columns"]:
            assert column["description"].strip(), f"{resource}.{column['name']} has no description"
            assert column["description"].strip().upper() not in {"TBD", "TODO"}
            is_control = column["name"].startswith("_dlt_")
            shapes = [k for k in ("source_ref", "source_fields") if k in column]
            if is_control:
                assert shapes == [], f"{resource}.{column['name']} is a control column"
            else:
                assert len(shapes) == 1, f"{resource}.{column['name']} needs exactly one of source_ref or source_fields"
