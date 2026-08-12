# Changelog

This changelog covers the public **AKT Reader — Evidence Lab** repository. It does not describe
releases of the runnable [AKT Reader application](https://github.com/jakegold1647/aktreader) or
the independent
[Congress Poland Registers benchmark dataset](https://github.com/jakegold1647/congress-poland-registers).

## Unreleased

Development version: `0.3.0.dev0`.

### Changed

- Source checkouts now install under the unambiguous `aktreader-research` distribution name.
- `aktreader-lab` is the preferred Evidence Lab command; `aktreader` remains a compatibility
  alias. The Python namespace remains shared with the Application, so separate environments are
  still required.
- `doctor` and `--version` now identify the Evidence Lab, its repository, and its source-only
  packaging status explicitly.
- `doctor` now verifies the `aktreader-research` checkout identity and 22 public assets before
  reporting the source-relative reproducibility paths as available. Alternate roots are
  diagnostic only, and code-only wheels fail closed.
- Existing pre-rename editable environments should be recreated so stale `aktreader`
  distribution metadata does not survive beside `aktreader-research`.

## [0.2.0] - 2026-08-12

### Added

- Source-attributed surname and town variant proposals with explicit false-friend exclusions.
- Schema-validated, reproducible variant batches and an exact replay verifier.
- Exact Julian/Gregorian civil-date conversion, including the 1900 leap-day boundary.
- A narrow relative-date resolver for two source-attested Russian phrase families.
- Read-only corpus date audits with portable, versioned JSON artifacts.
- Exact date-audit replay verification with schema, source, manifest, and validator drift checks.

### Changed

- Public documentation now distinguishes the Application, Evidence Lab, and Benchmark Dataset.
- Python support and the lockfile now consistently require Python 3.11 or newer.

### Known limits

- This release contains no archive scans or model weights and makes no validated handwriting-
  accuracy claim.
- Reader A's legacy labels intentionally produce five date findings across four files; the audit
  reports those findings without rewriting source labels.
- Reader B is a regression corpus for repository artifacts, not an independent performance
  benchmark.
- v0.2.0 is a GitHub source release. Standalone Python distributions are not published because
  repository-root schemas, lexicons, and labels are not yet packaged as runtime data.
- The Application and Evidence Lab still use the same `aktreader` Python namespace and command;
  install them in separate virtual environments.

## [0.1.0] - 2026-08-04

- Initial public Evidence Lab snapshot with schemas, evaluation labels, validation utilities,
  methodology, and reproducibility documentation.

[0.2.0]: https://github.com/jakegold1647/aktreader-research/releases/tag/v0.2.0
[0.1.0]: https://github.com/jakegold1647/aktreader-research/commits/b050856
