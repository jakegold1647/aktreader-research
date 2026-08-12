"""Deterministic batch application of the source-attributed variant bridge."""

from __future__ import annotations

import csv
import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

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
        raise VariantBatchError(f"cannot hash batch input {path}: {error}") from error
    return digest.hexdigest()


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
