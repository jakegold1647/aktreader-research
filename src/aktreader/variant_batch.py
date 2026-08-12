"""Deterministic batch application of the source-attributed variant bridge."""

from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aktreader.schema import validate_instance
from aktreader.variant_lexicon import (
    VARIANT_ENTITY_TYPES,
    VariantLexiconError,
    VariantProposalReport,
    VariantRelation,
    load_variant_lexicon,
)

BATCH_SCHEMA_VERSION = "1.0.0"
_INPUT_FIELDS = ("id", "query", "entity_type")


class VariantBatchError(ValueError):
    """Raised when a batch cannot be processed without ambiguity or data loss."""


@dataclass(frozen=True)
class VariantBatchRow:
    row_id: str
    row_number: int
    query: str
    entity_type: str


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise VariantBatchError(f"cannot hash file {path}: {error}") from error
    return digest.hexdigest()


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise VariantBatchError(f"duplicate JSON key is forbidden: {key!r}")
        value[key] = child
    return value


def _reject_json_constant(value: str) -> None:
    raise VariantBatchError(f"non-standard JSON number is forbidden: {value}")


def _load_artifact_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    """Load one strict JSON-object snapshot and hash the exact bytes that were parsed."""

    try:
        raw = path.read_bytes()
    except OSError as error:
        raise VariantBatchError(f"cannot read variant batch artifact {path}: {error}") from error
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise VariantBatchError(f"variant batch artifact is not UTF-8: {path}") from error
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as error:
        raise VariantBatchError(
            f"variant batch artifact is not valid JSON: {path}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise VariantBatchError(f"{path}: variant batch artifact must be a JSON object")
    return payload, digest


def _json_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _first_json_difference(
    expected: Any,
    observed: Any,
    *,
    pointer: str = "",
) -> str | None:
    """Return the first stable JSON Pointer whose value does not reproduce."""

    if type(expected) is not type(observed):
        return pointer or "/"
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(observed)):
            child_pointer = f"{pointer}/{_json_pointer_part(key)}"
            if key not in expected or key not in observed:
                return child_pointer
            difference = _first_json_difference(
                expected[key],
                observed[key],
                pointer=child_pointer,
            )
            if difference is not None:
                return difference
        return None
    if isinstance(expected, list):
        common_length = min(len(expected), len(observed))
        for index in range(common_length):
            difference = _first_json_difference(
                expected[index],
                observed[index],
                pointer=f"{pointer}/{index}",
            )
            if difference is not None:
                return difference
        if len(expected) != len(observed):
            return f"{pointer}/{common_length}"
        return None
    return None if expected == observed else pointer or "/"


def load_variant_batch_csv(path: Path) -> tuple[VariantBatchRow, ...]:
    """Load an explicit ``id,query,entity_type`` UTF-8 CSV contract."""

    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except (OSError, UnicodeError) as error:
        raise VariantBatchError(f"cannot read variant batch {path}: {error}") from error

    with handle:
        try:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != _INPUT_FIELDS:
                raise VariantBatchError(f"{path}: expected CSV header {','.join(_INPUT_FIELDS)}")
            rows: list[VariantBatchRow] = []
            seen_ids: dict[str, int] = {}
            for raw_row in reader:
                row_number = reader.line_num
                if None in raw_row or any(isinstance(value, list) for value in raw_row.values()):
                    raise VariantBatchError(
                        f"{path}:{row_number}: row has more columns than the CSV header"
                    )
                row_id = (raw_row["id"] or "").strip()
                query = raw_row["query"] or ""
                entity_type = (raw_row["entity_type"] or "").strip()
                blank = [
                    field
                    for field, value in (
                        ("id", row_id),
                        ("query", query.strip()),
                        ("entity_type", entity_type),
                    )
                    if not value
                ]
                if blank:
                    raise VariantBatchError(
                        f"{path}:{row_number}: blank required field(s): {', '.join(blank)}"
                    )
                for field, value in (("id", row_id), ("query", query)):
                    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
                        raise VariantBatchError(
                            f"{path}:{row_number}: {field} contains a control or format character"
                        )
                previous = seen_ids.get(row_id)
                if previous is not None:
                    raise VariantBatchError(
                        f"{path}:{row_number}: duplicate id {row_id!r}; first seen "
                        f"at row {previous}"
                    )
                if entity_type not in VARIANT_ENTITY_TYPES:
                    raise VariantBatchError(
                        f"{path}:{row_number}: unsupported entity_type {entity_type!r}"
                    )
                seen_ids[row_id] = row_number
                rows.append(
                    VariantBatchRow(
                        row_id=row_id,
                        row_number=row_number,
                        query=query,
                        entity_type=entity_type,
                    )
                )
        except UnicodeError as error:
            raise VariantBatchError(f"variant batch is not UTF-8: {path}") from error
    if not rows:
        raise VariantBatchError(f"{path}: variant batch contains no rows")
    return tuple(rows)


