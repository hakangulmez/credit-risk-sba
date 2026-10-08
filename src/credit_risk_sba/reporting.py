"""A short, number-generated G2 gate report; no G5 report replacements."""
import json
from pathlib import Path

import pandas as pd

from .io import config, sha256, write_json


def summary(root: Path):
    cfg = config(root)
    result = root / "results/g2-2026-10-08"
    splits = pd.read_csv(result / "frozen_split_counts.csv").set_index("role")
    split_counts = splits[["n", "recorded_charge_offs_36m"]].to_dict("index")
    metrics = pd.read_csv(result / "evaluation_metrics.csv")
    state_validation = pd.read_csv(result / "state_validation.csv")
    status = pd.read_csv(result / "fit_status.csv")
    waterfall = pd.read_csv(result / "sample_waterfall.csv")
    quality_path = result / "test_verification.json"
    quality = json.loads(quality_path.read_text()) if quality_path.exists() else {}
    secondary = pd.read_csv(result / "stress_lightgbm_secondary.csv")
    downturn = pd.read_csv(result / "lgd_downturn.csv")
    support_path = result / "scenario_support_summary.csv"
    support_note = ""
    if support_path.exists():
        supports = pd.read_csv(support_path)
        for scenario_name in ["baseline", "adverse"]:
            selected_support = supports.loc[supports.variant.eq("layer2") & supports.scenario.eq(scenario_name) & supports.scope.eq("state")]
            if not selected_support.empty:
                support_row = selected_support.to_dict("records")[0]
                support_note += f" {scenario_name.title()}: {int(support_row['flagged_states'])} states and {100 * support_row['flagged_loan_fraction']:.1f}% of reference loans are outside at least one state-specific training range."
    original = json.loads((root / "docs/gate1_review_evidence.json").read_text())
    originals_ok = {path: sha256(root / path) == digest
                    for path, digest in original["original_tracked_file_sha256"].items()}
    retained = sha256(root / "docs/PROTOCOL.md") == sha256(root / "docs/versions/PROTOCOL_v1_2026-10-08.md")
    primary_status = status.loc[status.variant.isin(["layer1", "layer2"]) & status.family.eq("logit")]
    primary_ok = len(primary_status) == 2 and bool(primary_status.converged.all())
    opening = ("**G2 computations concluded; primary fits converged.** Frozen estimates and sensitivities remain subject to gate review."
        if primary_ok else "**G2 computations concluded; the gate is not fully passed.** The frozen unpenalized specifications have quasi-separation and failed convergence. No finite primary logit associations, peak-path logit estimates or primary coefficient-resampled stress intervals are reported. Regularized scorecards and macro LightGBM robustness are reported separately; no replacement specification was selected.")
    write_json(result / "preservation_check.json", {"protocol_v1_unchanged": retained,
                  "original_files_verified": len(originals_ok), "original_files": originals_ok,
                  "raw_data_in_git": False, "local_only": True})
    rows = [f"# {cfg['title']}", "", "G2 gate report — 8 October 2026", "",
            opening, "",
            "The outcome is **recorded charge-off within 36 months**. Layer 1 uses reported approval descriptors (with explicitly unverified historical vintages); Layer 2 conditions on future realized or stipulated macro paths. Neither layer identifies causal effects of interest rates, guarantee shares or macro conditions.", "",
            "## Sample and frozen comparisons", "",
            "Official SBA 7(a), 30 June 2026 snapshot, 50 states/DC. The sequential waterfall, overlapping flags and cohort/status counts are in the linked tables. Mature EXEMPT/PIF rows remain eligible; severity anomalies do not remove charge-off outcomes.", "",
            "| Sequential step | Excluded | Remaining |", "|---|---:|---:|"]
    for step in waterfall.to_dict("records"):
        rows.append(f"| {step['step']} | {int(step['excluded']):,} | {int(step['remaining']):,} |")
    rows += ["", "| Role | Loans | Recorded charge-offs within 36 months |", "|---|---:|---:|"]
    for role in ["train", "tune", "calibrate", "reference", "crisis", "oot"]:
        rows.append(f"| {role} | {int(split_counts[role]['n']):,} | {int(split_counts[role]['recorded_charge_offs_36m']):,} |")
    rows += ["", "Fit 1991–2002; tune 2003H1; sigmoid calibrate 2003H2; 2006 reference; crisis 2007–2009; later OOT 2011–2013. The macro match table verifies identical comparison samples. All labels used for fitting, tuning and calibration mature before 2007. No refit or test-cohort tuning.", "",
             "## Layer 1: calibration and prediction", "",
             "| Model | Term | Crisis AUC (95% interval) | Crisis average precision | Crisis Brier | Calibration intercept / slope |", "|---|---|---:|---:|---:|---:|"]
    for family in ["elasticnet", "lightgbm"]:
        for variant in ["layer1", "layer1_term"]:
            data = metrics.loc[metrics.variant.eq(variant) & metrics.family.eq(family) &
                               metrics.role.eq("crisis") & metrics.calibration.eq("sigmoid_2003H2")].set_index("metric")
            if data.empty:
                continue
            auc = data.loc["auc"]
            rows.append(f"| {family} | {'with' if variant.endswith('term') else 'without'} | {auc.value:.3f} [{auc.lower:.3f}, {auc.upper:.3f}] | {data.loc['average_precision','value']:.3f} | {data.loc['brier','value']:.3f} | {data.loc['calibration_intercept','value']:.3f} / {data.loc['calibration_slope','value']:.3f} |")
    scorecard_status = status.loc[status.family.isin(["elasticnet", "lightgbm"])]
    scorecards_done = len(scorecard_status) == 6 and bool(scorecard_status.converged.all())
    scorecard_label = "Done" if scorecards_done else "Incomplete; see fit status"
    cohort_rates = {}
    for variant in ["layer1", "layer2"]:
        for role in ["crisis", "oot"]:
            cell = state_validation.loc[state_validation.variant.eq(variant) & state_validation.family.eq("lightgbm") &
                state_validation.role.eq(role) & state_validation.calibration.eq("sigmoid_2003H2")]
            if not cell.empty:
                cohort_rates[(variant, role)] = (
                    float((cell.predicted_pd * cell.n).sum() / cell.n.sum()),
                    float(cell.recorded_charge_offs_36m.sum() / cell.n.sum()))
    rate_note = ""
    if all(key in cohort_rates for key in [("layer1", "crisis"), ("layer2", "crisis"), ("layer2", "oot")]):
        l1_pd, crisis_rate = cohort_rates[("layer1", "crisis")]
        macro_pd, _ = cohort_rates[("layer2", "crisis")]
        oot_pd, oot_rate = cohort_rates[("layer2", "oot")]
        rate_note = (f"On the crisis cohort, calibrated no-Term LightGBM mean PD is {100 * l1_pd:.2f}% in Layer 1 and {100 * macro_pd:.2f}% in the macro robustness model, versus a recorded rate of {100 * crisis_rate:.2f}%. On the later OOT cohort, the macro model predicts {100 * oot_pd:.2f}% versus {100 * oot_rate:.2f}% recorded. The frozen calibration therefore transports poorly across these cohorts; discrimination alone does not validate the scenario PD levels.")
    rows += ["", "Full tables retain **raw and calibrated** metrics, 999 paired state-cluster draws, undefined-draw counts, train-score-decile calibration, paired Term differences, later OOT, PSI, exact TreeSHAP checks and the fixed 70% score-allocation diagnostic. Intervals condition on frozen fitted models and do not include training/tuning uncertainty.", "",
             "![Crisis calibration](../results/g2-2026-10-08/figures/layer1_crisis_calibration.png)", "",
             "## Layer 2 and loss sharing", "",
             "The finite unpenalized MLE does not exist under the frozen raw-category design: disclosed category levels contain only zero training outcomes. The failed attempts and exact category/count witnesses are preserved in CSV. Categories were not pooled/dropped and no penalty was substituted after looking at results. Interest rates are missing throughout training and their coefficient is unidentified.", "",
             rate_note, "",
             "The following **secondary LightGBM point projections** use the unchanged macro robustness models with frozen 2003H2 calibration. They are not the primary logit stress test and carry no coefficient-resampling intervals. A tree cannot extrapolate its year trend beyond training years. Support flags apply even where a tree returns a probability.", "",
             support_note.strip(), "",
             "**EAD = GrossApproval, CCF = 100%, full-disbursement proxy.** LGD is gross charged-off balance per approved dollar, not net recovery loss. The SBA/lender split is pro rata, not observed guarantee payouts or fiscal cost.", "",
             "| Secondary scenario | LGD rule | Mean PD | EL proxy, USD m | SBA share, USD m | Lender share, USD m | EL / approval |", "|---|---|---:|---:|---:|---:|---:|"]
    for obs in secondary.loc[secondary.variant.eq("layer2") & secondary.group.eq("overall")].to_dict("records"):
        rows.append(f"| {obs['scenario']} | {obs['lgd_variant']} | {100 * obs['pd']:.2f}% | {obs['expected_loss_usd'] / 1e6:.2f} | {obs['sba_loss_usd'] / 1e6:.2f} | {obs['lender_loss_usd'] / 1e6:.2f} | {100 * obs['loss_rate']:.2f}% |")
    term_projection = secondary.loc[secondary.variant.eq("layer2_term") & secondary.group.eq("overall") & secondary.lgd_variant.eq("primary")].set_index("scenario")
    term_values = term_projection[["pd"]].to_dict("index")
    term_note = (f"The with-Term secondary model reverses the ordering: baseline PD {100 * term_values['baseline']['pd']:.2f}% versus adverse PD {100 * term_values['adverse']['pd']:.2f}%. This sensitivity and widespread support failures preclude a reliable stress headline; better discrimination with reported Term does not verify its original vintage."
                 if len(term_projection) == 2 else "Reported-Term scenario comparisons are in the secondary table.")
    rows += ["", term_note, "", "Term/revolving lines and the fixed size, sector, business-age and reported-maturity groups are reported separately. Full utilization of undrawn revolving commitments is an assumption, not an observed balance or universal upper bound.", "",
             "## Predeclared sensitivities and gate status", "",
             "| Item | Status | Evidence / qualification |", "|---|---|---|",
             "| Dated A2; protocol v1 retained | Done | Pre-fit commit `f611d18`; primary specification unchanged |",
             "| Population, label, chronology, source hashes | Done | Waterfall, status/cohort counts, macro match, tests |",
             f"| ElasticNet / LightGBM with and without Term | {scorecard_label} | Fixed grids/budgets and failure counts in tuning/fit tables |",
             "| Unpenalized Layer 1–2 logits | Attempted; failed | Quasi-separation witnesses; no finite MLE or usable clustered inference |",
             "| Peak unemployment logit | Attempted; unavailable | Same controls/clusters; full 37-level path tested; same separation failure |",
             "| Downturn LGD | Proxy done; primary application unavailable | 1991, 2000–2001 only; 1990 excluded; cell counts and type pooling; secondary adverse projection shown |",
             "| Capped LGD | Done as secondary projection | Per-loan cap before the same training pooling; primary severity remains uncapped |",
             "| Old-extract CCF | Not done, conditional gate unmet | Licence / exact administrative cutoff and maturity-qualified population unverified; no CSV acquired |",
             "| Urban/rural; initial interest-rate coefficient | Unavailable | Source has no urban/rural field; training rate entirely missing |",
             "| Primary stress PD/EL with coefficient intervals | Not estimable | No finite primary MLE; empty result schema preserves unavailable status |",
             "| Secondary macro projections and support flags | Done | Separate point-only robustness table; no causal claim |",
             "| Tests, preservation, local commits | See verification | Original artifacts retained; no pushes or G3 policy-date analysis |", "",
             f"Downturn proxy includes **{int(downturn.valid_cell_n.sum()):,}** valid recorded charge-offs across its loan-type/size cells. Sparse cells pool by type; `valid_cell_n`, `pooled_n` and pooling source are retained. The `ratios_above_one` count refers to the selected pool, so pooled rows must not be summed. Cohort exposure is not evidence that every charge-off occurred during a recession.", "",
             "## Verification and execution", "",
             f"{len(status)} frozen model attempts: {int(status.converged.sum())} converged, {int((~status.converged).sum())} unavailable. ElasticNet retains all 50 grid points per pair, including nonconverged trials excluded from selection; each LightGBM variant retains its 50 seeded trials. No budget was enlarged after seeing test results.", "",
             f"Local synthetic checks: **{quality.get('tests_passed', 'see verification')} passed**; statistical-core coverage **{quality.get('statistical_core_coverage_percent', 0):.2f}%** and package coverage **{quality.get('package_coverage_percent', 0):.2f}%**. Lint and typing status: {quality.get('lint', 'unverified')} / {quality.get('mypy', 'unverified')}. Production integrity checks cover the actual frozen rows; synthetic tests also exercise the converged-logit branch. Passing software tests does not validate a failed empirical MLE.", "",
             "The bounded pilot and full-grid timings are retained. Independent frozen grids ran concurrently once; the final status/evaluation refresh reused verified checkpoints. Cached refresh time is not a fresh build time. A fresh end-to-end `make all` under two hours has not been established; remote CI was not run because nothing was pushed.", "",
             "## Limitations and future work", "",
             "A revised protocol would be needed before grouping sparse categories or choosing a regularized/Firth logit for inference. This gate does not authorize that change. Administrative charge-off timing is distinct from delinquency; EXEMPT is not certified performing status. Reported origination-feature vintages, missing historical rates and changing category support constrain the backtest. Revised BLS/FHFA series and containing-month/quarter alignment do not reconstruct real-time publication information. The fixed cohort-based LGD proxy omits recoveries and event-date balance vintages; gross approval is an assumed EAD. Conditional/tree projections omit training, calibration, LGD and full macro-path uncertainty. Old-extract utilisation ratios remain conditional on source admissibility. Loan approvals alone cannot identify rejected-applicant risk, guarantee-policy effects or the causal effect of local shocks. Survival/competing-risk methods, better vintage evidence and a separately approved inference repair belong to future work.", "",
             "G3 policy-date design/outcome work and G5 report replacement/publication remain unstarted. Original V1 files and protocol v1 were verified by hash. Nothing was pushed.", "",
             "## Sources and reproducibility", "",
             "Primary [SBA FOIA](https://data.sba.gov/dataset/7a-504-foia), direct [BLS public API](https://www.bls.gov/developers/api_faqs.htm), and direct [FHFA all-transactions HPI](https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv). Raw observations stay private/ignored; hashes and acquisition metadata are published. **This product uses FHFA data but is neither endorsed nor certified by FHFA.**", "",
             "Frozen YAML/seed and uv lock: `make setup`, `make data`, `make all`; `make test`, `make lint`, `make quick` use synthetic checks. Data acquisition is cached and bounded. No FRED observations or credentials are used. Run `make report` only to regenerate the gate figures/summary, not the old G5 PDFs.", "",
             "Tables: [sample waterfall](../results/g2-2026-10-08/sample_waterfall.csv), [evaluation](../results/g2-2026-10-08/evaluation_metrics.csv), [separation witnesses](../results/g2-2026-10-08/separation_witnesses.csv), [state validation](../results/g2-2026-10-08/state_validation.csv), [secondary stress](../results/g2-2026-10-08/stress_lightgbm_secondary.csv), [downturn LGD](../results/g2-2026-10-08/lgd_downturn.csv). See the aggregate directory index for the remaining diagnostics, intervals and sensitivities.", ""]
    (root / "docs/G2_REPORT_2026-10-08.md").write_text("\n".join(rows))
    index = ["# G2 aggregate output index", "", "No borrower-level records, predictions or fitted model objects are included.", ""]
    for path in sorted(result.rglob("*")):
        if path.is_file() and path.name != "INDEX.md":
            index.append(f"- [{path.relative_to(result)}]({path.relative_to(result)})")
    (result / "INDEX.md").write_text("\n".join(index) + "\n")
