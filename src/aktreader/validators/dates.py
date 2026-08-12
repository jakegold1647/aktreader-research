"""Strict civil-date conversion and non-mutating date validators."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aktreader.validators.models import ValidationFinding
from aktreader.validators.support import observations_of, record_id_of

CALENDARS = ("gregorian", "julian")
DATE_VALIDATOR_VERSION = "1.0.0"
DATE_VALIDATOR_CODES = (
    "DATE_VALUE_INVALID",
    "REGISTRATION_BEFORE_EVENT",
    "DUAL_DATE_GAP",
    "RELATIVE_DATE_MISMATCH",
)
_DATE_FIELDS = ("registration_date", "event_date")
_ISO_DATE = re.compile(r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})(?P<suffix>.*)$")
_RELATIVE_PHRASES = (
    (re.compile(r"^сего числа(?:$|(?=[\s,.;:—]))"), "SAME_DAY", 0),
    (re.compile(r"^вчерашняго числа(?:$|(?=[\s,.;:—]))"), "PREVIOUS_DAY", -1),
)
_RELATIVE_DATE_WARNING = (
    "Relative-date arithmetic does not replace the literal phrase or establish an uncertain "
    "anchor; preserve both and verify against the act."
)
_USABLE_ANCHOR_CONFIDENCE = frozenset({"PROBABLE", "CONFIDENT", "CONFIDENT_ELIGIBLE"})


class CivilDateError(ValueError):
    """Raised when a normalized date cannot be interpreted without guessing."""


def _is_leap_year(year: int, calendar: str) -> bool:
    if calendar == "julian":
        return year % 4 == 0
    if calendar == "gregorian":
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    raise CivilDateError(f"unsupported calendar {calendar!r}")


@dataclass(frozen=True, order=True)
class CivilDate:
    """One calendar label, kept separate from Python's proleptic Gregorian date."""

    year: int
    month: int
    day: int

    def isoformat(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


def _validate_civil_date(value: CivilDate, calendar: str) -> CivilDate:
    if not 1 <= value.year <= 9999:
        raise CivilDateError("year must be between 0001 and 9999")
    if not 1 <= value.month <= 12:
        raise CivilDateError("month must be between 01 and 12")
    month_lengths = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    maximum = month_lengths[value.month - 1]
    if value.month == 2 and _is_leap_year(value.year, calendar):
        maximum = 29
    if not 1 <= value.day <= maximum:
        raise CivilDateError(
            f"day {value.day:02d} is invalid for {value.year:04d}-{value.month:02d} "
            f"in the {calendar} calendar"
        )
    return value


def parse_civil_date(value: Any, *, calendar: str) -> CivilDate:
    """Parse one complete ISO date or datetime under the named civil calendar."""

    if calendar not in CALENDARS:
        raise CivilDateError(f"unsupported calendar {calendar!r}")
    if not isinstance(value, str):
        raise CivilDateError("date value must be a string")
    match = _ISO_DATE.fullmatch(value)
    if match is None:
        raise CivilDateError("date must start with an exact YYYY-MM-DD")
    result = _validate_civil_date(
        CivilDate(
            year=int(match.group("year")),
            month=int(match.group("month")),
            day=int(match.group("day")),
        ),
        calendar,
    )
    suffix = match.group("suffix")
    if suffix:
        if not suffix.startswith(("T", " ")):
            raise CivilDateError("text after YYYY-MM-DD must be a valid ISO time")
        try:
            # Validate only the time suffix against a neutral Gregorian date. The date itself
            # was validated above under its declared calendar, including Julian 1900-02-29.
            datetime.fromisoformat(f"2000-01-01{suffix}".replace("Z", "+00:00"))
        except ValueError as error:
            raise CivilDateError("text after YYYY-MM-DD must be a valid ISO time") from error
    return result


def _civil_date_to_day_number(value: CivilDate, calendar: str) -> int:
    """Return the midnight-aligned Julian day number for one civil calendar label."""

    # Integer calendar/JDN transforms follow the Fliegel-Van Flandern algorithms published by
    # the U.S. Naval Observatory: https://aa.usno.navy.mil/faq/JD_formula
    value = _validate_civil_date(value, calendar)
    adjustment = (14 - value.month) // 12
    year = value.year + 4800 - adjustment
    month = value.month + 12 * adjustment - 3
    common = value.day + (153 * month + 2) // 5 + 365 * year + year // 4
    if calendar == "gregorian":
        return common - year // 100 + year // 400 - 32045
    return common - 32083


def _day_number_to_gregorian(day_number: int) -> CivilDate:
    a = day_number + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    month_index = (5 * e + 2) // 153
    return CivilDate(
        year=100 * b + d - 4800 + month_index // 10,
        month=month_index + 3 - 12 * (month_index // 10),
        day=e - (153 * month_index + 2) // 5 + 1,
    )


def _day_number_to_julian(day_number: int) -> CivilDate:
    c = day_number + 32082
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    month_index = (5 * e + 2) // 153
    return CivilDate(
        year=d - 4800 + month_index // 10,
        month=month_index + 3 - 12 * (month_index // 10),
        day=e - (153 * month_index + 2) // 5 + 1,
    )


def convert_civil_date(value: str, *, from_calendar: str) -> dict[str, object]:
    """Convert one exact calendar label without inferring what a record physically says."""

    source = parse_civil_date(value, calendar=from_calendar)
    if value != source.isoformat():
        raise CivilDateError("conversion input must be an exact YYYY-MM-DD without a time")
    day_number = _civil_date_to_day_number(source, from_calendar)
    to_calendar = "julian" if from_calendar == "gregorian" else "gregorian"
    equivalent = (
        _day_number_to_julian(day_number)
        if to_calendar == "julian"
        else _day_number_to_gregorian(day_number)
    )
    _validate_civil_date(equivalent, to_calendar)
    return {
        "status": "EXACT_CALENDAR_CONVERSION",
        "input": {"calendar": from_calendar, "date": source.isoformat()},
        "equivalent": {"calendar": to_calendar, "date": equivalent.isoformat()},
        "warning": (
            "Calendar arithmetic does not establish that both dates were written in the act; "
            "preserve the literal source and mark derived dates explicitly."
        ),
    }


def _relative_phrase_spec(literal_phrase: Any) -> tuple[str, int] | None:
    if not isinstance(literal_phrase, str):
        return None
    for pattern, family, offset_days in _RELATIVE_PHRASES:
        if pattern.match(literal_phrase):
            return family, offset_days
    return None


def _relative_report(
    *,
    literal_phrase: Any,
    phrase_family: str | None,
    offset_days: int | None,
    anchor: Mapping[str, str] | None,
    resolved_value: Mapping[str, Any] | None,
    reason: str | None,
    details: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "status": "RESOLVED" if reason is None else "UNRESOLVED",
        "phrase_family": phrase_family,
        "literal_phrase": literal_phrase,
        "literal_phrase_unchanged": True,
        "offset_days": offset_days,
        "anchor": dict(anchor) if anchor is not None else None,
        "resolved_value": dict(resolved_value) if resolved_value is not None else None,
        "reason": reason,
        "details": list(details),
        "warning": _RELATIVE_DATE_WARNING,
    }


def _date_for_day_number(day_number: int, calendar: str) -> CivilDate:
    result = (
        _day_number_to_gregorian(day_number)
        if calendar == "gregorian"
        else _day_number_to_julian(day_number)
    )
    return _validate_civil_date(result, calendar)


def resolve_relative_date_phrase(
    literal_phrase: Any,
    registration_value: Any,
    *,
    anchor_state: str = "PRESENT",
    anchor_confidence: str = "PROBABLE",
) -> dict[str, object]:
    """Resolve two attested Russian relative-date families from an explicit usable anchor."""

    phrase_spec = _relative_phrase_spec(literal_phrase)
    if phrase_spec is None:
        return _relative_report(
            literal_phrase=literal_phrase,
            phrase_family=None,
            offset_days=None,
            anchor=None,
            resolved_value=None,
            reason="UNSUPPORTED_PHRASE",
        )
    phrase_family, offset_days = phrase_spec
    common = {
        "literal_phrase": literal_phrase,
        "phrase_family": phrase_family,
        "offset_days": offset_days,
        "anchor": None,
        "resolved_value": None,
    }
    if anchor_state != "PRESENT":
        return _relative_report(
            **common,
            reason="ANCHOR_NOT_PRESENT",
            details=(f"anchor observation_state is {anchor_state!r}",),
        )
    if anchor_confidence == "UNCLEAR":
        return _relative_report(
            **common,
            reason="ANCHOR_UNCLEAR",
            details=("anchor confidence is UNCLEAR",),
        )
    if anchor_confidence not in _USABLE_ANCHOR_CONFIDENCE:
        return _relative_report(
            **common,
            reason="ANCHOR_CONFIDENCE_UNSUPPORTED",
            details=(f"anchor confidence is {anchor_confidence!r}",),
        )
    if registration_value is None or registration_value == {}:
        return _relative_report(**common, reason="ANCHOR_MISSING")
    if not isinstance(registration_value, Mapping):
        reason = (
            "ANCHOR_CALENDAR_UNSPECIFIED"
            if isinstance(registration_value, str)
            else "ANCHOR_INVALID"
        )
        return _relative_report(
            **common,
            reason=reason,
            details=("anchor must declare a julian or gregorian calendar",),
        )

    calendar_keys = [calendar for calendar in CALENDARS if calendar in registration_value]
    if not calendar_keys:
        reason = "ANCHOR_CALENDAR_UNSPECIFIED" if "date" in registration_value else "ANCHOR_MISSING"
        return _relative_report(
            **common,
            reason=reason,
            details=("anchor must declare a julian or gregorian calendar",),
        )
    if "date" in registration_value:
        return _relative_report(
            **common,
            reason="ANCHOR_INVALID",
            details=("generic date cannot be combined with explicit calendar anchors",),
        )

    parsed: dict[str, CivilDate] = {}
    errors: list[str] = []
    for calendar in calendar_keys:
        try:
            raw_value = registration_value[calendar]
            parsed_value = parse_civil_date(
                raw_value,
                calendar=calendar,
            )
            if raw_value != parsed_value.isoformat():
                raise CivilDateError("anchor must be an exact YYYY-MM-DD without a time")
            parsed[calendar] = parsed_value
        except CivilDateError as error:
            errors.append(f"{calendar}: {error}")
    if errors:
        return _relative_report(
            **common,
            reason="ANCHOR_INVALID",
            details=tuple(errors),
        )

    normalized_anchor = {
        calendar: parsed[calendar].isoformat() for calendar in CALENDARS if calendar in parsed
    }
    if len(parsed) == 2:
        gregorian_day = _civil_date_to_day_number(parsed["gregorian"], "gregorian")
        julian_day = _civil_date_to_day_number(parsed["julian"], "julian")
        if gregorian_day != julian_day:
            expected_gregorian = _day_number_to_gregorian(julian_day).isoformat()
            expected_julian = _day_number_to_julian(gregorian_day).isoformat()
            return _relative_report(
                literal_phrase=literal_phrase,
                phrase_family=phrase_family,
                offset_days=offset_days,
                anchor=normalized_anchor,
                resolved_value=None,
                reason="ANCHOR_CALENDAR_MISMATCH",
                details=(
                    f"julian anchor converts to gregorian {expected_gregorian}",
                    f"gregorian anchor converts to julian {expected_julian}",
                    "neither anchor side was selected",
                ),
            )

    source_calendar = calendar_keys[0]
    source_day = _civil_date_to_day_number(parsed[source_calendar], source_calendar)
    target_day = source_day + offset_days
    try:
        resolved = {
            calendar: _date_for_day_number(target_day, calendar).isoformat()
            for calendar in CALENDARS
            if calendar in parsed
        }
    except CivilDateError as error:
        return _relative_report(
            literal_phrase=literal_phrase,
            phrase_family=phrase_family,
            offset_days=offset_days,
            anchor=normalized_anchor,
            resolved_value=None,
            reason="RESULT_OUT_OF_RANGE",
            details=(str(error),),
        )
    resolved["resolved_from_relative_phrase"] = True
    return _relative_report(
        literal_phrase=literal_phrase,
        phrase_family=phrase_family,
        offset_days=offset_days,
        anchor=normalized_anchor,
        resolved_value=resolved,
        reason=None,
    )


def _calendar_dates(value: Any) -> dict[str, CivilDate]:
    if isinstance(value, str):
        try:
            return {"unspecified": parse_civil_date(value, calendar="gregorian")}
        except CivilDateError:
            return {}
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, CivilDate] = {}
    for calendar in CALENDARS:
        if calendar not in value:
            continue
        try:
            result[calendar] = parse_civil_date(value[calendar], calendar=calendar)
        except CivilDateError:
            continue
    if not result and "date" in value:
        try:
            result["unspecified"] = parse_civil_date(value["date"], calendar="gregorian")
        except CivilDateError:
            pass
    return result


def validate_relative_date_consistency(record: Any) -> tuple[ValidationFinding, ...]:
    """Flag a stored event date that contradicts an exactly resolvable source phrase."""

    observations = observations_of(record)
    registration = observations.get("registration_date")
    event = observations.get("event_date")
    if not isinstance(registration, Mapping) or not isinstance(event, Mapping):
        return ()
    if (
        event.get("observation_state") != "PRESENT"
        or event.get("confidence") not in _USABLE_ANCHOR_CONFIDENCE
    ):
        return ()

    resolution = resolve_relative_date_phrase(
        event.get("original_script"),
        registration.get("value"),
        anchor_state=str(registration.get("observation_state", "")),
        anchor_confidence=str(registration.get("confidence", "")),
    )
    if resolution["status"] != "RESOLVED":
        return ()
    expected_value = resolution.get("resolved_value")
    stored_value = event.get("value")
    if not isinstance(expected_value, Mapping) or not isinstance(stored_value, Mapping):
        # A scalar stored date does not say which civil calendar its day belongs to.
        return ()

    expected_dates = _calendar_dates(expected_value)
    stored_dates = _calendar_dates(stored_value)
    shared_calendars = [
        calendar
        for calendar in CALENDARS
        if calendar in expected_dates and calendar in stored_dates
    ]
    mismatches = {
        calendar: {
            "stored": stored_dates[calendar].isoformat(),
            "expected": expected_dates[calendar].isoformat(),
        }
        for calendar in shared_calendars
        if stored_dates[calendar] != expected_dates[calendar]
    }
    if not mismatches:
        return ()

    rendered = "; ".join(
        f"{calendar} stored {values['stored']}, expected {values['expected']}"
        for calendar, values in mismatches.items()
    )
    return (
        ValidationFinding(
            code="RELATIVE_DATE_MISMATCH",
            message=(
                "event_date contradicts the exact "
                f"{resolution['phrase_family']} resolution from registration_date: "
                f"{rendered}. Neither source field was rewritten."
            ),
            record_ids=(record_id_of(record),),
            field_paths=("registration_date", "event_date"),
            evidence={
                "literal_phrase": resolution["literal_phrase"],
                "phrase_family": resolution["phrase_family"],
                "offset_days": resolution["offset_days"],
                "anchor": resolution["anchor"],
                "stored_value": stored_value,
                "expected_value": expected_value,
                "mismatches": mismatches,
            },
        ),
    )


def _date_value_errors(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        try:
            parse_civil_date(value, calendar="gregorian")
        except CivilDateError as error:
            return (str(error),)
        return ()
    if not isinstance(value, Mapping):
        return ("date value must be an ISO string or calendar object",)

    date_keys = [key for key in (*CALENDARS, "date") if key in value]
    if not date_keys:
        return ("calendar object must contain gregorian, julian, or date",)
    errors: list[str] = []
    for key in date_keys:
        calendar = key if key in CALENDARS else "gregorian"
        try:
            parse_civil_date(value[key], calendar=calendar)
        except CivilDateError as error:
            errors.append(f"{key}: {error}")
    return tuple(errors)


def validate_date_value_shapes(record: Any) -> tuple[ValidationFinding, ...]:
    """Flag confident core dates that are not complete normalized ISO values."""

    observations = observations_of(record)
    findings: list[ValidationFinding] = []
    for path, evidence in observations.items():
        if not isinstance(evidence, Mapping):
            continue
        if (
            evidence.get("observation_state") != "PRESENT"
            or evidence.get("confidence") == "UNCLEAR"
        ):
            continue
        value = evidence.get("value")
        explicit_calendar_object = isinstance(value, Mapping) and any(
            key in value for key in (*CALENDARS, "date")
        )
        if path not in _DATE_FIELDS and not explicit_calendar_object:
            continue
        errors = _date_value_errors(value)
        if not errors:
            continue
        findings.append(
            ValidationFinding(
                code="DATE_VALUE_INVALID",
                message=(
                    f"{path} is PRESENT but cannot be validated as a complete normalized "
                    f"ISO date: {'; '.join(errors)}."
                ),
                record_ids=(record_id_of(record),),
                field_paths=(str(path),),
                evidence={"errors": errors},
            )
        )
    return tuple(findings)


def _day_number(value: CivilDate, calendar: str) -> int:
    declared = "gregorian" if calendar == "unspecified" else calendar
    return _civil_date_to_day_number(value, declared)


def validate_registration_event_order(record: Any) -> tuple[ValidationFinding, ...]:
    """Flag a registration date earlier than the event date."""

    observations = observations_of(record)
    registration_evidence = observations.get("registration_date")
    event_evidence = observations.get("event_date")
    if not isinstance(registration_evidence, Mapping) or not isinstance(event_evidence, Mapping):
        return ()
    if (
        registration_evidence.get("observation_state") != "PRESENT"
        or registration_evidence.get("confidence") == "UNCLEAR"
        or event_evidence.get("observation_state") != "PRESENT"
        or event_evidence.get("confidence") == "UNCLEAR"
    ):
        return ()
    registration = _calendar_dates(registration_evidence.get("value"))
    event = _calendar_dates(event_evidence.get("value"))
    if not registration or not event:
        return ()

    shared = [
        calendar
        for calendar in (*CALENDARS, "unspecified")
        if calendar in registration and calendar in event
    ]
    if shared:
        registration_calendar = event_calendar = shared[0]
    elif set(registration) <= set(CALENDARS) and set(event) <= set(CALENDARS):
        registration_calendar = next(calendar for calendar in CALENDARS if calendar in registration)
        event_calendar = next(calendar for calendar in CALENDARS if calendar in event)
    else:
        return ()

    registration_date = registration[registration_calendar]
    event_date = event[event_calendar]
    if _day_number(registration_date, registration_calendar) >= _day_number(
        event_date, event_calendar
    ):
        return ()
    representation = (
        registration_calendar
        if registration_calendar == event_calendar
        else f"{registration_calendar}-to-{event_calendar}"
    )
    return (
        ValidationFinding(
            code="REGISTRATION_BEFORE_EVENT",
            message=(
                f"Registration date {registration_date.isoformat()} precedes event date "
                f"{event_date.isoformat()} in the {representation} representation."
            ),
            record_ids=(record_id_of(record),),
            field_paths=("registration_date", "event_date"),
            evidence={
                "calendar": representation,
                "registration_date": registration_date.isoformat(),
                "event_date": event_date.isoformat(),
            },
        ),
    )


def validate_dual_date_gaps(record: Any) -> tuple[ValidationFinding, ...]:
    """Flag Julian/Gregorian labels that do not identify the same civil day."""

    observations = observations_of(record)
    findings: list[ValidationFinding] = []
    for path, evidence in observations.items():
        if not isinstance(evidence, Mapping):
            continue
        if (
            evidence.get("observation_state") != "PRESENT"
            or evidence.get("confidence") == "UNCLEAR"
        ):
            continue
        dates = _calendar_dates(evidence.get("value"))
        if "gregorian" not in dates or "julian" not in dates:
            continue
        gregorian = dates["gregorian"]
        julian = dates["julian"]
        gregorian_day = _civil_date_to_day_number(gregorian, "gregorian")
        julian_day = _civil_date_to_day_number(julian, "julian")
        if gregorian_day == julian_day:
            continue
        expected_gregorian = _day_number_to_gregorian(julian_day)
        expected_julian = _day_number_to_julian(gregorian_day)
        findings.append(
            ValidationFinding(
                code="DUAL_DATE_GAP",
                message=(
                    f"{path} pairs Julian {julian.isoformat()} with Gregorian "
                    f"{gregorian.isoformat()}, but they identify different civil days. "
                    f"The Julian value converts to Gregorian {expected_gregorian.isoformat()}; "
                    f"the Gregorian value converts to Julian {expected_julian.isoformat()}. "
                    "Neither side was selected."
                ),
                record_ids=(record_id_of(record),),
                field_paths=(str(path),),
                evidence={
                    "gregorian": gregorian.isoformat(),
                    "julian": julian.isoformat(),
                    "expected_gregorian_from_julian": expected_gregorian.isoformat(),
                    "expected_julian_from_gregorian": expected_julian.isoformat(),
                    "calendar_day_offset": gregorian_day - julian_day,
                },
            )
        )
    return tuple(findings)


def validate_dates(record: Any) -> tuple[ValidationFinding, ...]:
    """Run all date validators without mutating the record."""

    return (
        validate_date_value_shapes(record)
        + validate_registration_event_order(record)
        + validate_dual_date_gaps(record)
        + validate_relative_date_consistency(record)
    )
