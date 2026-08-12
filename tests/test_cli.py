import io
import json
from pathlib import Path

from aktreader import __version__
from aktreader.cli import PROJECT_ROOT, _emit_json, build_parser, environment_report, main


def test_environment_report_is_honest_about_phase() -> None:
    report = environment_report()

    assert report["aktreader_version"] == __version__
    assert report["phase"] == "P2"
    assert report["pipeline_available"] is True
    assert report["python_supported"] is True
    assert report["reader_backend"] == "local-open-weights-only"
    assert report["network_required"] is False


def test_doctor_json_is_machine_readable(capsys) -> None:
    exit_code = main(["doctor", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["phase"] == "P2"
    assert payload["pipeline_available"] is True
    assert payload["network_required"] is False


def test_no_command_prints_help(capsys) -> None:
    exit_code = main([])

    assert exit_code == 0
    assert "Local-only" in capsys.readouterr().out


def test_parser_exposes_no_api_key_or_network_backend_options() -> None:
    help_text = build_parser().format_help().lower()

    assert "--api" not in help_text
    assert "--url" not in help_text
    assert "hosted" not in help_text


def test_date_convert_is_machine_readable_and_preserves_evidence_boundary(capsys) -> None:
    exit_code = main(["date-convert", "1900-02-29", "--from-calendar", "julian"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "EXACT_CALENDAR_CONVERSION"
    assert payload["input"] == {"calendar": "julian", "date": "1900-02-29"}
    assert payload["equivalent"] == {"calendar": "gregorian", "date": "1900-03-13"}
    assert "does not establish" in payload["warning"]


def test_date_convert_rejects_invalid_declared_calendar_date(capsys) -> None:
    exit_code = main(["date-convert", "1900-02-29", "--from-calendar", "gregorian"])

    assert exit_code == 2
    assert "invalid" in capsys.readouterr().err


def test_date_audit_cli_distinguishes_findings_from_clean_labels(capsys) -> None:
    reader_a_exit = main(["date-audit", str(PROJECT_ROOT / "labels" / "readerA")])
    reader_a = json.loads(capsys.readouterr().out)
    reader_b_exit = main(["date-audit", str(PROJECT_ROOT / "labels" / "readerB")])
    reader_b = json.loads(capsys.readouterr().out)

    assert reader_a_exit == 1
    assert reader_a["status"] == "FINDINGS"
    assert reader_a["finding_count"] == 5
    assert reader_b_exit == 0
    assert reader_b["status"] == "PASS"
    assert reader_b["finding_count"] == 0


def test_date_audit_cli_reports_malformed_json_as_incomplete(tmp_path: Path, capsys) -> None:
    malformed = tmp_path / "broken.json"
    malformed.write_text("{", encoding="utf-8")

    exit_code = main(["date-audit", str(malformed)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert report["status"] == "INCOMPLETE"
    assert report["parse_failure_count"] == 1


def test_date_convert_refuses_to_silently_drop_a_time(capsys) -> None:
    exit_code = main(
        ["date-convert", "1890-01-01T12:00:00", "--from-calendar", "julian"]
    )

    assert exit_code == 2
    assert "without a time" in capsys.readouterr().err


def test_relative_date_cli_resolves_consistent_dual_anchor(capsys) -> None:
    exit_code = main(
        [
            "date-resolve-relative",
            "вчерашняго числа",
            "--julian",
            "1900-03-01",
            "--gregorian",
            "1900-03-14",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "RESOLVED"
    assert payload["phrase_family"] == "PREVIOUS_DAY"
    assert payload["resolved_value"] == {
        "gregorian": "1900-03-13",
        "julian": "1900-02-29",
        "resolved_from_relative_phrase": True,
    }


def test_relative_date_cli_returns_json_and_exit_one_for_refusal(capsys) -> None:
    exit_code = main(
        [
            "date-resolve-relative",
            "сего числа",
            "--julian",
            "1890-01-01",
            "--anchor-confidence",
            "UNCLEAR",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["status"] == "UNRESOLVED"
    assert payload["reason"] == "ANCHOR_UNCLEAR"
    assert captured.err == ""


def test_relative_date_cli_missing_anchor_fails_closed(capsys) -> None:
    exit_code = main(["date-resolve-relative", "вчерашняго числа"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["reason"] == "ANCHOR_MISSING"


def test_variant_key_is_machine_readable_and_marks_collisions_as_proposals(capsys) -> None:
    exit_code = main(["variant-key", "Goldsztejn", "Goldsztajn"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "PROPOSAL_ONLY"
    assert payload["algorithm"] == "Daitch-Mokotoff Soundex"
    assert payload["shared_codes"]
    assert "does not establish" in payload["warning"]


def test_variant_propose_preserves_input_and_negative_evidence(capsys) -> None:
    exit_code = main(["variant-propose", "Kanarek", "--kind", "surname"])

    payload = json.loads(capsys.readouterr().out)
    by_form = {item["form"]: item for item in payload["proposals"]}
    assert exit_code == 0
    assert payload["status"] == "PROPOSAL_ONLY"
    assert payload["literal_input"] == "Kanarek"
    assert payload["literal_input_unchanged"] is True
    assert by_form["KANALEK"]["relation"] == "RULED_OUT"
    assert by_form["Kania"]["relation"] == "DOCUMENTED_FORM"


def test_json_emitter_falls_back_to_ascii_escapes_on_legacy_console() -> None:
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="ascii")

    _emit_json({"name": "Мяра"}, stream=stream)
    stream.flush()

    assert json.loads(buffer.getvalue().decode("ascii")) == {"name": "Мяра"}


def test_prompt_verify_and_canonical_label_validation_are_machine_readable(
    tmp_path: Path, capsys
) -> None:
    prompt_exit = main(["prompt-verify", "--root", str(PROJECT_ROOT)])
    prompt = json.loads(capsys.readouterr().out)
    source_path = PROJECT_ROOT / "labels" / "readerB" / "serock-1890-death-1.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["observations"] = {
        "principal.age": payload["observations"]["principal.age"]
    }
    label_path = tmp_path / "grounded-label.json"
    label_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    label_exit = main(["label-validate", str(label_path)])
    labels = json.loads(capsys.readouterr().out)

    assert prompt_exit == label_exit == 0
    assert prompt["status"] == "PASS"
    assert len(prompt["sha256"]) == 64
    assert labels["count"] == 1
    assert labels["labels"][0]["schema_kind"] == "canonical"
    assert labels["labels"][0]["quality_metrics"]["groundedness"]["violation_count"] == 0
    assert Path(labels["labels"][0]["path"]) == label_path


def test_label_validate_report_surveys_instead_of_stopping(tmp_path: Path, capsys) -> None:
    source_path = PROJECT_ROOT / "labels" / "readerB" / "serock-1890-death-1.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["observations"] = {
        "principal.age": payload["observations"]["principal.age"]
    }
    grounded_path = tmp_path / "grounded-label.json"
    grounded_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    ungrounded_path = (
        PROJECT_ROOT
        / "labels"
        / "readerA"
        / "superseded"
        / "wave006-july-pass-ruled-compromised"
        / "serock-1877-birth-1.json"
    )

    exit_code = main(
        ["label-validate", "--report", str(grounded_path), str(ungrounded_path)]
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert report["status"] == "FAIL"
    assert report["count"] == 2
    assert report["failing_count"] == 1
    by_status = {entry["status"]: entry for entry in report["labels"]}
    assert by_status["GROUNDED"]["violations"] == []
    ungrounded = by_status["UNGROUNDED"]
    assert ungrounded["record_id"] == "serock-1877-birth-1"
    assert any(
        violation["code"] == "PRESENT_RU_ORIGINAL_SCRIPT_HAS_NO_CYRILLIC"
        for violation in ungrounded["violations"]
    )


def test_label_validate_report_passes_when_every_label_is_grounded(
    tmp_path: Path, capsys
) -> None:
    source_path = PROJECT_ROOT / "labels" / "readerB" / "serock-1890-death-1.json"
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["observations"] = {
        "principal.age": payload["observations"]["principal.age"]
    }
    grounded_path = tmp_path / "grounded-label.json"
    grounded_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    exit_code = main(["label-validate", "--report", str(grounded_path)])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["status"] == "PASS"
    assert report["failing_count"] == 0
