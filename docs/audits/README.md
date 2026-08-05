# Audit records — why this directory is otherwise empty

**This file is not an audit. It contains no findings.** It exists so that a
reader who follows a reference into `docs/audits/` learns where that record
actually is, instead of finding nothing and assuming the reference is a
mistake.

Some frozen artifacts in this repository pin audit records that are **owner-held
internal records, not published in this research edition**. The references are
real and deliberate; the files are not distributed.

## Currently referenced, not published

| Referenced as | Referenced by |
|---|---|
| `docs/audits/gold-attestation-audit-2026-07-29.json` | `training/plan-0001.json` (`inputs.gold_attestation_audit`), `training/readiness-0001.json` (`input_pins.gold_attestation_audit`) |
| `docs/audits/gold-attestation-audit-2026-07-29.md` | `docs/p2-baseline-addendum.md`, which already labels it "internal audit record; not published in this repository" |

The `.json` is the machine-readable artifact consumed by the training preflight;
the `.md` is the narrative record. Neither is in this repository.

## What is verifiable without them

`training/readiness-0001.json` pins that audit **by SHA-256**, not by path alone:

```
"gold_attestation_audit": {
  "path": "…/docs/audits/gold-attestation-audit-2026-07-29.json",
  "sha256": "64be4f1f968326f712b4d23922d0eb260aff7405c2d5be4316a48bad17e93128"
}
```

So the pin is content-addressed. Anyone who is given the file can confirm it is
the exact artifact the gate was measured against, regardless of where it sits on
disk. What cannot be done from a clone alone is re-running the gate — see the
note on owner-local input paths in [REPRODUCIBILITY.md](../../REPRODUCIBILITY.md).

## The finding that matters, and where it is already stated

The audit's headline result is not hidden behind the unpublished file. It is
recorded in [docs/p2-baseline-addendum.md](../p2-baseline-addendum.md): the
gold-attestation re-audit found **0/36** acts with complete per-field image
references and dated human attestations, which is why the 1.30% filiation
figure is retained as a research-derived before-picture and must not be
described as publication-grade image-verified accuracy.

If this directory ever gains a real audit file, it belongs beside this note, and
this table should shrink accordingly.
