# Editorial correction completion — 9 October 2026

Completed locally under CREDIT_RISK_EDITORIAL_BRIEF_2026-10-09.md. No estimates, predictions, calibration, resampling, bins, source observations or frozen ledgers were changed. Publication/Drive approval is pending.

## Source identification and scope

The current three-report sources are in **credit-risk-sba-public**, starting from `57f2b2cfc8038aadfa1cdde988336587548b8e55`. The research checkout starts from `40c7c5ec9e3386dcf1ebfafcb5335da0e4e6b179` and contains the shared policy/technical sources; those sources, PDFs, headline figure, supplementary prose-cell map and reporting checks were mirrored. The working paper, notebook and public wrapper exist only in the public checkout. The two READMEs retain their respective layouts. DECISIONS.md has a new dated entry appended after the complete original bytes in each checkout.

The empirical release remains `8f7343584d55a14f8cae47c3e9fded3ed56503d4`. This is a presentation correction, not a new empirical release. All protected research code, specifications, generated numerical tables, aggregate results, claim registry and historical hash ledgers remain unchanged. The original published distribution ledger is retained; a separate PUBLIC_EDITORIAL_MANIFEST_2026-10-09.json describes the local current files.

## Required corrections

1. Policy note status is “October 2026 · Working paper”. Its obsolete external-release/local-draft statements are removed. Its no-new-analysis methods note remains.
2. Reader prose/captions use plain stage names, while historical documents and path/link targets keep their names. The exact new history sentence appears in all three PDFs, README and notebook markdown:

> The final estimation protocol was frozen after first-round results had been seen and before any final-round model was estimated. Deviations are logged in DECISIONS.md.

The post-results amendment, first-round failures, inherited 2003H1 settings, 2003H2 calibration, calendar overlap, reused 2013 cohort and future-path conditional validation remain disclosed.
3. Two descriptive saved-group paragraphs were added to the technical report (page 5) and working paper (page 6). The policy note contains a brief, number-free clause about the two highest crisis groups.
4. The full EAD/LGD/guarantee statement appears once per current PDF, README and notebook markdown. Loss captions use a short section/limitations reference. Every scenario/support caption keeps its fixed-2006-portfolio interpretation. No stress caption adopts the retrospective-validation label. Interval language now says which refits converged; the primary scenario count of 198/199 is explicitly scoped to that specification, not every model.
5. Optional literature additions were omitted because direct publisher/DOI verification could not be completed. No reference was silently supplied from secondary sources.
6. A local delivery copy is prepared in `delivery/credit-risk-sba-2026-10-09-editorial/` relative to the portfolio folder. It supersedes the prior 9 October delivery for reading only; both copies are retained. No upload has occurred.

## Replaced phrases and retained exceptions

| Prior phrase | Current wording/action |
|---|---|
| G1 | data and protocol stage; no baseline reader-surface occurrence needed replacement |
| G2 | first estimation round |
| G2-bis | final estimation round / final-round, as grammar requires |
| G5 | reporting stage / reporting checks / Report build notes |
| accepted research run / reviewed research snapshot / accepted run | saved results of the final estimation round / final estimation round, as context requires |
| accepted technical report | technical report |
| unchanged gate report | retained first-round report |
| October 2026 • Local review draft | October 2026 · Working paper |
| External release requires separate approval. | deleted from policy note |
| local drafts only | deleted from policy note |
| successful-draw conditioning | intervals use only the refits that converged (198 of 199 for the primary scenario model) |
| hybrid-path plausibility | whether mixed baseline/adverse paths are economically plausible |

The replacement includes the prior required history sentence as a whole. Full before/after line records for each repository are in `report/editorial/wording_replacements.json`; they intentionally contain old labels for auditing. Historical gate reports, old archives, original registry/source file names and paths remain untouched. PUBLIC_RELEASE.md and the working-paper build note distinguish their original historical basis from the current revision; current build instructions describe the isolated compiler.

## New calibration prose and exact cells

> In the 2007–2009 crisis cohort, the lowest training-score group has 0.70% predicted versus 5.22% recorded. The two highest groups have nearly equal recorded rates (16.72% and 16.42%) despite mean predictions of 6.02% and 13.16%. Descriptively, the error is more than a common level shift: the score separates recorded rates little at the top, consistent with the stored diagnostic slope of 0.314. No difference test or mechanism is inferred.

> For calibrated Layer 2 LightGBM in 2013–2014, predicted and recorded rates are close descriptively in training-score groups 1–8. Larger deviations appear in the two highest groups: 6.42% versus 3.49%, and 10.17% versus 5.81%. The latter contains only 155 loans, with a stored recorded-rate band of [2.41, 11.87]%. Average agreement coexists with overprediction in the highest-risk groups; the wide top-group band limits precision. These comparisons use saved groups and bands, without new intervals or tests.

All displayed values come from existing registered cells. The machine registry was not rewritten because these cells were already registered. The supplementary display macros and human CLAIMS.md additions bind to those same IDs and hashes. No new interval, difference test, bin edge, evaluation or equivalence test was calculated. The claim that groups 1–8 are descriptively close is supported by 16 additional saved mean-rate cells, not a statistical equivalence claim.

