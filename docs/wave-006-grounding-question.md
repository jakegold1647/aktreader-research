# Wave 006 grounding-gate question

**Status: OPEN — awaiting maintainer decision. This document decides nothing.**

**Recorded:** 2026-08-04

The frozen wave-006 Reader A labels (Serock 1877 births, acts 1–8) fail the v1.4 grounded
gate. The labels are frozen evidence and were not edited; the gate is the frozen contract and
was not relaxed. This brief enumerates exactly what fails, under which contract clause, and
the two resolution paths the project's own rules permit. Choosing between them is a
maintainer decision.

## Exact failure inventory

`aktreader label-validate --report` on the eight frozen labels returns status `UNGROUNDED`
for all eight, with nine violating observations. Every violation carries the single code
`PRESENT_RU_ORIGINAL_SCRIPT_HAS_NO_CYRILLIC`. No wave-006 observation fails the
transcription-substring gate: each disputed excerpt does occur verbatim in that label's
continuous transcription.

| Act | Field | `original_script` | `value` | Grade |
|---:|---|---|---|---|
| 1 | `act_number_on_page` | `№ 1` | `1` | PROBABLE |
| 2 | `act_number_on_page` | `№ 2` | `2` | PROBABLE |
| 3 | `act_number_on_page` | `№ 3` | `3` | PROBABLE |
| 4 | `act_number_on_page` | `№ 4` | `4` | PROBABLE |
| 5 | `act_number_on_page` | `№ 5` | `5` | PROBABLE |
| 6 | `act_number_on_page` | `№ 6` | `6` | PROBABLE |
| 6 | `declarant.autograph` | `Josek Peniek` | `[unclear: Josek Peniek/Josek Peniez]` | UNCLEAR |
| 7 | `act_number_on_page` | `№ 7` | `7` | PROBABLE |
| 8 | `act_number_on_page` | `№ 8` | `8` | PROBABLE |

Regenerate from the repository root (exits non-zero while any label fails the gate):

```powershell
.\.venv\Scripts\python.exe -m aktreader label-validate --report `
  .\labels\readerA\serock-1877-birth-1.json .\labels\readerA\serock-1877-birth-2.json `
  .\labels\readerA\serock-1877-birth-3.json .\labels\readerA\serock-1877-birth-4.json `
  .\labels\readerA\serock-1877-birth-5.json .\labels\readerA\serock-1877-birth-6.json `
  .\labels\readerA\serock-1877-birth-7.json .\labels\readerA\serock-1877-birth-8.json
```

## Governing contract clauses

- Prompt v1.4.0, grounding contract: "For a number or symbol on a Russian-language act,
  include enough adjacent inked wording that the supporting excerpt contains Cyrillic. If no
  supporting excerpt can be copied, do not assert PRESENT; use the honest typed state that
  describes the evidence." (`prompts/reader_prompt-v1.4.0.md`)
- Mechanical gate 1 of the wave-005 remediation: every PRESENT observation on a
  Russian-language act must carry Cyrillic in `original_script`
  ([P2 baseline addendum](p2-baseline-addendum.md)), enforced fail-closed by
  `PRESENT_RU_ORIGINAL_SCRIPT_HAS_NO_CYRILLIC` in `src/aktreader/grounding.py` and by the
  `x-aktreader-grounding-contract` declaration in both v1.4 schemas.
- CONTRIBUTING: "Never edit a frozen Reader label in place; add a new attributable artifact."

## Why the two failing fields differ in kind

- **`act_number_on_page` (8 of 9 violations).** The recorded ink is the margin numeral
  `№ N`. Whether adjacent Cyrillic wording exists to quote (for example the act's opening
  line beside the margin number) is a page fact that only a re-examination of the scans can
  establish; this brief does not assert it either way.
- **`declarant.autograph` (act 6).** The recorded ink is a Latin-script signature on a
  Russian-language act. If the declarant genuinely signed in Latin script, no
  Cyrillic-containing excerpt of the signature itself can exist; the clause's fallback
  ("use the honest typed state") is the prompt's own answer for that case, but applying it
  retroactively to a frozen label is exactly the step that requires a new artifact.

## Resolution path 1 — errata re-pass (new attributable artifacts)

Leave the frozen labels untouched. Commission a fresh blind pass (or the restructured
protocol's same-vendor verification pass) over the eight acts whose output either quotes
adjacent Cyrillic for each margin numeral or records the prompt's mandated non-PRESENT typed
state where no Cyrillic-containing excerpt exists on the page.

- Keeps the contract uniform: no grandfathering, matching the wave-001 precedent where
  frozen pre-contract labels fail the gate by design.
- Produces gate-passing wave-006 evidence eligible for verification and consensus.
- Costs a reader session and coordinator time.
- Carries the wave-005 supervisory hazard: the re-pass must be framed as fresh blind
  evidence, never as "make the gate pass," or coverage pressure can again convert
  abstention into fabrication.

## Resolution path 2 — explicit contract decision for inherently non-Cyrillic ink

Amend the contract in a new frozen version (prompt v1.5, schema contract bump, validator
change, tests): scope the Cyrillic requirement so that fields whose page ink is inherently
non-Cyrillic — margin numerals recorded as `№ N`, Latin-script autographs — satisfy the gate
through the (retained) transcription-substring requirement alone, or through a new
explicitly typed evidence state.

- Acknowledges a physical reality of the sources: some genuine ink on a Russian-language
  act contains no Cyrillic.
- Weakens, by exactly the scoped amount, the anti-fabrication gate purchased with the
  measured wave-005 incident; the scoping must be narrow enough that it cannot be reached
  by a fabricated name or date.
- Requires new pinned digests and a documented protocol correction, like the v1.1 and v1.2
  precedents.
- Would retroactively make the frozen wave-006 labels pass as stored. That is a deliberate
  departure from the no-grandfathering precedent and should be decided explicitly, not
  inherited as a side effect.

## Non-decisions

This brief does not edit any frozen label, does not change the validator or schemas, and
does not recommend a path. Until the maintainer decides, wave-006 Reader A output remains
loadable audit evidence that cannot enter consensus, silver, or training, exactly as the
guards require.
