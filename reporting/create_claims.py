"""Freeze claims before prose. Select saved aggregates and register arithmetic."""

import json
from pathlib import Path

import yaml

from .registry import BASE, OUT, ROOT, Registry, digest


def create(root: Path = ROOT) -> Registry:
    r = Registry(root)
    specs = [
        (
            "evaluation_metrics.csv",
            ["variant", "model", "cohort", "metric"],
            [
                "value",
                "lower",
                "upper",
                "n",
                "recorded_charge_offs_36m",
                "bootstrap_draws",
                "undefined_draws",
            ],
        ),
        (
            "calibration_means.csv",
            ["variant", "model", "cohort"],
            ["n", "events", "mean_predicted", "recorded_rate"],
        ),
        (
            "calibration_deciles.csv",
            ["variant", "model", "cohort", "bin"],
            [
                "lower_edge",
                "upper_edge",
                "n",
                "predicted_pd",
                "recorded_rate",
                "lower",
                "upper",
                "undefined_draws",
            ],
        ),
        (
            "firth_macro_associations.csv",
            ["variant", "feature", "group", "group_value"],
            ["value", "lower", "upper", "n", "effective_interval_draws", "attempted_draws"],
        ),
        (
            "firth_stress.csv",
            ["variant", "scenario", "lgd_variant", "group", "group_value", "metric"],
            [
                "value",
                "lower",
                "upper",
                "pd_n",
                "loss_n",
                "effective_interval_draws",
                "attempted_draws",
            ],
        ),
        (
            "scenario_support_summary.csv",
            ["variant", "scenario", "scope", "feature"],
            ["flagged_loan_n", "flagged_fraction", "flagged_approval_usd", "n"],
        ),
        (
            "term_audit_summary.csv",
            ["scope", "group"],
            [
                "n",
                "valid_n",
                "date_missing_n",
                "date_invalid_n",
                "term_missing_n",
                "term_invalid_n",
                "match_abs_le_3_n",
                "match_abs_le_3_share",
                "charge_off_after_label_window_n",
            ],
        ),
        ("source_population_waterfall.csv", ["step"], ["excluded", "remaining"]),
        (
            "final_sample_waterfall_complete.csv",
            ["layer", "role"],
            ["eligible_n", "macro_excluded_n", "n", "events", "non_events"],
        ),
        (
            "initial_interest_rate_missingness.csv",
            ["years"],
            ["eligible_n", "missing_n", "missing_share"],
        ),
        (
            "design_rank_checks.csv",
            ["variant"],
            ["n", "events", "full_columns", "rank", "states", "state_dummy_columns"],
        ),
        (
            "fit_status.csv",
            ["variant", "family"],
            [
                "converged",
                "iterations",
                "n",
                "separation_flag",
                "optimizer_success",
                "normalized_gradient",
                "valid_estimate",
            ],
        ),
        (
            "lgd_primary.csv",
            ["loan_type", "size_band"],
            ["valid_cell_n", "pooled_n", "lgd_proxy", "excluded_severity_n", "ratios_above_one"],
        ),
        (
            "firth_coefficients.csv",
            ["variant", "coefficient"],
            ["value", "lower", "upper", "effective_interval_draws"],
        ),
        (
            "firth_average_associations.csv",
            ["variant", "feature", "contrast"],
            ["value", "lower", "upper", "effective_interval_draws"],
        ),
        (
            "post_pooling_separation_witnesses.csv",
            ["variant", "feature", "level"],
            ["n", "events", "non_events"],
        ),
    ]
    wanted_groups = {
        ("layer1", "firth_raw", "crisis_2007_2009"),
        ("layer1", "firth_raw", "additional_cohort_2011_2013"),
        ("layer2", "firth_raw", "post_amendment_validation_2013_2014"),
        ("layer2", "lightgbm_calibrated", "post_amendment_validation_2013_2014"),
    }
    for name, keys, cols in specs:
        keep = None
        if name == "calibration_deciles.csv":
            keep = lambda x: (x["variant"], x["model"], x["cohort"]) in wanted_groups
        elif name in {"firth_stress.csv", "firth_macro_associations.csv"}:
            keep = lambda x: x["group"] in {"overall", "loan_type"}
        elif name == "term_audit_summary.csv":
            keep = lambda x: x["scope"] in {"overall", "status"}
        elif name in {"firth_coefficients.csv", "firth_average_associations.csv"}:
            field = "coefficient" if name == "firth_coefficients.csv" else "feature"
            keep = lambda x, field=field: (
                x["variant"] in {"layer1", "layer2", "layer2_peak"}
                and x[field]
                in {
                    "log_approval",
                    "guarantee_share",
                    "log_jobs",
                    "u0",
                    "du",
                    "peak_du",
                    "h0",
                    "dh",
                    "year_trend",
                }
            )
        r.add_csv(name, keys, cols, keep)
    for cohort, tag in [("crisis_2007_2009", "crisis"), ("additional_cohort_2011_2013", "later")]:
        s = {"variant": "layer1", "model": "firth_raw", "cohort": cohort}
        r.alias(
            "auc_" + tag,
            "evaluation_metrics.csv",
            {**s, "metric": "auc"},
            finding="C1: modest out-of-time discrimination; not strong transportability",
        )
        r.alias(
            "pd_" + tag,
            "calibration_means.csv",
            s,
            "mean_predicted",
            finding="C2: raw Firth calibration failure",
        )
        r.alias(
            "rate_" + tag,
            "calibration_means.csv",
            s,
            "recorded_rate",
            finding="C2: recorded administrative outcome, not delinquency",
        )
    for model, tag in [("firth_raw", "firth"), ("lightgbm_calibrated", "tree")]:
        s = {"variant": "layer2", "model": model, "cohort": "post_amendment_validation_2013_2014"}
        r.alias(
            "pd_l2_" + tag,
            "calibration_means.csv",
            s,
            "mean_predicted",
            finding="C3: realized-path retrospective cohort check",
        )
        r.alias(
            "rate_l2_" + tag,
            "calibration_means.csv",
            s,
            "recorded_rate",
            finding="C3: already partly exposed calendar/cohort",
        )
        for metric in ["calibration_intercept", "calibration_slope"]:
            r.alias(
                tag + "_" + metric,
                "evaluation_metrics.csv",
                {**s, "metric": metric},
                finding="C3: average agreement does not imply risk-group calibration",
            )
    for variant, feature, tag in [("layer2", "du", "endpoint"), ("layer2_peak", "peak_du", "peak")]:
        r.alias(
            tag,
            "firth_macro_associations.csv",
            {"variant": variant, "feature": feature, "group": "overall", "group_value": "all"},
            finding="C4/C5: +1 pp finite-change conditional association on observed 2006 portfolio; not derivative or causal",
        )
    for scenario in ["baseline", "adverse", "adverse_minus_baseline"]:
        for metric in (
            ["pd", "expected_loss_usd", "sba_loss_usd", "lender_loss_usd", "loss_rate"]
            if scenario != "adverse_minus_baseline"
            else [
                "pd_change_pp",
                "expected_loss_usd_change",
                "sba_loss_usd_change",
                "lender_loss_usd_change",
            ]
        ):
            alias = scenario + "_" + metric
            r.alias(
                alias,
                "firth_stress.csv",
                {
                    "variant": "layer2",
                    "scenario": scenario,
                    "lgd_variant": "primary",
                    "group": "overall",
                    "group_value": "all",
                    "metric": metric,
                },
                finding="C6/C7/C8: fixed-portfolio assumption-based scenario projection, not validation or fiscal cost",
            )
    r.derive("el_ratio", "divide", ["adverse_expected_loss_usd", "baseline_expected_loss_usd"])
    for scenario in ["baseline", "adverse"]:
        r.derive(
            scenario + "_sba_share",
            "divide",
            [scenario + "_sba_loss_usd", scenario + "_expected_loss_usd"],
            unit="fraction",
        )
        r.derive(
            scenario + "_lender_share", "complement", [scenario + "_sba_share"], unit="fraction"
        )
    for status in ["CHGOFF", "PIF"]:
        for col in [
            "n",
            "valid_n",
            "term_invalid_n",
            "match_abs_le_3_share",
            "charge_off_after_label_window_n",
        ]:
            r.alias(
                "term_" + status + "_" + col,
                "term_audit_summary.csv",
                {"scope": "status", "group": status},
                col,
                finding="C9: timing unverifiable; low matching does not prove original vintage",
            )
    for scope in ["state_specific", "pooled_global"]:
        for col in ["flagged_loan_n", "flagged_fraction", "flagged_approval_usd", "n"]:
            r.alias(
                "support_" + scope + "_" + col,
                "scenario_support_summary.csv",
                {
                    "variant": "layer2",
                    "scenario": "adverse",
                    "scope": scope,
                    "feature": "any_numeric",
                },
                col,
                finding="C10: univariate check, not joint support or plausible paths",
            )
    # Approved metadata/history constants, separate from empirical estimates.
    for filename in ["bootstrap_summary.json", "benchmark_status.json"]:
        p = BASE / filename
        for row in json.loads((root / p).read_text()):
            identity = {k: row[k] for k in ["variant", "family"] if k in row}
            for col, value in row.items():
                if col in identity or isinstance(value, (list, dict)):
                    continue
                key = "M" + digest_text([filename, identity, col])
                r.entries[key] = {
                    "id": key,
                    "source_path": str(p),
                    "source_sha256": digest(root / p),
                    "json_record_selector": identity,
                    "column": col,
                    "raw_value": value,
                    "units": "saved run metadata",
                    "interval": None,
                    "supported_interpretation": "Method/convergence metadata; not a new estimate",
                    "locations": ["technical methods/status"],
                    "qualifications": ["No new fitting or tuning"],
                    "prohibited_interpretations": ["new G5 statistical evidence"],
                }
    config_path = Path("config/g2_bis_2026-10-08.yaml")
    config = yaml.safe_load((root / config_path).read_text())
    constants = {
        "horizon_months": 36,
        "pool_cutoff": config["categorical_pooling"]["threshold"],
        "seed": config["seed"],
        "attempts": config["bootstrap"]["attempts"],
        "evaluation_draws": config["evaluation"]["conditional_frozen_fit_state_cluster_draws"],
        "max_iterations": config["firth"]["max_iter"],
        "state_count": r.entries[
            r.lookup_id("design_rank_checks.csv", {"variant": "layer2"}, "states")
        ]["raw_value"],
        "lgd_min_cell": 50,
    }
    (root / OUT / "method_constants.json").write_text(
        json.dumps(
            {
                "config_path": str(config_path),
                "config_sha256": digest(root / config_path),
                "protocol_path": "docs/PROTOCOL.md",
                "protocol_sha256": digest(root / "docs/PROTOCOL.md"),
                "constants": constants,
                "metadata_not_new_estimates": True,
                "tuning_history": "2003H1 in G2; unchanged selected settings inherited by G2-bis",
            },
            indent=2,
        )
        + "\n"
    )
    for name, value in constants.items():
        k = "method_" + name
        r.entries[k] = {
            "id": k,
            "raw_value": value,
            "units": "method constant, not estimate",
            "source_path": str(config_path)
            if name not in {"horizon_months", "lgd_min_cell", "state_count"}
            else (
                "docs/PROTOCOL.md"
                if name != "state_count"
                else str(BASE / "design_rank_checks.csv")
            ),
            "source_sha256": digest(root / config_path)
            if name not in {"horizon_months", "lgd_min_cell", "state_count"}
            else digest(
                root
                / ("docs/PROTOCOL.md" if name != "state_count" else BASE / "design_rank_checks.csv")
            ),
            "metadata_selector": {"name": name},
            "interval": None,
            "supported_interpretation": "Frozen method constant; horizon and LGD count documented in original protocol; state count from Layer 2 rank row",
            "locations": ["technical methods/equations"],
            "qualifications": ["No new estimation"],
            "prohibited_interpretations": ["new G5 inference"],
        }
        r.aliases[k] = k
    paths = {
        "pool_cutoff": ["categorical_pooling", "threshold"],
        "seed": ["seed"],
        "attempts": ["bootstrap", "attempts"],
        "evaluation_draws": ["evaluation", "conditional_frozen_fit_state_cluster_draws"],
        "max_iterations": ["firth", "max_iter"],
    }
    for name, route in paths.items():
        r.entries["method_" + name]["yaml_path"] = route
    r.entries["method_horizon_months"]["text_pattern"] = r"d \+ (36) calendar months"
    r.entries["method_lgd_min_cell"]["text_pattern"] = r"cells with <(50) valid defaults"
    r.entries["method_state_count"]["selector"] = {"variant": "layer2"}
    r.entries["method_state_count"]["column"] = "states"
    r.save()
    return r


def digest_text(value):
    import hashlib

    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:14]


if __name__ == "__main__":
    registry = create()
    print(
        "Claims frozen before report prose:",
        len(registry.entries),
        "cells;",
        len(registry.aliases),
        "named aliases.",
    )
