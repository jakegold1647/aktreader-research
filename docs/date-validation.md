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

## Audit label files without rewriting them

`date-audit` exposes the same date validators as a deterministic, read-only corpus survey:

```powershell
aktreader date-audit labels\readerB
aktreader date-audit labels\readerA
aktreader date-audit labels\readerA\serock-1890-death-16.json
```

An explicit file must be JSON. A directory contributes only its top-level JSON files unless
`--recursive` is supplied. Results are sorted by resolved path, and overlapping arguments such
as a directory plus one file inside it are rejected instead of double-counted. JSON sidecars
with neither `observations` nor `fields` are reported as `SKIPPED_NON_LABEL`; malformed JSON or
malformed label containers are `PARSE_FAIL`. Every readable file carries its SHA-256 in the
report.

| Exit | Report status | Meaning |
| ---: | --- | --- |
| 0 | `PASS` | Every recognized label was readable and produced no date finding. |
| 1 | `FINDINGS` | The audit completed and at least one label produced a finding. |
| 2 | `INCOMPLETE` | A file could not be parsed, no label was recognized, or the input selection was invalid. |

The committed top-level corpus is a regression fixture for the command. Reader B has 27 labels
and passes with no findings. Reader A has 59 labels plus one non-label index sidecar and reports
five `DATE_VALUE_INVALID` findings across four labels. This is expected historical evidence,
not a prompt to edit the frozen labels. The finding report preserves each validator message,
record and field paths, severity, confidence-blocking flag, and evidence object.

Relative source phrases remain literal evidence. For example, `вчерашняго числа` (“yesterday”)
may be resolved only when the registration date is usable; the normalized event date carries the
resolved ISO value while `original_script` retains the phrase. The narrow resolver below does not
parse Russian or Polish number-words and does not guess through an unclear anchor date.

## Resolve an attested relative phrase

`date-resolve-relative` recognizes two exact, start-anchored historical phrase families:

| Literal prefix | Family | Operation |
| --- | --- | --- |
| `сего числа` | `SAME_DAY` | Keep the anchor civil day |
| `вчерашняго числа` | `PREVIOUS_DAY` | Subtract one civil day |

Field-level text after that exact prefix is preserved but not interpreted. Thus
`сего числа въ пять часовъ утра` can resolve the date, while the utility does not turn the
Russian time clause into `05:00`.

Supply at least one explicit calendar anchor:

```powershell
aktreader date-resolve-relative "вчерашняго числа" `
  --julian 1890-02-07 `
  --gregorian 1890-02-19
```

A resolved report exits 0 and returns the literal phrase unchanged, `offset_days`, normalized
anchor dates, and a `resolved_value` marked `resolved_from_relative_phrase`. A refusal exits 1
but still emits JSON on stdout. Stable refusal reasons are:

| Reason | Meaning |
| --- | --- |
| `UNSUPPORTED_PHRASE` | The supplied field does not begin with one of the two exact forms. |
| `ANCHOR_MISSING` | No explicit registration anchor was supplied. |
| `ANCHOR_NOT_PRESENT` | The registration observation state is not `PRESENT`. |
| `ANCHOR_UNCLEAR` | The registration confidence is `UNCLEAR`. |
| `ANCHOR_CONFIDENCE_UNSUPPORTED` | The confidence state is not usable under this contract. |
| `ANCHOR_CALENDAR_UNSPECIFIED` | A scalar or generic `date` was supplied without naming its calendar. |
| `ANCHOR_INVALID` | A declared date is malformed, timed, or mixes generic and explicit calendar forms. |
| `ANCHOR_CALENDAR_MISMATCH` | Supplied Julian and Gregorian anchors identify different civil days. |
| `RESULT_OUT_OF_RANGE` | The shifted date falls outside supported four-digit civil years. |

Anchor dates must be exact `YYYY-MM-DD` values; registration times are irrelevant to the event
day and are not silently discarded. A consistent dual anchor resolves both calendars. An
inconsistent pair reports both counterfactual conversions and selects neither. Near-matches,
modernized spelling, uncertain bracketed text, line-break dehyphenation, Polish forms, and
written number-words are unsupported rather than fuzzily normalized.

The committed fixtures
[`serock-1890-death-4`](../labels/readerB/serock-1890-death-4.json) and
[`serock-1890-death-16`](../labels/readerA/serock-1890-death-16.json) exercise the positive and
unclear-anchor paths respectively. A corpus regression also replays all 19 currently usable
top-level Reader B relative-date fixtures and reproduces their normalized calendar values. The
frozen labels remain unchanged.

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
