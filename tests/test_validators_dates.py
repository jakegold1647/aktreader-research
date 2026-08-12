import copy
import json
from pathlib import Path

import pytest

from aktreader.labels import load_reader_label
from aktreader.validators.dates import (
    CivilDateError,
    convert_civil_date,
    parse_civil_date,
    resolve_relative_date_phrase,
    validate_date_value_shapes,
    validate_dates,
    validate_dual_date_gaps,
    validate_registration_event_order,
    validate_relative_date_consistency,
)

ROOT = Path(__file__).resolve().parents[1]


def _field(value, confidence="PROBABLE"):
    return {
        "value": value,
        "confidence": confidence,
        "observation_state": "PRESENT",
    }


def _record(registration, event):
    return {
        "record_id": "synthetic-date-record",
        "observations": {
            "registration_date": _field(registration),
            "event_date": _field(event),
        },
    }


def test_registration_before_event_is_flagged_without_mutation() -> None:
    record = _record("1890-01-01", "1890-01-02")
    before = copy.deepcopy(record)

    findings = validate_registration_event_order(record)

    assert [finding.code for finding in findings] == ["REGISTRATION_BEFORE_EVENT"]
    assert findings[0].blocks_confident is True
    assert record == before


def test_registration_on_or_after_event_passes() -> None:
    assert validate_registration_event_order(_record("1890-01-02", "1890-01-01")) == ()
    assert validate_registration_event_order(_record("1890-01-01", "1890-01-01")) == ()


def test_valid_12_and_13_day_dual_dates_pass() -> None:
    before_1900 = _record(
        {"gregorian": "1890-01-13", "julian": "1890-01-01"},
        {"gregorian": "1890-01-11", "julian": "1889-12-30"},
    )
    after_1900 = _record(
        {"gregorian": "1901-01-14", "julian": "1901-01-01"},
        {"gregorian": "1901-01-13", "julian": "1900-12-31"},
    )

    assert validate_dual_date_gaps(before_1900) == ()
    assert validate_dual_date_gaps(after_1900) == ()


def test_wrong_dual_date_gap_is_flagged() -> None:
    record = _record(
        {"gregorian": "1890-01-12", "julian": "1890-01-01"},
        "1890-01-01",
    )

    findings = validate_dual_date_gaps(record)

    assert [finding.code for finding in findings] == ["DUAL_DATE_GAP"]
    assert findings[0].evidence["expected_gregorian_from_julian"] == "1890-01-13"
    assert findings[0].evidence["expected_julian_from_gregorian"] == "1889-12-31"
    assert findings[0].evidence["calendar_day_offset"] == -1
    assert "Neither side was selected" in findings[0].message


@pytest.mark.parametrize(
    ("julian", "gregorian"),
    [
        ("1900-02-16", "1900-02-28"),
        ("1900-02-17", "1900-03-01"),
        ("1900-02-28", "1900-03-12"),
        ("1900-02-29", "1900-03-13"),
        ("1900-03-01", "1900-03-14"),
    ],
)
def test_1900_julian_leap_transition_uses_exact_calendar_days(julian: str, gregorian: str) -> None:
    record = _record({"gregorian": gregorian, "julian": julian}, "1900-02-01")

    assert validate_dual_date_gaps(record) == ()
    assert convert_civil_date(julian, from_calendar="julian")["equivalent"] == {
        "calendar": "gregorian",
        "date": gregorian,
    }
    assert convert_civil_date(gregorian, from_calendar="gregorian")["equivalent"] == {
        "calendar": "julian",
        "date": julian,
    }


def test_old_march_1900_heuristic_pair_is_rejected() -> None:
    record = _record(
        {"gregorian": "1900-03-01", "julian": "1900-02-16"},
        "1900-02-01",
    )

    findings = validate_dual_date_gaps(record)

    assert [finding.code for finding in findings] == ["DUAL_DATE_GAP"]
    assert findings[0].evidence["expected_gregorian_from_julian"] == "1900-02-28"
    assert findings[0].evidence["expected_julian_from_gregorian"] == "1900-02-17"


def test_cross_year_pair_converts_in_both_directions() -> None:
    forward = convert_civil_date("1889-12-30", from_calendar="julian")
    reverse = convert_civil_date("1890-01-11", from_calendar="gregorian")

    assert forward["equivalent"]["date"] == "1890-01-11"
    assert reverse["equivalent"]["date"] == "1889-12-30"


def test_cross_calendar_registration_event_order_is_compared() -> None:
    record = _record(
        {"gregorian": "1890-01-13"},
        {"julian": "1890-01-02"},
    )

    findings = validate_registration_event_order(record)

    assert [finding.code for finding in findings] == ["REGISTRATION_BEFORE_EVENT"]
    assert findings[0].evidence["calendar"] == "gregorian-to-julian"


