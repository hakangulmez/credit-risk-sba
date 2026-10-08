# Working-paper completion — 8 October 2026

The separate academic manuscript is complete using the accepted G2-bis/G5 aggregates. The research question centres on temporal calibration and conditional public–lender loss accounting in SBA 7(a) lending.

## Deliverables

- `report/working_paper.pdf`: 13 pages, 18 tables, one four-panel figure, ten bibliography entries.
- `report/paper/working_paper.tex` and `preamble.tex`: editable manuscript and layout source.
- `report/paper/references_verified.json`: four additional primary-source reference checks.
- `report/paper/provenance.json`: 243 fixed input hashes and display-label substitutions.
- `report/paper/validation.json`: PDF/source hashes, page-level visual review and checks.
- `docs/WORKING_PAPER_2026-10-08.md`: scope, literature and reproduction notes.
- `scripts/working_paper.py`, `make paper` and `make paper-check`: offline compilation/checks from frozen public inputs.
- README and public reproduction notes link the separate manuscript.

## Preservation and empirical scope

The accepted two-page policy note, ten-page technical report, all empirical aggregates, claims, specifications, research code, protocols and executed notebook remain unchanged. The original private research checkout is clean and untouched. No model fits, prediction generation, tuning, recalibration, new diagnostics or observation acquisition occurred. Literature verification concerned reference metadata and source arguments only.

The prior notebook-stage public manifest is retained at `docs/releases/notebook_snapshot_2026-10-08_manifest.json`; the previous README and Makefile are copied from the prior public commit into `docs/releases/pre-paper-2026-10-08/`. Existing Git history and dated releases remain intact.

Calibration diagnostics are explicitly described as a joint intercept/slope regression, not an intercept-only calibration-in-the-large calculation. Post-results amendments, reused cohorts/calendar overlap, future realized macro information, calibration failure and assumption-based EAD/LGD/pro-rata allocation remain visible. No stronger empirical conclusion is substituted.

## Checks and stopping boundary

55 portable reporting/notebook/manuscript tests passed; seven original private/archive/machine-specific tests remain excluded under the existing public test scope. Lint, formatting and typing of the new builder passed. The manuscript compiled offline with cached TeX resources, and every page was visually checked. The distribution manifest and original registered empirical claims are checked separately by `make report-check`.

Completed locally. No push, publication, sharing, paid call or further empirical gate. The manuscript is a working paper, not a peer-reviewed publication.