| Display macro | Existing cell ID | Unique selector | Column | Display |
|---|---|---|---|---|
| CrisisGroupOnePred | `N9044d0d913ef84` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, bin=1` | `predicted_pd` | 0.70 |
| CrisisGroupOneRecorded | `N1d1baf054f7f2f` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, bin=1` | `recorded_rate` | 5.22 |
| CrisisGroupNinePred | `Nfece26f5c2f5d2` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, bin=9` | `predicted_pd` | 6.02 |
| CrisisGroupNineRecorded | `Naacd5357c61b4b` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, bin=9` | `recorded_rate` | 16.72 |
| CrisisGroupTenPred | `N5c4e9b68430987` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, bin=10` | `predicted_pd` | 13.16 |
| CrisisGroupTenRecorded | `Nf23b0857a0e39d` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, bin=10` | `recorded_rate` | 16.42 |
| TreeGroupNinePred | `N7431e90143bb60` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=9` | `predicted_pd` | 6.42 |
| TreeGroupNineRecorded | `Nd9d972b86d8e80` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=9` | `recorded_rate` | 3.49 |
| TreeGroupTenPred | `N08df4340e58445` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=10` | `predicted_pd` | 10.17 |
| TreeGroupTenRecorded | `N972696014ba9f9` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=10` | `recorded_rate` | 5.81 |
| TreeGroupTenN | `Na0278d31b91525` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=10` | `n` | 155 |
| TreeGroupTenLower | `Nb99cd58f8c10b7` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=10` | `lower` | 2.41 |
| TreeGroupTenUpper | `Nd736db9631b846` | `variant=layer2, model=lightgbm_calibrated, cohort=post_amendment_validation_2013_2014, bin=10` | `upper` | 11.87 |
| CrisisDiagnosticSlope | `N3e3a57a63c1964` | `variant=layer1, model=firth_raw, cohort=crisis_2007_2009, metric=calibration_slope` | `value` | 0.314 |

Source for the groups is `results/g2-bis-2026-10-08/calibration_deciles.csv`; the diagnostic slope is from the existing `evaluation_metrics.csv`. The full 30 cell-use records, units/scales, selectors, source hashes and the 16 supporting group-1–8 means are in `report/editorial/calibration_prose_claims.json`. Registry bytes, original numerical macros and saved cutoffs/bands remain unchanged.

## Optional literature verification

