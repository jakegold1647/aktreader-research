from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import aktreader.date_audit as date_audit_module
from aktreader.cli import PROJECT_ROOT
from aktreader.cli_support import CliConfigurationError
from aktreader.date_audit import (
    DateAuditError,
    build_date_audit_report,
    date_audit_exit_code,
    expand_date_audit_inputs,
    verify_date_audit_artifact,
)
from aktreader.schema import ContractValidationError, validate_instance

DATE_AUDIT_SCHEMA = PROJECT_ROOT / "schemas" / "date-audit-1.0.0.schema.json"


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


def _write_audit_artifact(
    artifact_path: Path,
    inputs: tuple[Path, ...],
    *,
    recursive: bool = False,
) -> dict:
    report = build_date_audit_report(
        expand_date_audit_inputs(inputs, recursive=recursive),
        recursive=recursive,
    )
    artifact_path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


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
    validate_instance(report, DATE_AUDIT_SCHEMA)
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
    validate_instance(report, DATE_AUDIT_SCHEMA)


def test_date_audit_report_is_identical_across_checkout_roots(tmp_path: Path) -> None:
    reports = []
    roots = [tmp_path / "first-checkout", tmp_path / "second-checkout"]
    for root in roots:
        labels = root / "labels" / "readerB"
        labels.mkdir(parents=True)
        _write_label(labels / "b.json")
        _write_label(labels / "a.json")
        reports.append(
            build_date_audit_report(expand_date_audit_inputs((labels,)))
        )

    assert reports[0] == reports[1]
    report = reports[0]
    assert report["schema_version"] == "1.0.0"
    assert report["validator_version"] == "1.0.0"
    assert report["validator_codes"] == [
        "DATE_VALUE_INVALID",
        "REGISTRATION_BEFORE_EVENT",
        "DUAL_DATE_GAP",
        "RELATIVE_DATE_MISMATCH",
    ]
    assert report["path_mode"] == "COMMON_ROOT_RELATIVE"
    assert [entry["path"] for entry in report["files"]] == ["a.json", "b.json"]
    assert len(report["input_manifest_sha256"]) == 64
    assert all(str(root) not in json.dumps(report) for root in roots)
    validate_instance(report, DATE_AUDIT_SCHEMA)


def test_date_audit_schema_rejects_undeclared_report_fields(tmp_path: Path) -> None:
    label = tmp_path / "label.json"
    _write_label(label)
    report = build_date_audit_report((label,))
    report["undeclared"] = True

    with pytest.raises(ContractValidationError, match="Additional properties"):
        validate_instance(report, DATE_AUDIT_SCHEMA)


def test_date_audit_verifier_replays_an_artifact_under_a_different_root(
    tmp_path: Path,
) -> None:
    source_labels = tmp_path / "source-checkout" / "labels"
    replay_labels = tmp_path / "replay-checkout" / "labels"
    source_labels.mkdir(parents=True)
    replay_labels.mkdir(parents=True)
    for root in (source_labels, replay_labels):
        _write_label(root / "b.json")
        _write_label(root / "a.json")
    artifact_path = tmp_path / "date-audit.json"
    artifact = _write_audit_artifact(artifact_path, (source_labels,))

    report = verify_date_audit_artifact(
        artifact_path=artifact_path,
        raw_paths=(replay_labels,),
        schema_path=DATE_AUDIT_SCHEMA,
    )

    assert report["status"] == "PASS"
    assert report["verification"] == "EXACT_REPRODUCTION"
    assert report["artifact_status"] == "PASS"
    assert report["artifact_sha256"] == hashlib.sha256(
        artifact_path.read_bytes()
    ).hexdigest()
    assert report["input_manifest_sha256"] == artifact["input_manifest_sha256"]


def test_date_audit_verifier_replays_recursive_selection(tmp_path: Path) -> None:
    labels = tmp_path / "labels"
    nested = labels / "nested"
    nested.mkdir(parents=True)
    _write_label(labels / "top.json")
    _write_label(nested / "deep.json")
    artifact_path = tmp_path / "recursive-audit.json"
    _write_audit_artifact(artifact_path, (labels,), recursive=True)

    report = verify_date_audit_artifact(
        artifact_path=artifact_path,
        raw_paths=(labels,),
        schema_path=DATE_AUDIT_SCHEMA,
    )

    assert report["status"] == "PASS"
    assert report["recursive"] is True
    assert report["file_count"] == 2


