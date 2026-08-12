# Where an outside contributor can actually help

Read [CONTRIBUTING.md](../CONTRIBUTING.md) first — it is the rules. This file is
the opposite: a list of work that is genuinely open.

## The honest constraint, stated up front

Most of this project's remaining work is gated on material an outsider does not
have. The register scans are private source material and are never redistributed
(see [DATA_GOVERNANCE.md](../DATA_GOVERNANCE.md)); the model bytes are fetched by
the owner outside the application; the human-review inputs under `human_check/`
are owner-local and are not in the repository, which is why
`python -m aktreader adjudicate --wave 006` exits 2 on a fresh clone. That is
correct fail-closed behavior, not a bug.

So the backlog in `labels/consensus/RESCAN_QUEUE.md` and
`training/readiness-0001.json` — the things the project most needs — are mostly
not delegable. Rather than list them as if they were, here is what genuinely is.

Everything below runs from a clean clone with `pip install -e ".[dev]"` and
needs no scan, no model, and no network.

## 1. The variant bridge (P4) — the best entry point

**Current status:** four separately usable slices now ship. `variant-key`
generates branching Daitch–Mokotoff keys. `variant-propose` combines those keys
with source-attributed forms, explicit variants, and ruled-out near-misses while
preserving the literal query. `variant-batch` applies that contract to stable,
typed CSV rows and emits a source-hashed, schema-valid artifact.
`variant-batch-verify` independently regenerates and compares a stored artifact.
See [the variant bridge](variant-key.md).

**Why it matters:** `Goldsztejn` and `Goldstein` are the same family and will not
match each other in a search index. This module is what makes a name found.

**Why it suits an outsider:** it is pure string work with a real, already-collected
test corpus and no private data anywhere near it.

**Seed data, already in the repo:** `resources/SEROCK_NAME_LEXICON.md` and
`skills/jewish-onomastics.md` contain attested cases —
`Pułtusk = POUFTOUSK = RULTUSK = PULSTUK`, `Jarząbek → IAZHOMBEK` (a
Hebrew-transliteration round trip), `Serock → SEROK`, and the ruled-out
`Kanarek ≠ KANALEK` near-miss.

**The trap to respect, and the thing that makes this interesting:** some
near-misses are *not* variants. `KANALEK` is flagged in the lexicon as a
Yad Vashem near-miss that is **not** Kanarek. A variant expander that cannot
express "close, but ruled out by a document" is worse than none, because it
merges families. Proposals must be additive and must never rewrite a literal
recorded name — see the P4 boundary in [SPEC.md](../SPEC.md).

**Scope of the next good PR:** add a small, publicly attributable set of
relationships to `resources/serock_variant_relations.csv`, including tests that
show the intended direction and any false friend. Do not infer equivalence from
the older lexicon's cluster membership or from spelling distance, and do not
attempt a learned matcher in the same change.

## 2. Date-expression coverage

`src/aktreader/validators/dates.py` validates normalized ISO values and exact
Julian/Gregorian equivalence. Its narrow relative resolver recognizes only the
attested `сего числа` and `вчерашняго числа` families from usable explicit anchors;
it deliberately does **not** parse general Russian or Polish word dates. See
[the date contract](date-validation.md).

An additional attested phrase is useful only with a narrow evidence-backed scope:
one documented phrase family, literal fixtures, normalized expectations, and tests
that preserve rather than discard the original wording. Use the date-expression
issue template. Do not add a general word-number parser from remembered vocabulary.

Before proposing a date change, run `python -m aktreader date-audit labels/readerB`
and the specific label files your fixtures exercise. The audit is read-only and emits
complete finding evidence. Reader A's five known prose-value findings are frozen
historical cases, not starter edits; a contribution should add an attributable fixture
or validator rule rather than rewrite those labels.

## 3. Check the CLI documentation against the code

`consensus-merge` is now written up in
[docs/consensus-merge.md](consensus-merge.md), reconstructed by reading
`src/aktreader/cli.py` and `src/aktreader/consensus.py`. Checking that
description against the implementation — and against the other commands' docs —
is genuinely useful: a merge rule described slightly wrong is worse than one
not described at all, because it gets trusted. Reading the label model closely
enough to find such an error is also the fastest way to learn it.

## 4. Adversarial review of the evaluation protocol

[docs/p2-evaluation.md](p2-evaluation.md) argues for a specific metric design:
per-field exact match, no zero-filling of failed jobs, `UNCLEAR` as a valid
answer, and a refusal to convert disputed-only catches into an accuracy estimate.

If that reasoning is wrong, saying so with an argument is more valuable than any
code in this list. The project's stated position is that a confidently wrong
number is worse than no number.

## 5. Schema counterexamples

Bring a register type the schemas mis-model. A page whose structure the canonical
schema cannot express — a different town, a different clerk's formula, an
unusual act type — is a bug report of the most useful kind, even without an
attached scan. Describe the structure; the image is not required.

## 6. Rights-cleared sample material

If you hold validated transcriptions paired with rights-cleared images from
Congress Poland registers, that is the single scarcest input to this work. Open
an issue before sending anything. Material is credited as the contributor
requires, and nothing restricted is accepted — see
[DATA_GOVERNANCE.md](../DATA_GOVERNANCE.md).

## What not to send

- Anything derived from a memorial institution's restricted collection.
- Model downloads, hosted-model API calls, archive scraping, or login automation.
- An edit to a frozen Reader label. Labels are append-only; add a new
  attributable artifact instead.
- A change that makes a reading *look* more confident without adding evidence.
