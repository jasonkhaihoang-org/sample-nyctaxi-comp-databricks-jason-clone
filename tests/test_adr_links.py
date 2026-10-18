"""ADRs and design records list each other: the two-way link adr_lint does not check."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = ROOT / "docs" / "adr"
DESIGN_DIR = ROOT / "docs" / "design"

_CITATION = re.compile(r"\bADR[- ](\d{4})(?!\w)|adr/(\d{4})-", re.IGNORECASE)
_LINK = re.compile(r"\]\(([^)#\s]+\.md)")


def _adrs() -> dict[str, Path]:
    return {p.name[:4]: p for p in ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md")}


def _affected_designs(adr: Path) -> set[Path]:
    section = re.split(r"^## Affected designs\s*$", adr.read_text(), maxsplit=1, flags=re.M)
    if len(section) < 2:
        return set()
    body = re.split(r"^## ", section[1], maxsplit=1, flags=re.M)[0]
    return {(adr.parent / link).resolve() for link in _LINK.findall(body)}


def _cited(record: Path) -> set[str]:
    return {a or b for a, b in _CITATION.findall(record.read_text())}


def _superseded(adr: Path) -> bool:
    return re.search(r"^status:\s*rejected", adr.read_text(), re.M) is not None


def test_every_cited_adr_lists_the_record():
    adrs = _adrs()
    missing = [
        f"{record.relative_to(ROOT)} cites ADR {number}, which does not list it"
        for record in sorted(DESIGN_DIR.rglob("*.md"))
        for number in sorted(_cited(record))
        if number in adrs and record.resolve() not in _affected_designs(adrs[number])
    ]
    assert not missing, "\n".join(missing)


def test_every_listed_record_exists_and_cites_the_adr():
    wrong = []
    for number, adr in sorted(_adrs().items()):
        if _superseded(adr):
            continue
        for record in sorted(_affected_designs(adr)):
            if not record.exists():
                wrong.append(f"{adr.name} lists {record.relative_to(ROOT)}, which does not exist")
            elif number not in _cited(record):
                wrong.append(f"{adr.name} lists {record.relative_to(ROOT)}, which does not cite it")
    assert not wrong, "\n".join(wrong)
