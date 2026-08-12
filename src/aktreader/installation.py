"""Inspect source-checkout contracts required by the Evidence Lab."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import tomllib

from aktreader import DISTRIBUTION_NAME

AssetKind = Literal["file", "json-directory"]


@dataclass(frozen=True)
class ContractAsset:
    """One public asset required for the Lab's scan-free reproducibility paths."""

    name: str
    relative_path: str
    kind: AssetKind = "file"


CONTRACT_ASSETS = (
    ContractAsset("act_record_schema", "schemas/act-record-2.0.0.schema.json"),
    ContractAsset("date_audit_schema", "schemas/date-audit-1.0.0.schema.json"),
    ContractAsset("model_output_schema", "schemas/model-output-1.0.0.schema.json"),
    ContractAsset(
        "model_output_gold_map",
        "schemas/model-output-to-gold-map-1.0.0.json",
    ),
    ContractAsset("reader_label_schema", "schemas/reader-label-1.0.0.schema.json"),
    ContractAsset(
        "grounded_reader_label_schema",
        "schemas/reader-label-1.0.0-v1.4.schema.json",
    ),
    ContractAsset("variant_batch_schema", "schemas/variant-batch-1.0.0.schema.json"),
    ContractAsset("reader_prompt", "prompts/reader_prompt.md"),
    ContractAsset("reader_prompt_digest", "prompts/reader_prompt.sha256"),
    ContractAsset("reader_prompt_manifest", "prompts/manifest.json"),
    ContractAsset("act_formula_skill", "skills/napoleonic-act-formula.md"),
    ContractAsset("cyrillic_skill", "skills/cyrillic-paleography.md"),
    ContractAsset("uncertainty_skill", "skills/uncertainty-grading.md"),
    ContractAsset("name_lexicon", "resources/serock_name_lexicon.csv"),
    ContractAsset("variant_relations", "resources/serock_variant_relations.csv"),
    ContractAsset("gold_manifest", "gold/manifest.json"),
    ContractAsset("gold_schema", "gold/schema.json"),
    ContractAsset("holdout_manifest", "gold/clerk_year_holdout.json"),
    ContractAsset("gold_records", "gold/acts", kind="json-directory"),
    ContractAsset("reader_a_labels", "labels/readerA", kind="json-directory"),
    ContractAsset("reader_b_labels", "labels/readerB", kind="json-directory"),
    ContractAsset("variant_batch_example", "examples/variant-batch.example.csv"),
)


def _checkout_identity(root: Path) -> tuple[str, str | None]:
    metadata = root / "pyproject.toml"
    if not metadata.is_file():
        return "MISSING", None
    try:
        project = tomllib.loads(metadata.read_text(encoding="utf-8")).get("project")
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return "MALFORMED", None
    if not isinstance(project, dict) or not isinstance(project.get("name"), str):
        return "MALFORMED", None
    observed = project["name"]
    if observed != DISTRIBUTION_NAME:
        return "WRONG_DISTRIBUTION", observed
    return "MATCH", observed


def _inspect_asset(root: Path, asset: ContractAsset) -> dict[str, Any]:
    path = root / Path(asset.relative_path)
    if asset.kind == "file":
        return {
            "path": asset.relative_path,
            "kind": asset.kind,
            "available": path.is_file(),
        }
    file_count = sum(1 for candidate in path.glob("*.json") if candidate.is_file())
    return {
        "path": asset.relative_path,
        "kind": asset.kind,
        "available": path.is_dir() and file_count > 0,
        "file_count": file_count,
    }


def inspect_evidence_lab_checkout(root: Path | str) -> dict[str, Any]:
    """Report Lab identity and public asset presence without mutating the checkout."""
    resolved = Path(root).resolve()
    identity_status, observed_distribution = _checkout_identity(resolved)
    assets = {
        asset.name: _inspect_asset(resolved, asset)
        for asset in CONTRACT_ASSETS
    }
    missing = [
        details["path"]
        for details in assets.values()
        if not details["available"]
    ]
    available_count = len(CONTRACT_ASSETS) - len(missing)
    return {
        "root": str(resolved),
        "identity_status": identity_status,
        "observed_distribution_name": observed_distribution,
        "contract_asset_count": len(CONTRACT_ASSETS),
        "available_contract_asset_count": available_count,
        "contract_assets_available": not missing,
        "missing_contract_assets": missing,
        "contract_assets": assets,
        "ready": identity_status == "MATCH" and not missing,
    }
