# G2-bis execution and source notes — 8 October 2026

Scope: Layers 1–2 only. No G3, G5, publication, push or paid API calls. The protocol/configuration commit is `1d39a458ee1bbd0e1604a5b78a2e6f8372fb1c53`, preceding all empirical G2-bis refits. This amendment was made after observing failed G2 fits and calibration results. Older estimates are not improvement targets. Original protocol and G2 artifacts remain at their original paths.

Run from the local repository with its existing environment; do not run the historical `make all` or `make report` recipes, which target G2 outputs. G2-bis uses separate dated output directories:

```sh
.venv/bin/python -c 'from pathlib import Path; from credit_risk_sba.bis_data import prepare; prepare(Path.cwd())'
.venv/bin/python scripts/g2_bis/validate_firth.py
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python -m credit_risk_sba.bis_runner --pilot
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python -m credit_risk_sba.bis_runner
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python -m credit_risk_sba.bis_benchmarks
.venv/bin/python -m credit_risk_sba.bis_term
.venv/bin/python -m credit_risk_sba.bis_diagnostics
.venv/bin/python -m credit_risk_sba.bis_finalize
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/pytest --cov=credit_risk_sba --cov-fail-under=70 --cov-report=json:data/g2-bis-2026-10-08/coverage.json > data/g2-bis-2026-10-08/final_tests.log 2>&1
.venv/bin/ruff check src tests --cache-dir data/.ruff_cache
.venv/bin/mypy src/credit_risk_sba --cache-dir data/.mypy_cache
.venv/bin/python scripts/g2_bis/software_checks.py
.venv/bin/python scripts/g2_bis/validate_results.py
.venv/bin/python -m credit_risk_sba.bis_reporting
```

The independent R validation uses brglm2 in `data/g2-bis-2026-10-08/R-library`, installed locally, not system-wide. The fixed synthetic weighted example compares mean-bias-reduced logit coefficients with our explicitly frequency-weighted Jeffreys/Firth objective. Unit tests also cover analytic weighted intercepts, finite-difference scores, integer-weight row replication, separation, rank, and inference identities. Empirical draw checkpoints are resumed, never redrawn; the first five pilot attempts remain in 199. Failed MLE coefficients/predictions and failed ElasticNet fits are suppressed.

## Sources and coverage

No loan, FHFA or earlier BLS release was refreshed. The original SBA snapshot remains 30 June 2026. Only missing 2017 monthly unemployment was obtained directly from BLS in separate dated files, recorded with actual retrieval timestamps, request parameters, byte lengths and SHA-256 in `results/g2-bis-2026-10-08/source_manifest.json`. The additions do not replace earlier frozen levels. This creates a mixed retrieval vintage of revised observations, not real-time information. FRED was not used.

Full paths require 37 unemployment levels from the containing disbursement month through month +36, and 13 HPI quarters from the containing quarter through quarter +12 plus the quarter −4 level used for annual log growth. Interior gaps invalidate the path even if endpoints exist. No interpolation or backfilling. FHFA coverage through 2017 is already present in the frozen file. This product uses FHFA data but is neither endorsed nor certified by FHFA.

## Numerical and interval interpretation

Categorical maps use training frequencies only, with strict count/n <0.001 pooling and all ProjectState effects retained. Outcome-dependent cell summaries are diagnostics after mapping, never inputs to pooling. Ordinary logit and Firth share exactly the same rows and reduced columns. Median imputation/missing flags and standardization are train-only; zero columns are omitted before inference. Unseen levels map to fitted Other when present. Otherwise linear models use the zero dummy vector with no fictitious coefficient; native categorical trees encounter a missing category. Application counts expose this qualification.

The line search allows at most 1e−8 penalized-objective decrease for floating-point noise; this does not relax any of the three committed 1e−5 convergence criteria. Firth point predictions are raw. Calibration intercept/slope regressions are diagnostic and do not alter those probabilities. Training diagnostic tables are point-only. Evaluation intervals retain the v1 999 state-cluster resampling procedure conditional on each fitted model. They are distinct from the 199 positive state-weighted multiplier refits used for Firth coefficients, average associations and stress. The latter assumes independence across state clusters and holds preprocessing, portfolio, LGD, exposure/guarantee allocation and macro paths fixed; it excludes their uncertainty and source-vintage uncertainty. Successful convergence and finite coefficients do not prove calibration.

Numeric Firth coefficients are on train-standardized scales. Average marginal associations convert slopes back to native feature units and report percentage-point probability changes; log approval/jobs remain log units. Categorical associations are discrete contrasts against the frozen training reference category. Layer 1 averages use its estimation population; Layer 2 averages use the fixed 2006 scenario portfolio. No causal interpretation is made.

Layer 2 outputs carry “Retrospective conditional validation using realized macro paths.” Its 1991–2009 estimation labels mature by end-2012. The 2010 LightGBM calibration labels extend to end-2013, overlapping the calendar period of the 2013 validation cohort. That cohort already entered G2 later-cohort evaluation; this is post-amendment validation rather than an untouched confirmatory test. Macro paths extend into future realized years, so this is not approval-time prediction. The fixed 2006 portfolio is included in Layer 2 estimation and is a scenario portfolio, not an out-of-sample performance test.

Every loss table states: EAD = GrossApproval, full-disbursement proxy, CCF = 100%; gross charge-off LGD proxy; assumption-based pro-rata guarantee allocation. The split is neither observed payouts nor measured fiscal cost. LGD training, downturn cohort pooling, per-loan caps, reference identity/order and baseline/adverse inputs are checked against G2 values. State-specific and pooled-global ranges are separate univariate checks and cannot establish joint support.

## Timing audit and retained unavailability

Term audit uses all applicable eligible CHGOFF/PIF records, including charge-offs after the 36-month label window. Elapsed months are actual days/(365.25/12). Source Term values are reread only from frozen loan files to distinguish missing from invalid values before historical numeric cleaning. Year/type/status distributions and valid/missing/invalid counts are exported. Metadata or original vintages are needed for approval-time verification; a low duration-match share cannot supply that evidence. Primary models remain Term-free for any verdict.

The old-extract utilisation/CCF sensitivity remains unavailable because its original licence/cutoff requirements are unmet. Urban/rural comparisons remain unavailable in the source. InitialInterestRate is explicitly excluded from shared models; this is a comparability decision, not a fitted missing-rate coefficient. Other A2 LGD, peak-unemployment and with-Term sensitivities are retained without search.
