# Wave 006 methods note: a compromised pass caught by blind consensus

**Recorded:** 2026-08-04. Register: Serock, fond 73/826/0, 1877 births, acts 1-10.

Wave 006 is the project's first production wave on a new register year and its first under
the restructured reader protocol (fresh, context-isolated reader instances for every pass).
It produced two findings worth recording as methodology results rather than operational
history.

## 1. Blind consensus caught a confabulated pass

An earlier Reader A pass over acts 1-8 had been frozen in July. When the wave completed -
a fresh blind Reader B pass over all ten acts, followed by consensus merge and a fresh
arbiter instance ruling on 18 contested items against the source pixels - the arbitration
went 17 of 18 against the July pass. The decisive case was act 6: the July label described
a family that is not on the page, wrapped around the act's real signature block. Adjacent
errors (registration dates, occupations rendered as trades not present in the ink)
followed the same pattern.

The July pass was ruled compromised and superseded in full; the wave's fresh replacement
pass - produced blind, with no access to the July labels - is canonical, and independently
measures GROUNDED against the v1.4 anti-fabrication gate for all ten acts.

The method, not any reader, is the result: a single-reader pipeline would have shipped the
confabulated family as data. Two independent blind readings plus pixel-level arbitration
identified it, quarantined it, and replaced it, with the full audit trail retained under
`labels/readerA/superseded/`. This repeats, on the project's own second reader class, the
wave-005 finding that motivated the consensus design. Protocol v1.2 accordingly retires
session-context reads entirely: every reader pass now runs on a fresh instance.

## 2. Both blind readers overrode wrong metadata from the ink

The wave brief carried `language: "pl"` for this register, on the reasoning that Serock's
registers are Polish-era before and after the Russian-language period. The ink of all ten
1877 acts is Russian chancery Cyrillic - as expected for 1868-1915 - and both blind
readers, working independently and without access to each other or to the brief's
provenance, labeled `language: "ru"` from the page and flagged the discrepancy. The brief
metadata has been corrected with an erratum on the private source side.

This is the language-conditional grounding guard's first production test, and it passed in
the strongest available way: the readers trusted the ink over the metadata, and said so.

## Outcome summary

Eight of ten acts reached 2-of-3 consensus across every field after arbitration; two acts
each retain exactly one field gated on human review of a single ambiguous initial (the
child's given-name initial in act 1; the mother's maiden-name initial in act 9). Those
fields are recorded as explicit alternatives, not guesses, pending qualified human
adjudication.
