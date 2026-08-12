# Civil-date conversion and validation

AKT Reader treats a normalized date and the words physically written in an act as different
evidence. The normalized value supports mechanical comparison. `original_script` preserves the
literal Russian or Polish wording, including relative phrases and dual day-words.

## Convert one known calendar date

`date-convert` performs local, deterministic civil-calendar arithmetic:

```powershell
aktreader date-convert 1890-01-01 --from-calendar julian
aktreader date-convert 1900-02-29 --from-calendar julian
```

The first command returns Gregorian `1890-01-13`. The second accepts 29 February 1900 in the
Julian calendar and returns Gregorian `1900-03-13`; that date is invalid when declared
Gregorian. Conversion input must be exactly `YYYY-MM-DD` so the command never discards a time or
free-text qualifier.

The result says `EXACT_CALENDAR_CONVERSION`, but this is exact arithmetic only. It does not prove
that both dates appear in the ink. A derived date must remain marked as derived, and a
single-dated act must not be rewritten as if it contained a dual date.

## Normalized value contract

The date validators accept a complete ISO date or datetime:

```json
"1890-01-13"
```

or an explicit calendar object:

```json
{
  "julian": "1890-01-01",
  "gregorian": "1890-01-13",
  "gregorian_derived": true
}
```

Times may follow a normalized date in valid ISO form, for example
`1890-01-13T12:00:00`. Prose such as `1890-01-13, hour not stated` and relative placeholders
such as `same day` are not normalized dates. A confident `registration_date` or `event_date`
with such a value receives `DATE_VALUE_INVALID` instead of silently bypassing validation.
An `UNCLEAR` value is not mechanically decided.

When this contract was introduced, a survey of the live top-level Reader A/Reader B labels
surfaced five legacy Reader A fields that had stored phrases such as `same day, 05:00`,
`1890-07-21 ~13:00`, or `hour not stated` in the normalized value. Those frozen source labels
were not rewritten. New consensus builds carry `DATE_VALUE_INVALID` findings so the prose cannot
quietly pass as a validated date.

Relative source phrases remain literal evidence. For example, `вчерашняго числа` (“yesterday”)
may be resolved only when the registration date is usable; the normalized event date carries the
resolved ISO value while `original_script` retains the phrase. This module does not parse Russian
or Polish number-words and does not guess through an unclear anchor date.

## Exact dual-calendar check

`DUAL_DATE_GAP` now compares absolute civil days, not a month-level “12 days before 1900 / 13
days after” shortcut. The shortcut fails during the 1900 transition because the Julian calendar
has 29 February 1900 and the Gregorian calendar does not. Exact examples are:

| Julian | Gregorian |
| --- | --- |
| `1900-02-16` | `1900-02-28` |
| `1900-02-17` | `1900-03-01` |
| `1900-02-28` | `1900-03-12` |
| `1900-02-29` | `1900-03-13` |
| `1900-03-01` | `1900-03-14` |

The implementation uses integer calendar/day-number transforms. The calendrical rules and the
Fliegel–Van Flandern conversion algorithms are documented by the
[U.S. Naval Observatory](https://aa.usno.navy.mil/faq/JD_formula); its
[calendar notes](https://aa.usno.navy.mil/faq/calendars) explain that 1900 is not a Gregorian
leap year.

`REGISTRATION_BEFORE_EVENT` also compares a Gregorian-only value with a Julian-only value when
both calendars are explicit. When a dual pair disagrees, the finding reports both
Gregorian-from-Julian and Julian-from-Gregorian equivalents and selects neither. Findings never
mutate the record or repair a date automatically.
