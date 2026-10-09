# Gate 1 — data source and licence check

**Historical extract review, retained unchanged below.** Amendment A1 subsequently made official SBA FOIA the primary source. The earlier protocol hold is superseded by the approved Layer 2/EAD decisions. Current source findings: [DATA.md](../DATA.md); frozen design: [PROTOCOL.md](PROTOCOL.md). The mirror remains a qualified fallback/sensitivity source, not the primary modelling population.

Checked 8 October 2026. This is a source review, not a fitted-model result or an approved rebuild protocol. Hakan requested that `PROTOCOL.md` remain unwritten until the macro-conditional PD design decision arrives.

## Source and attribution

Min Li, Amy Mickel and Stanley Taylor (2018), **“Should This Loan be Approved or Denied?”: A Large Dataset with Class Assignment Guidelines**, *Journal of Statistics Education*, **26(1), 55–66**, DOI [10.1080/10691898.2018.1434342](https://doi.org/10.1080/10691898.2018.1434342). Bibliographic details and the article licence were cross-checked against [Crossref's publisher-deposited record](https://api.crossref.org/works/10.1080/10691898.2018.1434342) and the [publisher's article record](https://www.tandfonline.com/doi/full/10.1080/10691898.2018.1434342).

The publisher identifies National SBA and SBA Case files with accompanying documentation as supplementary material. The fetched mirror's dictionary identifies the source as the United States Small Business Administration and its submitters as Li, Mickel and Taylor. It describes **899,164 observations, 27 variables, historical coverage 1987–2014**. These are **documentation counts**, not newly computed CSV counts. The review concerns National SBA, not the smaller case-study sample. Attribution is consistent with the published source; byte identity with the publisher's CSV has not been established.

## Actual copy inspected

The unchanged [`scripts/fetch_data.py:10`](../scripts/fetch_data.py) points to this [LRZ public ZIP](https://syncandshare.lrz.de/dl/fi7RqQyyVyyUs1Gsvu7dHa/sba-loan-data.zip). A public HEAD request returned HTTP 200. Bounded HTTP range requests returned HTTP 206 and exposed the ZIP directory and the documentation member. **The loan CSV and full archive were not downloaded; the existing fetcher was not executed.**

| Archive member | Compressed bytes | Uncompressed bytes |
|---|---:|---:|
| `sba-loan-data/` | 0 | 0 |
| `sba-loan-data/SBAnational.csv` | 45,017,581 | 179,430,516 |
| `sba-loan-data/SBA_Data_Documentation.docx` | 15,761 | 18,567 |

The ZIP's HTTP-reported length is **45,033,868 bytes**. Member sizes come from its central directory. The extracted dictionary passed ZIP CRC-32 and length checks and was read in full with Pandoc. Its SHA-256 is:

```text
2425e0f035b9ef757eddbc0ec8275ae0f157d1eee4a26c722203dd30f3f356fd
```

The private review copy is outside the repository at `../.cache/credit-risk-gate1/SBA_Data_Documentation.docx`. There is **no full-archive or CSV SHA-256** because neither complete file was fetched. No licence/readme member appears in the ZIP directory; the dictionary contains no licence grant. Public inspection metadata and baseline source hashes are in [gate1_review_evidence.json](gate1_review_evidence.json).

## Licence and hosting terms — distinct findings

- **Article licence: verified CC BY 4.0.** The article's copyright statement and Crossref's `content-version: vor` licence record identify [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). This is evidence about the article; it does not independently prove the licence of the LRZ CSV.
- **Mirror's data-specific licence: unverified.** Neither the archive inventory nor the dictionary supplies one. The publisher's supplementary landing page could not be retrieved during this check. No dataset-specific permission statement or canonical CSV checksum was obtained. A general open-access policy or a third-party mirror's licence should not be substituted for a licence covering these files.
- **LRZ service terms: verified.** [LRZ Sync+Share terms](https://syncandshare.lrz.de/tos), version **1.7, 15 July 2024**, apply to service users, including authorized external users. Section 4 places responsibility for copyright and permitted distribution on the folder owner. Service access supplies no independent blanket data-reuse grant. LRZ also disclaims indefinite readability and ties retention to the hosting account (sections 3 and 8).

**Disposition:** attribution and article licence confirmed; mirror's data licence remains an open source qualification. Before Gate 2 acquisition/reuse, establish a data-specific licence or documented permission for the actual source. Nothing has been redistributed or added to Git from the archive. No author, publisher or host has been contacted.

## What the source can establish about the target

The [paper, §3.3](https://www.tandfonline.com/doi/abs/10.1080/10691898.2018.1434342), explicitly warns that the extract is restricted to known outcomes and that this favors early charge-offs over unresolved long-maturity loans in recent cohorts. This confirms an outcome-selection problem, not merely unequal loan ages.

For the requested 36-month target, the inferential consequence is that restricting disbursements to cutoff minus 36 months is necessary for administrative follow-up but **does not reconstruct missing survivors**. A model trained on this extract cannot automatically be described as population origination PD. The cohort denominator, active-loan coverage, administrative as-of date and charge-off-date completeness need evidence before that claim is supportable. The dictionary's historical year range supplies no precise as-of day. No cutoff day has been invented and no removal counts have been computed.

The dictionary defines `ApprovalDate` as the SBA commitment date, `Term` as loan term in months, `DisbursementGross` as amount disbursed, `SBA_Appv` as SBA's guaranteed approved amount, and `ChgOffDate` as the default declaration date. It gives no measurement vintage for `Term`, `CreateJob` or `RetainedJob`, and does not establish that total disbursements were known on the first disbursement date. These are unresolved timing facts; the complete feature-eligibility table belongs in the pending protocol.

## Repository lineage and stopping point

The analysis started from an earlier internal version of this project; that version is not part of this repository. The local `v1-original` tag preserves **`1a4e1aca4474778b43fdbfbbdccd8003eee4c70c`**. The clone contains **26 commits** and is not shallow; its recorded authors are Hakan Zeki Gülmez and `kbekk`. The inherited README's other repository reference is recorded as an issue, not evidence of a formal GitHub fork or permission. The repository has no tracked `LICENSE` file; no new licence has been assigned to inherited code.

All original tracked files, including notebook outputs, models and PDFs, remain unchanged. No preprocessing, fitting, tuning, ablation or score reproduction has run. During review, the v2 brief was moved to `../_archive/2026-10-08/` and `../CREDIT_RISK_SPEC_v3_2026-10-08.md` appeared. The v3 file was read fully; its presence has not been treated as lifting Hakan's explicit hold on `PROTOCOL.md`. Gate 1 remains incomplete, and no later gate has started. The next design decision must account for the confirmed selected-outcome sample as well as macro conditioning.
