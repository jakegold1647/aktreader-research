import copy
from pathlib import Path

import pytest

from aktreader.labels import load_reader_label
from aktreader.validators.dates import (
    CivilDateError,
    convert_civil_date,
    parse_civil_date,
    validate_date_value_shapes,
    validate_dates,
    validate_dual_date_gaps,
    validate_registration_event_order,
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


def test_unclear_dates_are_not_mechanically_decided() -> None:
    record = _record("1890-01-01", "1890-01-02")
    record["observations"]["event_date"]["confidence"] = "UNCLEAR"

    assert validate_dates(record) == ()
