# AKT Reader — Evidence Lab

> **Repository role:** `aktreader-research` holds evaluation evidence, research methodology,
> and reproducibility tooling. It is not the reader application and it is not the independent
> benchmark dataset.

The Python distribution is named `aktreader-research`. Its recommended console command is
`aktreader-lab`; the older `aktreader` command remains as a compatibility alias.

[![CI](https://github.com/jakegold1647/aktreader-research/actions/workflows/ci.yml/badge.svg)](https://github.com/jakegold1647/aktreader-research/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](DATA_GOVERNANCE.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

This repository is the evidence and methodology companion to AKT Reader, a local toolkit for
extracting structured information from nineteenth-century civil-register acts written in
Russian Cyrillic and Polish. It is designed for historical and genealogical research where
uncertain readings must remain visible and traceable to the source record.

The project does not claim transcription authority or historical truth. It produces reviewable evidence objects: structured fields, literal-script readings, confidence grades, explicit alternatives, and source-span provenance. Researchers should verify every material conclusion against the underlying record.

## What is included

- A Python CLI and validation library for local, credential-free extraction workflows.
- Schemas for register-native, uncertainty-aware act records.
- A curated evaluation-only gold corpus of 36 historical acts.
- Privacy preflight, provenance, consensus, validation, and leakage-safe evaluation tooling.
- Proposal-only name and town retrieval with phonetic, source-attributed, and ruled-out forms.
- Tests, reproducibility documentation, and a manifest for reviewed open training-source candidates.

## What is not included

- Archive scans or cropped images.
- Raw reviewer traces, internal coordination records, or private operational history.
- Hosted-model calls, API keys, automatic model downloads, archive scraping, or memorial-institution data.
- A completed accuracy claim: the one measured local baseline is a deliberately weak research-derived before-picture, not validated accuracy — see the [P2 local baseline addendum](docs/p2-baseline-addendum.md).

## Which repository do I need?

| Repository | Role | Use it when you want to... |
| --- | --- | --- |
| [`aktreader`](https://github.com/jakegold1647/aktreader) | **AKT Reader — Application** | Run or improve the local scan-to-evidence reader. |
| **`aktreader-research` (you are here)** | **AKT Reader — Evidence Lab** | Audit its claims, reproduce evaluations, inspect labels, or develop evidence-aware research utilities. |
| [`congress-poland-registers`](https://github.com/jakegold1647/congress-poland-registers) | **Congress Poland Registers — Benchmark Dataset** | Build or evaluate against an independent, rights-cleared HTR corpus. |

The application and evidence lab have separate histories on purpose. The application ships the
reader; this repository holds the evidence about how well it reads. The benchmark is independent
of both and is still under construction.

The Application and Evidence Lab still share the `aktreader` Python package namespace, so use a
separate virtual environment for each repository. Installing both into one environment is not
supported. Their distribution and preferred command identities are now distinct:
`aktreader-app` / `aktreader` for the Application and
`aktreader-research` / `aktreader-lab` for the Evidence Lab.

If this checkout was already installed before the distribution rename, recreate its virtual
environment. Package installers treat `aktreader` and `aktreader-research` as different
distributions and may otherwise leave stale metadata or command wrappers behind.

## Research use

The initial pilot concerns civil registers from partitioned Poland. The gold records are evaluation-only; they are not training data and are not presented as a population-level historical reconstruction. The repository records source locations and artifact hashes where available, but does not redistribute source scans.

For a concise project brief to share with researchers, see [Researcher overview](RESEARCHER_OVERVIEW.md).

Read [data governance](DATA_GOVERNANCE.md), [reproducibility notes](REPRODUCIBILITY.md), the [architecture](docs/architecture.md), and the [evaluation report](docs/p2-evaluation.md) before using outputs in research.

## Install and verify

Python 3.11 or newer is required; CI runs 3.11 and 3.13 on Linux and Windows.
This is currently a source-checkout release: clone this repository and use the editable install
below. Standalone wheels and source distributions are not published because several commands
intentionally read versioned schemas, lexicons, and labels from the repository checkout.

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\aktreader-lab.exe doctor
```

Linux and macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/aktreader-lab doctor
```

`doctor` exits successfully only when the running command resolves this `aktreader-research`
source checkout and all 22 public assets needed by the scan-free reproducibility paths are
present. Its report distinguishes the Evidence Lab from the `aktreader-app` checkout and names
every missing schema, prompt binding, lexicon, corpus, label collection, or example input.
`doctor --inspect-root PATH` can diagnose another checkout, but does not reconfigure the running
command. It therefore cannot make a code-only wheel claim that its repository assets are present.
Model weights, runtime binaries, source scans, and private review packets remain outside this
readiness check.

The toolkit is intentionally local-first. Model binaries and weights are supplied and pinned by the researcher; AKT Reader does not download or contact models on its own.

Exact Julian/Gregorian conversion is available without a scan or model:

```powershell
.\.venv\Scripts\aktreader-lab.exe date-convert 1900-02-29 --from-calendar julian
.\.venv\Scripts\aktreader-lab.exe date-resolve-relative "вчерашняго числа" `
  --julian 1890-02-07 `
  --gregorian 1890-02-19
.\.venv\Scripts\aktreader-lab.exe date-audit `
  --output artifacts\readerB-date-audit.json `
  labels\readerB
.\.venv\Scripts\aktreader-lab.exe date-audit-verify `
  --artifact artifacts\readerB-date-audit.json `
  labels\readerB
```

The date validators reject malformed normalized values and compare dual dates as exact civil
days, including the Julian leap-day transition in 1900. They do not infer that a second date was
physically written. When a supported relative phrase, usable anchor, and named stored calendar
do decide the same field, they also flag a contradictory stored date without repairing it. The
relative resolver handles only two source-attested Russian phrase families and refuses uncertain
anchors. See
[civil-date conversion and validation](docs/date-validation.md).

`date-audit` is a read-only corpus survey: explicit files and top-level directory JSON are
sorted deterministically, malformed input is reported without stopping the remaining survey,
and recursion is opt-in. The frozen Reader B directory passes. Reader A intentionally exits 1
with five findings in four legacy labels; the source files are not rewritten. Reports use
common-root-relative POSIX paths, carry source and input-manifest hashes, identify the exact
validator set, and are checked against `schemas/date-audit-1.0.0.schema.json` before emission.
`date-audit-verify` schema-checks a saved artifact and replays it exactly from the supplied input
selection. A verification `PASS` proves reproduction; `artifact_status` separately preserves
whether the original audit passed, found issues, or was incomplete.

The P4 name-retrieval tools are also available without scans or a model:

```powershell
.\.venv\Scripts\aktreader-lab.exe variant-key Goldsztejn Goldsztajn
.\.venv\Scripts\aktreader-lab.exe variant-propose Kanarek --kind surname
.\.venv\Scripts\aktreader-lab.exe variant-propose Serock --kind town
.\.venv\Scripts\aktreader-lab.exe variant-batch `
  --input examples\variant-batch.example.csv `
  --output variant-proposals.json
.\.venv\Scripts\aktreader-lab.exe variant-batch-verify `
  --artifact variant-proposals.json `
  --input examples\variant-batch.example.csv
```

Proposal-producing variant commands emit `PROPOSAL_ONLY`. `variant-propose` and `variant-batch`
keep documented forms, curated variants, phonetic candidates, and explicit false friends
separate; a similarity is never proof of identity. `variant-batch-verify` proves that a stored
batch is schema-valid and exactly reproducible from the supplied CSV and current source
lexicons. See [the variant bridge](docs/variant-key.md).

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) is the rules. [docs/where-to-help.md](docs/where-to-help.md) is the work: what is genuinely open to an outside contributor, and an honest account of how much of the backlog is gated on private scans and owner-held artifacts. The variant bridge is the best entry point — pure string work, real test data already in the repository, no scan or model access needed.

Challenges to the evaluation methodology are treated as first-class contributions. A confidently wrong number is worse than no number.

## Citation

If you use the Evidence Lab, cite the software record in [CITATION.cff](CITATION.cff) and identify
the repository release and commit SHA used in your work. Cite the AKT Reader application and the
archival collection separately when they are part of the work.

## License and data terms

The code is released under the MIT License. The repository's original transcriptions and derived structured records are released under CC BY 4.0, subject to the provenance and scope notes in [LICENSE](LICENSE) and [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md). Source scans are not redistributed.

## Status

This is a research software release, not a finished transcription system. The methodology and safeguards are implemented; performance on nineteenth-century handwriting must be established through the documented baseline and independent review.

## Owner-only open training sources

The included manifest identifies reviewed open datasets for Base-script adaptation. The application never calls the downloader or automatically retrieves data. No text-side lexicon corpus currently clears every gate; see `resources/open_datasets.manifest.json` before any separate source-rights review.
