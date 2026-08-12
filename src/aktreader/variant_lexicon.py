"""Source-attributed variant proposals with explicit negative evidence.

The lexicon is a search aid, never a rewriting or identity-matching system.
Literal inputs are returned unchanged and every non-phonetic relationship
retains its source reference.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from aktreader.variants import daitch_mokotoff_codes

_BASE_FIELDS = (
    "normalized_form",
    "type",
    "variant",
    "script",
    "source_tier",
    "source_ref",
)
_RELATION_FIELDS = (
    "canonical_form",
    "entity_type",
    "form",
    "relation",
    "script",
    "source_tier",
    "source_ref",
)
VARIANT_ENTITY_TYPES = frozenset({"surname", "given", "town"})
_SCRIPTS = frozenset({"latin", "cyrillic"})
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")


class VariantRelation(str, Enum):
    """Strength and direction of one additive search relationship."""

    DOCUMENTED_FORM = "DOCUMENTED_FORM"
    ATTESTED_VARIANT = "ATTESTED_VARIANT"
    PHONETIC_CANDIDATE = "PHONETIC_CANDIDATE"
    RULED_OUT = "RULED_OUT"


_RELATION_RANK = {
    VariantRelation.PHONETIC_CANDIDATE: 1,
    VariantRelation.DOCUMENTED_FORM: 2,
    VariantRelation.ATTESTED_VARIANT: 3,
    VariantRelation.RULED_OUT: 4,
}


class VariantLexiconError(ValueError):
    """Raised when a machine lexicon cannot support safe proposal behavior."""


@dataclass(frozen=True, order=True)
class VariantEvidence:
    source_tier: str
    source_ref: str

    def as_dict(self) -> dict[str, str]:
        return {"source_tier": self.source_tier, "source_ref": self.source_ref}


@dataclass(frozen=True)
class LexiconRelation:
    canonical_form: str
    entity_type: str
    form: str
    relation: VariantRelation
    script: str
    evidence: tuple[VariantEvidence, ...]


@dataclass(frozen=True)
class VariantProposal:
    canonical_form: str
    entity_type: str
    form: str
    relation: VariantRelation
    script: str
    shared_codes: tuple[str, ...]
    evidence: tuple[VariantEvidence, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "canonical_form": self.canonical_form,
            "entity_type": self.entity_type,
            "form": self.form,
            "relation": self.relation.value,
            "script": self.script,
            "shared_codes": list(self.shared_codes),
            "evidence": [item.as_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class VariantProposalReport:
    literal_input: str
    entity_type: str | None
    query_codes: tuple[str, ...]
    proposals: tuple[VariantProposal, ...]

    def as_dict(self, *, include_warning: bool = True) -> dict[str, object]:
        counts = {relation.value: 0 for relation in VariantRelation}
        for proposal in self.proposals:
            counts[proposal.relation.value] += 1
        payload: dict[str, object] = {
            "status": "PROPOSAL_ONLY",
            "literal_input": self.literal_input,
            "literal_input_unchanged": True,
            "entity_type": self.entity_type,
            "query_codes": list(self.query_codes),
            "counts": counts,
            "proposals": [proposal.as_dict() for proposal in self.proposals],
        }
        if include_warning:
            payload["warning"] = (
                "Search proposals do not establish identity and never replace a recorded form; "
                "RULED_OUT evidence takes precedence over phonetic similarity."
            )
        return payload


def _match_key(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    return " ".join(normalized.split()).casefold()


def _script_for(value: str) -> str:
    return "cyrillic" if _CYRILLIC_RE.search(value) else "latin"


def _codes_or_empty(value: str) -> tuple[str, ...]:
    try:
        return daitch_mokotoff_codes(value)
    except ValueError:
        return ()


def _shared_codes(left: tuple[str, ...], right: str) -> tuple[str, ...]:
    if not left:
        return ()
    return tuple(sorted(set(left) & set(_codes_or_empty(right))))


def _read_rows(path: Path, expected_fields: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise VariantLexiconError(f"cannot read variant lexicon {path}: {error}") from error
    with handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise VariantLexiconError(f"{path}: expected CSV header {','.join(expected_fields)}")
        rows: list[dict[str, str]] = []
        for line_number, raw_row in enumerate(reader, start=2):
            if None in raw_row or any(isinstance(value, list) for value in raw_row.values()):
                raise VariantLexiconError(
                    f"{path}:{line_number}: row has more columns than the CSV header"
                )
            row = {key: (value or "").strip() for key, value in raw_row.items()}
            blank = [field for field in expected_fields if not row[field]]
            if blank:
                raise VariantLexiconError(
                    f"{path}:{line_number}: blank required field(s): {', '.join(blank)}"
                )
            rows.append(row)
    if not rows:
        raise VariantLexiconError(f"{path}: lexicon contains no rows")
    return rows


def _validate_common(
    *, path: Path, line_number: int, entity_type: str, form: str, script: str
) -> None:
    if entity_type not in VARIANT_ENTITY_TYPES:
        raise VariantLexiconError(f"{path}:{line_number}: unsupported entity_type {entity_type!r}")
    if script not in _SCRIPTS:
        raise VariantLexiconError(f"{path}:{line_number}: unsupported script {script!r}")
    letters = [character for character in form if character.isalpha()]
    if script == "cyrillic":
        script_matches = bool(letters) and all(
            _CYRILLIC_RE.fullmatch(character) for character in letters
        )
    else:
        script_matches = bool(letters) and not any(
            _CYRILLIC_RE.fullmatch(character) for character in letters
        )
        if script_matches:
            script_matches = bool(_codes_or_empty(form))
    if not script_matches:
        raise VariantLexiconError(
            f"{path}:{line_number}: form does not match declared {script} script"
        )


def _aggregate(relations: list[LexiconRelation]) -> tuple[LexiconRelation, ...]:
    grouped: dict[
        tuple[str, str, str, VariantRelation, str],
        tuple[str, str, set[VariantEvidence]],
    ] = {}
    for relation in relations:
        key = (
            _match_key(relation.canonical_form),
            relation.entity_type,
            _match_key(relation.form),
            relation.relation,
            relation.script,
        )
        if key not in grouped:
            grouped[key] = (relation.canonical_form, relation.form, set())
        grouped[key][2].update(relation.evidence)
    return tuple(
        sorted(
            (
                LexiconRelation(
                    canonical_form=canonical,
                    entity_type=key[1],
                    form=form,
                    relation=key[3],
                    script=key[4],
                    evidence=tuple(sorted(evidence)),
                )
                for key, (canonical, form, evidence) in grouped.items()
            ),
            key=lambda item: (
                item.entity_type,
                _match_key(item.canonical_form),
                _match_key(item.form),
                item.relation.value,
            ),
        )
    )


def load_variant_lexicon(base_path: Path, relation_path: Path) -> VariantLexicon:
    """Load the public source lexicon plus explicit relationship decisions."""

    base_rows = _read_rows(base_path, _BASE_FIELDS)
    relation_rows = _read_rows(relation_path, _RELATION_FIELDS)
    relations: list[LexiconRelation] = []
    anti_entries: list[tuple[str, str, str, int]] = []

    for line_number, row in enumerate(base_rows, start=2):
        raw_type = row["type"]
        if raw_type == "anti-entry":
            anti_entries.append(
                (
                    _match_key(row["variant"]),
                    row["source_tier"],
                    row["source_ref"],
                    line_number,
                )
            )
            continue
        _validate_common(
            path=base_path,
            line_number=line_number,
            entity_type=raw_type,
            form=row["variant"],
            script=row["script"],
        )
        relations.append(
            LexiconRelation(
                canonical_form=row["normalized_form"],
                entity_type=raw_type,
                form=row["variant"],
                relation=VariantRelation.DOCUMENTED_FORM,
                script=row["script"],
                evidence=(VariantEvidence(row["source_tier"], row["source_ref"]),),
            )
        )

    explicit_by_pair: dict[tuple[str, str, str], VariantRelation] = {}
    ruled_out_evidence: set[tuple[str, str, str]] = set()
    for line_number, row in enumerate(relation_rows, start=2):
        _validate_common(
            path=relation_path,
            line_number=line_number,
            entity_type=row["entity_type"],
            form=row["form"],
            script=row["script"],
        )
        try:
            relation = VariantRelation(row["relation"])
        except ValueError as error:
            raise VariantLexiconError(
                f"{relation_path}:{line_number}: unsupported relation {row['relation']!r}"
            ) from error
        if relation not in {
            VariantRelation.ATTESTED_VARIANT,
            VariantRelation.RULED_OUT,
        }:
            raise VariantLexiconError(
                f"{relation_path}:{line_number}: explicit relation must be "
                "ATTESTED_VARIANT or RULED_OUT"
            )
        pair = (
            row["entity_type"],
            _match_key(row["canonical_form"]),
            _match_key(row["form"]),
        )
        previous = explicit_by_pair.get(pair)
        if previous is not None and previous is not relation:
            raise VariantLexiconError(
                f"{relation_path}:{line_number}: pair is both {previous.value} and {relation.value}"
            )
        explicit_by_pair[pair] = relation
        if relation is VariantRelation.RULED_OUT:
            ruled_out_evidence.add((_match_key(row["form"]), row["source_tier"], row["source_ref"]))
        relations.append(
            LexiconRelation(
                canonical_form=row["canonical_form"],
                entity_type=row["entity_type"],
                form=row["form"],
                relation=relation,
                script=row["script"],
                evidence=(VariantEvidence(row["source_tier"], row["source_ref"]),),
            )
        )

    for form, source_tier, source_ref, line_number in anti_entries:
        if (form, source_tier, source_ref) not in ruled_out_evidence:
            raise VariantLexiconError(
                f"{base_path}:{line_number}: anti-entry lacks an explicit RULED_OUT "
                "relation with matching source evidence"
            )
    return VariantLexicon(_aggregate(relations))


class VariantLexicon:
    """Immutable, local-only proposal index over source-attributed forms."""

    def __init__(self, relations: tuple[LexiconRelation, ...]) -> None:
        if not relations:
            raise VariantLexiconError("variant lexicon contains no usable relationships")
        self._relations = relations

    @property
    def relations(self) -> tuple[LexiconRelation, ...]:
        return self._relations

    def propose(
        self,
        literal_input: str,
        *,
        entity_type: str | None = None,
        include_phonetic: bool = True,
    ) -> VariantProposalReport:
        if not isinstance(literal_input, str) or not literal_input.strip():
            raise VariantLexiconError("variant proposal input must be a nonblank string")
        if entity_type is not None and entity_type not in VARIANT_ENTITY_TYPES:
            raise VariantLexiconError(f"unsupported entity_type {entity_type!r}")

        query_key = _match_key(literal_input)
        available = tuple(
            relation
            for relation in self._relations
            if entity_type is None or relation.entity_type == entity_type
        )
        positive_clusters = {
            (relation.entity_type, _match_key(relation.canonical_form))
            for relation in available
            if relation.relation is not VariantRelation.RULED_OUT
            and query_key in {_match_key(relation.canonical_form), _match_key(relation.form)}
        }
        query_codes = _codes_or_empty(literal_input) if include_phonetic else ()
        proposals: dict[tuple[str, str, str], VariantProposal] = {}

        def add(proposal: VariantProposal) -> None:
            key = (
                proposal.entity_type,
                _match_key(proposal.canonical_form),
                _match_key(proposal.form),
            )
            current = proposals.get(key)
            if current is None:
                proposals[key] = proposal
                return
            if _RELATION_RANK[proposal.relation] > _RELATION_RANK[current.relation]:
                proposals[key] = proposal
                return
            if proposal.relation is not current.relation:
                return
            proposals[key] = VariantProposal(
                canonical_form=current.canonical_form,
                entity_type=current.entity_type,
                form=current.form,
                relation=current.relation,
                script=current.script,
                shared_codes=tuple(sorted(set(current.shared_codes + proposal.shared_codes))),
                evidence=tuple(sorted(set(current.evidence + proposal.evidence))),
            )

        for relation in available:
            cluster = (relation.entity_type, _match_key(relation.canonical_form))
            exact_relation = query_key in {
                _match_key(relation.canonical_form),
                _match_key(relation.form),
            }
            if relation.relation is VariantRelation.RULED_OUT:
                relevant = cluster in positive_clusters or exact_relation
            else:
                relevant = cluster in positive_clusters
            if relevant and _match_key(relation.form) != query_key:
                add(
                    VariantProposal(
                        canonical_form=relation.canonical_form,
                        entity_type=relation.entity_type,
                        form=relation.form,
                        relation=relation.relation,
                        script=relation.script,
                        shared_codes=_shared_codes(query_codes, relation.form),
                        evidence=relation.evidence,
                    )
                )
            if (
                exact_relation
                and relation.relation is VariantRelation.RULED_OUT
                and _match_key(relation.form) == query_key
                and _match_key(relation.canonical_form) != query_key
            ):
                add(
                    VariantProposal(
                        canonical_form=relation.canonical_form,
                        entity_type=relation.entity_type,
                        form=relation.canonical_form,
                        relation=VariantRelation.RULED_OUT,
                        script=_script_for(relation.canonical_form),
                        shared_codes=_shared_codes(query_codes, relation.canonical_form),
                        evidence=relation.evidence,
                    )
                )
            if (
                relevant
                and relation.relation is not VariantRelation.RULED_OUT
                and _match_key(relation.form) == query_key
                and _match_key(relation.canonical_form) != query_key
            ):
                add(
                    VariantProposal(
                        canonical_form=relation.canonical_form,
                        entity_type=relation.entity_type,
                        form=relation.canonical_form,
                        relation=relation.relation,
                        script=_script_for(relation.canonical_form),
                        shared_codes=_shared_codes(query_codes, relation.canonical_form),
                        evidence=relation.evidence,
                    )
                )

        if include_phonetic and query_codes:
            for relation in available:
                if relation.relation is VariantRelation.RULED_OUT:
                    continue
                if _match_key(relation.form) == query_key:
                    continue
                shared = _shared_codes(query_codes, relation.form)
                if not shared:
                    continue
                add(
                    VariantProposal(
                        canonical_form=relation.canonical_form,
                        entity_type=relation.entity_type,
                        form=relation.form,
                        relation=VariantRelation.PHONETIC_CANDIDATE,
                        script=relation.script,
                        shared_codes=shared,
                        evidence=relation.evidence,
                    )
                )

        ordered = tuple(
            sorted(
                proposals.values(),
                key=lambda item: (
                    -_RELATION_RANK[item.relation],
                    item.entity_type,
                    _match_key(item.canonical_form),
                    _match_key(item.form),
                ),
            )
        )
        return VariantProposalReport(
            literal_input=literal_input,
            entity_type=entity_type,
            query_codes=query_codes,
            proposals=ordered,
        )
