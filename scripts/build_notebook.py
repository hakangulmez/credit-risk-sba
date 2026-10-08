"""Create the source of the frozen-results research walkthrough."""

from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CELLS: list[dict] = []


def cell(kind: str, source: str) -> None:
    source = textwrap.dedent(source).strip() + "\n"
    value = {
        "cell_type": kind,
        "id": hashlib.sha256((str(len(CELLS)) + source).encode()).hexdigest()[:12],
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }
    if kind == "code":
        value.update(execution_count=None, outputs=[])
    CELLS.append(value)


def build() -> None:
    CELLS.clear()
    cell(
        "markdown",
        """
        # Local economic conditions and public–lender loss sharing in SBA 7(a) lending

        **Research walkthrough — frozen results, 8 October 2026**

        How does recorded charge-off risk vary across cohorts and local economic conditions,
        and how are assumption-based losses allocated between SBA and lenders?

        This notebook follows the complete analytical pipeline and displays the accepted
        saved results. **Run All works without raw borrower data, model objects, network
        access or new estimation.** Model estimation is explained, rather than silently
        rerun. The optional private re-estimation guide is disabled by default.

        Sections: sources and sample → design and chronology → scorecard validation →
        calibration → macro associations → scenario PD/loss sharing → sensitivities →
        diagnostics and full result catalogue → private replication requirements.
        All numerical displays come from saved aggregates or the claims registry.
    """,
    )
    cell(
        "code",
        """
        from pathlib import Path
        import json
        import sys

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import yaml
        from IPython.display import HTML, Image, Markdown, display

        ROOT = next(
            path for path in (Path.cwd(), *Path.cwd().parents)
            if (path / "PUBLIC_RELEASE_MANIFEST.json").is_file()
        )
        sys.path.insert(0, str(ROOT))
        from reporting.checks import verify_claims
        from reporting.registry import Registry

        SOURCE = ROOT / "results/g2-bis-2026-10-08"
        payload = json.loads((ROOT / "results/g5-2026-10-08/claims_registry.json").read_text())
        provenance = verify_claims(ROOT, payload)
        registry = Registry(ROOT)
        registry.entries, registry.aliases = payload["claims"], payload["aliases"]
        config = yaml.safe_load((ROOT / "config/g2_bis_2026-10-08.yaml").read_text())
        RESULTS = {
            str(path.relative_to(ROOT)): pd.read_csv(path)
            for path in sorted((ROOT / "results").rglob("*.csv"))
        }
        tables = {
            path.stem: RESULTS[str(path.relative_to(ROOT))]
            for path in sorted(SOURCE.glob("*.csv"))
        }
        plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})

        def show(frame, title=None, rows=None):
            if title:
                display(Markdown("**" + title + "**"))
            display(HTML(frame.to_html(index=False, max_rows=rows, float_format=lambda v: f"{v:,.4f}")))

        def show_result(path, rows=None):
            key = path if path in RESULTS else "results/g2-bis-2026-10-08/" + path
            show(RESULTS[key], key, rows=rows)

        def select(frame, **values):
            mask = pd.Series(True, index=frame.index)
            for column, value in values.items():
                mask &= frame[column].eq(value)
            return frame.loc[mask].copy()

        print("Mode: frozen aggregate results only; no model fitting or acquisition.")
        print("Provenance:", provenance)
    """,
    )
    cell(
        "markdown",
        """
        ## 1. Economic question and data

        SBA guarantees redistribute potential credit losses between public and private
        balance sheets. An origination scorecard can rank loans while failing to transfer
        its probability level across economic regimes. We therefore distinguish
        discrimination, calibration, conditional macro associations and loss accounting.

        Loan source: official SBA 7(a) FOIA files, snapshot **30 June 2026**, with loans of
        all disclosed statuses and complete 36-month outcome windows. Macro sources:
        direct BLS state unemployment and FHFA all-transactions state HPI. Observations
        are revised histories, not historical real-time releases. The outcome is
        **recorded charge-off within 36 months of first disbursement**, not delinquency.

        The source audit and selection rules are in `DATA.md` and the fixed protocols.
        This product uses FHFA data but is neither endorsed nor certified by FHFA.

        Cohort plots describe the eligible disclosed sample. Boundary years are partial;
        in particular, 2023 includes only disbursements with a mature outcome window by
        the snapshot cutoff. They are not full-year population incidence estimates.
    """,
    )
    cell(
        "code",
        """
        show(tables["source_population_waterfall"], "Source-to-eligible population waterfall")
        show(tables["final_sample_waterfall_complete"], "Final samples and temporal roles")
    """,
    )
    cell(
        "code",
        """
        cohort = tables["cohort_counts"].copy()
        cohort["recorded_rate_pct"] = 100 * cohort["events"] / cohort["eligible"]
        fig, axes = plt.subplots(1, 2, figsize=(12, 3.5))
        axes[0].bar(cohort["year"], cohort["eligible"], color="#0072B2")
        axes[0].set(xlabel="First-disbursement cohort", ylabel="Eligible loans", title="Sample composition")
        axes[1].plot(cohort["year"], cohort["recorded_rate_pct"], color="#D55E00", marker=".")
        axes[1].set(xlabel="First-disbursement cohort", ylabel="Recorded charge-off (%)", title="Descriptive cohort rates")
        fig.tight_layout()
        plt.show()
        show(cohort, "All cohort counts and recorded rates")
    """,
    )
    cell(
        "markdown",
        """
        ## 2. Feature construction, models and chronology

        **Layer 1:** Firth logit uses approval descriptors and state effects; fits use
        1991–2002, benchmark settings were chosen on 2003H1, benchmark calibration uses
        2003H2, and checks use 2007–2009 and 2011–2013.

        **Layer 2:** Firth logit adds realized or stipulated state macro paths and a
        linear disbursement-year trend; fits use 1991–2009, tree calibration uses 2010,
        and conditional validation uses 2013–2014. Future macro paths make this
        **retrospective conditional validation, not real-time approval prediction**.
        Calibration labels overlap the 2013 validation calendar; that cohort had
        already been inspected. The 2006 scenario portfolio enters Layer 2 estimation.

        Firth is primary because ordinary logits do not yield valid finite estimates
        under the accepted design. Finite Firth coefficients do not prove calibration.
        ElasticNet and LightGBM are fixed-setting predictive benchmarks/robustness.
        Primary models exclude Term and InitialInterestRate. Frequency pooling uses
        training counts only; state effects remain separate. Imputation, scaling and
        category maps use training data only.

        **Design history:** the Firth specification was frozen after the initial failed
        logit/calibration results were seen, and before the Firth fits. This is a
        post-results amendment; see `docs/METHOD_HISTORY.md`.
    """,
    )
    cell(
        "code",
        """
        design_choices = pd.DataFrame([
            {"Choice": "Outcome", "Fixed rule": config["outcome"]},
            {"Choice": "Primary estimator", "Fixed rule": "Firth logit, Term-free"},
            {"Choice": "Frequency pooling", "Fixed rule": f"Training share < {config['categorical_pooling']['threshold']}; ProjectState excluded"},
            {"Choice": "Inference", "Fixed rule": f"{config['bootstrap']['attempts']} positive state-weighted re-estimation attempts"},
            {"Choice": "Seed", "Fixed rule": str(config["seed"])},
            {"Choice": "Reference portfolio", "Fixed rule": str(config["reference_year"])},
        ])
        show(design_choices, "Fixed design choices")
        show(tables["initial_interest_rate_missingness"], "Rate missingness: excluded shared predictor")
        show(tables["design_rank_checks"], "Training design and state effects")
        show(tables["layer1_pooled_level_counts"], "Layer 1 pooled levels: diagnostic events/non-events", rows=12)
        show(tables["layer2_pooled_level_counts"], "Layer 2 pooled levels", rows=12)
    """,
    )
    cell(
        "markdown",
        """
        ## 3. Main findings from the claim ledger

        Intervals below are the saved intervals, with explicit units. No fresh interval,
        fit, threshold selection or diagnostic estimation is performed here.
    """,
    )
    cell(
        "code",
        """
        headline_aliases = [
            "auc_crisis", "pd_crisis", "auc_later", "pd_later",
            "pd_l2_firth", "pd_l2_tree", "tree_calibration_intercept", "tree_calibration_slope",
            "endpoint", "peak", "baseline_expected_loss_usd", "adverse_expected_loss_usd",
            "adverse_minus_baseline_expected_loss_usd_change", "baseline_sba_share", "adverse_sba_share",
        ]
        headline = pd.DataFrame([
            {"Claim": alias, "Saved display": registry.human_display(alias)[0], "Units": registry.human_display(alias)[1]}
            for alias in headline_aliases
        ])
        show(headline, "Registered headline quantities")
        display(Image(filename=str(ROOT / "figures/g5/headline.png"), width=900))
    """,
    )
    cell(
        "markdown",
        """
        ## 4. Discrimination and temporal validation

        AUC measures risk ranking; average precision depends on the outcome prevalence;
        Brier score measures probability accuracy. Keep these separate from calibration.
        The saved metric intervals condition on fitted models and differ from the
        training-refit intervals used for Firth associations and scenarios.
    """,
    )
    cell(
        "code",
        """
        metrics = tables["evaluation_metrics"]
        validation_cohorts = ["crisis_2007_2009", "additional_cohort_2011_2013", "post_amendment_validation_2013_2014"]
        main_metrics = metrics.loc[metrics["variant"].isin(["layer1", "layer2"]) & metrics["cohort"].isin(validation_cohorts)]
        ranking = main_metrics.loc[main_metrics["metric"].isin(["auc", "average_precision", "brier"])]
        show(ranking.pivot(index=["variant", "model", "cohort"], columns="metric", values="value").reset_index(), "Term-free model comparison")
        show(ranking[["variant", "model", "cohort", "metric", "value", "lower", "upper", "bootstrap_draws", "undefined_draws"]], "Saved evaluation intervals")
    """,
    )
    cell(
        "markdown",
        """
        ## 5. Calibration: average level, intercept/slope and risk groups

        Average agreement does not establish calibration across risk groups. Diagnostic
        intercept and slope ideals are 0 and 1. Firth probabilities remain raw; these
        diagnostics do not update them. Risk bins retain the saved training-score edges
        and their unequal evaluation counts. A zero recorded rate in a nonempty bin is
        a valid saved result, not missing information.
    """,
    )
    cell(
        "code",
        """
        means = tables["calibration_means"]
        main_means = means.loc[means["variant"].isin(["layer1", "layer2"]) & means["cohort"].isin(validation_cohorts)].copy()
        main_means["predicted_pct"] = 100 * main_means["mean_predicted"]
        main_means["recorded_pct"] = 100 * main_means["recorded_rate"]
        show(main_means[["variant", "model", "cohort", "n", "events", "predicted_pct", "recorded_pct"]], "Mean prediction versus recorded outcome (%)")
        show(main_metrics.loc[main_metrics["metric"].isin(["calibration_intercept", "calibration_slope"]), ["variant", "model", "cohort", "metric", "value", "lower", "upper", "undefined_draws"]], "Saved calibration intercept/slope and intervals")
        display(Image(filename=str(ROOT / "figures/g5/calibration_groups.png"), width=900))
    """,
    )
    cell(
        "code",
        """
        bins = tables["calibration_deciles"]
        combinations = [
            ("layer1", "firth_raw", "crisis_2007_2009"),
            ("layer1", "firth_raw", "additional_cohort_2011_2013"),
            ("layer2", "firth_raw", "post_amendment_validation_2013_2014"),
            ("layer2", "lightgbm_calibrated", "post_amendment_validation_2013_2014"),
        ]
        for variant, model, cohort_name in combinations:
            block = select(bins, variant=variant, model=model, cohort=cohort_name)
            assert len(block) == 10 and (block["n"] > 0).all()
            show(block[["bin", "lower_edge", "upper_edge", "n", "predicted_pd", "recorded_rate", "lower", "upper", "undefined_draws"]], f"Saved risk groups: {variant} / {model} / {cohort_name}")
    """,
    )
    cell(
        "markdown",
        """
        ## 6. Conditional macro associations

        Endpoint unemployment change is **u at month +36 minus u at the disbursement
        month**. Peak change is **max(u month − u start)** within the window; it can capture
        an increase followed by recovery. These are separately estimated specifications.
        The +1 pp conditional contrast is a finite probability change on the fixed 2006
        portfolio, not a causal effect or an automatic derivative.

        Saved macro variables: `u0` is starting unemployment in percent, `du` and
        `peak_du` are unemployment changes in percentage points, `h0` is starting
        four-quarter HPI growth as 100 × log(HPI / HPI one year earlier), and `dh` is
        the 36-month HPI log change as 100 × log(HPI end / HPI start).

        State effects do not identify unemployment, housing or guarantee coefficients
        causally. Numeric logit coefficients are on training-standardized feature scales;
        saved average associations use their stated native units/contrasts.
    """,
    )
    cell(
        "code",
        """
        macro = tables["firth_macro_associations"]
        main_macro = macro.loc[macro["variant"].isin(["layer2", "layer2_peak"]) & macro["group"].eq("overall")]
        show(main_macro[["variant", "feature", "change", "value", "lower", "upper", "n", "effective_interval_draws", "interpretation"]], "Endpoint and peak unemployment contrasts (probability pp)")
        associations = tables["firth_average_associations"]
        important = associations.loc[associations["variant"].isin(["layer1", "layer2"]) & associations["feature"].isin(["log_approval", "guarantee_share", "log_jobs", "u0", "du", "h0", "dh", "year_trend"])]
        show(important[["variant", "feature", "value", "lower", "upper", "contrast", "effective_interval_draws"]], "Selected saved average associations (not causal)")
        show(macro.loc[macro["variant"].isin(["layer2", "layer2_peak"]) & macro["group"].eq("loan_type"), ["variant", "feature", "group_value", "value", "lower", "upper", "effective_interval_draws"]], "Loan-type conditional contrasts")
    """,
    )
    cell(
        "markdown",
        """
        ## 7. Stress scenarios and public–lender loss accounting

        The 2006 reference portfolio is a **scenario portfolio, not an out-of-sample
        validation test**. Paths are stipulated. Display their context using
        `macro_information_context`; the inherited validation label in another source
        column is not a scenario interpretation.

        **EAD = GrossApproval, CCF = 100%, full-disbursement proxy.** LGD is gross charge-off
        amount divided by that same approval proxy, not net-of-recovery LGD. Expected loss
        is summed as PD × EAD × LGD. Allocation uses each loan's guaranteed-approval share
        pro rata for SBA and its complement for lenders. These are loss proxies, not
        observed guarantee payouts or measured fiscal costs. Scenario PDs reweight loans,
        so aggregate SBA shares need not be constant.

        Saved paired-difference intervals use paired draws; do not subtract marginal
        interval endpoints. Probability miscalibration can affect levels, differences
        and ratios. Intervals hold the portfolio, macro paths, EAD and LGD assumptions fixed.
    """,
    )
    cell(
        "code",
        """
        paths = tables["scenario_paths"]
        show(paths.groupby("scenario")[["u0", "du", "peak_du", "h0", "dh"]].agg(["min", "max"]).reset_index(), "Stipulated state-path ranges (descriptive summary)")
        show(tables["loss_population"], "PD and loss accounting population")
        stress = tables["firth_stress"]
        overall = select(stress, variant="layer2", lgd_variant="primary", group="overall")
        main_stress = overall.loc[overall["metric"].isin(["pd", "expected_loss_usd", "sba_loss_usd", "lender_loss_usd", "pd_change_pp", "expected_loss_usd_change", "sba_loss_usd_change", "lender_loss_usd_change"])].copy()
        main_stress["display_units"] = np.where(main_stress["metric"].str.contains("loss_usd"), "USD millions", np.where(main_stress["metric"].eq("pd"), "PD percent", "probability pp"))
        scale = np.where(main_stress["metric"].str.contains("loss_usd"), 1e-6, np.where(main_stress["metric"].eq("pd"), 100, 1))
        for field in ["value", "lower", "upper"]:
            main_stress[field] = main_stress[field] * scale
        show(main_stress[["scenario", "metric", "value", "lower", "upper", "display_units", "effective_interval_draws"]], "Primary Firth scenario PD and loss proxies")
        assert overall["macro_information_context"].str.contains("scenario portfolio").all()
    """,
    )
    cell(
        "code",
        """
        scenarios = ["baseline", "adverse"]
        allocation = overall.loc[overall["scenario"].isin(scenarios)].pivot(index="scenario", columns="metric", values="value").reindex(scenarios)
        assert np.allclose(allocation["expected_loss_usd"], allocation["sba_loss_usd"] + allocation["lender_loss_usd"])
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar(scenarios, allocation["sba_loss_usd"] / 1e6, label="SBA pro-rata proxy", color="#0072B2")
        ax.bar(scenarios, allocation["lender_loss_usd"] / 1e6, bottom=allocation["sba_loss_usd"] / 1e6, label="Lender-retained proxy", color="#E69F00")
        ax.set(ylabel="Expected-loss proxy (USD millions)", title="Fixed 2006 portfolio; stipulated scenarios (point estimates)")
        ax.legend()
        fig.tight_layout()
        plt.show()
        shares = allocation[["expected_loss_usd", "sba_loss_usd", "lender_loss_usd"]].copy()
        shares["sba_share_pct"] = 100 * shares["sba_loss_usd"] / shares["expected_loss_usd"]
        shares["lender_share_pct"] = 100 - shares["sba_share_pct"]
        show(shares.reset_index(), "Scenario-dependent pro-rata allocation (dollar columns in USD)")
    """,
    )
    cell(
        "markdown",
        """
        ## 8. Predeclared sensitivities and subgroup results

        Endpoint versus peak unemployment, primary versus capped/downturn LGD, and
        with-Term variants remain separately labelled. With-Term results do not replace
        the Term-free headline. Downturn LGD uses only training charge-offs from the
        1991 and 2000–2001 disbursement cohorts, with the fixed small-cell pooling rule.
        Revolving lines are separate; 100% utilization is an assumption.
    """,
    )
    cell(
        "code",
        """
        sensitivity = stress.loc[stress["group"].eq("overall") & stress["metric"].isin(["pd", "expected_loss_usd", "expected_loss_usd_change"])].copy()
        sensitivity["units"] = np.where(sensitivity["metric"].eq("pd"), "PD percent", "USD millions")
        sensitivity["display_value"] = sensitivity["value"] * np.where(sensitivity["metric"].eq("pd"), 100, 1e-6)
        sensitivity["display_lower"] = sensitivity["lower"] * np.where(sensitivity["metric"].eq("pd"), 100, 1e-6)
        sensitivity["display_upper"] = sensitivity["upper"] * np.where(sensitivity["metric"].eq("pd"), 100, 1e-6)
        show(sensitivity[["variant", "lgd_variant", "scenario", "metric", "display_value", "display_lower", "display_upper", "units", "effective_interval_draws"]], "All overall Firth scenario sensitivities")
        lgd = pd.concat([tables["lgd_primary"], tables["lgd_capped"], tables["lgd_downturn"]], ignore_index=True)
        show(lgd[["variant", "loan_type", "size_band", "cohorts", "valid_cell_n", "pool", "pooled_n", "lgd_proxy", "ratios_above_one"]], "LGD proxy cells and pooling")
    """,
    )
    cell(
        "code",
        """
        loan_type_losses = stress.loc[stress["variant"].eq("layer2") & stress["lgd_variant"].eq("primary") & stress["group"].eq("loan_type") & stress["metric"].isin(["pd", "expected_loss_usd", "sba_loss_usd", "lender_loss_usd"])]
        show(loan_type_losses[["scenario", "group_value", "metric", "value", "lower", "upper", "pd_n", "loss_n", "effective_interval_draws"]], "Term versus revolving: saved values (PD fraction; losses USD)")
        subgroup_results = stress.loc[stress["variant"].eq("layer2") & stress["lgd_variant"].eq("primary") & stress["group"].isin(["size_band", "naics2", "age_group", "maturity_group"])]
        show(subgroup_results[["scenario", "group", "group_value", "metric", "value", "lower", "upper", "pd_n", "effective_interval_draws"]], "All other primary subgroup results: available as subgroup_results", rows=18)
        show(tables["paired_term_differences"], "Saved paired with-Term differences: qualified sensitivity", rows=12)
        benchmark_stress = tables["benchmark_stress_point"]
        show(benchmark_stress.loc[benchmark_stress["variant"].eq("layer2") & benchmark_stress["lgd_variant"].eq("primary") & benchmark_stress["group"].eq("overall")], "Fixed-tree stress robustness: point estimates only", rows=16)
    """,
    )
    cell(
        "markdown",
        """
        ## 9. Numerical failures, support and timing audit

        Valid convergence and failure counts are part of the result. Failed draws were
        not redrawn; successful denominators vary by specification and estimate.
        State-specific and pooled-global **univariate range checks** are separate and
        do not establish joint support or scenario plausibility.

        Term timing remains **unverifiable**. Low agreement with elapsed repayment or
        charge-off time does not verify an approval-time vintage. All primary models
        exclude Term regardless. Unknown predictor vintages remain a limitation.
    """,
    )
    cell(
        "code",
        """
        fit_status = tables["fit_status"].copy()
        fit_status.loc[fit_status["variant"].eq("layer2_peak") & fit_status["family"].eq("Firth primary"), "family"] = "Firth peak sensitivity"
        show(fit_status[["variant", "family", "converged", "message", "iterations", "n", "specification_role"]], "Saved point-fit status (presentation label corrected; source unchanged)")
        bootstrap = pd.DataFrame(json.loads((SOURCE / "bootstrap_summary.json").read_text()))
        show(bootstrap, "All attempted, successful and failed training refits")
        support = tables["scenario_support_summary"].copy()
        support["flagged_percent"] = 100 * support["flagged_fraction"]
        show(support[["variant", "scenario", "scope", "flagged_loan_n", "n", "flagged_percent", "definition"]], "State-specific and global univariate support")
        term = select(tables["term_audit_summary"], scope="status")
        show(term[["group", "n", "valid_n", "term_invalid_n", "match_abs_le_3_share", "difference_median", "verdict"]], "Term audit by recorded status")
        show(tables["preprocessing_application_counts"], "Missing/unseen-level application counts", rows=12)
    """,
    )
    cell(
        "markdown",
        """
        ## 10. Other saved diagnostics

        Population stability is descriptive distribution drift. TreeSHAP is predictive
        attribution, not identification. The fixed 70% allocation is a diagnostic,
        not an operational approval policy or evidence of increased lending benefits.
        Full tables remain available in `tables` and in the catalogue below.
    """,
    )
    cell(
        "code",
        """
        show(tables["population_stability"].loc[tables["population_stability"]["variant"].eq("layer1")], "Layer 1 population stability", rows=16)
        show(tables["treeshap"].loc[tables["treeshap"]["variant"].isin(["layer1", "layer2"])], "Fixed-tree predictive attribution", rows=16)
        show(tables["portfolio_allocation_70pct"].loc[tables["portfolio_allocation_70pct"]["variant"].isin(["layer1", "layer2"])], "Fixed-score allocation diagnostic", rows=10)
    """,
    )
    cell(
        "markdown",
        """
        ## 11. Full result catalogue

        Every published CSV is loaded into `RESULTS`, including dated initial-model,
        amended-model and report-display tables. The current study uses the amended
        Firth design; historical estimates are retained for audit, not pooled with it.
        `tables` provides every current empirical CSV by filename stem.

        To show a complete table, edit the next cell's `RESULT_FILE` and rerun it, or call
        `show_result("firth_coefficients.csv")`. No rows are dropped from stored DataFrames.
        The default compact previews explicitly show truncation; `rows=None` displays
        the entire selected table. This avoids pretending that a preview is all rows.
    """,
    )
    cell(
        "code",
        """
        catalogue = pd.DataFrame([
            {"Result file": path, "Rows": len(frame), "Columns": len(frame.columns), "Result set": Path(path).parts[1]}
            for path, frame in RESULTS.items()
        ])
        show(catalogue, "Every saved CSV in this repository")
        RESULT_FILE = "firth_coefficients.csv"
        show_result(RESULT_FILE, rows=16)
        print("Use show_result(RESULT_FILE, rows=None) for the complete table.")
    """,
    )
    cell(
        "markdown",
        """
        ## 12. Optional private re-estimation guide — disabled

        This section is a **manual guide**, not an automatic model-execution switch.
        Set `ENABLE_PRIVATE_REESTIMATION_GUIDE = True` only to reveal the actual module
        order and prerequisites. It never imports model code, launches fits, downloads
        data or overwrites accepted results.

        Full empirical replication needs a separate vetted workspace containing the
        accepted raw SBA/macro vintages, initial eligible/macro-matched loan panels,
        benchmark checkpoints, fixed maps and original hash ledgers. A fresh current
        source download is not guaranteed to match the accepted vintage. Existing
        research modules use dated output paths; do not run them against this reviewed
        public checkout. See the detailed dated execution and source records.
    """,
    )
    cell(
        "code",
        """
        ENABLE_PRIVATE_REESTIMATION_GUIDE = False
        if ENABLE_PRIVATE_REESTIMATION_GUIDE:
            display(Markdown(
                "**Manual module order, in a separate verified workspace:**\\n\\n"
                "1. Verify frozen inputs and hashes; construct the eligible 36-month panel.\\n"
                "2. `credit_risk_sba.bis_data.prepare`: verify/append missing dated macro coverage and prepare paths.\\n"
                "3. `scripts/g2_bis/validate_firth.py`: independent implementation validation.\\n"
                "4. `python -m credit_risk_sba.bis_runner --pilot`: bounded pilot including initial scheduled draws.\\n"
                "5. `python -m credit_risk_sba.bis_runner`: remaining scheduled attempts, no redrawing.\\n"
                "6. `python -m credit_risk_sba.bis_benchmarks`: inherited-setting robustness.\\n"
                "7. `python -m credit_risk_sba.bis_term` and `bis_diagnostics`: timing and diagnostics.\\n"
                "8. `python -m credit_risk_sba.bis_finalize`: saved aggregates/intervals and preservation checks.\\n"
                "9. `scripts/g2_bis/validate_results.py`, software checks and `bis_reporting`: validation/reporting.\\n\\n"
                "**No commands above are executed by this notebook.** Full instructions are in "
                "`docs/G2_BIS_EXECUTION_2026-10-08.md`."
            ))
        else:
            print("Private re-estimation guide disabled. No model runs or acquisition performed.")
    """,
    )
    cell(
        "markdown",
        """
        ## 13. Interpretation and limits

        Modest risk discrimination and failed cohort calibration remain substantive
        findings. Average agreement does not solve group calibration. Local macro
        quantities are conditional associations. Loss allocation is assumption-based
        accounting, with fixed path/LGD/EAD uncertainty excluded from the reported
        training-refit intervals. The borrower sample excludes rejected applicants;
        descriptor vintages, revised macro histories and administrative status rules
        further limit interpretation. There is no causal guarantee-policy estimate or
        deployed lending rule.

        **Read next:** `report/policy_note.pdf`, `report/technical_report.pdf`, `CLAIMS.md`,
        `DATA.md`, `PUBLIC_RELEASE.md` and `docs/METHOD_HISTORY.md`. Additional recalibration,
        competing risks and policy identification require separate future protocols.
    """,
    )
    cell(
        "code",
        """
        completion = {
            "Mode": "Frozen aggregate walkthrough",
            "Verified source cells": provenance["verified_cells"],
            "Permitted derived claims": provenance["derived_cells"],
            "Saved CSV tables available": len(RESULTS),
            "Private model execution": False,
            "Network/data acquisition": False,
        }
        show(pd.DataFrame([completion]), "Walkthrough completed")
    """,
    )
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3.11", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "portfolio": {
                "mode": "frozen-aggregate-walkthrough",
                "empirical_execution": False,
                "source_commit": "40c7c5ec9e3386dcf1ebfafcb5335da0e4e6b179",
            },
        },
        "cells": CELLS,
    }
    target = ROOT / "notebooks/research_walkthrough.ipynb"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
    print(f"Created {len(CELLS)} cells; frozen-results mode only.")


if __name__ == "__main__":
    build()
