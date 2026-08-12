from pathlib import Path

from aktreader.installation import CONTRACT_ASSETS, inspect_evidence_lab_checkout

ROOT = Path(__file__).resolve().parents[1]


def test_repository_is_a_complete_evidence_lab_checkout() -> None:
    report = inspect_evidence_lab_checkout(ROOT)

    assert report["identity_status"] == "MATCH"
    assert report["observed_distribution_name"] == "aktreader-research"
    assert report["contract_asset_count"] == len(CONTRACT_ASSETS) == 22
    assert report["available_contract_asset_count"] == 22
    assert report["contract_assets_available"] is True
    assert report["missing_contract_assets"] == []
    assert report["contract_assets"]["gold_records"]["file_count"] == 36
    assert report["contract_assets"]["reader_a_labels"]["file_count"] == 60
    assert report["contract_assets"]["reader_b_labels"]["file_count"] == 27
    assert report["ready"] is True


def test_matching_metadata_without_assets_is_not_ready(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aktreader-research"\nversion = "0"\n',
        encoding="utf-8",
    )

    report = inspect_evidence_lab_checkout(tmp_path)

    assert report["identity_status"] == "MATCH"
    assert report["available_contract_asset_count"] == 0
    assert report["missing_contract_assets"] == [
        asset.relative_path for asset in CONTRACT_ASSETS
    ]
    assert report["ready"] is False


def test_application_metadata_is_rejected_even_when_an_asset_exists(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "aktreader-app"\nversion = "0"\n',
        encoding="utf-8",
    )
    schema = tmp_path / "schemas" / "act-record-2.0.0.schema.json"
    schema.parent.mkdir()
    schema.write_text("{}\n", encoding="utf-8")

    report = inspect_evidence_lab_checkout(tmp_path)

    assert report["identity_status"] == "WRONG_DISTRIBUTION"
    assert report["observed_distribution_name"] == "aktreader-app"
    assert report["available_contract_asset_count"] == 1
    assert report["ready"] is False


def test_malformed_project_metadata_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")

    report = inspect_evidence_lab_checkout(tmp_path)

    assert report["identity_status"] == "MALFORMED"
    assert report["observed_distribution_name"] is None
    assert report["ready"] is False
