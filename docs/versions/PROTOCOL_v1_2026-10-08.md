# Layers 1–2 protocol — 8 October 2026 (A1)

Frozen before fitting; implements Amendment A1 and Hakan's EAD decision. G1 ends here. Changes require a dated entry in [DECISIONS.md](../DECISIONS.md), retaining this version and reporting deviations. Sources, hashes and qualifications: [DATA.md](../DATA.md). Seed: **20261008**.

## Population, target and chronological separation

Primary population: official SBA **7(a)** approved and disbursed loans, project state in the 50 states/DC; 504 is excluded. Freeze FOIA **30 June 2026**. Let d be `FirstDisbursementDate`, w = d + 36 calendar months (month-end clamped). Require w ≤ snapshot. Label Y = 1 iff a valid `ChargeOffDate` lies in **[d,w]**; otherwise Y = 0, including mature EXEMPT/PIF loans and charge-offs after w. EXEMPT means unresolved status withheld, not verified performing. This is recorded charge-off risk, not delinquency risk or risk for rejected applicants. PIF represents an absorbing repayment outcome for this loan-level target.

Canonicalize whitespace in statuses (`P I F` → PIF), program and dates; raw revolver **N/Y** → term/revolving (dictionary also describes 0/1). Exclude/count CANCLD/COMMIT, missing disbursement, incomplete windows, unknown status, nonpositive approval and unmapped project state. Quarantine impossible date orders, dates after snapshot, CHGOFF without event date and contradictory event/status records; never repair them with approval dates or current balances. Preserve file/row identifiers: `LocationID` is a **lender** identifier. Report overlapping exclusion flags and a sequential denominator waterfall. Amount anomalies do not by themselves remove default observations from PD estimation.

| Disbursement cohort | Fixed role |
|---|---|
| 1991–2002 | Fit preprocessing, coefficients and LGD |
| 2003 Jan–Jun / Jul–Dec | Tune / calibrate, respectively; neither is fitted into the scorecard |
| 2004–2006 | Label-maturity buffer; **2006** reference portfolio only |
| **2007–2009** / **2011–2013** | Crisis test / additional OOT check; no tuning, refitting or calibration |

All fitting/validation labels mature before 2007. Keep the same eligible rows across model/Term comparisons; missing predictors use train-only handling. FOIA contains payoff dates, unlike the extract: fixed-horizon classification is chosen for the 36-month estimand, not because survival analysis is impossible.

## Feature timing: all 42 source columns

**A** = explicitly at approval/application; **A\*** = reported origination descriptor, historical vintage unverified; **D** = disbursement; **L** = later; **U** = timing unspecified/current record. A\* values are an explicit retrospective reconstruction assumption, not proof of real-time availability. Layer 1 excludes D/L/U predictors. Test original-vintage assumptions when metadata permit; unresolved qualifications stay in every report.

| Exact columns (grouped only for space) | Timing and use |
|---|---|
| `GrossApproval`, `SBAGuaranteedApproval`, `ProcessingMethod` | A\*; log approval, guarantee share, method |
| `ApprovalDate`, `ApprovalFY` | A; date/FY metadata only |
| `InitialInterestRate`, `JobsSupported` | A; numeric rate and log1p application jobs (self-reported estimates) |
| `FixedorVariableInterestInd`, `NaicsCode`, `BusinessType`, `BusinessAge`, `FranchiseCode`, `RevolverStatus`, `ProjectState` | A\*; categorical inputs: NAICS 2-digit, franchise presence, project state |
| `TermInMonths` | A\*/U; **excluded from primary**; fixed with-Term sensitivity, reported-term vintage assumption |
| `Program`, `AsOfDate` | A / L; population/snapshot metadata only |
| `FirstDisbursementDate` | D; cohort, label origin and macro alignment only |
| `LoanStatus`, `ChargeOffDate`, `PaidInFullDate`, `GrossChargeOffAmount` | L; eligibility/label/LGD only; no PD predictors |
| `SoldSecMrktInd` | L; secondary-market sale, excluded |
| `LocationID`, `BankName`, `BankFDICNumber`, `BankNCUANumber`, `BankStreet`, `BankCity`, `BankState`, `BankZip` | U/current lender assignment; excluded from predictors |
| `BorrName`, `BorrStreet`, `BorrCity`, `BorrState`, `BorrZip` | U/address vintage; excluded from predictors and public row-level outputs |
| `NaicsDescription`, `FranchiseName`, `ProjectCounty`, `SBADistrictOffice`, `CongressionalDistrict`, `CollateralInd` | U/redundant text/geography/collateral timing; excluded |

New-business grouping uses startup/new/≤2-year categories; existing uses “at least 2”/older categories; change-of-ownership, unanswered and missing remain separate. The source's “existing or more than 2 years” category is existing. `TermInMonths≥240` denotes **long maturity, a possible real-estate proxy**, not observed collateral type. UrbanRural is absent: its requested disparity diagnostic is unavailable without a separately verified crosswalk; do not invent it.

## Layer 1: models, calibration and diagnostics

Unweighted unpenalized logit (coefficients/average marginal associations), ElasticNet logit and LightGBM estimate loan-level 36-month PD; no oversampling or balanced-class priors. Numeric medians, missing flags, scaling and categorical missing/unknown encodings are fitted on 1991–2002 only. Log-transform approval/jobs; other continuous inputs enter linearly in logits. No feature, cohort or identification search. Each model has the fixed with/without-Term pair.

