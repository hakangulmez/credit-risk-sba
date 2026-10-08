# Working paper — 8 October 2026

**Local economic conditions and public–lender loss sharing in SBA 7(a) lending**

[PDF](../report/working_paper.pdf) · [LaTeX manuscript](../report/paper/working_paper.tex) · [Verified references](../report/paper/references_verified.json) · [Input provenance](../report/paper/provenance.json)

This is a separate academic manuscript of the accepted research. It expands the introduction, related literature and economic discussion while retaining the existing estimates, tables, intervals, samples and limitations. It is a working paper, not a peer-reviewed publication. The two-page policy note and ten-page technical report are retained byte-for-byte. Their dated research/reporting provenance is unchanged.

## Research question and contribution

How well do reconstructed approval-descriptor models discriminate and calibrate across disbursement cohorts, and how do conditional macroeconomic scenarios change assumption-based public–lender loss allocation?

The contribution is an auditable empirical illustration combining the official SBA status universe, complete 36-month windows, temporal model roles, archived failures, calibration evidence and conditional scenario accounting. It does not introduce a new estimator, identify causal guarantee effects, verify operational deployment or measure fiscal costs.

## Editorial additions

- Economic motivation connects probability calibration to portfolio amounts and public guarantees.
- Related literature distinguishes causal credit-supply designs from the current conditional allocation exercise, discrimination from calibration, and coefficient bias reduction from probability accuracy.
- The exact joint calibration diagnostic is made explicit: `logit(q) = alpha + b × logit(p)`, with both parameters estimated. The saved intercept is not an intercept-only calibration-in-the-large estimate with slope fixed at one. Its sign alone does not determine the direction of the cohort mean error. No new diagnostic was estimated.
- Economic discussion explains why calibration errors may affect scenario differences and ratios, why aggregate guarantee shares need not remain constant, and why expected losses are not tail-risk estimates.
- The current repository appears in the cover and audit links. Internal specification names are translated to readable labels in build copies only; frozen table files are not edited.

The design amendment remains explicitly post-results: the Firth specification was fixed after the initial G2 failures and calibration results had been inspected, and before G2-bis estimation. Layer 2 remains retrospective conditional validation with realized paths and disclosed cohort/calendar reuse. The fixed 2006 portfolio is a scenario portfolio included in Layer 2 estimation, not a performance holdout.

## Literature

Four additional references were checked using publisher or author-hosted bibliographic information and abstracts on 8 October 2026:

- [Bachas, Kim and Yannelis (2021), Loan guarantees and credit supply](https://doi.org/10.1016/j.jfineco.2020.08.008): guarantee-schedule notches address credit supply; the present study has no corresponding causal design.
- [Van Calster et al. (2019), Calibration: the Achilles heel of predictive analytics](https://doi.org/10.1186/s12916-019-1466-7): discrimination and calibration assess different properties. Its clinical application domain is identified in the paper.
- [Puhr et al. (2017), Firth's logistic regression with rare events](https://doi.org/10.1002/sim.7273): coefficient bias reduction does not establish accurate probability prediction. This is not evidence that the Firth penalty caused this study's cohort errors.
- [BCBS (2018), Stress testing principles](https://www.bis.org/bcbs/publ/d450.htm): clear objectives, methodology and documentation are conceptual context, not a regulatory compliance claim.

The previously accepted Firth, Kosmidis–Firth, teaching-dataset and official-source references remain. No numerical result from another paper is imported into the research findings, and no agency observations or raw inputs were refreshed.

## Reproduce the manuscript

```sh
uv sync --frozen --python 3.11
make paper-check REPORT_PYTHON=.venv/bin/python
make paper REPORT_PYTHON=.venv/bin/python
```

The build requires `pdfinfo` and Tectonic with cached TeX packages; set `TECTONIC` if needed. It runs offline, copies the frozen generated tables and figure into `data/working-paper-build/`, and compiles the manuscript there. It never rebuilds estimates or overwrites the accepted PDFs. The distributed paper is `report/working_paper.pdf`; rebuilds remain under ignored `data/`.

The input manifest fixes the complete public empirical aggregate directories, specifications, research code, notebook, protocols, claims registry, accepted report PDFs and reused presentation inputs. `make report-check` also verifies the current distribution manifest and original cell-level claims. `make report-test` includes the working-paper boundary checks.

The manuscript may be circulated as a working paper with its stated limitations. Any additional empirical extension or journal-specific revision requires a separate scope; this writing round adds no fitting, predictions, tuning, recalibration or new data acquisition.

## Subsequent technical-report presentation correction — 9 October 2026

The statement above about byte-identical reports describes the working-paper basis on 8 October. The technical report's current presentation was edited on 9 October to remove obsolete repository/draft wording and the teaching-extract comparison. The original technical PDF and sources remain byte-identical under `docs/releases/technical-report-before-editorial-2026-10-09/`. `report/paper/provenance.json` points to those archived inputs so the working paper's original basis remains fixed. Its manuscript, PDF, tables, numerical inputs and estimates are unchanged.


## Local editorial revision — 9 October 2026

Current report sources use plain stage names and the disclosed post-results chronology. The added calibration paragraphs reuse saved cells and intervals from calibration_deciles.csv, recorded in CLAIMS.md and report/editorial/calibration_prose_claims.json. The original input ledger is unchanged; authorized replaced presentation inputs are verified in the dated pre-editorial archive. No estimates, bins or statistical tests were recomputed. The current working-paper limit is 14 pages. Publication and Drive delivery of this revision await approval.
