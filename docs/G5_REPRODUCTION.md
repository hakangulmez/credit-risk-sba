# Results-only reproduction — 8 October 2026

Research estimates are those of local release `8f7343584d55a14f8cae47c3e9fded3ed56503d4`. Reporting selects aggregate cells and performs presentation arithmetic only. It does not import the research package, read borrower records, deserialize fitted models, generate predictions, or estimate diagnostics.

Run `make report`, `make report-test`, and `make report-check` from this repository. `REPORT_PYTHON` defaults to `.venv/bin/python`; it can point to another Python 3.11 environment containing the existing rendering dependencies (NumPy, Matplotlib and PyYAML). Tests additionally need pytest; lint/type checks need ruff/mypy. The existing locked environment is sufficient. Set `TECTONIC` to a cached Tectonic executable when it is not on PATH. The local portfolio executable is `~/portfolio/.tools/tectonic/tectonic`. Compilation uses `--only-cached`; missing fonts/packages cause a clear build failure rather than a download. Latin Modern and the portfolio typography conventions are reused in a new compact article layout; no SBA-specific report template was available.

## Inputs and outputs

The machine-readable input allowlist is `results/g5-2026-10-08/private_free_rehearsal.json`: the source files named by the claims registry, that registry itself, and the reporting code/LaTeX sources. Sources are frozen G2-bis CSV/JSON aggregates and method metadata in the existing protocol/config. Every source hash and unique cell selector is checked before rendering. `CLAIMS.md` was committed before report prose; later refinements added explicit metadata selectors and effective interval-count arithmetic without changing the research values.

Current outputs: README, the two PDFs in `report/`, new LaTeX/generated tables under `report/g5/`, figures under `figures/g5/`, local LinkedIn drafts under `figures/linkedin/g5/`, and `CV_BULLET_DRAFT.md`. Derived CSVs, cell-level table maps, rendered snippets and validation metadata live in `results/g5-2026-10-08/`. TeX intermediates and visual review images stay in ignored `data/g5-2026-10-08/`; these are reporting scratch files, not research inputs. PDF bytes may differ across rebuilds because of creation metadata, while the source values remain hash-bound.

A separate staging directory was populated with this input allowlist and reporting sources only. It contained no `data/`, `models/` or `.env` before `make report`. Both PDFs built successfully. The test suite independently repeats this rehearsal; it creates only reporting scratch files afterward. No service access, acquisition or empirical inference is part of this build.

## Preservation and interval conventions

`preservation_inventory.json` lists all protected paths and hashes. README and Makefile are authorized replacements: their old hashes are verified against byte-identical archived copies in `versions/pre-g5-2026-10-08/`. DECISIONS is append-only and its complete original prefix is verified. Every other original tracked research artifact and every protected private artifact is checked at its original path. Existing frozen ledgers are not edited. Retained `v1-original` and historical documents remain historical evidence, not current headlines.

Stress/support rows take context from `macro_information_context`; their inherited `layer_interpretation` is not used for scenario captions. Saved paired-difference bounds are used directly. Ratios/shares are arithmetic of point aggregates with no invented interval. Conditional evaluation bands use the saved 999-draw state-cluster procedure; Firth intervals use successful re-estimated training-state multiplier attempts out of 199. Effective denominators and failures are saved metadata, not newly executed bootstrap evidence.

Four calibration displays reuse the exact saved training-score cutoffs, counts and recorded-rate bands; the evaluation samples are not rebinned. The forty requested bins are available and nonempty. A recorded rate of zero in a nonempty bin is not a missing value. Code preserves genuinely unavailable cells instead of converting them to zero.

## Verification scope

New reporting tests exercise selectors, source hashes, conversions, stored intervals, paired provenance, accounting identities, missing values, scenario labels, semantic positive/negative examples, the isolated build, page limits and protected hashes. Compatible legacy tests cover administrative label/cohort and deterministic accounting rules only. No fitting, prediction, calibration or bootstrap test is rerun. The prior full 78-test statistical suite and its coverage remain retained G2-bis evidence; they are not described as a new G5 full-suite run.

Language checks are safeguards, not proof of economic validity. Findings and captions were also manually checked against the ledger. Every page of both PDFs and both chart PDFs was rendered and inspected. Source-vintage limitations, cohort/calibration failures, conditional information sets, successful-draw assumptions and proxy loss allocation remain material qualifications.
