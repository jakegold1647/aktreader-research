# AKT Reader — Evidence Lab: researcher overview

## The short version

AKT Reader is an open research software project for extracting structured evidence from nineteenth-century civil-register acts written in Russian Cyrillic and Polish. It is designed for the difficult middle ground between a scanned archival page and a defensible historical conclusion: a reading may be useful without being certain, and uncertainty should remain visible all the way through the data pipeline.

The public evidence lab is at
[jakegold1647/aktreader-research](https://github.com/jakegold1647/aktreader-research). The
runnable reader application is a separate repository at
[jakegold1647/aktreader](https://github.com/jakegold1647/aktreader).
The independent benchmark dataset is being developed separately at
[jakegold1647/congress-poland-registers](https://github.com/jakegold1647/congress-poland-registers).

## Research question

Can local, uncertainty-aware extraction make historical register research faster while preserving the distinctions that matter to historians and genealogists—literal script, normalized interpretation, alternative readings, source spans, confidence, and human review?

The first project context is civil registers from partitioned Poland, especially records written in Russian Cyrillic between the late nineteenth and early twentieth centuries, with Polish-language material in the surrounding corpus.

## What exists today

The repository provides:

- a Python CLI and validation library for local extraction workflows;
- register-native schemas for acts, model outputs, labels, adjudication, and provenance;
- a curated 36-act evaluation-only gold corpus;
- dual-reader, consensus, uncertainty-grading, and privacy-preflight tooling;
- local-reader boundaries that do not download models, call hosted APIs, or handle credentials;
- source-attributed name and town variant proposals with reproducible batch verification;
- exact civil-date conversion and portable, replay-verifiable corpus audits;
- reproducibility guidance and a public test suite.

The project has a real development history: the public edition preserves the substantive commit history of the working project after removing private operational material. The public history is scrubbed of reviewer-session traces, internal coordination, source crops, and provider-specific identifiers.

## Methodological commitments

AKT Reader treats an extraction as an evidence object, not an authoritative transcription. A useful output should make it possible to ask:

1. What did the reader literally observe?
2. What normalized value or interpretation was proposed?
3. What alternatives or absences were considered?
4. Which span, artifact, or source reference supports the field?
5. What confidence and review status should govern its use?

The gold corpus is reserved for evaluation. Archive scans are not redistributed. The repository does not claim population-level historical reconstruction or validated accuracy on the full handwriting problem.

## Current status

The public snapshot is software-complete enough for inspection, schema work, evaluation design, and researcher collaboration. Its local historical-handwriting baseline has been executed exactly once and measured as a deliberately weak before-picture — 1/77 filiation fields exact against a research-derived comparison corpus (see the [P2 local baseline addendum](docs/p2-baseline-addendum.md)). The project therefore does not yet support claims such as “X% accurate on nineteenth-century registers.” Those claims are a research milestone, not a marketing assumption.

From a clean clone, the public snapshot verifies with a fully passing test suite (run `python -m pytest`; continuous integration enforces this on every push) and builds as a Python source distribution and wheel. These checks establish repository integrity; they do not substitute for an independent handwriting benchmark.

## What collaboration would be useful

Researchers who work with historical records can help most by bringing one concrete use case, for example:

- a register type or language/formula the schemas do not represent well;
- a small, rights-cleared sample suitable for benchmark design;
- an archival provenance or citation convention that should be captured;
- a disagreement pattern where a confidence grade is misleading;
- an independent evaluation protocol or replication attempt.

The best first conversation is not a request to endorse the system. It is a request to identify where the evidence model, data governance, or evaluation design fails to reflect real research practice.

## Suggested conversation opener

> We are building local, evidence-first tooling for historical Cyrillic and Polish civil registers. The goal is not to hide uncertainty behind an OCR score: it is to preserve literal readings, alternatives, provenance, and review state so researchers can decide what is safe to use. We have a public research edition with schemas, an evaluation corpus, and reproducibility tooling, and we are looking for concrete records or evaluation practices that would challenge the design.

## Read next

- [README](README.md) — installation and project orientation
- [Data governance](DATA_GOVERNANCE.md) — rights, privacy, and use boundaries
- [Reproducibility notes](REPRODUCIBILITY.md) — what to record for a study
- [Architecture](docs/architecture.md) — evidence model and pipeline boundaries
- [Evaluation report](docs/p2-evaluation.md) — documented diagnostics and the measured local baseline
- [P2 local baseline addendum](docs/p2-baseline-addendum.md) — the measured before-picture and its limits
- [Citation record](CITATION.cff) — how to cite the software
- [Changelog](CHANGELOG.md) — release-by-release changes and known limits
