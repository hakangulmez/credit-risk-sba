# Claims and provenance — 8 October 2026

Research release: `8f7343584d55a14f8cae47c3e9fded3ed56503d4`. Created before G5 report prose. All research numbers in reporting are selected from saved aggregates; no new empirical computation.

The [machine-readable registry](results/g5-2026-10-08/claims_registry.json) includes exact source hashes, unique selectors/columns, raw values, units, model/role/denominator, interval scope, display rules and arithmetic dependencies. Named findings below are aliases into that cell-level registry. Unavailable cells stay unavailable.

**Stress/support mapping:** use `macro_information_context` and display “Scenario projections on the fixed 2006 portfolio; not out-of-sample validation”. Ignore the inherited retrospective-validation label in these scenario rows. Calibration-group displays preserve training-score bins, stored edges/counts and conditional state-cluster bands.

Calibration error can change probability levels, differences and ratios. No derived share/ratio interval is invented. All primary models are Term-free; with-Term remains a timing-unverified sensitivity. Coefficients/finite changes are not causal.

| Claim alias | Display value (stored interval where available) | Units | Source cell ID | Interpretation |
|---|---|---|---|---|
| auc_crisis | 0.607 [0.587, 0.626] | AUC (unitless) | `N9f03a9b8e4b9e7` | C1: modest out-of-time discrimination; not strong transportability |
| pd_crisis | 5.73 | percent (%) | `N8d9852d435f5a3` | C2: raw Firth calibration failure |
| rate_crisis | 12.25 | percent (%) | `N5b982a8342fccf` | C2: recorded administrative outcome, not delinquency |
| auc_later | 0.666 [0.638, 0.691] | AUC (unitless) | `N6f79fba978c544` | C1: modest out-of-time discrimination; not strong transportability |
| pd_later | 4.50 | percent (%) | `N49c537150442cb` | C2: raw Firth calibration failure |
| rate_later | 1.49 | percent (%) | `N22e2dd3c5958fe` | C2: recorded administrative outcome, not delinquency |
| pd_l2_firth | 2.80 | percent (%) | `N244e456120043a` | C3: realized-path retrospective cohort check |
| rate_l2_firth | 1.48 | percent (%) | `Nbc91e4ca98d236` | C3: already partly exposed calendar/cohort |
| firth_calibration_intercept | -1.226 [-1.805, -0.772] | calibration_intercept (unitless) | `Nb06a7a1e59ab95` | C3: average agreement does not imply risk-group calibration |
| firth_calibration_slope | 0.830 [0.681, 0.945] | calibration_slope (unitless) | `N34f5519c69a13a` | C3: average agreement does not imply risk-group calibration |
| pd_l2_tree | 1.51 | percent (%) | `Ndc9a8338cfceaf` | C3: realized-path retrospective cohort check |
| rate_l2_tree | 1.48 | percent (%) | `Ne70caeacd606a8` | C3: already partly exposed calendar/cohort |
| tree_calibration_intercept | -0.431 [-0.835, -0.112] | calibration_intercept (unitless) | `N9effc87e5151ba` | C3: average agreement does not imply risk-group calibration |
| tree_calibration_slope | 0.894 [0.812, 0.967] | calibration_slope (unitless) | `Ne0b15147e6a4b0` | C3: average agreement does not imply risk-group calibration |
| endpoint | 0.535 [0.266, 0.772] | probability percentage points (pp) | `Nccf90c54643a4c` | C4/C5: +1 pp finite-change conditional association on observed 2006 portfolio; not derivative or causal |
| peak | 0.679 [0.439, 0.933] | probability percentage points (pp) | `N56fcbc9a1e699b` | C4/C5: +1 pp finite-change conditional association on observed 2006 portfolio; not derivative or causal |
| baseline_pd | 5.16 [4.61, 5.79] | percent (%) | `N8650138597f873` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| baseline_expected_loss_usd | 215.58 [194.85, 234.99] | USD millions | `Ne2267a072204c1` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| baseline_sba_loss_usd | 135.38 [123.96, 146.81] | USD millions | `N57a02a19520504` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| baseline_lender_loss_usd | 80.20 [70.79, 88.69] | USD millions | `N88ef103fa3874d` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| baseline_loss_rate | 1.67 [1.51, 1.83] | percent (%) | `Na71ec3da674c39` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_pd | 12.78 [12.46, 13.34] | percent (%) | `Nb4b1aa9f09e220` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_expected_loss_usd | 572.87 [528.21, 620.28] | USD millions | `Nde151c730b3a97` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_sba_loss_usd | 360.71 [328.19, 393.90] | USD millions | `N46cdc99b7dd6b9` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_lender_loss_usd | 212.16 [199.49, 227.03] | USD millions | `N1bfe104484281e` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_loss_rate | 4.45 [4.10, 4.82] | percent (%) | `N7fe1102688963a` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_minus_baseline_pd_change_pp | 7.619 [6.772, 8.617] | probability percentage points (pp) | `Nf7dd6ccc2d5232` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_minus_baseline_expected_loss_usd_change | 357.30 [304.86, 411.90] | USD millions | `N02244f98698985` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_minus_baseline_sba_loss_usd_change | 225.33 [189.40, 261.74] | USD millions | `Nd4473b2ee7b4a4` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| adverse_minus_baseline_lender_loss_usd_change | 131.96 [114.46, 151.14] | USD millions | `N14ea5b5bec6e9f` | C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost |
| el_ratio | 2.66 | unitless | `el_ratio` | Scenario projections on the fixed 2006 portfolio; not out-of-sample validation |
| baseline_sba_share | 62.80 | percent (%) | `baseline_sba_share` | Scenario projections on the fixed 2006 portfolio; not out-of-sample validation |
| baseline_lender_share | 37.20 | percent (%) | `baseline_lender_share` | Scenario projections on the fixed 2006 portfolio; not out-of-sample validation |
| adverse_sba_share | 62.97 | percent (%) | `adverse_sba_share` | Scenario projections on the fixed 2006 portfolio; not out-of-sample validation |
| adverse_lender_share | 37.03 | percent (%) | `adverse_lender_share` | Scenario projections on the fixed 2006 portfolio; not out-of-sample validation |
| term_CHGOFF_n | 217,195 | count | `N7a18024e7d5d1a` | C9: timing unverifiable; low matching does not prove original vintage |
| term_CHGOFF_valid_n | 216,172 | count | `Na3c0f1b49cccac` | C9: timing unverifiable; low matching does not prove original vintage |
| term_CHGOFF_term_invalid_n | 1,023 | count | `N4a018ff4ba8b36` | C9: timing unverifiable; low matching does not prove original vintage |
| term_CHGOFF_match_abs_le_3_share | 4.66 | percent (%) | `Nd12a607c2ac701` | C9: timing unverifiable; low matching does not prove original vintage |
| term_CHGOFF_charge_off_after_label_window_n | 151,175 | count | `N97476df352cb5b` | C9: timing unverifiable; low matching does not prove original vintage |
| term_PIF_n | 1,151,100 | count | `N7151c27af58a1a` | C9: timing unverifiable; low matching does not prove original vintage |
| term_PIF_valid_n | 1,150,806 | count | `N3f559c8036095e` | C9: timing unverifiable; low matching does not prove original vintage |
| term_PIF_term_invalid_n | 294 | count | `Nbbe08783ab11f5` | C9: timing unverifiable; low matching does not prove original vintage |
| term_PIF_match_abs_le_3_share | 14.45 | percent (%) | `N7afcae84e5181e` | C9: timing unverifiable; low matching does not prove original vintage |
| term_PIF_charge_off_after_label_window_n | 0 | count | `N8585d1295c8865` | C9: timing unverifiable; low matching does not prove original vintage |
| support_state_specific_flagged_loan_n | 990 | count | `Nee3aaec7d017e1` | C10: univariate check, not joint support or plausible paths |
| support_state_specific_flagged_fraction | 1.11 | percent (%) | `Nffd0062d202f48` | C10: univariate check, not joint support or plausible paths |
| support_state_specific_flagged_approval_usd | 99.55 | USD millions | `Nc3fdeaa66e8192` | C10: univariate check, not joint support or plausible paths |
| support_state_specific_n | 89,002 | count | `N7b1e90de7a774d` | C10: univariate check, not joint support or plausible paths |
| support_pooled_global_flagged_loan_n | 0 | count | `N2be6949849b5f5` | C10: univariate check, not joint support or plausible paths |
| support_pooled_global_flagged_fraction | 0.00 | percent (%) | `N3bd463d5ecfd07` | C10: univariate check, not joint support or plausible paths |
| support_pooled_global_flagged_approval_usd | 0.00 | USD millions | `N31b90e2af722ae` | C10: univariate check, not joint support or plausible paths |
| support_pooled_global_n | 89,002 | count | `N21055d4a669e33` | C10: univariate check, not joint support or plausible paths |
| method_horizon_months | 36 | calendar months | `method_horizon_months` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_pool_cutoff | 0.001 | fraction of training observations | `method_pool_cutoff` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_seed | 20261008 | integer seed | `method_seed` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_attempts | 199 | attempted training-refit draws | `method_attempts` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_evaluation_draws | 999 | conditional evaluation draws | `method_evaluation_draws` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_max_iterations | 100 | iterations | `method_max_iterations` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_state_count | 51 | states | `method_state_count` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |
| method_lgd_min_cell | 50 | valid charge-offs (count) | `method_lgd_min_cell` | Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row |

