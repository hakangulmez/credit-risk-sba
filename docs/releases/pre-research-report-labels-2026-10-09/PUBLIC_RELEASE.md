# Public snapshot — 8 October 2026

This repository publishes **Local economic conditions and public–lender loss sharing in SBA 7(a) lending**, Layers 1–2, after completed reporting review. The accepted local source commit is `40c7c5ec9e3386dcf1ebfafcb5335da0e4e6b179`; the empirical release is `8f7343584d55a14f8cae47c3e9fded3ed56503d4`. These hashes identify the preserved local history, not commits in this fresh public repository.

## Included and excluded material

The snapshot contains current research and reporting source code, fixed configs, protocols and their dated versions, aggregate results from the first and final estimation rounds and reporting stage, current report PDFs and figures and the executed research walkthrough notebook. Research numbers and frozen source files are copied byte-for-byte. The current reports include the dated editorial corrections described below; earlier sources and PDFs are retained. The public README, Makefile, ignore rules and this publication wrapper document the new distribution scope. `PUBLIC_RELEASE_MANIFEST.json` retains the previous published distribution ledger. `PUBLIC_EDITORIAL_MANIFEST_2026-10-09.json` records the current local editorial snapshot separately.

No raw borrower records, fitted models, loan-level predictions, credentials, runtime caches, old resolved-loan notebook/models/reports, or CV/LinkedIn drafts are distributed. Some retained provenance files contain paths and hashes of private artifacts, but none contains those artifacts. Raw SBA/BLS/FHFA inputs are not redistributed; source rights and vintage qualifications remain in DATA.md.

The full local research checkout and verified Git bundles preserve the old project and its complete history. Dated execution reports and their manifests describe their original local runs; paths absent from this public snapshot are intentionally not distributed. Their local-only restrictions are historical. Current publication authorization does not authorize new empirical work or Layers 3–4.

## Results walkthrough notebook

`notebooks/research_walkthrough.ipynb` runs from top to bottom using frozen aggregate CSV/JSON files. Its checked outputs are stored for GitHub preview. It covers the analytical pipeline, all primary results, saved sensitivities and diagnostic tables; every published CSV is available through `RESULTS` and the result catalogue. Compact previews explicitly indicate truncation, and `show_result(..., rows=None)` displays a complete selected table.

Install the optional locked notebook group with `uv sync --frozen --group notebook --python 3.11`, then open the notebook using `uv run --group notebook jupyter lab notebooks/research_walkthrough.ipynb`. For a headless check, run `make notebook-check REPORT_PYTHON=.venv/bin/python`; it writes a separately executed copy and execution metadata under ignored `data/notebook-check/`, without modifying accepted outputs or estimates. Notebook execution makes no model fits, diagnostic estimations or network requests. The private re-estimation guide is disabled by default and only reveals manual prerequisites/module order; it never launches the empirical pipeline.

The README now introduces the accepted study directly; its previous source/design comparison is retained in `docs/METHOD_HISTORY.md`. The Firth amendment's post-results timing remains explicit. Notebook dependencies were added as a separate group without changing any existing locked package version. The original public release is retained at Git tag/release `v2026.10.08` and its file manifest at `docs/releases/public_snapshot_2026-10-08_manifest.json`.

## Reproduce presentation from frozen aggregates

The separate [working paper](report/working_paper.pdf) expands the economic motivation, literature and discussion using the same frozen estimates. Its [scope and reproduction notes](docs/WORKING_PAPER_2026-10-08.md) distinguish editorial additions from empirical evidence. `make paper` compiles offline under ignored `data/working-paper-build/`; `make paper-check` verifies its fixed inputs and page limit. The original policy, technical and working-paper PDFs are retained in the dated pre-editorial archive; current versions include the editorial corrections below. The notebook-stage distribution manifest and its README/Makefile are retained under `docs/releases/`.

Use Python 3.11 and `uv sync --frozen --python 3.11`. Then run:

```sh
make report-check REPORT_PYTHON=.venv/bin/python
make report-test REPORT_PYTHON=.venv/bin/python
```

`report-check` verifies the release-file hashes, 4,578 registered claim cells including five permitted derived claims, saved table provenance, report page counts, current affirmative-claim checks, notebook read-only scope/execution outputs and working-paper input hashes. It requires Poppler's `pdfinfo`. It does not claim to verify undistributed private files.

`report-test` selects the portable reporting and editorial regression checks that do not fit models and notebook scope regression checks. Seven original tests are intentionally excluded because they require private preservation inventories, undistributed correction archives or CV/social drafts, the original Makefile, or a machine-specific cached TeX installation. The original 50-test reporting result remains historical evidence, not the public-subset count. Synthetic research tests are supplied as source and are not invoked by these reporting commands.

For an optional PDF rebuild, install Tectonic and populate its TeX cache separately, set `TECTONIC` if it is not on PATH, and run:

```sh
make report REPORT_PYTHON=.venv/bin/python
```

The wrapper checks the current distribution and archived originals, copies report sources and saved tables into isolated staging, and compiles with the editorial builder under ignored `data/editorial-2026-10-09/`. It never imports the research package, regenerates frozen reporting results or replaces distributed PDFs, README, source aggregates or registry. It produces no communication drafts. Compilation uses cached packages only; PDF creation metadata can change bytes without changing the reported research values.

Full empirical replication requires separately acquired and verified frozen-source vintages and private preprocessing/model checkpoints. A current download is not guaranteed to reproduce the accepted input vintage. This public snapshot demonstrates report reproduction from frozen aggregates; it does not claim full clean-clone empirical reproduction.

## Interpretation

The outcome is recorded charge-off within 36 months. Layer 2 conditions on realized or stipulated macro paths; coefficients and sensitivities are associations. Calibration failures remain substantive findings. EAD = GrossApproval, CCF = 100%; gross LGD and pro-rata guarantee allocation make losses assumption-based proxies. Layer 3 and additional methods remain future work.

## Earlier technical-report editorial correction — 9 October 2026

That correction made the technical report link to the current research repository and removed the obsolete repository/draft cover text and the teaching-extract comparison. Its population description now refers directly to the official SBA FOIA source; the unavailable empirical utilization check remains explicit. No estimates, numerical tables, macro definitions, samples or interpretation qualifications changed. The post-results timing of the Firth amendment remains explicit.

The earlier PDF, its LaTeX source and preamble, and its distribution manifest are retained byte-for-byte under `docs/releases/technical-report-before-editorial-2026-10-09/`. The working-paper input manifest points to those archived original inputs where appropriate. At that earlier correction, the working paper, policy note and notebook were unchanged. The correction is presentation only and does not constitute a new empirical release. The report remains 10 pages, with all 18 tables and every page visually checked.


## Local editorial revision — 9 October 2026 (approval pending)

The current checkout contains corrected working-paper status, plain stage labels, two saved-group calibration paragraphs and concise loss references. This revision is local only. All existing results directories, frozen registry and historical hash manifests remain unchanged; `PUBLIC_EDITORIAL_MANIFEST_2026-10-09.json` records the current local presentation. The earlier source/PDF versions are retained under `docs/releases/pre-editorial-2026-10-09/`. Notebook code and stored outputs are unchanged. Current report builds call the isolated editorial compiler and write to ignored `data/editorial-2026-10-09/`; they do not regenerate frozen reporting results or communication drafts. Public/website PDF paths are unchanged; verification after an approved push is pending.
