# Variant retrieval keys

`aktreader variant-key` generates Daitch–Mokotoff Soundex keys for one or more Latin-script
names. It is the first separately shippable slice of the P4 variant bridge and requires no scan,
model, private data, or network access.

```powershell
aktreader variant-key Goldsztejn Goldsztajn
```

Both spellings emit `584360`, so the command reports that code under `shared_codes`. The whole
result is marked `PROPOSAL_ONLY` and includes this warning:

> A shared phonetic key proposes a search candidate; it does not establish that two names
> identify the same person or family.

That distinction is product behavior. The encoder never edits a literal name, merges records,
or promotes a phonetic collision into consensus. It only supplies additive search keys for a
human or a later evidence-aware proposal layer.

## Behavior

- Every code is six digits; ambiguous sounds return every branch.
- Case, spaces, punctuation, and common Latin diacritics are handled mechanically.
- Polish `ą` and `ę` retain their Daitch–Mokotoff branching behavior.
- Unsupported scripts fail closed. Transliterate Cyrillic before requesting a key; silently
  converting it to `000000` would create meaningless collisions.
- Multiple inputs are compared and any shared codes are listed, but no identity conclusion is
  produced.

The implementation follows the published
[JewishGen Daitch–Mokotoff coding chart](https://www.jewishgen.org/InfoFiles/soundex.html).
Regression tests include its documented examples and attested spellings from
`resources/serock_name_lexicon.csv`.

## Known boundary and next P4 slice

Phonetic similarity cannot represent source-backed relationships. The repository's lexicon says
that `KANALEK` is a near-miss, not a `Kanarek` variant; a numeric key alone has no way to carry
that ruling. Conversely, the encoder finds a shared branch for `Jarząbek` and `IAZHOMBEK`, but
that still does not prove the names identify one person.

The next P4 slice should load the public lexicon into typed, attributable proposals such as
`ATTESTED_VARIANT`, `PHONETIC_CANDIDATE`, and `RULED_OUT`. It must preserve literal input and
source references, and must never allow a phonetic candidate to override a ruled-out relation.
