import json
from pathlib import Path

from aktreader import __version__
from aktreader.cli import PROJECT_ROOT, build_parser, environment_report, main


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
