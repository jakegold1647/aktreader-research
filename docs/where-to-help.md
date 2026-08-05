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

**What:** an expansion library that maps a surname or town name to the forms it
actually appears under in indexes: Daitch-Mokotoff soundex, transliteration
round-trips, and documented OCR manglings.

**Why it matters:** `Goldsztejn` and `Goldstein` are the same family and will not
match each other in a search index. This module is what makes a name found.

**Why it suits an outsider:** it is pure string work with a real, already-collected
test corpus and no private data anywhere near it.

**Seed data, already in the repo:** `resources/SEROCK_NAME_LEXICON.md` and
`skills/jewish-onomastics.md` contain attested cases —
`Pułtusk = POUFTOUSK = RULTUSK = PULSTUK`, `Jarząbek → IAZHOMBEK` (a
Hebrew-transliteration round trip), `Serock → SEROK`, `Kanarek → KANALEK`.

**The trap to respect, and the thing that makes this interesting:** some
near-misses are *not* variants. `KANALEK` is flagged in the lexicon as a
Yad Vashem near-miss that is **not** Kanarek. A variant expander that cannot
express "close, but ruled out by a document" is worse than none, because it
merges families. Proposals must be additive and must never rewrite a literal
recorded name — see the P4 boundary in [SPEC.md](../SPEC.md).

**Scope of a good first PR:** the D-M soundex encoder alone, with tests drawn
from the lexicon table, is a complete and useful contribution. Do not attempt
the whole module.

## 2. Date-expression coverage

`src/aktreader/validators/dates.py` (127 lines) parses the date expressions these
registers use, where dates are written as words in Russian and Polish and follow
the Napoleonic act formula documented in `skills/napoleonic-act-formula.md`
(register span 1874–1904). Additional attested date phrasings, with tests, are
useful and require only the formula document.

## 3. Document `consensus-merge`

`python -m aktreader consensus-merge` is implemented (`src/aktreader/cli.py`) and
mentioned in no document. Reading the implementation and writing it up accurately
is a real contribution and an unusually good way to learn the label model.

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
