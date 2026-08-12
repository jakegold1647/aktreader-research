import hashlib
import json
from pathlib import Path

import pytest

import aktreader.variant_batch as variant_batch_module
from aktreader.cli import PROJECT_ROOT, main
from aktreader.schema import validate_instance
from aktreader.variant_batch import (
    VariantBatchError,
    build_variant_batch,
    load_variant_batch_csv,
    verify_variant_batch_artifact,
)

LEXICON = PROJECT_ROOT / "resources" / "serock_name_lexicon.csv"
RELATIONS = PROJECT_ROOT / "resources" / "serock_variant_relations.csv"
SCHEMA = PROJECT_ROOT / "schemas" / "variant-batch-1.0.0.schema.json"
EXAMPLE = PROJECT_ROOT / "examples" / "variant-batch.example.csv"


def _write_batch(path: Path, rows: str) -> Path:
    path.write_text("id,query,entity_type\n" + rows, encoding="utf-8", newline="")
    return path


def _build(path: Path, *, include_phonetic: bool = True) -> dict[str, object]:
    return build_variant_batch(
        input_path=path,
        lexicon_path=LEXICON,
        relations_path=RELATIONS,
        include_phonetic=include_phonetic,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_artifact(
    path: Path,
    source: Path,
    *,
    include_phonetic: bool = True,
) -> dict[str, object]:
    artifact = _build(source, include_phonetic=include_phonetic)
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return artifact


def test_batch_artifact_is_schema_valid_ordered_and_source_hashed(tmp_path: Path) -> None:
    source = _write_batch(
        tmp_path / "names.csv",
        "surname-1,Kanarek,surname\n"
        "surname-2,Goldstein,surname\n"
        "town-1,Serock,town\n"
        "surname-3,Мяра,surname\n",
    )

    artifact = _build(source)

    validate_instance(artifact, SCHEMA)
    assert artifact["schema_version"] == "1.0.0"
    assert artifact["status"] == "PROPOSAL_ONLY"
    assert artifact["input_sha256"] == _sha256(source)
    assert artifact["lexicon_sha256"] == _sha256(LEXICON)
    assert artifact["relations_sha256"] == _sha256(RELATIONS)
    assert artifact["row_count"] == 4
    assert artifact["proposal_count"] == sum(artifact["relation_counts"].values())
    rows = artifact["rows"]
    assert [row["id"] for row in rows] == [
        "surname-1",
        "surname-2",
        "town-1",
        "surname-3",
    ]
    assert [row["row_number"] for row in rows] == [2, 3, 4, 5]
    assert rows[-1]["literal_input"] == "Мяра"
    assert all(row["literal_input_unchanged"] is True for row in rows)
    assert all("warning" not in row for row in rows)


def test_published_example_builds_as_documented() -> None:
    artifact = _build(EXAMPLE)

    validate_instance(artifact, SCHEMA)
    assert artifact["row_count"] == 4
    assert [row["id"] for row in artifact["rows"]] == [
        "surname-1",
        "surname-2",
        "town-1",
        "surname-3",
    ]


def test_same_bytes_produce_the_same_artifact(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")

    assert _build(source) == _build(source)


def test_query_is_preserved_exactly_after_csv_decoding(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", ' one ,"  Kanarek  ", surname \n')

    artifact = _build(source)

    row = artifact["rows"][0]
    assert row["id"] == "one"
    assert row["entity_type"] == "surname"
    assert row["literal_input"] == "  Kanarek  "


def test_quoted_comma_in_query_is_preserved(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", 'town-1,"Serock, Poland",town\n')

    artifact = _build(source)

    assert artifact["rows"][0]["literal_input"] == "Serock, Poland"


def test_no_phonetic_mode_suppresses_unknown_soundalikes(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Goldstein,surname\n")

    phonetic = _build(source)
    documented_only = _build(source, include_phonetic=False)

    assert phonetic["proposal_count"] == 2
    assert phonetic["relation_counts"]["PHONETIC_CANDIDATE"] == 2
    assert documented_only["proposal_count"] == 0
    assert documented_only["rows"][0]["query_codes"] == []
    assert documented_only["include_phonetic"] is False


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("query,entity_type\nKanarek,surname\n", "expected CSV header"),
        ("id,query,entity_type\n", "contains no rows"),
        ("id,query,entity_type\none,,surname\n", "blank required field"),
        ("id,query,entity_type\none,Kanarek,person\n", "unsupported entity_type"),
        (
            "id,query,entity_type\none,Kanarek,surname\none,Serock,town\n",
            "duplicate id",
        ),
        (
            "id,query,entity_type\none,Kanarek,surname,unexpected\n",
            "more columns than the CSV header",
        ),
        (
            'id,query,entity_type\none,"Kana\trek",surname\n',
            "query contains a control or format character",
        ),
    ],
)
def test_malformed_batch_contracts_fail_closed(tmp_path: Path, contents: str, message: str) -> None:
    source = tmp_path / "names.csv"
    source.write_text(contents, encoding="utf-8")

    with pytest.raises(VariantBatchError, match=message):
        load_variant_batch_csv(source)


def test_non_utf8_batch_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "names.csv"
    source.write_bytes(b"id,query,entity_type\none,\xff,surname\n")

    with pytest.raises(VariantBatchError, match="not UTF-8"):
        load_variant_batch_csv(source)


def test_utf8_bom_is_accepted(tmp_path: Path) -> None:
    source = tmp_path / "names.csv"
    source.write_bytes(b"\xef\xbb\xbfid,query,entity_type\none,Kanarek,surname\n")

    rows = load_variant_batch_csv(source)

    assert len(rows) == 1
    assert rows[0].row_id == "one"


def test_source_drift_is_detected_before_an_artifact_is_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    real_sha256 = variant_batch_module._sha256_path
    input_hash_calls = 0

    def drifting_hash(path: Path) -> str:
        nonlocal input_hash_calls
        digest = real_sha256(path)
        if path == source:
            input_hash_calls += 1
            if input_hash_calls == 2:
                return "0" * 64
        return digest

    monkeypatch.setattr(variant_batch_module, "_sha256_path", drifting_hash)

    with pytest.raises(VariantBatchError, match="input changed while"):
        _build(source)


def test_cli_writes_valid_artifact_and_requires_explicit_replacement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    output = tmp_path / "proposals.json"

    assert main(["variant-batch", "--input", str(source), "--output", str(output)]) == 0
    summary = json.loads(capsys.readouterr().out)
    artifact = json.loads(output.read_text(encoding="utf-8"))
    validate_instance(artifact, SCHEMA)
    assert summary["status"] == "SUCCEEDED"
    assert summary["artifact_status"] == "PROPOSAL_ONLY"
    assert summary["row_count"] == 1

    original_bytes = output.read_bytes()
    assert main(["variant-batch", "--input", str(source), "--output", str(output)]) == 2
    captured = capsys.readouterr()
    assert "pass --replace-existing" in captured.err
    assert output.read_bytes() == original_bytes

    assert (
        main(
            [
                "variant-batch",
                "--input",
                str(source),
                "--output",
                str(output),
                "--replace-existing",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert output.read_bytes() == original_bytes


def test_cli_never_overwrites_the_input_even_with_replace_existing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    original_bytes = source.read_bytes()

    exit_code = main(
        [
            "variant-batch",
            "--input",
            str(source),
            "--output",
            str(source),
            "--replace-existing",
        ]
    )

    assert exit_code == 2
    assert "must not overwrite" in capsys.readouterr().err
    assert source.read_bytes() == original_bytes


def test_invalid_batch_leaves_no_partial_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,person\n")
    output = tmp_path / "proposals.json"

    exit_code = main(["variant-batch", "--input", str(source), "--output", str(output)])

    assert exit_code == 2
    assert "unsupported entity_type" in capsys.readouterr().err
    assert not output.exists()


def test_verifier_accepts_exact_semantic_reproduction(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    artifact = _write_artifact(artifact_path, source)
    # Byte formatting is not evidence-bearing; JSON values and array positions are.
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    report = verify_variant_batch_artifact(
        artifact_path=artifact_path,
        input_path=source,
        lexicon_path=LEXICON,
        relations_path=RELATIONS,
        schema_path=SCHEMA,
    )

    assert report["status"] == "PASS"
    assert report["verification"] == "EXACT_REPRODUCTION"
    assert report["artifact_sha256"] == _sha256(artifact_path)
    assert report["schema_sha256"] == _sha256(SCHEMA)
    assert report["row_count"] == 1


def test_cli_verifies_no_phonetic_artifact_without_a_mode_override(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Goldstein,surname\n")
    artifact_path = tmp_path / "proposals.json"
    _write_artifact(artifact_path, source, include_phonetic=False)

    exit_code = main(
        [
            "variant-batch-verify",
            "--artifact",
            str(artifact_path),
            "--input",
            str(source),
        ]
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["status"] == "PASS"
    assert report["include_phonetic"] is False
    assert report["proposal_count"] == 0


def test_verifier_rejects_schema_invalid_artifact(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    artifact = _write_artifact(artifact_path, source)
    artifact["row_count"] = 0
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(ValueError, match="schema validation failed"):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


def test_verifier_rejects_schema_valid_content_drift_at_a_json_pointer(
    tmp_path: Path,
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    artifact = _write_artifact(artifact_path, source)
    artifact["warning"] = "Still proposal-only, but not the generated warning."
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(VariantBatchError, match=r"supplied sources at /warning$"):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


def test_verifier_rejects_reordered_rows(tmp_path: Path) -> None:
    source = _write_batch(
        tmp_path / "names.csv",
        "one,Kanarek,surname\ntwo,Serock,town\n",
    )
    artifact_path = tmp_path / "proposals.json"
    artifact = _write_artifact(artifact_path, source)
    artifact["rows"].reverse()
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(VariantBatchError, match=r"supplied sources at /rows/0/"):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


def test_verifier_rejects_reordered_proposals(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    artifact = _write_artifact(artifact_path, source)
    proposals = artifact["rows"][0]["proposals"]
    assert len(proposals) > 1
    proposals.reverse()
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    with pytest.raises(
        VariantBatchError,
        match=r"supplied sources at /rows/0/proposals/0/",
    ):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


def test_verifier_rejects_changed_source_input(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    _write_artifact(artifact_path, source)
    source.write_text(
        "id,query,entity_type\none,Kanarek,surname\ntwo,Serock,town\n",
        encoding="utf-8",
    )

    with pytest.raises(VariantBatchError, match=r"supplied sources at /input_sha256$"):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (b"\xff", "artifact is not UTF-8"),
        (b"{", "artifact is not valid JSON"),
        (b"[]", "artifact must be a JSON object"),
        (b'{"value": NaN}', "non-standard JSON number"),
    ],
)
def test_verifier_rejects_non_strict_json(
    tmp_path: Path,
    contents: bytes,
    message: str,
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    artifact_path.write_bytes(contents)

    with pytest.raises(VariantBatchError, match=message):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


def test_verifier_rejects_duplicate_artifact_keys(tmp_path: Path) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    _write_artifact(artifact_path, source)
    rendered = artifact_path.read_text(encoding="utf-8")
    artifact_path.write_text(
        rendered.replace(
            '"status": "PROPOSAL_ONLY",',
            '"status": "PROPOSAL_ONLY",\n  "status": "PROPOSAL_ONLY",',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(VariantBatchError, match="duplicate JSON key"):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )


def test_verifier_rejects_artifact_drift_during_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _write_batch(tmp_path / "names.csv", "one,Kanarek,surname\n")
    artifact_path = tmp_path / "proposals.json"
    _write_artifact(artifact_path, source)
    real_sha256 = variant_batch_module._sha256_path

    def drifting_hash(path: Path) -> str:
        if path == artifact_path:
            return "0" * 64
        return real_sha256(path)

    monkeypatch.setattr(variant_batch_module, "_sha256_path", drifting_hash)

    with pytest.raises(VariantBatchError, match="artifact changed while"):
        verify_variant_batch_artifact(
            artifact_path=artifact_path,
            input_path=source,
            lexicon_path=LEXICON,
            relations_path=RELATIONS,
            schema_path=SCHEMA,
        )
