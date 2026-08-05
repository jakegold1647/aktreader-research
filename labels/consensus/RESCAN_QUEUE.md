# Rescan queue — consolidated scan-quality blockers (all waves)

**Purpose:** every field across waves 003–006 that the readers/arbiter declared
unresolvable *because of the scan, not the ink*. This is the acquisition
shopping list: four image files, nine blocked fields. Ordering better images of
these four spreads unblocks every item below; nothing else in the corpus is
scan-limited.

Assembled 2026-08-05 (offline extraction, opus-verified against the source
docs line-by-line; three draft rows were dropped as false positives — see the
wave arbitration files for the underlying rulings). The consensus and
arbitration docs remain authoritative.

## The four files to reacquire

| Image file | Register | Blocked acts |
|---|---|---|
| `Serock_1890_deaths_39-42.jpg` | 1890 deaths | 40, 41, 42 |
| `Serock_1890_deaths_47-49.jpg` | 1890 deaths | 49 |
| `Serock_1877_births_01-02.jpg` | 1877 births | 1, 2 |
| `Serock_1877_births_07-10.jpg` | 1877 births | 9, 10 |

## Blocked fields, by image

| Source Image File | Act | Field(s) Blocked | What a better scan resolves | Source doc + lines |
| --- | --- | --- | --- | --- |
| Serock_1890_deaths_39-42.jpg | 42 | Filiation: father, mother's given name, mother's née | Severe recto-verso bleed-through defeats 8× + contrast isolation; would settle pooled [Szmul/Manes], [Bejla Frajda/Bluma Dwojra], née [Szelkobroda/Wielkobroda/Szechtman] | readerC_arbitration_wave004.md:33, :81; …41-49_wave004_CONSENSUS.md:153, :186 |
| Serock_1890_deaths_47-49.jpg | 49 | Red rectification layer: red given name + surname, red mother's given name + née; trailing red margin line | Red strokes overlap struck black and JPEG noise defeats channel isolation; would confirm «Гольдблюмъ» (currently PROBABLE) and the UNRESOLVABLE mother tokens | readerC_arbitration_wave004.md:48, :51–52, :54, :81; CONSENSUS_wave004:151, :153, :186 |
| Serock_1890_deaths_39-42.jpg | 41 | Reg-date line 1 (the «двадцать» token) | Token is partially overlapped by folio number "65"; a clean scan converts the LEANING «двадцать третьяго Сентября» | readerC_arbitration_wave004.md:14, :81 |
| Serock_1890_deaths_39-42.jpg | 40 | Second red marginal authentication, signed «М. М⟨янкинъ?⟩» (different hand) | Reads the co-signatory name and the red margin formula in a hand distinct from act 49's | readerC_arbitration_wave004.md:76; CONSENSUS_wave004:187–188; wave003_CONSENSUS:225 |
| Serock_1890_deaths_39-42.jpg | 40 | Family surname [Бобекъ/Бодекъ] | 2–2 reader deadlock explicitly stated as settleable "only by a human eye or a better scan" | …30-40_wave003_CONSENSUS.md:268 |
| Serock_1877_births_01-02.jpg | 1 | Child-name initial А/Я (Анкель vs Янкель), naming line | Identity-bearing initial; right margin crowds the line — would convert the BOTH-UNCLEAR ruling | readerC_arbitration_wave006.md:14, :43, :47 |
| Serock_1877_births_01-02.jpg | 2 | Declarant given name [Шмуль/Шендель]; also reg-hour and age tokens crowded against the gutter | Gutter crowding is the stated cause; would break the pooled given-name tie the Latin signature can't | readerC_arbitration_wave006.md:40, :43, :49 |
| Serock_1877_births_07-10.jpg | 9 | Mother's née initial К/В (Кацнеровска/Важнеровска) | Stroke overlap at this JPEG quality defeats К/В and ц/ж at 8× — rescan explicitly recommended | readerC_arbitration_wave006.md:28, :43 |
| Serock_1877_births_07-10.jpg | 10 | Birth hour (4 vs 6) | Right-page edge clips final tokens; ruled B only on «часовъ/часа» agreement logic — a rescan settles it | readerC_arbitration_wave006.md:22, :43, :50 |

## Not rescans — verification reads and reviews still owed

| Item | Owed work | Source |
| --- | --- | --- |
| Wave-005, act 13 declarant rows | Single-coverage; needs a verification read for a second vote before anything enters | …07-29_wave005_CONSENSUS.md:275–276, :284–285 |
| Wave-005, all 32 disputes | Reader C arbitration outstanding — "NO RESOLVED appendix yet" (worksheet: `readerC_arbitration_wave005_WORKSHEET.md`) | wave005_CONSENSUS:278, :284 |
| Wave-005 #20 / act 29 | Correction question unresolved | wave005_CONSENSUS:285 |
| Act 47 mother's née «Bogdan» | Single-coverage, explicitly NOT promoted | CONSENSUS_wave004:79, :146 |
| Standing witness (wave-003 item 20 / wave-005 #31) | Expert review, first chair — [Колтунъ/Килтуръ/Ковшунъ] × [работникъ/кладбищный служитель]; fields excluded from silver corpus-wide | wave003_CONSENSUS:274–279; CONSENSUS_wave004:150; wave005_CONSENSUS:189–192 |
| Act 48 declarant 1 surname | Resolved NEITHER; new pooled [unclear], no promotion — needs a fresh read | CONSENSUS_wave004:149 |
| Wave-006 acts 1 and 9 | Gated on the human-review queue in addition to the rescans above | readerC_arbitration_wave006.md:52 |
| Wave-006 July A session, acts 1–8 | Process audit recommended after the act-6 fabrication-class failure | readerC_arbitration_wave006.md:38 |

## Acquisition note

The register images derive from online genealogy photography of fond 73/826/0
(Serock civil registers); the fond shows zero official scans online, so better
images mean either higher-resolution photography of the originals or archival
reproduction on request. Any reacquisition should capture the **full spread at
maximum resolution with raking-light or contrast variants for the red-ink
layers** — the act-49 red layer and act-42 bleed-through are the two hardest
targets and should drive the quality bar.
