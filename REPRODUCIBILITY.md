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

## Where a fresh clone stops

The P2 baseline itself cannot be reproduced from the repository alone. `python -m aktreader reader-inspect --config examples/p2-baseline.local-reader.json` fails closed (exit code 2) at the first missing artifact — the pinned `llama-mtmd-cli.exe` runtime — and that is the correct behavior on any machine without the owner-provisioned artifacts. Completing `batch-run` additionally requires:

- the runtime executable, model GGUF, and projector GGUF whose SHA-256 pins are committed in `examples/p2-baseline.artifacts.json`; the owner fetches these bytes outside the application, which never downloads them; and
- the 24 checksum-verified register scans referenced by absolute owner-local path in `examples/p2-baseline.jobs.json`; scans are private source material and are never distributed with this repository.

A reproduction on new hardware must therefore re-provision those artifacts, verify them with `reader-inspect`, and only then run the committed manifest exactly as documented in the [evaluation report](docs/p2-evaluation.md). Supply only local paths to a model runtime and artifacts that you are authorized to use.