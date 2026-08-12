# Public release scope

This document covers **AKT Reader — Evidence Lab v0.2.0**. It is the evidence,
methodology, and reproducibility repository—not the runnable
[AKT Reader application](https://github.com/jakegold1647/aktreader) and not the independent
[Congress Poland Registers benchmark dataset](https://github.com/jakegold1647/congress-poland-registers).

The release includes the validation library and CLI, schemas, curated evaluation corpus,
anonymized reproducibility labels, proposal-only variant utilities, civil-date tools, portable
audit artifacts, and exact replay verifiers. See [the changelog](CHANGELOG.md) for the release
delta.

It excludes private operational coordination, reviewer/session traces, source-scan crops,
model weights, and private audit-dependent test cases. These exclusions do not change the
project's claim boundaries: no publication-grade handwriting accuracy claim exists. The one
measured local baseline run is recorded as a weak research-derived before-picture in
[the P2 local baseline addendum](docs/p2-baseline-addendum.md).

Every release candidate must pass:

```text
uv lock --locked
python -m pytest
python -m ruff check .
python -m tools.check_dependency_licenses
uv build
```

CI repeats lint, tests, and dependency-license checks on Python 3.11 and 3.13, on both Linux and
Windows. Build integrity and a passing test suite establish repository integrity; they do not
establish handwriting accuracy.

v0.2.0 is distributed through GitHub's repository source archives. The wheel and Python source
distribution are built only as metadata/regression checks and are not attached to the release:
they do not yet include the repository-root schemas, lexicons, labels, and other assets required
by several commands. Use a clone and editable install as documented in the README.
