"""Validate Fabric item conventions under src/.

Checks (spec sections 3, 10):
  1. Every <Name>.<Type>/ dir under src/ has a .platform file holding valid
     JSON whose metadata.type / metadata.displayName match the folder name,
     with no logicalId key anywhere in the document.
  2. Every *.Notebook/ has notebook-content.py.
  3. Every *.DataBuildToolJob/ has dbt-content.json.
  4. Every *.DataPipeline/ has pipeline-content.json.
  5. No SAMPLE (case-insensitive) anywhere under src/dlt/.
  6. Each src/dlt/*.Notebook/notebook-content.py contains the strings
     _load_id, _source_file and _loaded_at.

Empty tree passes: no items yet means no violations.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

REQUIRED_CONTENT = {
    "Notebook": "notebook-content.py",
    "DataBuildToolJob": "dbt-content.json",
    "DataPipeline": "pipeline-content.json",
}

STAMPS = ("_load_id", "_source_file", "_loaded_at")


def fail(errors, msg):
    errors.append(msg)


def check_platform(item_dir, name, item_type, errors):
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
    if "logicalId" in json.dumps(doc):
        # Covers top-level logicalId and nested config.logicalId.
        fail(errors, "%s/.platform: must not contain logicalId" % item_dir)
    meta = doc.get("metadata", {}) if isinstance(doc, dict) else {}
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
    errors = []
    items = 0
    if os.path.isdir(SRC):
        for dirpath, dirnames, _filenames in os.walk(SRC):
            for d in sorted(dirnames):
                if "." not in d:
                    continue
                name, item_type = d.rsplit(".", 1)
                item_dir = os.path.join(dirpath, d)
                items += 1
                check_platform(item_dir, name, item_type, errors)
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
                for fn in sorted(filenames):
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
            with open(nb, errors="ignore") as f:
                text = f.read()
            for stamp in STAMPS:
                if stamp not in text:
                    fail(errors, "%s: missing %s" % (nb, stamp))

    if errors:
        print("tree INVALID: %d error(s)" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 1
    print("tree OK: %d items" % items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