def _batch_row_payload(row: VariantBatchRow, report: VariantProposalReport) -> dict[str, object]:
    payload = report.as_dict(include_warning=False)
    return {"id": row.row_id, "row_number": row.row_number, **payload}


def _require_unchanged(path: Path, expected_sha256: str, *, role: str) -> None:
    if _sha256_path(path) != expected_sha256:
        raise VariantBatchError(f"{role} changed while the variant batch was being built: {path}")


def build_variant_batch(
    *,
    input_path: Path,
    lexicon_path: Path,
    relations_path: Path,
    include_phonetic: bool = True,
) -> dict[str, object]:
    """Build one deterministic, source-hashed proposal artifact in input order."""

    input_sha256 = _sha256_path(input_path)
    lexicon_sha256 = _sha256_path(lexicon_path)
    relations_sha256 = _sha256_path(relations_path)
    rows = load_variant_batch_csv(input_path)
    lexicon = load_variant_lexicon(lexicon_path, relations_path)
    rendered_rows: list[dict[str, object]] = []
    relation_counts = {relation.value: 0 for relation in VariantRelation}
    proposal_count = 0

    for row in rows:
        try:
            report = lexicon.propose(
                row.query,
                entity_type=row.entity_type,
                include_phonetic=include_phonetic,
            )
        except VariantLexiconError as error:
            raise VariantBatchError(
                f"{input_path}:{row.row_number}: cannot propose variants: {error}"
            ) from error
        rendered_rows.append(_batch_row_payload(row, report))
        proposal_count += len(report.proposals)
        for proposal in report.proposals:
            relation_counts[proposal.relation.value] += 1

    _require_unchanged(input_path, input_sha256, role="variant batch input")
    _require_unchanged(lexicon_path, lexicon_sha256, role="variant source lexicon")
    _require_unchanged(relations_path, relations_sha256, role="variant relation lexicon")

    return {
        "schema_version": BATCH_SCHEMA_VERSION,
        "status": "PROPOSAL_ONLY",
        "input_sha256": input_sha256,
        "lexicon_sha256": lexicon_sha256,
        "relations_sha256": relations_sha256,
        "include_phonetic": include_phonetic,
        "row_count": len(rendered_rows),
        "proposal_count": proposal_count,
        "relation_counts": relation_counts,
        "rows": rendered_rows,
        "warning": (
            "Batch search proposals do not establish identity and never replace an input; "
            "RULED_OUT evidence takes precedence over phonetic similarity."
        ),
    }


def verify_variant_batch_artifact(
    *,
    artifact_path: Path,
    input_path: Path,
    lexicon_path: Path,
    relations_path: Path,
    schema_path: Path,
) -> dict[str, object]:
    """Prove that a stored batch is schema-valid and exactly reproducible."""

    artifact, artifact_sha256 = _load_artifact_snapshot(artifact_path)
    schema_sha256 = _sha256_path(schema_path)
    validate_instance(artifact, schema_path)

    include_phonetic = artifact["include_phonetic"]
    if not isinstance(include_phonetic, bool):
        raise VariantBatchError("variant batch include_phonetic must be a boolean")
    expected = build_variant_batch(
        input_path=input_path,
        lexicon_path=lexicon_path,
        relations_path=relations_path,
        include_phonetic=include_phonetic,
    )

    difference = _first_json_difference(expected, artifact)
    if difference is not None:
        raise VariantBatchError(
            "variant batch artifact does not reproduce exactly from the supplied sources "
            f"at {difference}"
        )
    _require_unchanged(schema_path, schema_sha256, role="variant batch schema")
    if _sha256_path(artifact_path) != artifact_sha256:
        raise VariantBatchError(
            f"variant batch artifact changed while it was being verified: {artifact_path}"
        )

    return {
        "status": "PASS",
        "verification": "EXACT_REPRODUCTION",
        "artifact_status": artifact["status"],
        "artifact": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "schema_version": artifact["schema_version"],
        "schema_sha256": schema_sha256,
        "include_phonetic": include_phonetic,
        "row_count": artifact["row_count"],
        "proposal_count": artifact["proposal_count"],
        "input_sha256": artifact["input_sha256"],
        "lexicon_sha256": artifact["lexicon_sha256"],
        "relations_sha256": artifact["relations_sha256"],
    }
