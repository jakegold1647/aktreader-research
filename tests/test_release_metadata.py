import re
from pathlib import Path

import tomllib

from aktreader import __version__

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.2.0"
RELEASE_DATE = "2026-08-12"


def _cff_field(name: str) -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(rf'^{re.escape(name)}:\s+"?([^"\n]+)"?$', text, re.MULTILINE)
    assert match is not None, f"missing {name} in CITATION.cff"
    return match.group(1).strip()


def test_release_versions_are_consistent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    root_package = next(
        package for package in lock["package"] if package["name"] == project["name"]
    )

    assert project["version"] == RELEASE_VERSION
    assert __version__ == RELEASE_VERSION
    assert root_package["version"] == RELEASE_VERSION
    assert project["requires-python"] == ">=3.11"
    assert lock["requires-python"] == project["requires-python"]


def test_release_identity_is_evidence_lab_specific() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Evidence" in project["description"]
    assert readme.startswith("# AKT Reader — Evidence Lab\n")
    assert "AKT Reader — Application" in readme
    assert "Congress Poland Registers — Benchmark Dataset" in readme


def test_citation_and_changelog_match_release() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert _cff_field("version") == RELEASE_VERSION
    assert _cff_field("date-released") == RELEASE_DATE
    assert f"## [{RELEASE_VERSION}] - {RELEASE_DATE}" in changelog
