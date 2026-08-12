# Variant bridge

The P4 variant bridge supplies additive search forms for names and towns. It never edits a
literal input, merges people, or promotes a similarity into an identity conclusion. Both
commands are local-only and require no scan, model, private data, or network access.

## Evidence-aware proposals

`variant-propose` combines the public Serock lexicon, explicit relationship decisions, and
Daitch–Mokotoff candidates:

```powershell
aktreader variant-propose Kanarek --kind surname
aktreader variant-propose Serock --kind town
aktreader variant-propose Goldstein --kind surname
```

The `Kanarek` report returns `Kania` as a `DOCUMENTED_FORM` and `KANALEK` as `RULED_OUT`.
The `Serock` report keeps `Serok`, `Serotzk`, `Srotsk`, and `Serock u/Narwią` as attested search
forms while carrying `Sierck-les-Bains` as a false friend. The literal query is returned
unchanged in every report.

Every proposal has one of four meanings:

| Relation | Meaning |
| --- | --- |
| `DOCUMENTED_FORM` | A row appears in the source lexicon's cluster. The cluster may include uncertainty, a married surname, or a pooled reading, so this is not automatically equivalence. |
| `ATTESTED_VARIANT` | The relationship is explicitly curated in `resources/serock_variant_relations.csv` with source evidence. |
| `PHONETIC_CANDIDATE` | The query and form share a Daitch–Mokotoff key. This is only a retrieval lead. |
| `RULED_OUT` | Source evidence explicitly rejects the relationship or reading. This takes precedence over every positive or phonetic proposal for the same pair. |

The loader fails closed when an old `anti-entry` lacks a `RULED_OUT` row with the same source
citation, when one pair is both attested and ruled out, when a CSV contract drifts, or when a
declared script does not match its form. Use `--no-phonetic` to return only documented and
explicit relationships. Cyrillic can be queried exactly; unsupported scripts are never reduced
to a meaningless all-zero key.

## Batch workflow

`variant-batch` applies the same proposal rules to an explicit UTF-8 CSV:

```csv
id,query,entity_type
surname-1,Kanarek,surname
surname-2,Goldstein,surname
town-1,Serock,town
surname-3,Мяра,surname
```

The exact input contract is `id,query,entity_type`. IDs must be nonblank and unique; every row
must explicitly choose `surname`, `given`, or `town`. The command does not infer a type from a
spelling or filename.

```powershell
aktreader variant-batch `
  --input examples\variant-batch.example.csv `
  --output variant-proposals.json
```

The output:

- preserves input order, stable IDs, row numbers, literal queries, and entity types;
- records SHA-256 for the input, source lexicon, and explicit relationship file;
- carries every proposal's relation, shared phonetic keys, and source evidence;
- validates against `schemas/variant-batch-1.0.0.schema.json` before writing;
- detects if an input or lexicon changes while the artifact is being built;
- writes atomically and refuses to replace an existing file without `--replace-existing`; and
- leaves no partial output when any row fails validation.

Use `--no-phonetic` for documented and explicitly curated relationships only. The published
sample is [`examples/variant-batch.example.csv`](../examples/variant-batch.example.csv).

## Raw phonetic keys

`variant-key` exposes the Daitch–Mokotoff encoder directly:

```powershell
aktreader variant-key Goldsztejn Goldsztajn
```

Both spellings emit `584360`, so the command reports that code under `shared_codes`. Every code
is six digits and ambiguous sounds return every branch. Case, spaces, punctuation, and common
Latin diacritics are handled mechanically; Polish `ą` and `ę` retain their documented branching
behavior.

The implementation follows the published
[JewishGen Daitch–Mokotoff coding chart](https://www.jewishgen.org/InfoFiles/soundex.html).
Regression tests include its published examples and this repository's attested spellings.

## Data contract and boundary

- `resources/serock_name_lexicon.csv` preserves source rows. Ordinary cluster membership becomes
  `DOCUMENTED_FORM`, not an inferred equivalence.
- `resources/serock_variant_relations.csv` contains only explicit `ATTESTED_VARIANT` and
  `RULED_OUT` decisions, including the P4 town seeds.
- Output evidence retains `source_tier` and `source_ref` from those files.
- A shared code or source cluster remains a search aid. It cannot establish that two records
  identify the same person or family.

The next useful contribution is a small set of additional explicit relationships backed by a
public citation and regression tests. Do not infer them from spelling distance or free-text
notes, and do not bundle a learned matcher into the same change.
