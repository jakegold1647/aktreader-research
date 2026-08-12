from __future__ import annotations

import json
from pathlib import Path

import pytest

from aktreader.cli import PROJECT_ROOT
from aktreader.cli_support import CliConfigurationError
from aktreader.date_audit import (
    build_date_audit_report,
    date_audit_exit_code,
    expand_date_audit_inputs,
)


def _write_label(path: Path, *, value: str = "1890-01-01") -> None:
    path.write_text(
        json.dumps(
            {
                "label_id": f"{path.stem}.test",
                "record_id": path.stem,
                "observations": {
                    "registration_date": {
                        "value": value,
                        "observation_state": "PRESENT",
                        "confidence": "PROBABLE",
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_expand_date_audit_inputs_is_sorted_and_recursion_is_explicit(tmp_path: Path) -> None:
    _write_label(tmp_path / "b.json")
    _write_label(tmp_path / "A.JSON")
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_label(nested / "c.json")
    (tmp_path / "notes.txt").write_text("not an audit input", encoding="utf-8")

    top_level = expand_date_audit_inputs((tmp_path,))
    recursive = expand_date_audit_inputs((tmp_path,), recursive=True)

    assert [path.name for path in top_level] == ["A.JSON", "b.json"]
    assert [path.name for path in recursive] == ["A.JSON", "b.json", "c.json"]


def test_expand_date_audit_inputs_rejects_overlap_and_empty_directories(
    tmp_path: Path,
) -> None:
    selected = tmp_path / "selected"
    selected.mkdir()
    label = selected / "one.json"
    _write_label(label)
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(CliConfigurationError, match="same JSON file more than once"):
        expand_date_audit_inputs((selected, label))
    with pytest.raises(CliConfigurationError, match="contains no JSON files"):
        expand_date_audit_inputs((empty,))


def test_date_audit_surveys_parse_failures_and_non_label_json(tmp_path: Path) -> None:
    label = tmp_path / "label.json"
    malformed = tmp_path / "malformed.json"
    sidecar = tmp_path / "index.json"
    _write_label(label)
    malformed.write_text("{", encoding="utf-8")
    sidecar.write_text('{"records": []}', encoding="utf-8")

    report = build_date_audit_report(expand_date_audit_inputs((tmp_path,)))

    assert report["status"] == "INCOMPLETE"
    assert report["audit_complete"] is False
    assert report["file_count"] == 3
    assert report["label_count"] == 1
    assert report["parse_failure_count"] == 1
    assert report["skipped_non_label_count"] == 1
    assert date_audit_exit_code(report) == 2
    assert {entry["status"] for entry in report["files"]} == {
        "PARSE_FAIL",
        "PASS",
        "SKIPPED_NON_LABEL",
    }
    malformed_entry = next(entry for entry in report["files"] if entry["status"] == "PARSE_FAIL")
    assert len(malformed_entry["source_sha256"]) == 64
    json.dumps(report)


def test_date_audit_serializes_complete_findings(tmp_path: Path) -> None:
    label = tmp_path / "bad-date.json"
    _write_label(label, value="1890-02-30")

    report = build_date_audit_report((label,))

    assert report["status"] == "FINDINGS"
    assert report["finding_code_counts"] == {"DATE_VALUE_INVALID": 1}
    assert date_audit_exit_code(report) == 1
    entry = report["files"][0]
    assert entry["source_sha256"]
    assert entry["finding_count"] == 1
    assert entry["findings"][0]["record_ids"] == ["bad-date"]
    assert entry["findings"][0]["field_paths"] == ["registration_date"]
    assert entry["findings"][0]["evidence"]["errors"] == [
        "day 30 is invalid for 1890-02 in the gregorian calendar"
    ]
    json.dumps(report)


def test_date_audit_exposes_relative_date_mismatches(tmp_path: Path) -> None:
    label = tmp_path / "relative-mismatch.json"
    label.write_text(
        json.dumps(
            {
                "record_id": "relative-mismatch",
                "observations": {
                    "registration_date": {
                        "value": {
                            "julian": "1890-02-07",
                            "gregorian": "1890-02-19",
                        },
                        "observation_state": "PRESENT",
                        "confidence": "PROBABLE",
                    },
                    "event_date": {
                        "value": {
                            "julian": "1890-02-05",
                            "gregorian": "1890-02-17",
                            "resolved_from_relative_phrase": True,
                        },
                        "original_script": "вчерашняго числа",
                        "observation_state": "PRESENT",
                        "confidence": "PROBABLE",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = build_date_audit_report((label,))

    assert report["status"] == "FINDINGS"
    assert report["finding_code_counts"] == {"RELATIVE_DATE_MISMATCH": 1}
    finding = report["files"][0]["findings"][0]
    assert finding["field_paths"] == ["registration_date", "event_date"]
    assert finding["evidence"]["mismatches"]["julian"] == {
        "stored": "1890-02-05",
        "expected": "1890-02-06",
    }


def test_frozen_reader_a_date_audit_finds_only_known_prose_values_without_writes() -> None:
    paths = expand_date_audit_inputs((PROJECT_ROOT / "labels" / "readerA",))
    before = {path: path.read_bytes() for path in paths}

    report = build_date_audit_report(paths)

    assert report["status"] == "FINDINGS"
    assert report["file_count"] == 60
    assert report["label_count"] == 59
    assert report["finding_count"] == 5
    assert report["failing_label_count"] == 4
    assert report["parse_failure_count"] == 0
    assert report["skipped_non_label_count"] == 1
    assert report["finding_code_counts"] == {"DATE_VALUE_INVALID": 5}
    assert date_audit_exit_code(report) == 1
    flagged = [
        (Path(entry["path"]).name, finding["field_paths"][0])
        for entry in report["files"]
        for finding in entry.get("findings", [])
    ]
    assert flagged == [
        ("serock-1890-death-16.json", "event_date"),
        ("serock-1890-death-26.json", "registration_date"),
        ("serock-1890-death-44.json", "event_date"),
        ("serock-1890-death-46.json", "registration_date"),
        ("serock-1890-death-46.json", "event_date"),
    ]
    assert {path: path.read_bytes() for path in paths} == before


def test_frozen_reader_b_date_audit_passes() -> None:
    paths = expand_date_audit_inputs((PROJECT_ROOT / "labels" / "readerB",))

    report = build_date_audit_report(paths)

    assert report["status"] == "PASS"
    assert report["file_count"] == 27
    assert report["label_count"] == 27
    assert report["finding_count"] == 0
    assert report["parse_failure_count"] == 0
    assert date_audit_exit_code(report) == 0
