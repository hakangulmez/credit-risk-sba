# Public snapshot — 8 October 2026

This repository publishes **Local economic conditions and public–lender loss sharing in SBA 7(a) lending**, Layers 1–2, after completed G5 review. The accepted local source commit is `40c7c5ec9e3386dcf1ebfafcb5335da0e4e6b179`; the empirical release is `8f7343584d55a14f8cae47c3e9fded3ed56503d4`. These hashes identify the preserved local history, not commits in this fresh public repository.

## Included and excluded material

The snapshot contains current research and reporting source code, fixed configs, protocols and their dated versions, aggregate G2/G2-bis/G5 results, accepted report PDFs and G5 figures. Research numbers, frozen source files and report PDFs are copied byte-for-byte. The public README, Makefile, ignore rules and this publication wrapper document the new distribution scope. `PUBLIC_RELEASE_MANIFEST.json` records every distributed file, its hash and its relationship to the original source snapshot.

No raw borrower records, fitted models, loan-level predictions, credentials, runtime caches, old resolved-loan notebook/models/reports, or CV/LinkedIn drafts are distributed. Some retained provenance files contain paths and hashes of private artifacts, but none contains those artifacts. Raw SBA/BLS/FHFA inputs are not redistributed; source rights and vintage qualifications remain in DATA.md.

The full local research checkout and verified Git bundles preserve the old project and its complete history. Dated execution reports and their manifests describe their original local runs; paths absent from this public snapshot are intentionally not distributed. Their local-only restrictions are historical. Current publication authorization does not authorize new empirical work or Layers 3–4.

## Reproduce presentation from frozen aggregates

Use Python 3.11 and `uv sync --frozen --python 3.11`. Then run:

```sh
make report-check REPORT_PYTHON=.venv/bin/python
make report-test REPORT_PYTHON=.venv/bin/python
```

`report-check` verifies the release-file hashes, 4,578 registered claim cells including five permitted derived claims, saved table provenance, report page counts and current affirmative-claim checks. It requires Poppler's `pdfinfo`. It does not claim to verify undistributed private files.

`report-test` selects the portable, non-fitting G5 reporting regression checks. Seven original tests are intentionally excluded because they require private preservation inventories, undistributed correction archives or CV/social drafts, the original Makefile, or a machine-specific cached TeX installation. The original 50-test G5 result remains historical evidence, not the public-subset count. Synthetic research tests are supplied as source and are not invoked by these reporting commands.

For an optional PDF rebuild, install Tectonic and populate its TeX cache separately, set `TECTONIC` if it is not on PATH, and run:

```sh
make report REPORT_PYTHON=.venv/bin/python
```

The wrapper copies only hash-bound aggregate inputs and report sources into an isolated temporary directory, calls the unchanged results-only renderer, and places rebuilt artifacts under ignored `data/public-report-rebuild/`. It never imports the research package or replaces accepted published PDFs, README, source aggregates or registry. Compilation uses cached packages only. PDF creation metadata can change bytes without changing the reported research values. The original renderer's local draft prose stays inside the temporary build.

Full empirical replication requires separately acquired and verified frozen-source vintages and private preprocessing/model checkpoints. A current download is not guaranteed to reproduce the accepted input vintage. This public snapshot demonstrates report reproduction from frozen aggregates; it does not claim full clean-clone empirical reproduction.

## Interpretation

The outcome is recorded charge-off within 36 months. Layer 2 conditions on realized or stipulated macro paths; coefficients and sensitivities are associations. Calibration failures remain substantive findings. EAD = GrossApproval, CCF = 100%; gross LGD and pro-rata guarantee allocation make losses assumption-based proxies. Layer 3 and additional methods remain future work.
