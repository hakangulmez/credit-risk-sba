"""Dated G2-bis report: all empirical numbers loaded from executed result tables."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .bis_data import LOSS_LABEL, NAME, VALIDATION_LABEL, js, table
from .io import sha256


def md(frame):
    frame = frame.fillna("unavailable")

    def text(x):
        return str(x).replace("|", "/").replace("\n", " ")

    return "\n".join(
        [
            "| " + " | ".join(map(text, frame.columns)) + " |",
            "| " + " | ".join(["---"] * len(frame.columns)) + " |",
        ]
        + [
            "| " + " | ".join(map(text, row)) + " |"
            for row in frame.itertuples(index=False, name=None)
        ]
    )


def ci(row, scale=1, digits=3):
    return f"{row['value'] * scale:.{digits}f} [{row['lower'] * scale:.{digits}f}, {row['upper'] * scale:.{digits}f}]"


def figures(root, means, stress):
    path = root / "results" / NAME / "figures"
    path.mkdir(exist_ok=True)
    selected = means.loc[
        means.model.eq("firth_raw") & ~means.cohort.str.startswith(("training", "calibration"))
    ]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    labels = selected.variant.str.replace("_", " ") + "\n" + selected.cohort.str.replace("_", " ")
    x = np.arange(len(selected))
    ax.bar(x - 0.18, 100 * selected.mean_predicted, width=0.36, label="Raw Firth mean PD")
    ax.bar(
        x + 0.18,
        100 * selected.recorded_rate,
        width=0.36,
        label="Recorded charge-off within 36 months",
    )
    ax.set_xticks(x, labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Percent")
    ax.legend(fontsize=8)
    ax.set_title("Calibration diagnostics, no primary probability correction")
    fig.text(
        0.01,
        0.035,
        "With-Term: timing-unverified sensitivities; peak: unemployment-path sensitivity.",
        fontsize=7,
    )
    fig.text(0.01, 0.01, "Layer 2: " + VALIDATION_LABEL, fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path / "firth_cohort_calibration.png", dpi=180)
    plt.close(fig)
    selected = stress.loc[
        stress.variant.eq("layer2")
        & stress.lgd_variant.eq("primary")
        & stress.group.eq("overall")
        & stress.metric.eq("expected_loss_usd")
        & stress.scenario.isin(["baseline", "adverse"])
    ]
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    y = selected.value.to_numpy() / 1e6
    x = np.arange(len(selected))
    ax.vlines(x, selected.lower / 1e6, selected.upper / 1e6)
    ax.scatter(x, y)
    ax.set_xticks(np.arange(len(selected)), selected.scenario)
    ax.set_ylabel("Gross expected-loss proxy, USD million")
    ax.set_title("Term-free Firth: fixed 2006 scenario portfolio")
    fig.text(
        0.08,
        0.02,
        "95% percentile intervals; 199 attempted re-estimated state-weighted draws.\n"
        "Stipulated paths and fixed LGD; 2006 portfolio included in Layer 2 estimation.\n"
        "Pro-rata split is not observed payouts or fiscal cost.\n"
        "Separate Layer 2 cohort check: " + VALIDATION_LABEL,
        fontsize=7.5,
        va="bottom",
    )
    fig.tight_layout(rect=(0, 0.22, 1, 1))
    fig.savefig(path / "primary_stress_intervals.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def comparison(root, means, evaluation, stress):
    oldeval = pd.read_csv(root / "results/g2-2026-10-08/evaluation_metrics.csv")
    oldstate = pd.read_csv(root / "results/g2-2026-10-08/state_validation.csv")
    oldstress = pd.read_csv(root / "results/g2-2026-10-08/stress_lightgbm_secondary.csv")
    rows = []
    for model in ["elasticnet_calibrated", "lightgbm_calibrated"]:
        family = model.removesuffix("_calibrated")
        for metric in ["auc", "average_precision", "brier"]:
            prior = oldeval.loc[
                oldeval.variant.eq("layer1")
                & oldeval.family.eq(family)
                & oldeval.role.eq("crisis")
                & oldeval.calibration.eq("sigmoid_2003H2")
                & oldeval.metric.eq(metric),
                "value",
            ].iloc[0]
            now = evaluation.loc[
                evaluation.variant.eq("layer1")
                & evaluation.model.eq(model)
                & evaluation.cohort.eq("crisis_2007_2009")
                & evaluation.metric.eq(metric),
                "value",
            ].iloc[0]
            rows.append(
                {
                    "comparison": "Layer 1 no-Term " + family + " crisis " + metric,
                    "G2": prior,
                    "G2_bis": now,
                    "change_components": "Same cohorts/frozen hyperparameters/calibration years; new training-frequency pooling and rate exclusion; no new search",
                }
            )
    for role, cohort in [("crisis", "crisis_2007_2009"), ("oot", "additional_cohort_2011_2013")]:
        before = oldstate.loc[
            oldstate.variant.eq("layer2")
            & oldstate.family.eq("lightgbm")
            & oldstate.role.eq(role)
            & oldstate.calibration.eq("sigmoid_2003H2")
        ]
        rows.append(
            {
                "comparison": "G2 Layer 2 LightGBM " + role + " calibration history",
                "G2": float(np.average(before.predicted_pd, weights=before.n)),
                "G2_bis": np.nan,
                "change_components": "Not a same-cohort held-out comparison: Layer 2 now trains through 2009, calibrates 2010, validates 2013-2014; the prior failures remain documented",
            }
        )
    now = means.loc[
        means.variant.eq("layer2")
        & means.model.eq("lightgbm_calibrated")
        & means.cohort.eq("post_amendment_validation_2013_2014")
    ].iloc[0]
    rows.append(
        {
            "comparison": "Layer 2 revised tree post-amendment mean PD vs its recorded rate",
            "G2": np.nan,
            "G2_bis": now.mean_predicted,
            "change_components": f"Recorded rate = {now.recorded_rate}; expanded estimation, different validation years, L1 frozen settings and 2010 calibration change jointly; components not isolated",
        }
    )
    for scenario in ["baseline", "adverse"]:
        prior = oldstress.loc[
            oldstress.variant.eq("layer2")
            & oldstress.scenario.eq(scenario)
            & oldstress.lgd_variant.eq("primary")
            & oldstress.group.eq("overall"),
            "expected_loss_usd",
        ].iloc[0]
        now = stress.loc[
            stress.variant.eq("layer2")
            & stress.scenario.eq(scenario)
            & stress.lgd_variant.eq("primary")
            & stress.group.eq("overall")
            & stress.metric.eq("expected_loss_usd")
        ].iloc[0]
        rows.append(
            {
                "comparison": scenario + " scenario EL proxy, USD",
                "G2": prior,
                "G2_bis": now.value,
                "change_components": "G2 secondary calibrated tree vs G2-bis primary raw Firth, with expanded estimation/cohort design; not an estimator-only contrast",
            }
        )
    result = pd.DataFrame(rows)
    result["loss_accounting"] = np.where(result.comparison.str.contains("EL proxy"), LOSS_LABEL, "")
    return table(root, "g2_to_g2_bis_headlines", result)


def report(root):
    out = root / "results" / NAME
    load = lambda name: pd.read_csv(out / (name + ".csv"))
    samples = load("final_sample_waterfall")
    waterfall = load("source_population_waterfall")
    ranks = load("design_rank_checks")
    fits = load("fit_status")
    rates = load("initial_interest_rate_missingness")
    scores = load("evaluation_metrics")
    means = load("calibration_means")
    stress = load("firth_stress")
    associations = load("firth_average_associations")
    macro = load("firth_macro_associations")
    term = load("term_audit_summary")
    support = load("scenario_support_summary")
    preserved = load("preservation_checks")
    boot = json.loads((out / "bootstrap_summary.json").read_text())
    runtime = json.loads((out / "bootstrap_runtime.json").read_text())
    pilot = json.loads((out / "pilot_runtime.json").read_text())
    benchmarks = json.loads((out / "benchmark_status.json").read_text())
    reference = json.loads((out / "firth_implementation_validation.json").read_text())
    tests = json.loads((out / "software_checks.json").read_text())
    source = json.loads((out / "source_manifest.json").read_text())
    calibration = means.loc[
        means.variant.eq("layer1")
        & means.model.eq("firth_raw")
        & means.cohort.eq("calibration_2003H2")
    ].iloc[0]
    frozen_splits = pd.read_csv(root / "results/g2-2026-10-08/frozen_split_counts.csv")
    original_calibration = frozen_splits.loc[frozen_splits.role.eq("calibrate")].iloc[0]
    cal_row = {
        "layer": "layer1",
        "role": "benchmark_calibration_2003H2",
        "years": "2003H2",
        "eligible_n": int(original_calibration.n),
        "macro_excluded_n": int(original_calibration.n - calibration.n),
        "n": int(calibration.n),
        "events": int(calibration.events),
        "non_events": int(calibration.n - calibration.events),
        "earliest_disbursement": calibration.start,
        "latest_disbursement": calibration.end,
        "latest_label_window": str(pd.Timestamp(calibration.end) + pd.DateOffset(months=36)),
        "latest_required_unemployment_year": 2006,
        "full_monthly_path_levels": 37,
        "full_HPI_window_quarters": 13,
        "interpretation": "Approval-descriptor benchmark calibration only; raw Firth remains uncalibrated",
    }
    samples = pd.concat([samples, pd.DataFrame([cal_row])], ignore_index=True)
    table(root, "final_sample_waterfall_complete", samples)
    comparisons = comparison(root, means, scores, stress)
    old_state = pd.read_csv(root / "results/g2-2026-10-08/state_validation.csv")
    old_later = old_state.loc[
        old_state.variant.eq("layer2")
        & old_state.family.eq("lightgbm")
        & old_state.role.eq("oot")
        & old_state.calibration.eq("sigmoid_2003H2")
    ]
    old_mean = np.average(old_later.predicted_pd, weights=old_later.n)
    old_rate = np.average(old_later.recorded_rate, weights=old_later.n)
    figures(root, means, stress)

    def metric(variant, model, cohort, metric):
        return scores.loc[
            scores.variant.eq(variant)
            & scores.model.eq(model)
            & scores.cohort.eq(cohort)
            & scores.metric.eq(metric)
        ].iloc[0]

    crisis = metric("layer1", "firth_raw", "crisis_2007_2009", "auc")
    later = means.loc[
        means.variant.eq("layer1")
        & means.model.eq("firth_raw")
        & means.cohort.eq("additional_cohort_2011_2013")
    ].iloc[0]
    term_charge = term.loc[term.scope.eq("status") & term.group.eq("CHGOFF")].iloc[0]
    lgd_down = load("lgd_downturn")
    main = stress.loc[
        stress.variant.eq("layer2") & stress.group.eq("overall") & stress.lgd_variant.eq("primary")
    ]
    key = main.loc[
        main.scenario.eq("adverse_minus_baseline") & main.metric.eq("expected_loss_usd_change")
    ].iloc[0]
    text = [
        "# G2-bis: SBA 7(a) recorded charge-off risk and conditional loss scenarios",
        "\nDated completion report — 8 October 2026. Local-only Layers 1–2; stop at G2-bis.",
        "\n## Decision chronology and headline",
        "\nThis is a design amendment made **after observing failed G2 fits and calibration results**. Protocol v2 and its fixed configuration were committed as `1d39a458ee1bbd0e1604a5b78a2e6f8372fb1c53` before empirical refits. Prior outcomes are not improvement targets. All primary models remain Term-free; with-Term results are qualified sensitivities. The outcome throughout is **recorded charge-off within 36 months**, not delinquency. Coefficients and marginal quantities are associations, not causal effects.",
        f"\nAll unit-weight Firth specifications converged: {int(fits.loc[fits.family.str.startswith('Firth'), 'converged'].sum())} of {int(fits.family.str.startswith('Firth').sum())}. Finite estimation does not repair transport calibration. The Term-free Layer 1 crisis AUC is {ci(crisis)}; its mean raw prediction is {100 * means.loc[means.variant.eq('layer1') & means.model.eq('firth_raw') & means.cohort.eq('crisis_2007_2009'), 'mean_predicted'].iloc[0]:.2f}% against {100 * means.loc[means.variant.eq('layer1') & means.model.eq('firth_raw') & means.cohort.eq('crisis_2007_2009'), 'recorded_rate'].iloc[0]:.2f}% recorded. The additional cohort has {100 * later.mean_predicted:.2f}% predicted versus {100 * later.recorded_rate:.2f}% recorded.",
        f"\nThe primary scenario adverse-minus-baseline expected-loss proxy is USD {ci(key, 1e-6, 2)} million. Its sign is reported as estimated, without a requirement that adverse losses increase. All point estimates and intervals below are generated from the executed CSV/JSON outputs.",
        "\n## Population, sources and chronology",
        "\nSequential source denominator accounting (inherited from the frozen G2 waterfall; original loans and eligibility rules unchanged):\n\n"
        + md(waterfall),
        "\nFinal layer/cohort waterfall (events mean recorded charge-off within 36 months):\n\n"
        + md(
            samples[
                [
                    "layer",
                    "role",
                    "years",
                    "eligible_n",
                    "macro_excluded_n",
                    "n",
                    "events",
                    "non_events",
                ]
            ]
        ),
        f"\nOnly {source['added_BLS_2017_rows']:,} missing direct-BLS 2017 unemployment observations were added. Actual retrieval times and new raw-file hashes are in [source_manifest.json](../results/{NAME}/source_manifest.json). Full unemployment levels through month +36 and HPI quarters through quarter +12 plus quarter −4 are verified; missing interior periods invalidate coverage. FHFA and all earlier BLS observations/source files are unchanged. The new 2017 observations are revised and separately retrieved, producing a mixed retrieval vintage. No loan replacement, general refresh or FRED acquisition occurred. FHFA already covered the required later years. This product uses FHFA data but is neither endorsed nor certified by FHFA.",
        "\nLayer 1 retains estimation 1991–2002, 2003H2 benchmark calibration, crisis 2007–2009 and additional 2011–2013 check. No new search, tuning or early stopping. Layer 2 estimates 1991–2009 and calibrates only its LightGBM robustness on 2010. Its 2013–2014 cohort check is **"
        + VALIDATION_LABEL
        + "** Estimation labels mature by end-2012; calibration labels extend to end-2013, overlapping the calendar period of the 2013 validation cohort. That cohort already entered G2 evaluation: this is post-amendment validation, not a previously untouched confirmatory test. No held-out result informs any model choice. Layer 1 is approval-descriptor prediction under unverified historical feature vintages; Layer 2 conditions on future realized or stipulated macro paths.",
        "\nInitialInterestRate missingness and explicit exclusion from every shared specification:\n\n"
        + md(rates[["years", "eligible_n", "missing_n", "missing_share"]]),
        "\n## Pooling, rank, numerical validation and estimator status",
        "\nTraining-frequency pooling uses strictly count/n <0.001 separately in each layer; no outcomes enter mapping and every ProjectState effect is retained. Original-to-pooled maps, counts and resulting-level events/non-events are exported for each specification. Train-only medians, missing indicators and standardization are fixed before the first bootstrap. Constant/redundant columns are dropped without outcomes. Unseen nonstate levels use fitted Other if available; otherwise no unsupported coefficient is introduced (zero dummy vector for logits; missing category for native trees). [Application counts](../results/"
        + NAME
        + "/preprocessing_application_counts.csv) disclose missing/unseen categories by cohort.\n\n"
        + md(
            ranks[
                [
                    "variant",
                    "n",
                    "events",
                    "full_columns",
                    "rank",
                    "states",
                    "state_dummy_columns",
                    "dropped",
                ]
            ]
        ),
        f"\nThe independent weighted R coefficient check differed by at most {reference['max_coefficient_difference']:.3g} from our implementation. Weighted Firth maximizes the explicitly case-weighted binomial log likelihood plus one half log determinant of weighted Fisher information. Numerical rules remain the committed max-iteration, max-step, condition, score, coefficient-change and likelihood-change limits. Analytic weighted intercepts, finite-difference gradients, integer replication, separation and an independent R brglm2 fit validate the implementation. See [firth_implementation_validation.json](../results/"
        + NAME
        + "/firth_implementation_validation.json) for the independent coefficient comparison and package versions. The ordinary MLE uses exactly the same rows and retained design columns; optimizer success is insufficient when separation or other convergence diagnostics fail.",
        "\nFit status:\n\n"
        + md(fits[["variant", "family", "converged", "message", "iterations", "n"]]),
        "\nSame-design ordinary-logit diagnostics (an optimizer convergence message is not a valid-estimate verdict):\n\n"
        + md(
            fits.loc[
                fits.family.eq("unpenalized same-design comparator"),
                [
                    "variant",
                    "optimizer_success",
                    "separation_flag",
                    "normalized_gradient",
                    "hessian_condition",
                    "valid_estimate",
                ],
            ]
        ),
        "\nPost-pooling binary separation witnesses:\n\n"
        + md(
            load("post_pooling_separation_witnesses").drop(
                columns=["layer_interpretation", "specification_role"], errors="ignore"
            )
        )
        + "\nLayer 1's outcome-pure pooled level invalidates ordinary MLE despite optimizer success. Layer 2's fixed iteration-limit failures do not, by themselves, establish separation. No invalid coefficients or predictions are presented.",
        "\nBenchmark status (frozen G2 Layer 1 settings; Layer 2 uses corresponding Layer 1 selected rounds; no held-out tuning):\n\n"
        + md(
            pd.DataFrame(benchmarks).assign(
                calibration_failure=lambda frame: frame.calibration_failure.fillna(
                    pd.Series(
                        np.where(frame.converged, "none", "not run: estimator failed"),
                        index=frame.index,
                    )
                )
            )[
                [
                    "variant",
                    "family",
                    "converged",
                    "iterations_or_rounds",
                    "calibration_n",
                    "calibration_start",
                    "calibration_end",
                    "calibration_failure",
                ]
            ]
        ),
        "\nFailed ordinary-logit and ElasticNet estimates supply no valid coefficients or predictions. They remain visible in status tables; no alternative specification is substituted.",
        "\n## Layer 1 prediction and calibration",
    ]
    rows = []
    for variant in ["layer1", "layer1_term"]:
        for cohort in ["crisis_2007_2009", "additional_cohort_2011_2013"]:
            models = scores.loc[
                scores.variant.eq(variant) & scores.cohort.eq(cohort), "model"
            ].unique()
            for model in models:
                mean = means.loc[
                    means.variant.eq(variant) & means.cohort.eq(cohort) & means.model.eq(model)
                ].iloc[0]
                rows.append(
                    {
                        "specification": variant,
                        "cohort": cohort,
                        "model": model,
                        "AUC [95%]": ci(metric(variant, model, cohort, "auc")),
                        "AP": f"{metric(variant, model, cohort, 'average_precision').value:.3f}",
                        "Brier": f"{metric(variant, model, cohort, 'brier').value:.4f}",
                        "cal. intercept": f"{metric(variant, model, cohort, 'calibration_intercept').value:.3f}",
                        "cal. slope": f"{metric(variant, model, cohort, 'calibration_slope').value:.3f}",
                        "mean predicted / recorded %": f"{100 * mean.mean_predicted:.2f} / {100 * mean.recorded_rate:.2f}",
                    }
                )
    text += [
        "\n" + md(pd.DataFrame(rows)),
        "\nFirth probabilities stay raw. Calibration intercept/slope regressions and train-score-decile bins are diagnostics, not a correction to the primary scores. Raw and separately calibrated benchmarks are distinguished. Evaluation bands retain the original 999 state-cluster resamples conditional on each fitted model; they do not include training uncertainty. Training diagnostics are point-only. [Full metrics](../results/"
        + NAME
        + "/evaluation_metrics.csv) retain AP/Brier and calibration bands and undefined-draw counts; [decile bins](../results/"
        + NAME
        + "/calibration_deciles.csv) include empty bins.\n\n![Cohort calibration](../results/"
        + NAME
        + "/figures/firth_cohort_calibration.png)",
        "\n## Firth coefficients, average associations and conditional macro validation",
        "\n[Coefficient table](../results/"
        + NAME
        + "/firth_coefficients.csv) reports all retained columns, references and re-estimated percentile intervals. Numeric coefficients use train-standardized features. [Average associations](../results/"
        + NAME
        + "/firth_average_associations.csv) convert numeric derivatives to native feature units, leaving log variables in log units; categorical terms are discrete contrasts against frozen references. Layer 1 averages over its estimation loans; Layer 2 over the fixed 2006 portfolio. No absent-training category receives a dummy estimate. Every interval reports its effective denominator.",
        "\nSelected numeric average associations (probability percentage points per native feature unit):\n\n"
        + md(
            associations.loc[
                associations.feature.isin(
                    [
                        "log_approval",
                        "guarantee_share",
                        "log_jobs",
                        "du",
                        "peak_du",
                        "h0",
                        "dh",
                        "TermInMonths",
                    ]
                ),
                ["variant", "feature", "value", "lower", "upper", "effective_interval_draws"],
            ]
        ),
        "\nLayer 2 +1 pp unemployment finite-change associations, fixed 2006 observed-macro portfolio:\n\n"
        + md(
            macro.loc[
                macro.group.eq("overall"),
                ["variant", "feature", "value", "lower", "upper", "effective_interval_draws"],
            ]
        ),
        "\n"
        + VALIDATION_LABEL
        + " The endpoint Δu and peak-path alternatives keep all other applicable controls fixed. These are conditional associations, not estimates of an intervention on unemployment. Detailed fixed size, sector, age and reported-maturity group associations remain in the CSV.",
        "\nLayer 2 raw/calibrated validation and calibration diagnostics:\n\n"
        + md(
            means.loc[
                means.variant.str.startswith("layer2"),
                ["variant", "model", "cohort", "n", "events", "mean_predicted", "recorded_rate"],
            ]
        ),
        "\nLayer 2 held-out diagnostic scores:\n\n"
        + md(
            scores.loc[
                scores.variant.str.startswith("layer2")
                & scores.cohort.eq("post_amendment_validation_2013_2014"),
                ["variant", "model", "metric", "value", "lower", "upper", "undefined_draws"],
            ]
        ),
        "\n## Fixed portfolio stress, allocation and retained sensitivities",
        "\n"
        + LOSS_LABEL
        + " The pro-rata split is neither observed guarantee payouts nor measured fiscal costs. The fixed 2006 portfolio, exposure, guarantee shares and scenario paths are unchanged. Its inclusion in expanded Layer 2 estimation is explicit; it is a scenario portfolio, not out-of-sample performance. PD averages use all reference loans; loss uses the valid-share population recorded in the loss table. LGD is the original ratio-of-sums charge-off/approval proxy with fixed loan-type/size pooling, not net-of-recovery loss.\n\n![Primary stress](../results/"
        + NAME
        + "/figures/primary_stress_intervals.png)",
        "\nPrimary overall projections and paired adverse-minus-baseline differences (PD fractions except explicitly labelled pp; monetary quantities in USD):\n\n"
        + md(
            main[
                [
                    "scenario",
                    "metric",
                    "value",
                    "lower",
                    "upper",
                    "effective_interval_draws",
                    "pd_n",
                    "loss_n",
                ]
            ]
        ),
        "\n"
        + LOSS_LABEL
        + " Term/revolving split:\n\n"
        + md(
            stress.loc[
                stress.variant.eq("layer2")
                & stress.group.eq("loan_type")
                & stress.lgd_variant.eq("primary"),
                [
                    "scenario",
                    "group_value",
                    "metric",
                    "value",
                    "lower",
                    "upper",
                    "effective_interval_draws",
                ],
            ]
        ),
        "\n"
        + LOSS_LABEL
        + " All predeclared estimator/path/LGD sensitivities, overall:\n\n"
        + md(
            stress.loc[
                stress.group.eq("overall")
                & stress.metric.isin(
                    ["pd", "expected_loss_usd", "pd_change_pp", "expected_loss_usd_change"]
                ),
                [
                    "variant",
                    "scenario",
                    "lgd_variant",
                    "metric",
                    "value",
                    "lower",
                    "upper",
                    "effective_interval_draws",
                ],
            ]
        ),
        f"\nThe downturn proxy still uses only 1991 and 2000–2001 cohorts, with {int(lgd_down.valid_cell_n.sum()):,} valid training charge-offs and original sparse-cell rules. Per-loan capped LGD is a separate fixed sensitivity; primary LGD stays uncapped. Primary, capped and downturn tables numerically reconcile with their G2 versions. Peak unemployment replaces Δu rather than augmenting it. With-Term fits remain timing-qualified sensitivities. Old-extract CCF remains unavailable because its licence/cutoff admissibility conditions are unmet; no extract was acquired. Urban/rural fields are absent and historical rate coefficients are unsupported. [Secondary trees](../results/"
        + NAME
        + "/benchmark_stress_point.csv) report raw and calibrated point projections without pretending to have Firth training-refit intervals.",
        "\nUnivariate support checks — state-specific and pooled-global separately:\n\n"
        + md(
            support[
                [
                    "variant",
                    "scenario",
                    "scope",
                    "flagged_loan_n",
                    "flagged_fraction",
                    "flagged_approval_usd",
                    "n",
                ]
            ]
        ),
        "\nFlags compare each input against univariate training ranges; [feature-level counts](../results/"
        + NAME
        + "/scenario_support_by_feature.csv) expose which variables trigger them. Neither a lack of flags nor a tree probability demonstrates joint support. Approval-dollar exposure is reported even when one loan triggers several feature flags; the union summary counts each flagged loan once.",
        "\n## Term timing audit",
        "\nAll applicable eligible date-valid charge-offs and PIF records are included, including later-than-36-month charge-offs. Elapsed months use actual elapsed days/(365.25/12); difference is TermInMonths minus elapsed months. Frozen raw Term alone is reread to distinguish invalid/missing values before historical preprocessing.\n\n"
        + md(
            term.loc[
                term.scope.isin(["overall", "status"]),
                [
                    "scope",
                    "group",
                    "n",
                    "valid_n",
                    "date_missing_n",
                    "date_invalid_n",
                    "term_missing_n",
                    "term_invalid_n",
                    "match_abs_le_3_n",
                    "match_abs_le_3_share",
                    "charge_off_after_label_window_n",
                    "verdict",
                ],
            ]
        ),
        f"\nVerdict: **{term_charge.verdict}** The valid charge-off matching share is {100 * term_charge.match_abs_le_3_share:.2f}% and does not meet the predeclared strong-update descriptive flag. This does not verify original approval-time measurement. No supporting metadata/original vintage evidence was verified; PIF coincidence alone also cannot prove updating. Primary models stay Term-free. Full difference distributions, counts by approval year/loan type/status and all three classification definitions are in [term_audit_summary.csv](../results/"
        + NAME
        + "/term_audit_summary.csv) and [evidence](../results/"
        + NAME
        + "/term_audit_evidence.json).",
        "\n## Uncertainty, failures, runtime and preservation",
        "\nPositive state-weighted multiplier inference uses one independent Exp(1) weight per state per scheduled draw, normalized separately within each layer to the original loan count. Every state remains present. Underlying weights are shared across comparisons and paired scenarios. Each fit re-estimates the weighted likelihood and weighted Firth penalty with frozen maps/columns. Percentile intervals use successful fully defined draws only, never silently redrawn failures. State clusters are assumed independent. LGD, scenario paths, portfolio composition, preprocessing, exposure allocation and source vintages are held fixed; their uncertainty is excluded. Conditional 999-draw evaluation intervals remain distinct.",
        "\n"
        + md(
            pd.DataFrame(boot)[
                [
                    "variant",
                    "attempted",
                    "successful",
                    "failed",
                    "failure_reasons",
                    "point_converged",
                ]
            ]
        ),
        f"\nPilot wall time {pilot['seconds_this_execution']:.1f} seconds; peak RSS {pilot['peak_rss_GiB']:.2f} GiB. Its first five scheduled draws per model were retained in 199. Projected remaining time was {pilot['projected_remaining_seconds'] / 60:.1f} minutes. Actual remaining execution wall time was {runtime['seconds_this_execution'] / 60:.1f} minutes with peak RSS {runtime['peak_rss_GiB']:.2f} GiB; cached pilot fits are not counted as new attempts. Individual fit/association runtimes and failure messages are in [bootstrap_attempts.csv](../results/"
        + NAME
        + "/bootstrap_attempts.csv). Benchmarks and term/diagnostic work ran separately; full pipeline runtime is not a clean-build claim.",
        "\nSoftware/statistical checks:\n\n"
        + md(
            pd.DataFrame([tests])[
                [
                    "tests_passed",
                    "test_seconds",
                    "package_coverage_percent",
                    "statistical_core_coverage_percent",
                    "lint",
                    "mypy",
                    "preservation_entries",
                    "repo_disk_GiB",
                    "portfolio_disk_GiB",
                ]
            ]
        ),
        "\n[Completed-draw identity checks](../results/"
        + NAME
        + "/statistical_completion_checks.json) independently verify the saved state-weight/configuration hashes, finite successful-draw quantities, percentile coefficient intervals, effective denominators and paired scenario/allocation accounting without any new estimation.",
        f"\nPreservation checks passed for {len(preserved):,} baseline entries ({int(preserved.scope.eq('public').sum()):,} public; {int(preserved.scope.eq('private').sum()):,} private). Protocol v1, G2 outputs and private frozen files have identical hashes. DECISIONS.md alone has an authorized appended entry; its exact former bytes are retained and checked in the dated version. Existing implementation, Makefile and original reports remain unchanged. [Preservation ledger](../results/"
        + NAME
        + "/preservation_checks.csv) and [private run lineage](../results/"
        + NAME
        + "/private_run_lineage.json) contain hashes, not loan data. No raw/private data or secrets were committed.",
        "\n## G2 → G2-bis interpretation",
        "\n"
        + LOSS_LABEL
        + " Monetary rows below carry this same disclosure in the CSV.\n\n"
        + md(comparisons.drop(columns="loss_accounting")),
        f"\nG2 primary MLE/peak/stress associations were unavailable because fits failed; G2-bis estimates them with post-results Firth and pooled categories. This is an estimator/design change, not evidence of better validation. G2’s later-cohort Layer 2 calibration failure is retained: calibrated macro LightGBM predicted {100 * old_mean:.2f}% against {100 * old_rate:.2f}% recorded on 2011–2013; the exact figures derive from the preserved state-validation table. G2-bis Layer 2 simultaneously changes estimation coverage, calibration cohort, benchmark-settings source and validation years, so its differences cannot isolate a single cause. The new held-out sample is retrospectively conditional and partly previously observed; no confirmatory claim is made. Raw Firth convergence does not establish calibration or reliable counterfactual loss levels.",
        "\n## Limitations and stopping boundary",
        "\nAdministrative charge-off is not delinquency and mature EXEMPT loans are not certified performing. Approval-field historical vintages, selection into approved/disbursed lending, missing rates and unfamiliar categories limit retrospective reconstruction. Revised macro data and future realized paths cannot establish approval-time prediction. Gross approval/full utilisation and gross charge-off severity are proxies; recovery and payout information are absent. State-cluster independence, modest cluster count, fixed preprocessing/LGD/paths and successful-draw conditioning constrain inference. Marginal univariate support does not imply joint support. With-Term associations do not verify vintage. The source does not support rejected-applicant risk, causal macro/guarantee effects or measured fiscal costs. Old-extract utilisation remains inadmissible; no replacement is silently supplied.",
        "\nG2-bis ends here. No G3 policy-date analysis, G5 paper/notes, pushes, publication or paid calls were undertaken. Detailed execution/source qualifications: [G2_BIS_EXECUTION_2026-10-08.md](G2_BIS_EXECUTION_2026-10-08.md). The original G2 report and protocol v1 remain unchanged.",
        "\nReferences: [Firth controls and weighted case likelihood](https://search.r-project.org/CRAN/refmans/logistf/html/logistf.html); [fixed numerical criteria](https://search.r-project.org/CRAN/refmans/logistf/html/logistf.control.html); [brglm2 mean-bias reduction](https://cran.r-project.org/web/packages/brglm2/index.html); [Kosmidis and Firth (2021)](https://doi.org/10.1093/biomet/asaa052). Official [SBA FOIA](https://data.sba.gov/dataset/7a-504-foia), [BLS API](https://www.bls.gov/developers/) and [FHFA](https://www.fhfa.gov/hpi) sources; actual file hashes/retrieval metadata take precedence over live releases.",
    ]
    (root / "docs/G2_BIS_REPORT_2026-10-08.md").write_text("\n".join(text) + "\n")
    # All new public numerical outputs are bound to source/config and exact executing code.
    manifest = {
        "config_sha256": sha256(root / "config/g2_bis_2026-10-08.yaml"),
        "base_G2_commit": "bb7cc626bf80d6c5694dd7c640b13557b258c971",
        "protocol_commit": "1d39a458ee1bbd0e1604a5b78a2e6f8372fb1c53",
        "private_inputs": {
            str(p.relative_to(root)): sha256(p)
            for p in [
                root / "data" / NAME / "matched.parquet",
                root / "data" / NAME / "reference.parquet",
                root / "data" / NAME / "term_audit.parquet",
                root / "data" / NAME / "macro/unemployment_plus_2017.parquet",
            ]
        },
        "private_model_and_evaluation_artifacts": {
            str(p.relative_to(root)): sha256(p)
            for p in sorted((root / "models" / NAME).glob("*.joblib"))
            if "_draw_" not in p.name
        },
        "implementation": {
            str(p.relative_to(root)): sha256(p)
            for p in sorted((root / "src/credit_risk_sba").glob("bis_*.py"))
        },
        "new_outputs": {
            str(p.relative_to(root)): sha256(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "output_manifest.json"
        },
        "report_sha256": sha256(root / "docs/G2_BIS_REPORT_2026-10-08.md"),
        "newly_executed_models_and_diagnostics": True,
        "inherited_outputs": {
            "source_population_waterfall.csv": "Copied unchanged from results/g2-2026-10-08/sample_waterfall.csv; frozen eligibility was not rebuilt or refreshed"
        },
        "unchanged_fixed_inputs_recomputed_and_verified": [
            "lgd_primary.csv",
            "lgd_capped.csv",
            "lgd_downturn.csv",
            "scenario_paths.csv",
        ],
        "raw_and_private_data_not_committed": True,
    }
    js(out / "output_manifest.json", manifest)


if __name__ == "__main__":
    report(Path.cwd())