The registry also covers samples/waterfall, benchmark AP/Brier and calibration intervals, all four saved calibration-group displays, convergence/failed fits, sensitivities/support, coefficients and Term audit counts. Dates, section/page numbers and source identifiers are metadata, distinguished from estimates.

Prohibited stronger interpretations: strong transported model; calibration solved; causal macro/guarantee effects; measured tail risk; actual public spending or guarantee payments; joint support or path plausibility established; real-time macro forecast; IFRS 9/CECL implementation. Negated qualifications and discussion-only future methods are permitted.


## Editorial calibration-group prose — 9 October 2026

The following displays reuse existing cell IDs from the unchanged registry above. Each selector identifies a single saved CSV row; source hashes, selectors, columns and display conversions are repeated in [the editorial prose map](report/editorial/calibration_prose_claims.json). No intervals, bins or tests were recomputed.

| Prose macro | Display | Units | Existing cell ID | Unique source selector / column |
|---|---|---|---|---|
| CrisisGroupOnePred | 0.70 | percent (%) | `N9044d0d913ef84` | `{"bin": "1", "cohort": "crisis_2007_2009", "model": "firth_raw", "variant": "layer1"}` / `predicted_pd` |
| CrisisGroupOneRecorded | 5.22 | percent (%) | `N1d1baf054f7f2f` | `{"bin": "1", "cohort": "crisis_2007_2009", "model": "firth_raw", "variant": "layer1"}` / `recorded_rate` |
| CrisisGroupNinePred | 6.02 | percent (%) | `Nfece26f5c2f5d2` | `{"bin": "9", "cohort": "crisis_2007_2009", "model": "firth_raw", "variant": "layer1"}` / `predicted_pd` |
| CrisisGroupNineRecorded | 16.72 | percent (%) | `Naacd5357c61b4b` | `{"bin": "9", "cohort": "crisis_2007_2009", "model": "firth_raw", "variant": "layer1"}` / `recorded_rate` |
| CrisisGroupTenPred | 13.16 | percent (%) | `N5c4e9b68430987` | `{"bin": "10", "cohort": "crisis_2007_2009", "model": "firth_raw", "variant": "layer1"}` / `predicted_pd` |
| CrisisGroupTenRecorded | 16.42 | percent (%) | `Nf23b0857a0e39d` | `{"bin": "10", "cohort": "crisis_2007_2009", "model": "firth_raw", "variant": "layer1"}` / `recorded_rate` |
| TreeGroupNinePred | 6.42 | percent (%) | `N7431e90143bb60` | `{"bin": "9", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `predicted_pd` |
| TreeGroupNineRecorded | 3.49 | percent (%) | `Nd9d972b86d8e80` | `{"bin": "9", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `recorded_rate` |
| TreeGroupTenPred | 10.17 | percent (%) | `N08df4340e58445` | `{"bin": "10", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `predicted_pd` |
| TreeGroupTenRecorded | 5.81 | percent (%) | `N972696014ba9f9` | `{"bin": "10", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `recorded_rate` |
| TreeGroupTenN | 155 | count | `Na0278d31b91525` | `{"bin": "10", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `n` |
| TreeGroupTenLower | 2.41 | percent (%) | `Nb99cd58f8c10b7` | `{"bin": "10", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `lower` |
| TreeGroupTenUpper | 11.87 | percent (%) | `Nd736db9631b846` | `{"bin": "10", "cohort": "post_amendment_validation_2013_2014", "model": "lightgbm_calibrated", "variant": "layer2"}` / `upper` |
| CrisisDiagnosticSlope | 0.314 | unitless | `N3e3a57a63c1964` | `{"cohort": "crisis_2007_2009", "metric": "calibration_slope", "model": "firth_raw", "variant": "layer1"}` / `value` |

The groups 1–8 statement also links all sixteen stored predicted/recorded-rate cells in the editorial prose map. It is a descriptive comparison, not an equivalence claim. The crisis top-group pattern is read alongside the saved diagnostic slope; no mechanism or statistical test for group differences is asserted.