- Bellotti and Crook: publisher-indexed metadata was visible, but the direct [publisher page](https://www.tandfonline.com/doi/abs/10.1057/jors.2008.130) returned 403. The required complete direct verification was not achieved; omitted.
- Glennon and Nigro: the [DOI page](https://doi.org/10.1353/mcb.2005.0051) could not be opened and publisher access was blocked. The required complete verification was not achieved; omitted.

The existing bibliography and verified-reference ledger are unchanged. These were bibliographic checks only; no loan, macro or other empirical data were acquired. Details: `report/editorial/literature_verification.json`.

## Validation and visual QA

- Public reporting suite: **74 passed, 7 deselected**. Research reporting suite: **68 passed, 1 deselected**. These are reporting checks, not a new statistical-validation run. The legacy full renderer is excluded because it regenerates reporting results/communication drafts; public-only exclusions additionally concern undistributed private preservation inventories/drafts or original commands. New editorial contract checks cover tampered cells, missing chronology, duplicated loss qualifications and mislabeled scenario captions.
- Ruff lint and formatting passed on eight changed reporting/build/test files. Mypy passed on five reporting/build modules; common research files are byte-identical. Diff whitespace checks passed.
- Public protected inventory: **249 files**, **25 archived originals**. Research editorial inventory: **351 files**, **15 archived originals**. The older research protection check also passed for **238 tracked** and **1,170 private** entries, with its original 21 archive mappings. These inventories overlap and must not be added together.
- Public validation checks the current separate distribution manifest, all **4,573 source-bound and 5 derived** registered cells, 18 saved tables, unchanged notebook code/stored outputs and the original working-paper input basis. The new prose adds 30 uses of already-registered cells.
- No notebook execution took place this round. Frozen output assertions were inspected/validated; code and stored outputs are byte-identical as cell objects to their archived original.
- The isolated PDF build used existing saved tables/macros only and cached TeX. No CV/LinkedIn draft was generated. Current report commands stage rebuilt presentation under ignored `data/editorial-2026-10-09/` instead of regenerating results directories. Numerical figure content is unchanged; its caveat was shortened.

| PDF | Pages | Visual result |
|---|---:|---|
| policy_note.pdf | 2 | both pages passed |
| technical_report.pdf | 10 | all pages passed |
| working_paper.pdf | 13 | all pages passed |

Every rendered page was checked for clipped text, overlap, readability, captions, required qualifications and pagination. No overfull/undefined-reference build issue was found. Two nonfatal caption hypcap warnings concern inline-table anchors. Per-page PDF/render hashes are in `report/editorial/visual_qa.json`; local PNG evidence remains in ignored `data/editorial-qa/` in the public checkout. Shared policy/technical PDFs in the research checkout are byte-identical to the inspected public versions.

| Document | Page | Visual check |
|---|---:|---|
| policy_note | 1 | passed |
| policy_note | 2 | passed |
| technical_report | 1 | passed |
| technical_report | 2 | passed |
| technical_report | 3 | passed |
| technical_report | 4 | passed |
| technical_report | 5 | passed |
| technical_report | 6 | passed |
| technical_report | 7 | passed |
| technical_report | 8 | passed |
| technical_report | 9 | passed |
| technical_report | 10 | passed |
| working_paper | 1 | passed |
| working_paper | 2 | passed |
| working_paper | 3 | passed |
| working_paper | 4 | passed |
| working_paper | 5 | passed |
| working_paper | 6 | passed |
| working_paper | 7 | passed |
| working_paper | 8 | passed |
| working_paper | 9 | passed |
| working_paper | 10 | passed |
| working_paper | 11 | passed |
| working_paper | 12 | passed |
| working_paper | 13 | passed |

## File changes and hashes

The following inventory was captured before adding this stop report and the separate current distribution manifest, to avoid recursive self-hashes. The delivery `CHANGE_HASHES.json` is the complete final before/after inventory for **all** changed/new tracked files, including this report, new manifests and archives, after both local commits. Null before-hash means a new file. No files were deleted.

### credit-risk-sba-public

| File | Before SHA-256 | After SHA-256 |
|---|---|---|
| `CLAIMS.md` | 6714658d5fa465cbc1f7c5942eb9b725a557a14961ef2cc412f82f0798d649a7 | ae4b19a1e1d196b04bfafd4ef667cfaf20258049ae786bc94aed9078b1281ae4 |
| `DECISIONS.md` | 7647efba69e74fcac4d90cea9d056a2b0ee06706de2ddbc67b08f14f29e3773b | 8d947523d8d23033202dae8b56fe3272000fce70980923e4cd44ffc09c9ad1ee |
| `Makefile` | 45711828c446fc544c1993ded11a69955325ce8f773c88453153e1b64bf735b1 | 511a7d0648ca6580d264af63b0c423dd2c529f52de70ef5cf96e016435c7b27c |
| `PUBLIC_RELEASE.md` | 27d907d82c64ab447f87f681b47f8a81d37dcacaea34de2044da2f46943f4f68 | 2796c98c22757b8c2b2974a2f60ddaf80fe26c3e06005caa0d2fb232cd1f1aa6 |
| `README.md` | 73ecc71ad00745428d99bd63e90d718884ffd22745839467d6d0d93c82559359 | 88eb2d42ce1c78df236215819b3053fd432a919f2c7ac11d4633d98c64145ee4 |
| `docs/WORKING_PAPER_2026-10-08.md` | ee3fd23ced2f3d03bb29f8720d01905506912a8609876548f361ae1114c5da1e | 8f9118fa1bfb1176e59430d3081f9c2a6efa5cf24ea249c3a736e5f216f687e4 |
| `docs/releases/pre-editorial-2026-10-09/ARCHIVE_MANIFEST.json` | new | 0f9735c2c9269d991e76fad602c86b8436c1c56b5e715646fce1bde65277adfd |
| `docs/releases/pre-editorial-2026-10-09/CITATION.cff` | new | 1637aaf19d00d0a1633f772345ec455502c087b37152470cb1249cf74308cea6 |
| `docs/releases/pre-editorial-2026-10-09/CLAIMS.md` | new | 6714658d5fa465cbc1f7c5942eb9b725a557a14961ef2cc412f82f0798d649a7 |
| `docs/releases/pre-editorial-2026-10-09/DECISIONS.md` | new | 7647efba69e74fcac4d90cea9d056a2b0ee06706de2ddbc67b08f14f29e3773b |
| `docs/releases/pre-editorial-2026-10-09/Makefile` | new | 45711828c446fc544c1993ded11a69955325ce8f773c88453153e1b64bf735b1 |
| `docs/releases/pre-editorial-2026-10-09/PUBLIC_RELEASE.md` | new | 27d907d82c64ab447f87f681b47f8a81d37dcacaea34de2044da2f46943f4f68 |
| `docs/releases/pre-editorial-2026-10-09/README.md` | new | 73ecc71ad00745428d99bd63e90d718884ffd22745839467d6d0d93c82559359 |
| `docs/releases/pre-editorial-2026-10-09/docs/WORKING_PAPER_2026-10-08.md` | new | ee3fd23ced2f3d03bb29f8720d01905506912a8609876548f361ae1114c5da1e |
| `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.pdf` | new | ca4d0169ac451b71b15c0761c40152cc8b91596554efc76fbc2c4c132bdd6d65 |
| `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.png` | new | 472d63f4e6286864f43c0db59e54f6b99e0f42e4f5cfca9a090231e54e3042e4 |
| `docs/releases/pre-editorial-2026-10-09/figures/g5/headline_caption.txt` | new | c8e07750d919d371d22393fbd18e65a9ce1cc3566a8e710367284f20b11617ac |
| `docs/releases/pre-editorial-2026-10-09/notebooks/research_walkthrough.ipynb` | new | 6972f07d1fce2145571d990acdde49f6a87f850f9da85c1cdc550815382589ff |
| `docs/releases/pre-editorial-2026-10-09/report/g5/policy_note.tex` | new | 5cf2493ad2610e83f712537b1bc385a11ba5945e2f3296fd5abec1f0dffad3b3 |
| `docs/releases/pre-editorial-2026-10-09/report/g5/preamble.tex` | new | 7092612ece93b9f41100f73ff9092e5873b2653bb09358bcb5adf17972b82aa5 |
| `docs/releases/pre-editorial-2026-10-09/report/g5/technical_report.tex` | new | 008b8797035fbce5cc8b536146620cbe9efce0b6a0100585870a24dcf3170d6f |
| `docs/releases/pre-editorial-2026-10-09/report/paper/preamble.tex` | new | 771acdeced114717f32a21a89384e9750e43196ded3f355f6b2232fced468508 |
| `docs/releases/pre-editorial-2026-10-09/report/paper/working_paper.tex` | new | c91c840859bf94ff1efd1d2e5aa184be80599a5172458127bf9a6072c1a9e0ac |
| `docs/releases/pre-editorial-2026-10-09/report/policy_note.pdf` | new | 742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f |
| `docs/releases/pre-editorial-2026-10-09/report/technical_report.pdf` | new | 09900699969dca2a636d32f10f0d556e782beebb4afde238c168a15e2d012695 |
| `docs/releases/pre-editorial-2026-10-09/report/working_paper.pdf` | new | aede34fb5d16a905f478ece1e58e4f8173de67f9f57a45a2246b433c152da2af |
| `docs/releases/pre-editorial-2026-10-09/reporting/checks.py` | new | f343fca7ca2823ce0346e922552cac4e054756a13bcc61426e6633b83e8dbaea |
| `docs/releases/pre-editorial-2026-10-09/reporting/g5.py` | new | 6eb53a0c1e92e9d3d45000c2f1dbeff7738deaefa9f82a16419946985f84be15 |
| `docs/releases/pre-editorial-2026-10-09/scripts/public_release.py` | new | cad75797a521b54fe4ec3a948fdb625376b36312cb93e06c3fb0958eb3056e6f |
| `docs/releases/pre-editorial-2026-10-09/scripts/working_paper.py` | new | 7d3777d5a6a0b0c6258649a0e36559ca5ad187b54b3caa69510da33410f31428 |
| `docs/releases/pre-editorial-2026-10-09/tests/test_g5_reporting.py` | new | 0035af02ee10ca5fe1a2189b11356a25920ef677865051f34445179f86081b79 |
| `docs/releases/pre-editorial-2026-10-09/tests/test_working_paper.py` | new | e31b356afd0db6bd68e64cebe87263c66b99fe25b023a98a238745e549e4d296 |
| `figures/g5/headline.pdf` | ca4d0169ac451b71b15c0761c40152cc8b91596554efc76fbc2c4c132bdd6d65 | 98925f3a64d16223a85f79e42bca5aacf049a8e63776a852d9a02932fea86b95 |
| `figures/g5/headline.png` | 472d63f4e6286864f43c0db59e54f6b99e0f42e4f5cfca9a090231e54e3042e4 | cd40db0548bf03fdc13c3841fc0c4806d3bd18a5d45a54ddd8f80e5707954ec4 |
| `figures/g5/headline_caption.txt` | c8e07750d919d371d22393fbd18e65a9ce1cc3566a8e710367284f20b11617ac | 1c4e95bd803bc2f129cbbc2db8094c41b7109f442dee8c4348ea569bebf7903d |
| `notebooks/research_walkthrough.ipynb` | 6972f07d1fce2145571d990acdde49f6a87f850f9da85c1cdc550815382589ff | 1dc15bb92135ac472bda9449ce2b962ee2730d04e4d25b34fa80f2a7def979d3 |
| `report/editorial/calibration_prose_claims.json` | new | 5da97a731845cf06142a559a761fddd870027a90718dcef4c36ea37302aab410 |
| `report/editorial/literature_verification.json` | new | b3a35529b0d3ce13d96f6828cbffddeb7062bd7996c966fa384f68df8f24bbdf |
| `report/editorial/verification.json` | new | ec5e84289cd0027530f27733ab8c915917850888460bfc9c1ebb6132bc317175 |
| `report/editorial/visual_qa.json` | new | 32a637a52984833693ff10ed752a36d676db7f91f8ab09628bcd9d9570bc85a0 |
| `report/editorial/wording_replacements.json` | new | b40cedeba160011d95592f200adf5ff66532e4eaebd66374a06a6b75c0364ab0 |
| `report/g5/generated/editorial_numbers.tex` | new | f600ac4ceab9e8aa8c3796ae591939f3be2dcd286bbae0dc39d01228d2ca8d63 |
| `report/g5/policy_note.tex` | 5cf2493ad2610e83f712537b1bc385a11ba5945e2f3296fd5abec1f0dffad3b3 | 0131c1b2eddc73964b2d90c117d6922ae1ca5753e45afb266aeba2145c9377b0 |
| `report/g5/preamble.tex` | 7092612ece93b9f41100f73ff9092e5873b2653bb09358bcb5adf17972b82aa5 | 9bc774a7ea1eb3ea921c7d5bfba15e380544bdd98340a698cdb03a83626f41fc |
| `report/g5/technical_report.tex` | 008b8797035fbce5cc8b536146620cbe9efce0b6a0100585870a24dcf3170d6f | cceaf71cd84769b0e1c75eca368621140f4bd951d550ad8c0c636332a8e78dff |
| `report/paper/preamble.tex` | 771acdeced114717f32a21a89384e9750e43196ded3f355f6b2232fced468508 | 3caad0739f1946e0499b21ca3f3cce4efbda5ac3a4d9af43c63475cc55f3b2ad |
| `report/paper/working_paper.tex` | c91c840859bf94ff1efd1d2e5aa184be80599a5172458127bf9a6072c1a9e0ac | 03810af0abb41b0907e79220ae29cd9a071185beb8f4be74424c45f38ba3168f |
| `report/policy_note.pdf` | 742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f | 5a0d84c8177b40eb766942cc13efc5a6e469554006d6a2d93e7ff885f2b4af48 |
| `report/technical_report.pdf` | 09900699969dca2a636d32f10f0d556e782beebb4afde238c168a15e2d012695 | c80fefa1c7b0fc8d00f53b62405581d829944dd68e0df53d7018f9cf2ba86748 |
| `report/working_paper.pdf` | aede34fb5d16a905f478ece1e58e4f8173de67f9f57a45a2246b433c152da2af | c33fd47be4480cb6d565eddba46266c0a9d719c420426ab1fa23792319cb0aa7 |
| `reporting/checks.py` | f343fca7ca2823ce0346e922552cac4e054756a13bcc61426e6633b83e8dbaea | ef1a85c89a45609cbdfd6b3e42ea87d11d984a434031dc2d845edec19fabdc73 |
| `reporting/editorial.py` | new | 10ed415507aa77ada91d8d8df11cb094b075a67005dfea819156e3877d992c3f |
| `reporting/g5.py` | 6eb53a0c1e92e9d3d45000c2f1dbeff7738deaefa9f82a16419946985f84be15 | 0cffe417a968e209b128e9b197f5240d401bae17010a73f69f4ef1e006542109 |
| `scripts/public_release.py` | cad75797a521b54fe4ec3a948fdb625376b36312cb93e06c3fb0958eb3056e6f | 0657c779364794646bc55368192e67bc5852877d114ce09f635b0412443a9afc |
| `scripts/working_paper.py` | 7d3777d5a6a0b0c6258649a0e36559ca5ad187b54b3caa69510da33410f31428 | ac0653b46bc731c0f0cdcb3a1fae82e3cab874a1526ac4f4afd8e8e5a0da5045 |
| `tests/test_editorial.py` | new | 357d60975515c60283f8e9f3dfe88e3972fe6678e72ff6142e4acf74540b5229 |
| `tests/test_g5_reporting.py` | 0035af02ee10ca5fe1a2189b11356a25920ef677865051f34445179f86081b79 | 6210f6fd987ba3adb685203426720934505309e5ce938c539899e97ab936eb87 |
| `tests/test_working_paper.py` | e31b356afd0db6bd68e64cebe87263c66b99fe25b023a98a238745e549e4d296 | c1184ce85729b413f7b0f8e413417cc05e6a3ac0d19caaf712606d03054acd20 |

### credit-risk-sba

| File | Before SHA-256 | After SHA-256 |
|---|---|---|
| `CLAIMS.md` | 6714658d5fa465cbc1f7c5942eb9b725a557a14961ef2cc412f82f0798d649a7 | ae4b19a1e1d196b04bfafd4ef667cfaf20258049ae786bc94aed9078b1281ae4 |
| `DECISIONS.md` | 7647efba69e74fcac4d90cea9d056a2b0ee06706de2ddbc67b08f14f29e3773b | 8d947523d8d23033202dae8b56fe3272000fce70980923e4cd44ffc09c9ad1ee |
| `Makefile` | 02f7794ba301d2cb111e68138e365d3d5cb6955962f6992d68ca0ab50d1a6f4b | 569437bbe296e490b7c023669417f35163c35c91fe643aff946548b13a3d2900 |
| `README.md` | fa24ff5d95b7cb780f1544006c65450de877e5439259111ee3c0472299bad8e7 | 9d9a9992e1afa06443b9091017838aaf1dd3481a9ac57b47bb1f0f78e924a328 |
| `docs/releases/pre-editorial-2026-10-09/ARCHIVE_MANIFEST.json` | new | af945a713a2709b49c5ef5852591b126440c9ba7d5d3e5a562a1fd0e2058cdd8 |
| `docs/releases/pre-editorial-2026-10-09/CLAIMS.md` | new | 6714658d5fa465cbc1f7c5942eb9b725a557a14961ef2cc412f82f0798d649a7 |
| `docs/releases/pre-editorial-2026-10-09/DECISIONS.md` | new | 7647efba69e74fcac4d90cea9d056a2b0ee06706de2ddbc67b08f14f29e3773b |
| `docs/releases/pre-editorial-2026-10-09/Makefile` | new | 02f7794ba301d2cb111e68138e365d3d5cb6955962f6992d68ca0ab50d1a6f4b |
| `docs/releases/pre-editorial-2026-10-09/README.md` | new | fa24ff5d95b7cb780f1544006c65450de877e5439259111ee3c0472299bad8e7 |
| `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.pdf` | new | ca4d0169ac451b71b15c0761c40152cc8b91596554efc76fbc2c4c132bdd6d65 |
| `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.png` | new | 472d63f4e6286864f43c0db59e54f6b99e0f42e4f5cfca9a090231e54e3042e4 |
| `docs/releases/pre-editorial-2026-10-09/figures/g5/headline_caption.txt` | new | c8e07750d919d371d22393fbd18e65a9ce1cc3566a8e710367284f20b11617ac |
| `docs/releases/pre-editorial-2026-10-09/report/g5/policy_note.tex` | new | 5cf2493ad2610e83f712537b1bc385a11ba5945e2f3296fd5abec1f0dffad3b3 |
| `docs/releases/pre-editorial-2026-10-09/report/g5/preamble.tex` | new | 5d59a143bea3128487287ace7b4412613a1d61e96097d30ee94ca7b52649d178 |
| `docs/releases/pre-editorial-2026-10-09/report/g5/technical_report.tex` | new | 6725d18c1aaf369f41c424aeb6abaa3e4bd82db543fcd02e010822151e6cfa40 |
| `docs/releases/pre-editorial-2026-10-09/report/policy_note.pdf` | new | 742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f |
| `docs/releases/pre-editorial-2026-10-09/report/technical_report.pdf` | new | bfa6f907f578ed4f4566c8b18a86b60ec2eece2e02a86a82ec410a642e861428 |
| `docs/releases/pre-editorial-2026-10-09/reporting/checks.py` | new | f343fca7ca2823ce0346e922552cac4e054756a13bcc61426e6633b83e8dbaea |
| `docs/releases/pre-editorial-2026-10-09/reporting/g5.py` | new | 6eb53a0c1e92e9d3d45000c2f1dbeff7738deaefa9f82a16419946985f84be15 |
| `docs/releases/pre-editorial-2026-10-09/tests/test_g5_reporting.py` | new | 0035af02ee10ca5fe1a2189b11356a25920ef677865051f34445179f86081b79 |
| `figures/g5/headline.pdf` | ca4d0169ac451b71b15c0761c40152cc8b91596554efc76fbc2c4c132bdd6d65 | 98925f3a64d16223a85f79e42bca5aacf049a8e63776a852d9a02932fea86b95 |
| `figures/g5/headline.png` | 472d63f4e6286864f43c0db59e54f6b99e0f42e4f5cfca9a090231e54e3042e4 | cd40db0548bf03fdc13c3841fc0c4806d3bd18a5d45a54ddd8f80e5707954ec4 |
| `figures/g5/headline_caption.txt` | c8e07750d919d371d22393fbd18e65a9ce1cc3566a8e710367284f20b11617ac | 1c4e95bd803bc2f129cbbc2db8094c41b7109f442dee8c4348ea569bebf7903d |
| `report/editorial/calibration_prose_claims.json` | new | 5da97a731845cf06142a559a761fddd870027a90718dcef4c36ea37302aab410 |
| `report/editorial/literature_verification.json` | new | b3a35529b0d3ce13d96f6828cbffddeb7062bd7996c966fa384f68df8f24bbdf |
| `report/editorial/validation_checks.json` | new | 775fe79d9cf9cef8ab2b0509504f60b5687e575a8682f4d818ac1e15083b9352 |
| `report/editorial/verification.json` | new | a71322920c13efa5d2d44778a5aa2c7e16db8ae2e2f47ee7115cc455db5bf8a6 |
| `report/editorial/visual_qa.json` | new | 22538d56ccef9ec4697d8bd85061bcb1d05963e587c1a8f9bf51c898b2433f97 |
| `report/editorial/wording_replacements.json` | new | 8ddfc4d3436386e0f20c176c2cf34e6d82891e3e8d84096de4dde884d9ed76e5 |
| `report/g5/generated/editorial_numbers.tex` | new | f600ac4ceab9e8aa8c3796ae591939f3be2dcd286bbae0dc39d01228d2ca8d63 |
| `report/g5/policy_note.tex` | 5cf2493ad2610e83f712537b1bc385a11ba5945e2f3296fd5abec1f0dffad3b3 | 0131c1b2eddc73964b2d90c117d6922ae1ca5753e45afb266aeba2145c9377b0 |
| `report/g5/preamble.tex` | 5d59a143bea3128487287ace7b4412613a1d61e96097d30ee94ca7b52649d178 | 9bc774a7ea1eb3ea921c7d5bfba15e380544bdd98340a698cdb03a83626f41fc |
| `report/g5/technical_report.tex` | 6725d18c1aaf369f41c424aeb6abaa3e4bd82db543fcd02e010822151e6cfa40 | cceaf71cd84769b0e1c75eca368621140f4bd951d550ad8c0c636332a8e78dff |
| `report/policy_note.pdf` | 742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f | 5a0d84c8177b40eb766942cc13efc5a6e469554006d6a2d93e7ff885f2b4af48 |
| `report/technical_report.pdf` | bfa6f907f578ed4f4566c8b18a86b60ec2eece2e02a86a82ec410a642e861428 | c80fefa1c7b0fc8d00f53b62405581d829944dd68e0df53d7018f9cf2ba86748 |
| `reporting/checks.py` | f343fca7ca2823ce0346e922552cac4e054756a13bcc61426e6633b83e8dbaea | ef1a85c89a45609cbdfd6b3e42ea87d11d984a434031dc2d845edec19fabdc73 |
| `reporting/editorial.py` | new | 10ed415507aa77ada91d8d8df11cb094b075a67005dfea819156e3877d992c3f |
| `reporting/g5.py` | 6eb53a0c1e92e9d3d45000c2f1dbeff7738deaefa9f82a16419946985f84be15 | 0cffe417a968e209b128e9b197f5240d401bae17010a73f69f4ef1e006542109 |
| `tests/test_editorial.py` | new | 357d60975515c60283f8e9f3dfe88e3972fe6678e72ff6142e4acf74540b5229 |
| `tests/test_g5_reporting.py` | 0035af02ee10ca5fe1a2189b11356a25920ef677865051f34445179f86081b79 | 6210f6fd987ba3adb685203426720934505309e5ce938c539899e97ab936eb87 |

## Archive mappings

Archives were made before replacement. Each SHA-256 is identical for original bytes and the archived copy. Full baseline file hashes and mappings are recorded separately in each new `docs/releases/pre-editorial-2026-10-09/ARCHIVE_MANIFEST.json`; historical ledgers were not rewritten.

### credit-risk-sba-public

| Original | Archive | SHA-256 |
|---|---|---|
| `README.md` | `docs/releases/pre-editorial-2026-10-09/README.md` | 73ecc71ad00745428d99bd63e90d718884ffd22745839467d6d0d93c82559359 |
| `CLAIMS.md` | `docs/releases/pre-editorial-2026-10-09/CLAIMS.md` | 6714658d5fa465cbc1f7c5942eb9b725a557a14961ef2cc412f82f0798d649a7 |
| `DECISIONS.md` | `docs/releases/pre-editorial-2026-10-09/DECISIONS.md` | 7647efba69e74fcac4d90cea9d056a2b0ee06706de2ddbc67b08f14f29e3773b |
| `Makefile` | `docs/releases/pre-editorial-2026-10-09/Makefile` | 45711828c446fc544c1993ded11a69955325ce8f773c88453153e1b64bf735b1 |
| `PUBLIC_RELEASE.md` | `docs/releases/pre-editorial-2026-10-09/PUBLIC_RELEASE.md` | 27d907d82c64ab447f87f681b47f8a81d37dcacaea34de2044da2f46943f4f68 |
| `scripts/public_release.py` | `docs/releases/pre-editorial-2026-10-09/scripts/public_release.py` | cad75797a521b54fe4ec3a948fdb625376b36312cb93e06c3fb0958eb3056e6f |
| `scripts/working_paper.py` | `docs/releases/pre-editorial-2026-10-09/scripts/working_paper.py` | 7d3777d5a6a0b0c6258649a0e36559ca5ad187b54b3caa69510da33410f31428 |
| `reporting/g5.py` | `docs/releases/pre-editorial-2026-10-09/reporting/g5.py` | 6eb53a0c1e92e9d3d45000c2f1dbeff7738deaefa9f82a16419946985f84be15 |
| `reporting/checks.py` | `docs/releases/pre-editorial-2026-10-09/reporting/checks.py` | f343fca7ca2823ce0346e922552cac4e054756a13bcc61426e6633b83e8dbaea |
| `tests/test_g5_reporting.py` | `docs/releases/pre-editorial-2026-10-09/tests/test_g5_reporting.py` | 0035af02ee10ca5fe1a2189b11356a25920ef677865051f34445179f86081b79 |
| `tests/test_working_paper.py` | `docs/releases/pre-editorial-2026-10-09/tests/test_working_paper.py` | e31b356afd0db6bd68e64cebe87263c66b99fe25b023a98a238745e549e4d296 |
| `report/g5/preamble.tex` | `docs/releases/pre-editorial-2026-10-09/report/g5/preamble.tex` | 7092612ece93b9f41100f73ff9092e5873b2653bb09358bcb5adf17972b82aa5 |
| `report/g5/policy_note.tex` | `docs/releases/pre-editorial-2026-10-09/report/g5/policy_note.tex` | 5cf2493ad2610e83f712537b1bc385a11ba5945e2f3296fd5abec1f0dffad3b3 |
| `report/g5/technical_report.tex` | `docs/releases/pre-editorial-2026-10-09/report/g5/technical_report.tex` | 008b8797035fbce5cc8b536146620cbe9efce0b6a0100585870a24dcf3170d6f |
| `report/paper/preamble.tex` | `docs/releases/pre-editorial-2026-10-09/report/paper/preamble.tex` | 771acdeced114717f32a21a89384e9750e43196ded3f355f6b2232fced468508 |
| `report/paper/working_paper.tex` | `docs/releases/pre-editorial-2026-10-09/report/paper/working_paper.tex` | c91c840859bf94ff1efd1d2e5aa184be80599a5172458127bf9a6072c1a9e0ac |
| `report/policy_note.pdf` | `docs/releases/pre-editorial-2026-10-09/report/policy_note.pdf` | 742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f |
| `report/technical_report.pdf` | `docs/releases/pre-editorial-2026-10-09/report/technical_report.pdf` | 09900699969dca2a636d32f10f0d556e782beebb4afde238c168a15e2d012695 |
| `report/working_paper.pdf` | `docs/releases/pre-editorial-2026-10-09/report/working_paper.pdf` | aede34fb5d16a905f478ece1e58e4f8173de67f9f57a45a2246b433c152da2af |
| `figures/g5/headline.pdf` | `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.pdf` | ca4d0169ac451b71b15c0761c40152cc8b91596554efc76fbc2c4c132bdd6d65 |
| `figures/g5/headline.png` | `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.png` | 472d63f4e6286864f43c0db59e54f6b99e0f42e4f5cfca9a090231e54e3042e4 |
| `figures/g5/headline_caption.txt` | `docs/releases/pre-editorial-2026-10-09/figures/g5/headline_caption.txt` | c8e07750d919d371d22393fbd18e65a9ce1cc3566a8e710367284f20b11617ac |
| `notebooks/research_walkthrough.ipynb` | `docs/releases/pre-editorial-2026-10-09/notebooks/research_walkthrough.ipynb` | 6972f07d1fce2145571d990acdde49f6a87f850f9da85c1cdc550815382589ff |
| `CITATION.cff` | `docs/releases/pre-editorial-2026-10-09/CITATION.cff` | 1637aaf19d00d0a1633f772345ec455502c087b37152470cb1249cf74308cea6 |
| `docs/WORKING_PAPER_2026-10-08.md` | `docs/releases/pre-editorial-2026-10-09/docs/WORKING_PAPER_2026-10-08.md` | ee3fd23ced2f3d03bb29f8720d01905506912a8609876548f361ae1114c5da1e |

### credit-risk-sba

| Original | Archive | SHA-256 |
|---|---|---|
| `README.md` | `docs/releases/pre-editorial-2026-10-09/README.md` | fa24ff5d95b7cb780f1544006c65450de877e5439259111ee3c0472299bad8e7 |
| `CLAIMS.md` | `docs/releases/pre-editorial-2026-10-09/CLAIMS.md` | 6714658d5fa465cbc1f7c5942eb9b725a557a14961ef2cc412f82f0798d649a7 |
| `DECISIONS.md` | `docs/releases/pre-editorial-2026-10-09/DECISIONS.md` | 7647efba69e74fcac4d90cea9d056a2b0ee06706de2ddbc67b08f14f29e3773b |
| `Makefile` | `docs/releases/pre-editorial-2026-10-09/Makefile` | 02f7794ba301d2cb111e68138e365d3d5cb6955962f6992d68ca0ab50d1a6f4b |
| `reporting/g5.py` | `docs/releases/pre-editorial-2026-10-09/reporting/g5.py` | 6eb53a0c1e92e9d3d45000c2f1dbeff7738deaefa9f82a16419946985f84be15 |
| `reporting/checks.py` | `docs/releases/pre-editorial-2026-10-09/reporting/checks.py` | f343fca7ca2823ce0346e922552cac4e054756a13bcc61426e6633b83e8dbaea |
| `tests/test_g5_reporting.py` | `docs/releases/pre-editorial-2026-10-09/tests/test_g5_reporting.py` | 0035af02ee10ca5fe1a2189b11356a25920ef677865051f34445179f86081b79 |
| `report/g5/preamble.tex` | `docs/releases/pre-editorial-2026-10-09/report/g5/preamble.tex` | 5d59a143bea3128487287ace7b4412613a1d61e96097d30ee94ca7b52649d178 |
| `report/g5/policy_note.tex` | `docs/releases/pre-editorial-2026-10-09/report/g5/policy_note.tex` | 5cf2493ad2610e83f712537b1bc385a11ba5945e2f3296fd5abec1f0dffad3b3 |
| `report/g5/technical_report.tex` | `docs/releases/pre-editorial-2026-10-09/report/g5/technical_report.tex` | 6725d18c1aaf369f41c424aeb6abaa3e4bd82db543fcd02e010822151e6cfa40 |
| `report/policy_note.pdf` | `docs/releases/pre-editorial-2026-10-09/report/policy_note.pdf` | 742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f |
| `report/technical_report.pdf` | `docs/releases/pre-editorial-2026-10-09/report/technical_report.pdf` | bfa6f907f578ed4f4566c8b18a86b60ec2eece2e02a86a82ec410a642e861428 |
| `figures/g5/headline.pdf` | `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.pdf` | ca4d0169ac451b71b15c0761c40152cc8b91596554efc76fbc2c4c132bdd6d65 |
| `figures/g5/headline.png` | `docs/releases/pre-editorial-2026-10-09/figures/g5/headline.png` | 472d63f4e6286864f43c0db59e54f6b99e0f42e4f5cfca9a090231e54e3042e4 |
| `figures/g5/headline_caption.txt` | `docs/releases/pre-editorial-2026-10-09/figures/g5/headline_caption.txt` | c8e07750d919d371d22393fbd18e65a9ce1cc3566a8e710367284f20b11617ac |

## Delivery and stop boundary

The new local folder contains corrected PDFs, README, notebook, the local-public-commit snapshot ZIP, DELIVERY_INDEX.md, MANIFEST.json, SHA256SUMS and final CHANGE_HASHES.json. The index retains the earlier delivery and marks the new copy as superseding it for reading. Snapshot contents are allowlisted Git-tracked public files; no borrower records, fitted models, private predictions, runtime caches, credentials, CV, LinkedIn or email draft files are included. Communication-draft language is absent from the delivery index.

Current PDF link paths did not change. Live website/PDF verification of this revision is deferred until Hakan approves and the public commit is pushed; the website and published files were not edited. Both repositories are committed locally and checked clean; final commit IDs and the exact final-tree before/after hashes are in the local delivery manifest. Earlier delivery folders remain unchanged.

Nothing was pushed, uploaded, shared or published. No website or CV file was edited. No fitting, prediction, recalibration, bootstrap, binning, empirical data access/refresh or paid calls occurred. Stop here and await separate approval for public-repository push and Drive upload; the old Drive folder is retained.
