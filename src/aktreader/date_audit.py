"""Deterministic, read-only date audits for label files and directories."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aktreader.cli_support import (
    CliConfigurationError,
    local_input_path,
    parse_strict_json_bytes,
)
from aktreader.validators.dates import DATE_VALIDATOR_CODES, DATE_VALIDATOR_VERSION, validate_dates

DATE_AUDIT_SCHEMA_VERSION = "1.0.0"


def _path_sort_key(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    parts = tuple(str(part) for part in path.parts)
    return tuple(part.casefold() for part in parts), parts


def _portable_path_context(paths: Sequence[Path]) -> tuple[Path | None, str]:
    """Choose one common root without embedding that machine-local root in the report."""

    if not paths:
        return None, "COMMON_ROOT_RELATIVE"
    try:
        common = Path(os.path.commonpath([str(path) for path in paths]))
    except ValueError:
        return None, "ABSOLUTE_FALLBACK"
    if len(paths) == 1 or common in paths:
        common = common.parent
    return common, "COMMON_ROOT_RELATIVE"


def _display_path(path: Path, root: Path | None) -> str:
    if root is None:
        return path.as_posix()
    return path.relative_to(root).as_posix()


def _input_manifest_sha256(entries: Sequence[Mapping[str, Any]]) -> str:
    pins = [
        {"path": entry["path"], "source_sha256": entry.get("source_sha256")}
        for entry in entries
    ]
    encoded = json.dumps(
        pins,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expand_date_audit_inputs(
    raw_paths: Sequence[Path | str], *, recursive: bool = False
) -> tuple[Path, ...]:
    """Expand explicit files and directories into one unique, stable JSON file list."""

    if not raw_paths:
        raise CliConfigurationError("date audit requires at least one input path")

    selected: list[Path] = []
    seen: set[Path] = set()
    for raw_path in raw_paths:
        source = local_input_path(raw_path, role="date audit input")
        if source.is_file():
            if source.suffix.casefold() != ".json":
                raise CliConfigurationError(f"date audit input is not a JSON file: {source}")
            candidates = (source,)
        else:
            iterator = source.rglob("*") if recursive else source.iterdir()
            candidates = tuple(
                sorted(
                    (
                        candidate
                        for candidate in iterator
                        if candidate.is_file() and candidate.suffix.casefold() == ".json"
                    ),
                    key=_path_sort_key,
                )
            )
            if not candidates:
                scope = "recursively" if recursive else "at its top level"
                raise CliConfigurationError(
                    f"date audit directory contains no JSON files {scope}: {source}"
                )

        for candidate in candidates:
            resolved = local_input_path(candidate, role="date audit JSON file")
            if resolved in seen:
                raise CliConfigurationError(
                    "date audit input selects the same JSON file more than once: "
                    f"{resolved}"
                )
            seen.add(resolved)
            selected.append(resolved)

    return tuple(sorted(selected, key=_path_sort_key))


def _label_kind(payload: Mapping[str, Any]) -> str | None:
    observations = payload.get("observations")
    fields = payload.get("fields")
    if isinstance(observations, Mapping):
        return "canonical"
    if isinstance(fields, Mapping):
        return "legacy"
    if "observations" in payload or "fields" in payload:
        raise ValueError("label observations/fields must be a JSON object")
    return None


def _record_id(payload: Mapping[str, Any], path: Path) -> str:
    value = payload.get("record_id")
    return value if isinstance(value, str) and value else path.stem


def build_date_audit_report(
    paths: Sequence[Path], *, recursive: bool = False
) -> dict[str, Any]:
    """Audit exact files, surveying malformed and non-label JSON without writing to disk."""

    entries: list[dict[str, Any]] = []
    finding_codes: Counter[str] = Counter()
    label_count = 0
    finding_count = 0
    failing_label_count = 0
    parse_failure_count = 0
    skipped_non_label_count = 0

    ordered_paths = tuple(
        sorted((Path(path).resolve() for path in paths), key=_path_sort_key)
    )
    display_root, path_mode = _portable_path_context(ordered_paths)
    for path in ordered_paths:
        rendered_path = _display_path(path, display_root)
        try:
            raw_bytes = path.read_bytes()
        except OSError:
            parse_failure_count += 1
            entries.append(
                {
                    "path": rendered_path,
                    "status": "PARSE_FAIL",
                    "error": f"cannot read date audit input: {rendered_path}",
                }
            )
            continue
        source_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        try:
            payload = parse_strict_json_bytes(
                raw_bytes,
                role="date audit JSON file",
                source=rendered_path,
            )
            if not isinstance(payload, dict):
                raise CliConfigurationError("date audit JSON file must contain one JSON object")
        except CliConfigurationError as error:
            parse_failure_count += 1
            entries.append(
                {
                    "path": rendered_path,
                    "source_sha256": source_sha256,
                    "status": "PARSE_FAIL",
                    "error": str(error),
                }
            )
            continue

        try:
            label_kind = _label_kind(payload)
        except ValueError as error:
            parse_failure_count += 1
            entries.append(
                {
                    "path": rendered_path,
                    "source_sha256": source_sha256,
                    "status": "PARSE_FAIL",
                    "error": str(error),
                }
            )
            continue
        if label_kind is None:
            skipped_non_label_count += 1
            entries.append(
                {
                    "path": rendered_path,
                    "source_sha256": source_sha256,
                    "status": "SKIPPED_NON_LABEL",
                    "reason": "JSON object has neither observations nor fields",
                }
            )
            continue

        record_id = _record_id(payload, path)
        audit_record = (
            payload
            if payload.get("record_id") == record_id
            else {**payload, "record_id": record_id}
        )
        findings = validate_dates(audit_record)
        serialized_findings = [finding.as_dict() for finding in findings]
        label_count += 1
        finding_count += len(findings)
        finding_codes.update(finding.code for finding in findings)
        if findings:
            failing_label_count += 1
        entries.append(
            {
                "path": rendered_path,
                "source_sha256": source_sha256,
                "status": "FINDINGS" if findings else "PASS",
                "label_kind": label_kind,
                "label_id": payload.get("label_id"),
                "record_id": record_id,
                "finding_count": len(findings),
                "findings": serialized_findings,
            }
        )

    audit_complete = parse_failure_count == 0 and label_count > 0
    if not audit_complete:
        status = "INCOMPLETE"
    elif finding_count:
        status = "FINDINGS"
    else:
        status = "PASS"
    return {
        "schema_version": DATE_AUDIT_SCHEMA_VERSION,
        "validator_version": DATE_VALIDATOR_VERSION,
        "validator_codes": list(DATE_VALIDATOR_CODES),
        "status": status,
        "mode": "READ_ONLY",
        "audit_complete": audit_complete,
        "recursive": recursive,
        "path_mode": path_mode,
        "input_manifest_sha256": _input_manifest_sha256(entries),
        "file_count": len(ordered_paths),
        "label_count": label_count,
        "finding_count": finding_count,
        "failing_label_count": failing_label_count,
        "parse_failure_count": parse_failure_count,
        "skipped_non_label_count": skipped_non_label_count,
        "finding_code_counts": dict(sorted(finding_codes.items())),
        "files": entries,
    }


def date_audit_exit_code(report: Mapping[str, Any]) -> int:
    """Map an audit report to stable shell semantics."""

    if report.get("status") == "PASS":
        return 0
    if report.get("status") == "FINDINGS":
        return 1
    return 2
