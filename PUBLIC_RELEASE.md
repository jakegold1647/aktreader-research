# Public release scope

This research edition is a clean public snapshot of AKT Reader. It includes the local extraction toolkit, schemas, curated evaluation corpus, anonymized reproducibility labels, and a runnable public test suite.

It excludes private operational coordination, reviewer/session traces, source-scan crops, and private audit-dependent test cases. These exclusions do not change the project’s claim boundaries: no publication-grade handwriting accuracy claim exists. The one measured local baseline run is recorded as a weak research-derived before-picture in [the P2 local baseline addendum](docs/p2-baseline-addendum.md).

Verification for the initial snapshot (commit `b050856`):

```text
204 passed
python -m build: passed
```

Later public commits extend the suite; the current expected state is that
`python -m pytest`, `python -m ruff check .`, and
`python -m tools.check_dependency_licenses` all pass, enforced by CI on every
push to `main`.