@pytest.mark.parametrize(
    "value",
    [
        "1890-01-01garbage",
        "1890-01-01, hour not stated",
        "1890-01-01T25:00:00",
        "1890-02-30",
        "1890-1-01",
        "١٨٩٠-٠١-٠١",
    ],
)
def test_iso_looking_prefix_with_invalid_suffix_or_date_is_rejected(value: str) -> None:
    with pytest.raises(CivilDateError):
        parse_civil_date(value, calendar="gregorian")


def test_complete_iso_datetimes_remain_supported() -> None:
    assert parse_civil_date("1890-01-01 12:30:00", calendar="gregorian").isoformat() == "1890-01-01"
    assert (
        parse_civil_date("1890-01-01T12:30:00Z", calendar="gregorian").isoformat() == "1890-01-01"
    )


def test_julian_century_leap_day_is_valid_but_gregorian_one_is_not() -> None:
    assert parse_civil_date("1900-02-29", calendar="julian").isoformat() == "1900-02-29"
    with pytest.raises(CivilDateError, match="invalid.*gregorian"):
        parse_civil_date("1900-02-29", calendar="gregorian")


@pytest.mark.parametrize(
    "value",
    [
        "1890-01-01, hour not stated",
        {"gregorian": "1890-01-13", "julian": "not-a-date"},
        {"derived": "1890-01-01"},
        18900101,
    ],
)
def test_invalid_confident_core_date_value_is_a_finding(value) -> None:
    record = _record(value, "1890-01-01")

    findings = validate_date_value_shapes(record)

    assert [finding.code for finding in findings] == ["DATE_VALUE_INVALID"]
    assert findings[0].field_paths == ("registration_date",)
    assert findings[0].blocks_confident is True


def test_invalid_unclear_core_date_is_not_mechanically_decided() -> None:
    record = _record("[unclear: 17/18 September]", "1890-01-01")
    record["observations"]["registration_date"]["confidence"] = "UNCLEAR"

    assert validate_date_value_shapes(record) == ()


@pytest.mark.parametrize(
    ("record_id", "field_path"),
    [
        ("serock-1890-death-16", "event_date"),
        ("serock-1890-death-26", "registration_date"),
        ("serock-1890-death-44", "event_date"),
        ("serock-1890-death-46", "registration_date"),
        ("serock-1890-death-46", "event_date"),
    ],
)
def test_frozen_legacy_prose_dates_are_exposed_as_findings(
    record_id: str,
    field_path: str,
) -> None:
    label = load_reader_label(ROOT / "labels" / "readerA" / f"{record_id}.json")

    invalid_paths = {
        finding.field_paths[0]
        for finding in validate_date_value_shapes(label)
        if finding.code == "DATE_VALUE_INVALID"
    }

    assert field_path in invalid_paths


def test_attested_yesterday_fixture_resolves_without_mutating_label() -> None:
    fixture = json.loads(
        (ROOT / "labels" / "readerB" / "serock-1890-death-4.json").read_text(encoding="utf-8")
    )
    registration = fixture["observations"]["registration_date"]
    event = fixture["observations"]["event_date"]
    registration_before = copy.deepcopy(registration)
    event_before = copy.deepcopy(event)

    report = resolve_relative_date_phrase(
        event["original_script"],
        registration["value"],
        anchor_state=registration["observation_state"],
        anchor_confidence=registration["confidence"],
    )

    assert report["status"] == "RESOLVED"
    assert report["phrase_family"] == "PREVIOUS_DAY"
    assert report["literal_phrase"] == "вчерашняго числа"
    assert report["literal_phrase_unchanged"] is True
    assert report["anchor"] == {
        "gregorian": "1890-02-19",
        "julian": "1890-02-07",
    }
    assert report["resolved_value"] == {
        "gregorian": event["value"]["gregorian"],
        "julian": event["value"]["julian"],
        "resolved_from_relative_phrase": True,
    }
    assert registration == registration_before
    assert event == event_before


