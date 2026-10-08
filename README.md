# Local economic conditions and public–lender loss sharing in SBA 7(a) lending

How do recorded charge-off risk and assumption-based loss sharing vary across cohorts and fixed macroeconomic scenarios in SBA 7(a) lending?

![Discrimination, calibration and conditional scenarios](figures/g5/headline.png)

## Findings

1. Out-of-time discrimination is modest: Term-free Firth crisis AUC 0.607 [0.587, 0.626] and later-cohort AUC 0.666 [0.638, 0.691]. Crisis prediction is 5.73% versus 12.25% recorded; later prediction is 4.50% versus 1.49% recorded.
2. On the observed fixed portfolio, a conditional +1 pp endpoint unemployment change is associated with 0.535 [0.266, 0.772] pp higher probability; the separately estimated peak-path sensitivity gives 0.679 [0.439, 0.933] pp. Neither is causal or a derivative.
3. Baseline/adverse EL proxies are $215.6m / $572.9m. The paired difference is $357.3 [304.9, 411.9]m; pro-rata SBA shares are 62.80% / 62.97%, not measured public costs.

## Method

We estimate Term-free Firth logistic scorecards for recorded charge-off within 36 months of first disbursement. Layer 1 reconstructs approval descriptors from a snapshot; Layer 2 adds future realized or stipulated state unemployment and house-price paths and is a conditional exercise. ElasticNet/LightGBM benchmark tuning occurred on 2003H1 in G2, and the selected settings and boosting rounds were inherited unchanged by G2-bis; benchmark calibration uses separate cohorts. Training-state multiplier refits and fitted-model conditional evaluation bands measure different uncertainty components.

## Data and chronology

Official SBA 7(a) FOIA, snapshot 30 June 2026, plus direct BLS LAUS and FHFA all-transactions state HPI. No FRED observations; see [DATA.md](DATA.md) for source terms and frozen hashes. This product uses FHFA data but is neither endorsed nor certified by FHFA.

Layer 1: fit 1991–2002; tune 2003H1 in G2; calibrate benchmarks 2003H2; evaluate 2007–2009 and 2011–2013. Layer 2: fit 1991–2009; calibrate LightGBM on 2010; check 2013–2014. **Retrospective conditional validation using realized macro paths.** Calibration labels extend to end-2013; the 2013 cohort was seen previously. The fixed 2006 scenario portfolio enters Layer 2 estimation.

The G2-bis protocol was frozen after the G2 results had been seen and before any G2-bis model was estimated. Deviations are logged in DECISIONS.md.

## Read and reproduce

[Two-page policy note](report/policy_note.pdf) · [Technical report](report/technical_report.pdf) · [Claims/provenance](CLAIMS.md)

```sh
make report        # rebuild in an isolated directory; no fitting
make report-test   # reporting tests; no fitting
make report-check  # public-file hashes, claims and report checks
```

Python 3.11 and the locked environment in `uv.lock` are required. Use `uv sync --frozen --python 3.11`, then `make report-check REPORT_PYTHON=.venv/bin/python` and `make report-test REPORT_PYTHON=.venv/bin/python`. PDF rebuilding additionally requires Poppler (`pdfinfo`) and Tectonic with cached TeX packages; set `TECTONIC` to its executable. Rebuilds are offline and write only under ignored `data/public-report-rebuild/`. No raw loans, private predictions or fitted models are needed. [Public release and reproduction](PUBLIC_RELEASE.md) explains the exported snapshot and validation scope; the original [G5 build notes](docs/G5_REPRODUCTION.md) remain dated evidence.

## What changed from v1

The resolved-loans extract was replaced by official FOIA status coverage because selection on final loan outcome cannot be repaired with an age filter. The analysis defines complete calendar-month charge-off windows, uses separate temporal roles, excludes reported Term from primary specifications and distinguishes prediction from future-path conditioning. Failed ordinary logit fits led to an explicitly post-results protocol amendment and Firth estimation. These are joint changes in source, estimand and design; legacy and current metrics are not like-for-like performance comparisons. The original Git history, `v1-original` tag, superseded reports and full local research archive are retained outside this public snapshot. Dated G2 and G2-bis aggregate results and protocol versions are included here.

## Limitations and future work

- Administrative charge-off and mature EXEMPT classification do not measure delinquency or verify performance; the sample excludes rejected applicants.
- Descriptor/Term vintages remain unverified, rates are largely missing, and revised macro data are not historical information sets.
- Calibration fails across cohorts; average agreement in calibrated Layer 2 LightGBM does not establish group calibration. Post-results amendments and reused/calendar-overlapping cohorts limit confirmatory claims.
- EAD = GrossApproval; full-disbursement proxy, CCF = 100%. LGD is the gross charge-off proxy on the same approval denominator. SBA/lender amounts use assumption-based pro-rata guarantee allocation. Recoveries, amortization, actual payouts and loss-assumption uncertainty are absent; CCF 100% does not make the combined EL necessarily conservative.
- Independent-state/successful-draw conditioning and univariate support checks leave broader dependence and joint path plausibility unresolved. Future rolling-origin recalibration, block Shapley accounting, competing risks or separately authorized policy design require new protocols; none is executed here.

## Release and source rights

Public snapshot: 8 October 2026, based on accepted local research/reporting commit `40c7c5ec9e3386dcf1ebfafcb5335da0e4e6b179`. Publication was authorized after G5 review. This repository includes research code, frozen aggregate results and the accepted reports; it excludes borrower-level data, fitted models, private predictions, legacy scorecard assets and CV/social drafts. The original local archive remains authoritative for full history. Dated gate documents retain their historical execution restrictions. Layers 3–4 remain future work. Source rights and required attribution are in DATA.md; no source datasets are redistributed. See [release manifest](PUBLIC_RELEASE_MANIFEST.json).

Hakan Zeki Gülmez · M.Sc. Management & Technology (Economics & Econometrics), Technical University of Munich · [GitHub](https://github.com/hakangulmez) · [LinkedIn](https://www.linkedin.com/in/hakan-zeki-g%C3%BClmez-088700180/)
