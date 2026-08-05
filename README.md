# AKT Reader Research Edition

[![CI](https://github.com/jakegold1647/aktreader-research/actions/workflows/ci.yml/badge.svg)](https://github.com/jakegold1647/aktreader-research/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](DATA_GOVERNANCE.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

AKT Reader is a local, evidence-first toolkit for extracting structured information from nineteenth-century civil-register acts written in Russian Cyrillic and Polish. It is designed for historical and genealogical research where uncertain readings must remain visible and traceable to the source record.

The project does not claim transcription authority or historical truth. It produces reviewable evidence objects: structured fields, literal-script readings, confidence grades, explicit alternatives, and source-span provenance. Researchers should verify every material conclusion against the underlying record.

## What is included

- A Python CLI and validation library for local, credential-free extraction workflows.
- Schemas for register-native, uncertainty-aware act records.
- A curated evaluation-only gold corpus of 36 historical acts.
- Privacy preflight, provenance, consensus, validation, and leakage-safe evaluation tooling.
- Tests, reproducibility documentation, and a manifest for reviewed open training-source candidates.

## What is not included

- Archive scans or cropped images.
- Raw reviewer traces, internal coordination records, or private operational history.
- Hosted-model calls, API keys, automatic model downloads, archive scraping, or memorial-institution data.
- A completed accuracy claim: the one measured local baseline is a deliberately weak research-derived before-picture, not validated accuracy — see the [P2 local baseline addendum](docs/p2-baseline-addendum.md).

## Research use

The initial pilot concerns civil registers from partitioned Poland. The gold records are evaluation-only; they are not training data and are not presented as a population-level historical reconstruction. The repository records source locations and artifact hashes where available, but does not redistribute source scans.

For a concise project brief to share with researchers, see [Researcher overview](RESEARCHER_OVERVIEW.md).

Read [data governance](DATA_GOVERNANCE.md), [reproducibility notes](REPRODUCIBILITY.md), the [architecture](docs/architecture.md), and the [evaluation report](docs/p2-evaluation.md) before using outputs in research.

## Install and verify

Python 3.11 or newer is required; CI runs 3.11 and 3.13 on Linux and Windows.

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\aktreader.exe doctor
```

Linux and macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/aktreader doctor
```

The toolkit is intentionally local-first. Model binaries and weights are supplied and pinned by the researcher; AKT Reader does not download or contact models on its own.

## Citation

If you use AKT Reader, cite the software record in [CITATION.cff](CITATION.cff) and identify the repository release and commit SHA used in your work. Cite the archival collection separately according to its own requirements.

## License and data terms

The code is released under the MIT License. The repository's original transcriptions and derived structured records are released under CC BY 4.0, subject to the provenance and scope notes in [LICENSE](LICENSE) and [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md). Source scans are not redistributed.

## Status

This is a research software release, not a finished transcription system. The methodology and safeguards are implemented; performance on nineteenth-century handwriting must be established through the documented baseline and independent review.

## Owner-only open training sources

The included manifest identifies reviewed open datasets for Base-script adaptation. The application never calls the downloader or automatically retrieves data. No text-side lexicon corpus currently clears every gate; see `resources/open_datasets.manifest.json` before any separate source-rights review.