def test_date_audit_verification_pass_is_distinct_from_artifact_findings(
    tmp_path: Path,
) -> None:
    label = tmp_path / "bad-date.json"
    _write_label(label, value="1890-02-30")
    artifact_path = tmp_path / "date-audit.json"
    _write_audit_artifact(artifact_path, (label,))

    report = verify_date_audit_artifact(
        artifact_path=artifact_path,
        raw_paths=(label,),
        schema_path=DATE_AUDIT_SCHEMA,
    )

    assert report["status"] == "PASS"
    assert report["verification"] == "EXACT_REPRODUCTION"
    assert report["artifact_status"] == "FINDINGS"
    assert report["finding_count"] == 1


def test_date_audit_verifier_reports_first_changed_input_pointer(tmp_path: Path) -> None:
    labels = tmp_path / "labels"
    labels.mkdir()
    label = labels / "one.json"
    _write_label(label)
    artifact_path = tmp_path / "date-audit.json"
    _write_audit_artifact(artifact_path, (labels,))
    _write_label(label, value="1890-02-30")

    with pytest.raises(DateAuditError, match=r"at /failing_label_count$"):
        verify_date_audit_artifact(
            artifact_path=artifact_path,
            raw_paths=(labels,),
            schema_path=DATE_AUDIT_SCHEMA,
        )


def test_date_audit_verifier_rejects_schema_valid_artifact_tampering(tmp_path: Path) -> None:
    label = tmp_path / "one.json"
    _write_label(label)
    artifact_path = tmp_path / "date-audit.json"
    artifact = _write_audit_artifact(artifact_path, (label,))
    artifact["input_manifest_sha256"] = "0" * 64
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(DateAuditError, match=r"at /input_manifest_sha256$"):
        verify_date_audit_artifact(
            artifact_path=artifact_path,
            raw_paths=(label,),
            schema_path=DATE_AUDIT_SCHEMA,
        )


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (b"\xff", "artifact is not UTF-8"),
        (b"{", "artifact is not valid JSON"),
        (b"[]", "artifact must contain one JSON object"),
        (b'{"value": NaN}', "non-standard JSON number"),
    ],
)
def test_date_audit_verifier_rejects_non_strict_json(
    tmp_path: Path,
    contents: bytes,
    message: str,
) -> None:
    label = tmp_path / "one.json"
    _write_label(label)
    artifact_path = tmp_path / "date-audit.json"
    artifact_path.write_bytes(contents)

    with pytest.raises(DateAuditError, match=message):
        verify_date_audit_artifact(
            artifact_path=artifact_path,
            raw_paths=(label,),
            schema_path=DATE_AUDIT_SCHEMA,
        )


def test_date_audit_verifier_rejects_duplicate_artifact_keys(tmp_path: Path) -> None:
    label = tmp_path / "one.json"
    _write_label(label)
    artifact_path = tmp_path / "date-audit.json"
    _write_audit_artifact(artifact_path, (label,))
    rendered = artifact_path.read_text(encoding="utf-8")
    artifact_path.write_text(
        rendered.replace(
            '"schema_version": "1.0.0",',
            '"schema_version": "1.0.0",\n  "schema_version": "1.0.0",',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(DateAuditError, match="duplicate JSON key"):
        verify_date_audit_artifact(
            artifact_path=artifact_path,
            raw_paths=(label,),
            schema_path=DATE_AUDIT_SCHEMA,
        )


def test_date_audit_verifier_rejects_source_drift_during_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = tmp_path / "one.json"
    _write_label(label)
    artifact_path = tmp_path / "date-audit.json"
    _write_audit_artifact(artifact_path, (label,))
    real_build = date_audit_module.build_date_audit_report

    def drifting_build(paths, *, recursive=False):
        report = real_build(paths, recursive=recursive)
        _write_label(label, value="1890-02-30")
        return report

    monkeypatch.setattr(date_audit_module, "build_date_audit_report", drifting_build)

    with pytest.raises(DateAuditError, match="input changed while being verified"):
        verify_date_audit_artifact(
            artifact_path=artifact_path,
            raw_paths=(label,),
            schema_path=DATE_AUDIT_SCHEMA,
        )


def test_date_audit_verifier_rejects_artifact_drift_during_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = tmp_path / "one.json"
    _write_label(label)
    artifact_path = tmp_path / "date-audit.json"
    _write_audit_artifact(artifact_path, (label,))
    real_source_check = date_audit_module._require_sources_unchanged

    def drifting_source_check(paths, report):
        real_source_check(paths, report)
        artifact_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        date_audit_module,
        "_require_sources_unchanged",
        drifting_source_check,
    )

    with pytest.raises(DateAuditError, match="artifact changed while being verified"):
        verify_date_audit_artifact(
            artifact_path=artifact_path,
            raw_paths=(label,),
            schema_path=DATE_AUDIT_SCHEMA,
        )
