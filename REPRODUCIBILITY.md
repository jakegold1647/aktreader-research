# Reproducibility notes

AKT Reader is designed to make a local run inspectable rather than opaque. A complete study should record:

1. The repository release and commit SHA.
2. The supplied scan or crop identifier and SHA-256 hash.
3. The model, runtime, prompt, schema, and decoding configuration.
4. The configured privacy policy and any manual review decisions.
5. The resulting evidence JSON, including uncertainty and source spans.

The repository includes schemas, validators, and tests. It does not ship model weights, model executables, or archive scans. The measured local baseline is recorded in the [P2 local baseline addendum](docs/p2-baseline-addendum.md); it is a weak research-derived before-picture, not publication-grade benchmark accuracy, and no performance should be inferred from the presence of tests or example configurations.

## What a fresh clone reproduces

From a clean clone with only the development dependencies installed (`pip install -e ".[dev]"`), the following are fully reproducible offline, with no model, scan, or network access:

1. The full test suite: `python -m pytest`.
2. Lint: `python -m ruff check .`.
3. Environment report: `python -m aktreader doctor`.
4. Frozen-prompt verification: `python -m aktreader prompt-verify --root .` must report `PASS` with the digest pinned in `prompts/manifest.json` and `prompts/reader_prompt.sha256`.
5. Label validation and grounding surveys over the committed frozen labels, for example `python -m aktreader label-validate --report labels/readerA/serock-1877-birth-1.json` (`--report` is a flag; the labels are positional and more than one may be given). Expect exit 0 and `"status": "PASS"` — the canonical wave-006 Reader A labels return `GROUNDED` for all ten acts. Frozen pre-contract labels and the superseded July wave-006 pass (`labels/readerA/superseded/wave006-july-pass-ruled-compromised/`) still fail the v1.4 gate by design; for those, exit code 2 is the documented behavior.
6. P4 variant batches from the committed public lexicons: build one with `python -m aktreader variant-batch --input examples/variant-batch.example.csv --output variant-proposals.json`, then prove exact content reproduction with `python -m aktreader variant-batch-verify --artifact variant-proposals.json --input examples/variant-batch.example.csv`.
7. Exact civil-calendar arithmetic: `python -m aktreader date-convert 1900-02-29 --from-calendar julian` must return Gregorian `1900-03-13`. `python -m aktreader date-resolve-relative "вчерашняго числа" --julian 1890-02-07 --gregorian 1890-02-19` must resolve Julian `1890-02-06` and Gregorian `1890-02-18`. Both commands require no locale, model, scan, or network access.

8. A read-only date survey over the frozen labels: `python -m aktreader date-audit labels/readerB` must exit 0 with 27 labels and no findings. `python -m aktreader date-audit labels/readerA` must exit 1 with 59 labels, one skipped non-label index sidecar, and five `DATE_VALUE_INVALID` findings across four labels. These expected findings expose frozen historical prose values; the command does not repair them. Reports are schema-valid and use common-root-relative paths, so the same input tree produces the same JSON under a different checkout root.

## Where a fresh clone stops

The P2 baseline itself cannot be reproduced from the repository alone. `python -m aktreader reader-inspect --config examples/p2-baseline.local-reader.json` fails closed (exit code 2) at the first missing artifact — the pinned `llama-mtmd-cli.exe` runtime — and that is the correct behavior on any machine without the owner-provisioned artifacts. Completing `batch-run` additionally requires:

- the runtime executable, model GGUF, and projector GGUF whose SHA-256 pins are committed in `examples/p2-baseline.artifacts.json`; the owner fetches these bytes outside the application, which never downloads them; and
- the 24 checksum-verified register scans referenced by absolute owner-local path in `examples/p2-baseline.jobs.json`; scans are private source material and are never distributed with this repository.

A reproduction on new hardware must therefore re-provision those artifacts, verify them with `reader-inspect`, and only then run the committed manifest exactly as documented in the [evaluation report](docs/p2-evaluation.md). Supply only local paths to a model runtime and artifacts that you are authorized to use.

### Human adjudication packets

`python -m aktreader adjudicate --wave <id>` reads `human_check/waves/wave-<id>.json` and writes into `human_check/generated/wave-<id>`. That directory is owner-local and is not distributed: the packets embed source-pixel crops of register scans and named human answers. On a clean clone the command exits 2 against the absent wave specification, naming the path it wanted. **That is the intended fail-closed behavior, not a defect.** `human_check/` is gitignored so private review material cannot be committed by accident. See [docs/adjudication.md](docs/adjudication.md) for the packet format.

### The training-readiness gate report is owner-local by construction

`training/readiness-0001.json` is a frozen record of a gate evaluation measured on 2026-07-29. Its `input_pins` name the five inputs by **owner-local absolute path** (`E:\DNA\Project_RegisterReader\...`), so the report as committed cannot be re-derived from this clone. This is stated rather than corrected: rewriting the recorded paths would make a measurement that happened on one machine look portable, and a gate report that has been retouched is worth less than one that is honest about where it ran.

Two of those five pinned inputs are not in this repository at all — the gold-attestation audit (see [docs/audits/README.md](docs/audits/README.md)) is an owner-held internal record, and the paths point at the sibling `aktreader` repository's working tree rather than at `aktreader-research`.

What *is* portable is the verification mechanism: every pin carries a SHA-256, so each input can be confirmed by content rather than by location. A third party reproducing the gate would need the five pinned files, would verify each against its committed digest, and would then re-run the preflight; agreement with the recorded `status` and `metrics` is the check. Nothing about the gate's outcome depends on the paths themselves.
