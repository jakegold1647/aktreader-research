# Merging two blind reader labels

`aktreader consensus-merge` combines exactly two independently produced reader
labels for the same record into one consensus record. It sits between blind
reading and adjudication: reading produces labels, this command finds where the
readers disagree, and [`adjudicate`](adjudication.md) turns the residue into
human questions.

```powershell
aktreader consensus-merge `
  labels\readerA\serock-1877-birth-1.json `
  labels\readerB\serock-1877-birth-1.json `
  --output labels\consensus\serock-1877-birth-1.json
```

## Arguments

| Argument | Required | Meaning |
|---|---|---|
| `left_label` | yes | first blind reader label (positional) |
| `right_label` | yes | second blind reader label (positional) |
| `--output` | yes | where the consensus record is written |
| `--schema` | no | record schema; defaults to `schemas/act-record-2.0.0.schema.json` |
| `--replace-existing` | no | permit atomic replacement of an existing output |

Exactly two labels. There is no variadic form, because the merge rules below are
defined pairwise and a third reader is handled by arbitration, not by merging.

## What it refuses to do

The command fails closed before reading anything, with a configuration error, if:

- either path is not a file, or the two paths are the same file;
- the output path equals either source label — it will not overwrite a reader
  label, which is append-only;
- the output path equals the schema path;
- the output already exists and `--replace-existing` was not passed.

Labels are loaded through the grounded loader, so a label that fails the
groundedness contract stops the merge rather than flowing into consensus.

## The merge rule: agreement is not truth

Field by field, over the union of both readers' observations:

- **Either reader did not report the field** → `UNCLEAR`. Missing output is
  explicitly not treated as a blank.
- **Both readers agree** on observation state, value, and alternatives, and
  their `original_script` values do not conflict → an agreement field.
- **Anything else** → `UNCLEAR`, carrying a reason that names which axis
  disagreed: observation state, value, alternatives, or original script.

Agreement is graded `PROBABLE`, never `CONFIDENT`, for a `PRESENT` field. A
field is only marked `CONFIDENT_ELIGIBLE` when the pair is fully verified *and*
the original-script binding matched; otherwise the cap stays `PROBABLE`. Two
machines agreeing is a `SILVER`/`PROBABLE` signal, not human-verified gold — the
same rule stated in [CONTRIBUTING.md](../CONTRIBUTING.md).

Two blind readers can also share a blind spot, so agreement between them is
retained as a documented limitation rather than treated as corroboration.

## Validators run during the merge

The merge collects findings from date validation, formula-position validation on
each reader independently, and cross-reader groundedness. These are attached to
the consensus record as findings; they do not silently alter any value.

## Output

An immutable consensus record at `--output`, written against the schema, plus a
JSON summary on stdout:

| Field | Meaning |
|---|---|
| `record_id` | the merged record |
| `source_label_ids` | the two contributing reader label ids |
| `field_count` | fields in the merged record |
| `dual_disagreement_count` | fields where both readers reported and disagreed |
| `validator_finding_count` | findings raised by the validators |
| `groundedness_incident_count` | cross-reader groundedness incidents |
| `arbitration_request_count` | fields escalated for arbitration |
| `quality_metrics` | paired quality metrics for the two labels |

`arbitration_request_count` is the number that drives the next step: those are
the fields a third reader or a human adjudication packet has to settle.

## Where it sits in the wave workflow

```
blind read (Reader A)  ─┐
                        ├─→ consensus-merge ─→ consensus record ─→ adjudicate ─→ human answers
blind read (Reader B)  ─┘                          │
                                                   └─→ arbitration requests (Reader C / expert)
```

It never edits a reader label, and it never promotes anything to gold.