ElasticNet: 10 log-spaced C values, 1e-4–100, × l1 ratios {0,.25,.5,.75,1}; select minimum 2003H1 log loss. LightGBM: 50 seeded TPE trials; leaves {15,31,63}, min-child {50,100,200}, log learning rate [.02,.10], feature/bagging fractions [.7,1], bagging frequency 1, log L1/L2 penalties [1e-4,10]; maximum 1,500 rounds, 50-round early stopping on 2003H1. Fixed sigmoid calibration uses **2003H2 only**; report raw and calibrated scores. No post-calibration refit. Record fit failures; separation/nonconvergence is a failure, not permission to replace the logit silently.

Report AUC, average precision (PR-AUC), Brier, calibration intercept/slope and ten train-score-decile calibration bins; paired **999 state-cluster bootstrap** draws give 95% percentile intervals conditional on frozen fits. Report undefined draws and group counts. SHAP: seeded ≤5,000 crisis rows, no feature selection. PSI: train deciles with ±infinity tails and missing bin; categorical missing/unseen bins, epsilon 1e-6 renormalized. Compare portfolio allocations at fixed **70% lowest-PD acceptance**, deterministic file/row tie-breaking; this uses scores only and is not an operational approval rule.

## Layer 2: conditional macro paths and scenarios

Acquire observations **directly from BLS/FHFA**, retaining FRED IDs as references only. State is `ProjectState`. Monthly SA unemployment $u_0=u_{m(d)}$, $\Delta u=u_{m(w)}-u_0$ in percentage points; quarterly NSA all-transactions HPI $H$, $q=q(d)$: $h_0=100\log(H_q/H_{q-4})$, $\Delta h=100\log(H_{q+12}/H_q)$. No monthly HPI interpolation. Containing-period alignment is a declared approximation to exact-day windows; revised series and future realized paths are **scenario inputs**, never Layer 1 approval information. Require complete macro endpoints; count unmatched records and compare Layer 1 on that same subset.

Primary: no-Term origination logit plus these four macros, state fixed effects and **linear disbursement-year trend centred on 2000** (predictable in unseen years). LightGBM robustness adds the same four macros and year with Layer 1's frozen tuning/calibration procedure. Logit remains uncalibrated for coefficient-based inference. Validate predicted versus recorded crisis default rates by state and the later OOT cohort. Use state-cluster sandwich covariance. Report mean PD change in **percentage points** when $\Delta u$ rises by 1 pp, overall and by fixed size bands, NAICS-2, business age and reported maturity; no causal or elasticity claim.

Hold the **2006** portfolio, its exposures, state and year fixed. Baseline: each state's 2004–2006 mean unemployment level, zero unemployment change, mean annual HPI log growth $h_0$, and three times that growth for $\Delta h$. Adverse: January 2007 unemployment level and January 2007→January 2010 change; 2007Q1 HPI annual growth and 2007Q1→2010Q1 log change. These are fixed state-specific 2007–2010 paths, without choosing a worst date. Flag macro values outside training support. Resample logit coefficients **999** times from the state-cluster covariance, holding portfolio, LGD and scenarios fixed; report conditional 95% intervals for PD/EL/loss rates, not full uncertainty or causal policy effects.

## Loss accounting and predeclared sensitivities

**EAD = GrossApproval; full-disbursement proxy, CCF = 100% (conservative utilization assumption).** Repeat this label in **every loss table**. Undrawn revolving commitments make full utilization conservative; this is not verified outstanding principal or a universal upper bound.

Use training defaults with charge-off within 36 months: segment **LGD proxy = sum(GrossChargeOffAmount) / sum(GrossApproval)**, with matching EAD denominator. Segments: term/revolving × approval bands ≤$150k, ($150k,$350k], ($350k,$1m], >$1m. Pool cells with <50 valid defaults to loan-type LGD, then overall training LGD if needed. Missing/negative severity amounts are counted/excluded only from LGD, not PD. Do not silently cap ratios above one; report them and the fixed cap-at-one sensitivity. This is gross charged-off balance per approved dollar, **not net-of-recovery LGD**; amount vintage need not equal event-date balance.

For valid $g_i=\text{SBAGuaranteedApproval}_i/\text{GrossApproval}_i$, $EL_i=PD_i LGD_i EAD_i$; allocate $g_iEL_i$ to SBA and $(1-g_i)EL_i$ to lender. Set invalid shares to missing predictors; retain those rows for PD but report losses on the valid-share subset. Allocation is pro rata, not a measured guarantee payout or fiscal cost. Report term/revolving PD, EL and EL/sum(EAD) separately.

Predeclare old-extract **DisbursementGross/GrAppv** distributions by term/revolving, these size bands and disbursement year: count, missing/invalid count, p10/median/p90/p99 and fraction >1, without silent clipping. After licence/cutoff verification, use only a documented maturity-qualified population. A segment median from pre-2003 eligible observations, clipped explicitly to [0,1] **for the scenario only**, supplies an alternative CCF; sparse cells (<50) pool by loan type, then overall. Apply it only as an assumption-based EAD sensitivity; retain FOIA PD and primary LGD, and state that this holds severity fixed rather than jointly re-estimating it. No extract substitution or outcome-selected denominator in the primary model.

## Limits and gate

Approval-field vintages, administrative charge-off timing, revised macros, repayment selection in the fallback, exposure utilization, recovery omissions and extrapolation limit interpretation. `DATA.md` defines fallback admissibility; maturity filtering alone does not prove complete survivor coverage. G2 must test labels/boundaries, timing allowlists, split isolation, unseen/missing handling, scenario endpoints and exact loss allocation. **No fits, tuning, old-score reproduction, ARRA outcome analysis or pushes at G1. Stop for review.**
