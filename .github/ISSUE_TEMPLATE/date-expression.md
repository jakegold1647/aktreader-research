---
name: Attested date expression
about: A Russian or Polish register phrase the normalized-date layer should handle
title: "date expression: "
labels: documentation
---

Read [`docs/date-validation.md`](../../docs/date-validation.md) first. The current module
validates normalized dates and resolves two exact Russian relative forms; it does not claim to
parse arbitrary Russian or Polish number-words.

## Literal expression

- Language: Russian · Polish · mixed
- Exact text, preserving historical spelling and line breaks:
- Rhetorical slot: registration date · event date · bann · other

## Evidence

Identify the public repository record, rights-cleared source, or published formula where the
expression occurs. Do not attach a restricted scan or memorial-institution record.

- Source:
- Did you inspect it yourself? yes · no

## Expected interpretation

- Calendar stated by the source: Julian · Gregorian · dual · unstated
- Normalized value, if unambiguous:
- Anchor date, if this is relative (`same day`, `yesterday`, and so on):

If the expression or anchor is uncertain, say so. An unresolved phrase should fail closed, not
become a guessed date.

## Boundary case

What should the parser reject or leave unresolved? Include at least one near-match if possible.

Literal source text must remain available after normalization. A parser must never manufacture a
second calendar date that was not written.
