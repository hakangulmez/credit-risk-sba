# Research report — 9 October 2026

This is the economic research report for the applied research project **Local economic conditions and public–lender loss sharing in SBA 7(a) lending**. It develops the motivation, related literature and interpretation of the same saved estimates used by the policy note and technical report. It is an independent research report, not a peer-reviewed publication.

[Research report](../report/research_report.pdf) · [Policy note](../report/policy_note.pdf) · [Technical report](../report/technical_report.pdf) · [Manuscript source](../report/paper/working_paper.tex) · [Verified references](../report/paper/references_verified.json) · [Frozen input provenance](../report/paper/provenance.json)

## Presentation revision

The project is labelled Applied research project, the economic manuscript Research report, and the short document Policy note. Economic claims, qualifications, numerical inputs, tables, intervals, figures and empirical estimates are unchanged. The prior presentation is retained under docs/releases/pre-research-report-labels-2026-10-09/ with SHA-256 verification. Historical source filenames and dated documentation remain intact; working_paper.pdf is retained as a compatibility URL containing the current research report.

## Reproduce the presentation

Run `make paper` for an offline research-report rebuild and `make paper-check` for its frozen-input and interpretation checks. `make report-check report-test REPORT_PYTHON=.venv/bin/python` checks the public release and reporting contracts. Tectonic with cached TeX packages and Poppler are required for PDF compilation/inspection. The builders use saved aggregate results only; no fitting, prediction, recalibration, bootstrap, new binning or data acquisition occurs. Rebuilds write to ignored data directories and do not overwrite distributed PDFs automatically.

The technical report and results walkthrough retain their prior contents. The dated original manuscript and verification history are documented in [the retained original build note](WORKING_PAPER_2026-10-08.md).
