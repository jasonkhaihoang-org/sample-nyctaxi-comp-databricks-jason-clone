"""Validate Fabric item conventions under src/.

Checks (spec sections 3, 10):
  1. Every <Name>.<Type>/ dir under src/ has a .platform file holding valid
     JSON whose metadata.type / metadata.displayName match the folder name,
     with config.logicalId present and a valid UUID.
  2. Every *.Notebook/ has notebook-content.py.
  3. Every *.DataBuildToolJob/ has dbt-content.json.
  4. Every *.DataPipeline/ has pipeline-content.json.
  5. No SAMPLE (case-insensitive) anywhere under src/dlt/.
  6. Each src/dlt/*.Notebook/notebook-content.py contains the strings
     _load_id, _source_file and _loaded_at.
  7. Every GUID referenced from pipeline-content.json / dbt-content.json
     resolves to a known item logicalId or a recorded bound id
     (scripts/bound-ids.json, refreshed from Fabric sync commits);
     except the all-zeros workspaceId); no <PLACEHOLDER> may remain.

Post-sync, Fabric rewrites payload references to physical workspace item
IDs. Run `python3 scripts/validate_tree.py --record` after pulling a
Fabric sync commit to refresh bound-ids.json from the tree.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
BOUND_IDS = os.path.join(ROOT, "scripts", "bound-ids.json")

REQUIRED_CONTENT = {
    "Notebook": "notebook-content.py",
    "DataBuildToolJob": "dbt-content.json",
    "DataPipeline": "pipeline-content.json",
}

STAMPS = ("_load_id", "_source_file", "_loaded_at")

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
ALL_ZEROS = "00000000-0000-0000-0000-000000000000"


def fail(errors, msg):
    errors.append(msg)


def check_platform(item_dir, name, item_type, errors, known_ids):
    platform = os.path.join(item_dir, ".platform")
    if not os.path.isfile(platform):
        fail(errors, "%s: missing .platform" % item_dir)
        return
    try:
        with open(platform) as f:
            doc = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        fail(errors, "%s/.platform: invalid JSON (%s)" % (item_dir, e))
        return
    if not isinstance(doc, dict):
        fail(errors, "%s/.platform: document is not an object" % item_dir)
        return
    config = doc.get("config") if isinstance(doc.get("config"), dict) else {}
    lid = config.get("logicalId")
    if not lid or not UUID_RE.fullmatch(str(lid)):
        fail(
            errors,
            "%s/.platform: config.logicalId missing or not a UUID" % item_dir,
        )
    else:
        known_ids.add(str(lid).lower())
    meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    if meta.get("type") != item_type:
        fail(
            errors,
            "%s/.platform: metadata.type %r != folder type %r"
            % (item_dir, meta.get("type"), item_type),
        )
    if meta.get("displayName") != name:
        fail(
            errors,
            "%s/.platform: metadata.displayName %r != folder name %r"
            % (item_dir, meta.get("displayName"), name),
        )


def main():
    record = "--record" in sys.argv
    errors = []
    items = 0
    known_ids = set()
    bound = {"workspace": None, "ids": []}
    if os.path.isfile(BOUND_IDS):
        try:
            with open(BOUND_IDS) as f:
                bound = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            fail(errors, "bound-ids.json: invalid (%s)" % e)
            bound = {"workspace": None, "ids": []}
    if os.path.isdir(SRC):
        for dirpath, dirnames, _filenames in os.walk(SRC):
            for d in sorted(dirnames):
                if "." not in d:
                    continue
                name, item_type = d.rsplit(".", 1)
                item_dir = os.path.join(dirpath, d)
                items += 1
                check_platform(item_dir, name, item_type, errors, known_ids)
                required = REQUIRED_CONTENT.get(item_type)
                if required and not os.path.isfile(
                    os.path.join(item_dir, required)
                ):
                    fail(
                        errors,
                        "%s: missing %s" % (item_dir, required),
                    )

        dlt = os.path.join(SRC, "dlt")
        if os.path.isdir(dlt):
            for dirpath, _dirnames, filenames in os.walk(dlt):
                if "__pycache__" in dirpath:
                    continue
                for fn in sorted(filenames):
                    if fn.endswith((".pyc", ".pyo")):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        with open(p, errors="ignore") as f:
                            text = f.read()
                    except OSError as e:
                        fail(errors, "%s: unreadable (%s)" % (p, e))
                        continue
                    if re.search(r"sample", text, re.IGNORECASE):
                        fail(errors, "%s: contains SAMPLE" % p)

        for entry in sorted(os.listdir(dlt)) if os.path.isdir(dlt) else []:
            if not entry.endswith(".Notebook"):
                continue
            nb = os.path.join(dlt, entry, "notebook-content.py")
            if not os.path.isfile(nb):
                continue  # Already reported by the per-item check.
            try:
                with open(nb, errors="ignore") as f:
                    text = f.read()
            except OSError as e:
                fail(errors, "%s: unreadable (%s)" % (nb, e))
                continue
            for stamp in STAMPS:
                if stamp not in text:
                    fail(errors, "%s: missing %s" % (nb, stamp))

        allowed = set(known_ids) | {
            str(x).lower() for x in bound.get("ids", [])
        }
        if bound.get("workspace"):
            allowed.add(str(bound["workspace"]).lower())
        for dirpath, _dirnames, filenames in os.walk(SRC):
            for fn in sorted(filenames):
                if fn not in ("pipeline-content.json", "dbt-content.json"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, errors="ignore") as f:
                        text = f.read()
                except OSError as e:
                    fail(errors, "%s: unreadable (%s)" % (p, e))
                    continue
                if re.search(r"<[A-Za-z_]+>", text):
                    fail(errors, "%s: contains unfilled <PLACEHOLDER>" % p)
                for m in UUID_RE.findall(text):
                    if (
                        m.lower() != ALL_ZEROS
                        and m.lower() not in allowed
                        and not record
                    ):
                        fail(
                            errors,
                            "%s: references unknown id %s" % (p, m),
                        )

        if record:
            seen: dict = {}
            for dirpath, _dirnames, filenames in os.walk(SRC):
                for fn in sorted(filenames):
                    if fn not in ("pipeline-content.json", "dbt-content.json"):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        with open(p, errors="ignore") as f:
                            text = f.read()
                    except OSError:
                        continue
                    for m in UUID_RE.findall(text):
                        seen[m.lower()] = seen.get(m.lower(), 0) + 1
            fresh = {"workspace": None, "ids": []}
            for guid in sorted(seen):
                if guid == ALL_ZEROS or guid in known_ids:
                    continue
                # The workspace id is the one referenced everywhere.
                if seen[guid] == max(seen.values()):
                    fresh["workspace"] = guid
                else:
                    fresh["ids"].append(guid)
            with open(BOUND_IDS, "w") as f:
                json.dump(fresh, f, indent=2)
                f.write("\n")
            print("recorded %d bound ids" % (len(fresh["ids"]) + 1))

    if errors:
        print("tree INVALID: %d error(s)" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 1
    print("tree OK: %d items" % items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
