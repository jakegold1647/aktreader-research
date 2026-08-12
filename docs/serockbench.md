# SerockBench

SerockBench is AKTREADER’s scan-backed evaluation contract for uncertainty-honest civil-register
extraction. It is not a leaderboard built from vendor OCR claims.

## Corpus and isolation

- 36 human-verified acts: 29 Serock and 7 Pułtusk.
- 21 clerk-year groups.
- Russian-language births, marriages, and deaths.
- Every gold record is evaluation-only.
- `gold/clerk_year_holdout.json` forbids training overlap by clerk-year, not merely by act ID.

Before scoring, the harness rejects duplicate gold record IDs and duplicate record or clerk-year
IDs in the holdout manifest. Equality checks use sets only after uniqueness is established, so a
repeated gold row cannot receive extra metric weight while appearing to match the holdout.

Twenty-four gold records currently have localized scan artifacts. Twelve remain acquisition
targets; `examples/p2-baseline.want-list.json` maps five Serock gaps to exact zespół 318/0826d
units and ranges with `SOURCE_OBJECT_415`, while seven Pułtusk records fail closed pending their
separate collection map. Until those inputs are localized, a run’s maximum honest prediction
coverage is 24/36.

## Headline metrics

- **Filiation field exact match:** exact parentage-field agreement, including mother’s maiden
  name and typed observation state.
- **Filiation act exact match:** all evaluated filiation fields in an act must match.
- **Wrong-but-CONFIDENT:** incorrect CONFIDENT assertions divided by evaluated CONFIDENT
  assertions. Zero CONFIDENT assertions produce `N/A`, never a passing zero.
- **Calibration:** correctness reported separately for CONFIDENT, PROBABLE, and UNCLEAR.
- **Observation-state accuracy:** exact distinction among a value, `ABSENT_ON_FORM`, `BLANK`,
  `STATED_UNKNOWN`, and `ILLEGIBLE`.
- **Abstention rate:** the fraction of evaluated fields for which the Reader declines to assert a
  resolved value.

The P2 targets are at least 90% filiation exact match and below 2% wrong-but-CONFIDENT.

## Why wrong-but-confident leads

Genealogical extraction is asymmetric: an honest unresolved reading invites review, while a
plausible invented parent can corrupt a family graph. Wave 001 demonstrated the mechanism when a
prompt prior manufactured dual dates. Wave 002 caught a line-broken `Герш-/вельдъ` surname that
one Reader split into a phantom spouse; that one parse error cascaded through sex, age,
filiation, and survivor fields. Blind disagreement intercepted both failure classes before gold.

## Reproducing a report

```powershell
python -m aktreader eval `
  --predictions .\runs\p2-local-baseline\predictions `
  --gold-dir .\gold\acts `
  --holdout .\gold\clerk_year_holdout.json `
  --output .\runs\p2-local-baseline\serockbench.json
```

Preserve predictions, checkpoint, runtime fingerprint, prompt/schema hashes, and the generated
report together. Missing predictions reduce coverage; they are never backfilled from gold. Each
supplied prediction must be one UTF-8 JSON object with a non-empty string `record_id`. Duplicate
object keys, non-standard numbers such as `NaN`, and duplicate record IDs fail the run instead of
producing an ambiguous report.