def test_live_canonical_relative_fixtures_reproduce_their_normalized_dates() -> None:
    checked: list[str] = []
    for path in sorted((ROOT / "labels" / "readerB").glob("serock-1890-death-*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        observations = fixture.get("observations")
        if not isinstance(observations, dict):
            continue
        registration = observations.get("registration_date", {})
        event = observations.get("event_date", {})
        literal = event.get("original_script")
        if not isinstance(literal, str) or not literal.startswith(
            ("сего числа", "вчерашняго числа")
        ):
            continue
        if (
            registration.get("observation_state") != "PRESENT"
            or registration.get("confidence") == "UNCLEAR"
        ):
            continue

        report = resolve_relative_date_phrase(
            literal,
            registration.get("value"),
            anchor_state=registration.get("observation_state"),
            anchor_confidence=registration.get("confidence"),
        )

        assert report["status"] == "RESOLVED", (path, report)
        expected = event.get("value")
        assert isinstance(expected, dict)
        for calendar in ("gregorian", "julian"):
            if calendar in expected:
                assert report["resolved_value"][calendar] == expected[calendar]
        assert validate_relative_date_consistency(fixture) == ()
        checked.append(path.name)

    assert len(checked) >= 19


def test_relative_date_mismatch_is_flagged_without_rewriting_either_field() -> None:
    record = _record(
        {"julian": "1890-02-07", "gregorian": "1890-02-19"},
        {
            "julian": "1890-02-05",
            "gregorian": "1890-02-17",
            "resolved_from_relative_phrase": True,
        },
    )
    record["observations"]["event_date"]["original_script"] = "вчерашняго числа"
    before = copy.deepcopy(record)

    findings = validate_relative_date_consistency(record)

    assert [finding.code for finding in findings] == ["RELATIVE_DATE_MISMATCH"]
    assert findings[0].record_ids == ("synthetic-date-record",)
    assert findings[0].field_paths == ("registration_date", "event_date")
    assert findings[0].blocks_confident is True
    assert findings[0].evidence["phrase_family"] == "PREVIOUS_DAY"
    assert findings[0].evidence["mismatches"] == {
        "gregorian": {"stored": "1890-02-17", "expected": "1890-02-18"},
        "julian": {"stored": "1890-02-05", "expected": "1890-02-06"},
    }
    assert [finding.code for finding in validate_dates(record)] == [
        "RELATIVE_DATE_MISMATCH"
    ]
    assert record == before


def test_relative_date_match_accepts_time_without_treating_it_as_phrase_text() -> None:
    record = _record(
        {"julian": "1890-06-28"},
        {"julian": "1890-06-28T08:00:00", "resolved_from_relative_phrase": True},
    )
    record["observations"]["event_date"]["original_script"] = (
        "сего числа текущаго года въ восемь часовъ утра"
    )

    assert validate_relative_date_consistency(record) == ()


@pytest.mark.parametrize(
    ("literal", "anchor_confidence", "event_confidence", "anchor"),
    [
        ("вчерашняго числа", "UNCLEAR", "PROBABLE", {"julian": "1890-02-07"}),
        ("вчерашняго числа", "PROBABLE", "UNCLEAR", {"julian": "1890-02-07"}),
        ("вчерашняго числа", "PROBABLE", "PROBABLE", "1890-02-07"),
        ("позавчерашняго числа", "PROBABLE", "PROBABLE", {"julian": "1890-02-07"}),
    ],
)
def test_relative_date_consistency_refuses_when_the_evidence_does_not_decide(
    literal: str,
    anchor_confidence: str,
    event_confidence: str,
    anchor,
) -> None:
    record = _record(anchor, {"julian": "1890-02-01"})
    record["observations"]["registration_date"]["confidence"] = anchor_confidence
    record["observations"]["event_date"]["confidence"] = event_confidence
    record["observations"]["event_date"]["original_script"] = literal

    assert validate_relative_date_consistency(record) == ()


def test_attested_same_day_fixture_refuses_unclear_anchor() -> None:
    label = load_reader_label(ROOT / "labels" / "readerA" / "serock-1890-death-16.json")
    registration = label.observations["registration_date"]
    event = label.observations["event_date"]

    report = resolve_relative_date_phrase(
        event["original_script"],
        registration["value"],
        anchor_state=registration["observation_state"],
        anchor_confidence=registration["confidence"],
    )

    assert report["status"] == "UNRESOLVED"
    assert report["phrase_family"] == "SAME_DAY"
    assert report["literal_phrase"] == "сего числа въ пять часовъ утра"
    assert report["reason"] == "ANCHOR_UNCLEAR"
    assert report["resolved_value"] is None


def test_same_day_preserves_full_literal_time_clause_but_does_not_parse_it() -> None:
    literal = "сего числа текущаго года въ восемь часовъ утра"

    report = resolve_relative_date_phrase(literal, {"julian": "1890-06-28"})

    assert report["status"] == "RESOLVED"
    assert report["literal_phrase"] == literal
    assert report["resolved_value"] == {
        "julian": "1890-06-28",
        "resolved_from_relative_phrase": True,
    }
    assert "08:00" not in str(report["resolved_value"])


@pytest.mark.parametrize(
    ("anchor", "expected"),
    [
        ({"gregorian": "1890-01-01"}, {"gregorian": "1889-12-31"}),
        ({"julian": "1890-01-01"}, {"julian": "1889-12-31"}),
        ({"gregorian": "1900-03-01"}, {"gregorian": "1900-02-28"}),
        ({"julian": "1900-03-01"}, {"julian": "1900-02-29"}),
        (
            {"gregorian": "1900-03-14", "julian": "1900-03-01"},
            {"gregorian": "1900-03-13", "julian": "1900-02-29"},
        ),
    ],
)
def test_yesterday_handles_rollover_in_each_declared_calendar(anchor, expected) -> None:
    report = resolve_relative_date_phrase("вчерашняго числа", anchor)

    assert report["status"] == "RESOLVED"
    assert report["offset_days"] == -1
    assert report["resolved_value"] == {
        **expected,
        "resolved_from_relative_phrase": True,
    }


@pytest.mark.parametrize(
    "literal",
    [
        "позавчерашняго числа",
        "вчерашнего числа",
        "Вчерашняго числа",
        "[unclear: вчерашняго числа?]",
        "невчерашняго числа",
        "вче-рашняго числа",
        "",
    ],
)
def test_unsupported_or_uncertain_phrase_fails_without_fuzzy_matching(literal: str) -> None:
    report = resolve_relative_date_phrase(literal, {"julian": "1890-01-01"})

    assert report["status"] == "UNRESOLVED"
    assert report["phrase_family"] is None
    assert report["literal_phrase"] == literal
    assert report["reason"] == "UNSUPPORTED_PHRASE"


@pytest.mark.parametrize(
    ("anchor", "kwargs", "reason"),
    [
        (None, {}, "ANCHOR_MISSING"),
        ({}, {}, "ANCHOR_MISSING"),
        ("1890-01-01", {}, "ANCHOR_CALENDAR_UNSPECIFIED"),
        ({"date": "1890-01-01"}, {}, "ANCHOR_CALENDAR_UNSPECIFIED"),
        ({"julian": "not-a-date"}, {}, "ANCHOR_INVALID"),
        ({"gregorian": "1900-02-29"}, {}, "ANCHOR_INVALID"),
        ({"julian": "1890-01-01T12:00:00"}, {}, "ANCHOR_INVALID"),
        (
            {"date": "1890-01-13", "gregorian": "1890-01-13"},
            {},
            "ANCHOR_INVALID",
        ),
        (
            {"gregorian": "1890-01-12", "julian": "1890-01-01"},
            {},
            "ANCHOR_CALENDAR_MISMATCH",
        ),
        ({"julian": "1890-01-01"}, {"anchor_state": "BLANK"}, "ANCHOR_NOT_PRESENT"),
        (
            {"julian": "1890-01-01"},
            {"anchor_confidence": "UNCLEAR"},
            "ANCHOR_UNCLEAR",
        ),
        (
            {"julian": "1890-01-01"},
            {"anchor_confidence": ""},
            "ANCHOR_CONFIDENCE_UNSUPPORTED",
        ),
    ],
)
def test_relative_date_anchor_refusals_are_machine_readable(anchor, kwargs, reason) -> None:
    report = resolve_relative_date_phrase("сего числа", anchor, **kwargs)

    assert report["status"] == "UNRESOLVED"
    assert report["reason"] == reason
    assert report["resolved_value"] is None
    assert isinstance(report["details"], list)


def test_inconsistent_dual_anchor_reports_both_repairs_and_selects_neither() -> None:
    report = resolve_relative_date_phrase(
        "вчерашняго числа",
        {"gregorian": "1890-01-12", "julian": "1890-01-01"},
    )

    assert report["reason"] == "ANCHOR_CALENDAR_MISMATCH"
    assert report["anchor"] == {
        "gregorian": "1890-01-12",
        "julian": "1890-01-01",
    }
    assert report["details"] == [
        "julian anchor converts to gregorian 1890-01-13",
        "gregorian anchor converts to julian 1889-12-31",
        "neither anchor side was selected",
    ]


def test_previous_day_outside_supported_year_range_is_unresolved() -> None:
    report = resolve_relative_date_phrase(
        "вчерашняго числа",
        {"gregorian": "0001-01-01"},
    )

    assert report["status"] == "UNRESOLVED"
    assert report["reason"] == "RESULT_OUT_OF_RANGE"


def test_unclear_dates_are_not_mechanically_decided() -> None:
    record = _record("1890-01-01", "1890-01-02")
    record["observations"]["event_date"]["confidence"] = "UNCLEAR"

    assert validate_dates(record) == ()
