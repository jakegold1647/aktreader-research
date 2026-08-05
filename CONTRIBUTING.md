# Contributing to AKTREADER

AKTREADER treats provenance and uncertainty as product behavior. A contribution is not complete
when it merely produces plausible text; it must preserve the path from scan pixels to every
assertion.

Looking for something to pick up? [docs/where-to-help.md](docs/where-to-help.md)
lists the work that is genuinely open to an outside contributor, and is honest
about how much of the backlog is gated on private scans and owner-held artifacts.

## Before opening a change

- Use Python 3.11 or newer in an isolated environment.
- Install the development group and run `python -m pytest`.
- Run `python -m ruff check .` when Ruff is installed.
- Run `python -m tools.check_dependency_licenses` after any dependency edit.
- Do not add model downloads, hosted-model APIs, archive scraping, login automation, or secrets.
- Do not include restricted memorial-institution material in labels or training data.

## Data and label changes

- Never edit a frozen Reader label in place; add a new attributable artifact.
- Preserve the exact scan hash, prompt hash, Reader identity, blind group, clerk-year, source
  spans, observation states, and authority warning.
- A single Reader cannot emit `CONFIDENT`.
- Machine 2-of-3 resolution is `SILVER`/`PROBABLE`, not human-verified gold.
- Any training export must pass the clerk-year split validator against its chosen evaluation
  holdout.
- Corrections require recorded training consent before they can become training data.

## Code changes

Keep commands local-only and fail closed. Add regression tests for malformed JSON, provenance
drift, retry behavior, privacy boundaries, and split leakage when relevant. Generated files must
be deterministic and content-addressed where the pipeline promises reproducibility.

Pull requests should state:

1. the behavior changed;
2. the evidence or test that justifies it;
3. any schema/prompt/artifact identity changes;
4. whether benchmark comparability changes; and
5. whether the change touches privacy, consent, or training/evaluation isolation.

Code contributions are accepted under the MIT License; transcription and derived-record
contributions fall under CC BY 4.0 as described in [LICENSE](LICENSE) and
[DATA_GOVERNANCE.md](DATA_GOVERNANCE.md).
