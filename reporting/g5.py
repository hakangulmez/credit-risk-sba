"""Results-only tables, graphics and document rendering; never imports research code."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .registry import BASE, LOSS, OUT, ROOT, SCENARIO, Registry, digest, rows

HISTORY = "The final estimation protocol was frozen after first-round results had been seen and before any final-round model was estimated. Deviations are logged in DECISIONS.md."
COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
}


def load(root: Path = ROOT) -> Registry:
    payload = json.loads((root / OUT / "claims_registry.json").read_text())
    r = Registry(root)
    r.entries, r.aliases = payload["claims"], payload["aliases"]
    from .checks import verify_claims

    verify_claims(root, payload)
    return r


def escape(value: Any) -> str:
    return (
        str(value)
        .replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("$", r"\$")
        .replace("#", r"\#")
    )


def table(
    root: Path, name: str, headers: list[str], data: list[list[str]], ids: list[list[str]]
) -> None:
    import csv

    target = root / OUT / (name + ".csv")
    with target.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        csv_headers = headers.copy()
        csv_data = [row.copy() for row in data]
        csv_ids = [row.copy() for row in ids]
        if name in {"stress", "sensitivities", "support"}:
            csv_headers += ["macro_information_context"]
            csv_data = [row + [SCENARIO] for row in csv_data]
            csv_ids = [row + [""] for row in csv_ids]
        if name in {"stress", "sensitivities"}:
            csv_headers += ["loss_accounting"]
            csv_data = [row + [LOSS] for row in csv_data]
            csv_ids = [row + [""] for row in csv_ids]
        w.writerow(csv_headers)
        w.writerows(csv_data)
    tex = [
        r"\begingroup\small\setlength{\tabcolsep}{3pt}",
        r"\begin{tabularx}{\linewidth}{" + ("X" + "r" * (len(headers) - 1)) + r"}\toprule",
        " & ".join(map(escape, headers)) + r" \\ \midrule",
    ]
    tex += [" & ".join(map(escape, row)) + r" \\" for row in data]
    tex += [r"\bottomrule\end{tabularx}\endgroup"]
    (root / "report/g5/generated" / (name + ".tex")).write_text("\n".join(tex) + "\n")
    (root / OUT / (name + "_provenance.json")).write_text(
        json.dumps(
            {
                "registry_sha256": digest(root / OUT / "claims_registry.json"),
                "cells": csv_ids,
                "all_research_numbers_from_registry": True,
            },
            indent=2,
        )
        + "\n"
    )


def cell(
    r: Registry,
    file: str,
    selector: dict[str, Any],
    column: str = "value",
    scale: float = 1,
    digits: int = 3,
    ci: bool = False,
    integer: bool = False,
) -> tuple[str, str]:
    key = r.lookup_id(file, selector, column)
    return r.display(key, scale, digits, ci, integer), key


def tables(r: Registry) -> None:
    root = r.root
    made = []
    refs = []
    for row in rows(root / BASE / "source_population_waterfall.csv"):
        vals = [
            cell(r, "source_population_waterfall.csv", {"step": row["step"]}, c, integer=True)
            for c in ["excluded", "remaining"]
        ]
        made.append([row["step"].replace("_", " "), *[v for v, k in vals]])
        refs.append(["", *[k for v, k in vals]])
    table(root, "waterfall", ["Eligibility step", "Excluded", "Remaining"], made, refs)
    made = []
    refs = []
    for row in rows(root / BASE / "final_sample_waterfall_complete.csv"):
        sel = {"layer": row["layer"], "role": row["role"]}
        vals = [
            cell(r, "final_sample_waterfall_complete.csv", sel, c, integer=True)
            for c in ["n", "events", "non_events", "macro_excluded_n"]
        ]
        made.append(
            [
                row["layer"] + " " + row["role"].replace("_", " ") + " (" + row["years"] + ")",
                *[v for v, k in vals],
            ]
        )
        refs.append(["", *[k for v, k in vals]])
    table(
        root,
        "samples",
        ["Disbursement cohort / role", "Loans", "Events", "Non-events", "Macro exclusions"],
        made,
        refs,
    )
    made = []
    refs = []
    cal = []
    crefs = []
    for variant, cohorts, models in [
        (
            "layer1",
            ["crisis_2007_2009", "additional_cohort_2011_2013"],
            [
                "firth_raw",
                "elasticnet_raw",
                "elasticnet_calibrated",
                "lightgbm_raw",
                "lightgbm_calibrated",
            ],
        ),
        (
            "layer2",
            ["post_amendment_validation_2013_2014"],
            ["firth_raw", "lightgbm_raw", "lightgbm_calibrated"],
        ),
    ]:
        for cohort in cohorts:
            for model in models:
                label = (
                    variant.replace("layer", "L")
                    + " "
                    + (
                        "crisis"
                        if cohort.startswith("crisis")
                        else "later"
                        if cohort.startswith("additional")
                        else "validation"
                    )
                    + " "
                    + model.replace("lightgbm", "LGB").replace("elasticnet", "EN").replace("_", " ")
                )
                sel = {"variant": variant, "model": model, "cohort": cohort}
                vals = [
                    cell(r, "evaluation_metrics.csv", {**sel, "metric": m}, ci=True, digits=3)
                    for m in ["auc", "average_precision", "brier"]
                ]
                made.append([label, *[v for v, k in vals]])
                refs.append(["", *[k for v, k in vals]])
                vals = [
                    cell(r, "calibration_means.csv", sel, c, scale=100, digits=2)
                    for c in ["mean_predicted", "recorded_rate"]
                ] + [
                    cell(r, "evaluation_metrics.csv", {**sel, "metric": m}, ci=True, digits=3)
                    for m in ["calibration_intercept", "calibration_slope"]
                ]
                cal.append([label, *[v for v, k in vals]])
                crefs.append(["", *[k for v, k in vals]])
    table(
        root,
        "performance",
        ["Term-free model / cohort", "AUC [95%]", "AP [95%]", "Brier [95%]"],
        made,
        refs,
    )
    table(
        root,
        "calibration",
        ["Term-free model / cohort", "Predicted %", "Recorded %", "Intercept [95%]", "Slope [95%]"],
        cal,
        crefs,
    )
    made = []
    refs = []
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
            scale = 1e-6 if "usd" in metric else 100 if metric in {"pd", "loss_rate"} else 1
            made.append(
                [
                    scenario.replace("_", " "),
                    {
                        "pd": "PD (%)",
                        "expected_loss_usd": "EL ($m)",
                        "sba_loss_usd": "SBA ($m)",
                        "lender_loss_usd": "Lender ($m)",
                        "loss_rate": "Loss / approval (%)",
                        "pd_change_pp": "Change PD (pp)",
                        "expected_loss_usd_change": "Change EL ($m)",
                        "sba_loss_usd_change": "Change SBA ($m)",
                        "lender_loss_usd_change": "Change lender ($m)",
                    }[metric],
                    r.display(alias, scale, 2, True),
                    str(r.resolve(alias)["interval"]["successful_draws"]),
                ]
            )
            refs.append(["", "", r.aliases[alias], r.aliases[alias]])
    table(root, "stress", ["Scenario", "Quantity", "Point [95%]", "Successful draws"], made, refs)
    made = []
    refs = []
    for variant, feature in [("layer2", "du"), ("layer2_peak", "peak_du")]:
        sel = {"variant": variant, "feature": feature, "group": "overall", "group_value": "all"}
        val, key = cell(r, "firth_macro_associations.csv", sel, ci=True, digits=3)
        made.append([variant + " " + feature, val])
        refs.append(["", key])
    table(
        root,
        "macro",
        ["+1 pp change, conditional finite association", "Probability pp [95%]"],
        made,
        refs,
    )
    made = []
    refs = []
    for variant in ["layer2", "layer2_term", "layer2_peak"]:
        for lgd in ["primary", "capped", "downturn"]:
            sel = {
                "variant": variant,
                "lgd_variant": lgd,
                "scenario": "adverse",
                "group": "overall",
                "group_value": "all",
                "metric": "expected_loss_usd",
            }
            val, key = cell(r, "firth_stress.csv", sel, scale=1e-6, digits=1, ci=True)
            made.append(
                [
                    variant.replace("_term", " with-Term sensitivity").replace(
                        "_peak", " peak sensitivity"
                    )
                    + " / "
                    + lgd,
                    val,
                ]
            )
            refs.append(["", key])
    table(
        root,
        "sensitivities",
        ["Fixed adverse path / LGD specification", "EL proxy $m [95%]"],
        made,
        refs,
    )
    made = []
    refs = []
    for scenario in ["baseline", "adverse"]:
        for scope in ["state_specific", "pooled_global"]:
            sel = {
                "variant": "layer2",
                "scenario": scenario,
                "scope": scope,
                "feature": "any_numeric",
            }
            vals = [
                cell(r, "scenario_support_summary.csv", sel, "flagged_loan_n", integer=True),
                cell(
                    r, "scenario_support_summary.csv", sel, "flagged_fraction", scale=100, digits=2
                ),
                cell(
                    r,
                    "scenario_support_summary.csv",
                    sel,
                    "flagged_approval_usd",
                    scale=1e-6,
                    digits=2,
                ),
            ]
            made.append([scenario + " / " + scope.replace("_", " "), *[v for v, k in vals]])
            refs.append(["", *[k for v, k in vals]])
    table(
        root, "support", ["Univariate range scope", "Loans", "Share %", "Approval $m"], made, refs
    )
    made = []
    refs = []
    for status in ["CHGOFF", "PIF"]:
        vals = [
            cell(
                r,
                "term_audit_summary.csv",
                {"scope": "status", "group": status},
                c,
                scale=100 if c.endswith("share") else 1,
                digits=2,
                integer=not c.endswith("share"),
            )
            for c in [
                "n",
                "valid_n",
                "term_invalid_n",
                "match_abs_le_3_share",
                "charge_off_after_label_window_n",
            ]
        ]
        made.append([status, *[v for v, k in vals]])
        refs.append(["", *[k for v, k in vals]])
    table(
        root,
        "term",
        ["Status", "Applicable", "Valid", "Invalid Term", "Match %", "After window"],
        made,
        refs,
    )
    made = []
    refs = []
    for row in rows(root / BASE / "design_rank_checks.csv"):
        vals = [
            cell(r, "design_rank_checks.csv", {"variant": row["variant"]}, c, integer=True)
            for c in ["full_columns", "rank", "state_dummy_columns"]
        ]
        made.append([row["variant"], *[v for v, k in vals]])
        refs.append(["", *[k for v, k in vals]])
    table(root, "rank", ["Specification", "Original columns", "Rank", "State dummies"], made, refs)
    made = []
    refs = []
    for variant in ["layer1", "layer2", "layer2_peak"]:
        for feat in ["log_approval", "guarantee_share", "log_jobs"] + (
            ["u0", "du", "h0", "dh", "year_trend"]
            if variant == "layer2"
            else ["peak_du"]
            if variant == "layer2_peak"
            else []
        ):
            val, key = cell(
                r,
                "firth_coefficients.csv",
                {"variant": variant, "coefficient": feat},
                ci=True,
                digits=3,
            )
            made.append([variant + " / " + feat, val])
            refs.append(["", key])
    table(
        root,
        "coefficients",
        ["Feature (train-standardized where numeric)", "Log odds [95%]"],
        made,
        refs,
    )
    for index, (variant, model, cohort) in enumerate(
        [
            ("layer1", "firth_raw", "crisis_2007_2009"),
            ("layer1", "firth_raw", "additional_cohort_2011_2013"),
            ("layer2", "firth_raw", "post_amendment_validation_2013_2014"),
            ("layer2", "lightgbm_calibrated", "post_amendment_validation_2013_2014"),
        ],
        1,
    ):
        made = []
        refs = []
        for row in rows(root / BASE / "calibration_deciles.csv"):
            if (row["variant"], row["model"], row["cohort"]) != (variant, model, cohort):
                continue
            sel = {"variant": variant, "model": model, "cohort": cohort, "bin": row["bin"]}
            vals = [
                cell(r, "calibration_deciles.csv", sel, "n", integer=True),
                cell(r, "calibration_deciles.csv", sel, "lower_edge", scale=100, digits=2),
                cell(r, "calibration_deciles.csv", sel, "upper_edge", scale=100, digits=2),
                cell(r, "calibration_deciles.csv", sel, "predicted_pd", scale=100, digits=2),
                cell(
                    r, "calibration_deciles.csv", sel, "recorded_rate", scale=100, digits=2, ci=True
                ),
            ]
            made.append([row["bin"], *[v for v, k in vals]])
            refs.append(["", *[k for v, k in vals]])
        table(
            root,
            "bins_" + str(index),
            ["Bin", "Loans", "Lower edge %", "Upper edge %", "Predicted %", "Recorded % [95%]"],
            made,
            refs,
        )
    made = []
    refs = []
    for row in rows(root / BASE / "initial_interest_rate_missingness.csv"):
        vals = [
            cell(
                r,
                "initial_interest_rate_missingness.csv",
                {"years": row["years"]},
                c,
                scale=100 if c == "missing_share" else 1,
                digits=2,
                integer=c != "missing_share",
            )
            for c in ["eligible_n", "missing_n", "missing_share"]
        ]
        made.append([row["years"], *[v for v, k in vals]])
        refs.append(["", *[k for v, k in vals]])
    table(
        root,
        "rate_missingness",
        ["Estimation years", "Eligible", "Missing", "Missing %"],
        made,
        refs,
    )
    made = []
    refs = []
    for row in json.loads((root / BASE / "bootstrap_summary.json").read_text()):
        keys = [
            next(
                k
                for k, e in r.entries.items()
                if e.get("json_record_selector") == {"variant": row["variant"]}
                and e.get("source_path") == str(BASE / "bootstrap_summary.json")
                and e.get("column") == c
            )
            for c in ["attempted", "successful", "failed"]
        ]
        made.append(
            [
                row["variant"],
                *[r.display(k, integer=True) for k in keys],
                "iteration limit" if row["failed"] else "none",
            ]
        )
        refs.append(["", *keys, ""])
    table(
        root,
        "bootstrap",
        ["Specification", "Attempted", "Successful", "Failed", "Failure reason"],
        made,
        refs,
    )
    made = []
    refs = []
    for row in rows(root / BASE / "fit_status.csv"):
        vals = [
            cell(
                r,
                "fit_status.csv",
                {"variant": row["variant"], "family": row["family"]},
                c,
                integer=c == "iterations",
            )
            for c in ["converged", "iterations"]
        ]
        family_label = row["family"]
        if row["variant"] == "layer2_peak" and family_label == "Firth primary":
            family_label = "Firth peak sensitivity"
        made.append([row["variant"] + " / " + family_label, *[v for v, k in vals]])
        refs.append(["", *[k for v, k in vals]])
    table(
        root,
        "convergence",
        ["Specification / estimator", "Valid convergence", "Iterations"],
        made,
        refs,
    )
    values = {name: r.display(name) for name in r.aliases}
    (root / OUT / "display_values.json").write_text(json.dumps(values, indent=2) + "\n")
    macros = []
    specs = {
        "AucCrisis": ("auc_crisis", 1, 3, True),
        "AucLater": ("auc_later", 1, 3, True),
        "PdCrisis": ("pd_crisis", 100, 2, False),
        "RateCrisis": ("rate_crisis", 100, 2, False),
        "PdLater": ("pd_later", 100, 2, False),
        "RateLater": ("rate_later", 100, 2, False),
        "Endpoint": ("endpoint", 1, 3, True),
        "Peak": ("peak", 1, 3, True),
        "ElBase": ("baseline_expected_loss_usd", 1e-6, 1, True),
        "ElAdverse": ("adverse_expected_loss_usd", 1e-6, 1, True),
        "ElDiff": ("adverse_minus_baseline_expected_loss_usd_change", 1e-6, 1, True),
        "ElRatio": ("el_ratio", 1, 2, False),
        "ShareBase": ("baseline_sba_share", 100, 2, False),
        "ShareAdverse": ("adverse_sba_share", 100, 2, False),
        "LtwoFirth": ("pd_l2_firth", 100, 2, False),
        "LtwoTree": ("pd_l2_tree", 100, 2, False),
        "LtwoRate": ("rate_l2_firth", 100, 2, False),
        "TreeIntercept": ("tree_calibration_intercept", 1, 3, True),
        "TreeSlope": ("tree_calibration_slope", 1, 3, True),
        "SupportShare": ("support_state_specific_flagged_fraction", 100, 2, False),
        "TermMatch": ("term_CHGOFF_match_abs_le_3_share", 100, 2, False),
    }
    for name, (alias, scale, digits, ci) in specs.items():
        macros.append(
            "\\newcommand{\\" + name + "}{" + escape(r.display(alias, scale, digits, ci)) + "}"
        )
    (root / "report/g5/generated/numbers.tex").write_text("\n".join(macros) + "\n")
    (root / OUT / "snippet_provenance.json").write_text(
        json.dumps(
            {
                "registry_sha256": digest(root / OUT / "claims_registry.json"),
                "latex_macros": {
                    n: {"claim": a, "scale": s, "digits": d, "interval": c}
                    for n, (a, s, d, c) in specs.items()
                },
            },
            indent=2,
        )
        + "\n"
    )


def graphics(r: Registry) -> None:
    root = r.root
    target = root / "figures/g5"
    target.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    x = np.arange(2)
    axes[0].bar(
        x - 0.18,
        [r.value("pd_crisis") * 100, r.value("pd_later") * 100],
        0.36,
        color=COLORS["blue"],
        label="Raw Firth predicted",
    )
    axes[0].bar(
        x + 0.18,
        [r.value("rate_crisis") * 100, r.value("rate_later") * 100],
        0.36,
        color=COLORS["orange"],
        label="Recorded outcome",
    )
    axes[0].set_xticks(x, ["2007–2009", "2011–2013"])
    axes[0].set_ylabel("Recorded charge-off within 36 months (%)")
    axes[0].set_title("Layer 1: calibration does not transport")
    axes[0].legend(fontsize=9)
    sba = np.array([r.value("baseline_sba_loss_usd"), r.value("adverse_sba_loss_usd")]) / 1e6
    lender = (
        np.array([r.value("baseline_lender_loss_usd"), r.value("adverse_lender_loss_usd")]) / 1e6
    )
    axes[1].bar(x, sba, color=COLORS["blue"], label="Assumed SBA allocation")
    axes[1].bar(x, lender, bottom=sba, color=COLORS["green"], label="Assumed lender allocation")
    for i, s in enumerate(["baseline", "adverse"]):
        ci = r.resolve(s + "_expected_loss_usd")["interval"]
        axes[1].vlines(i, ci["lower"] / 1e6, ci["upper"] / 1e6, color="black", lw=1.6)
    axes[1].set_xticks(x, ["Baseline", "Adverse"])
    axes[1].set_ylabel("Gross expected-loss proxy (USD million)")
    axes[1].set_title("Layer 2: fixed 2006 scenario portfolio")
    axes[1].legend(fontsize=8, loc="upper left")
    axes[1].text(
        0.04,
        0.65,
        "Paired EL difference, not a level interval:\n$"
        + r.display("adverse_minus_baseline_expected_loss_usd_change", 1e-6, 1, True)
        + "m",
        transform=axes[1].transAxes,
        fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none"},
    )
    fig.suptitle(
        "Local economic conditions and public–lender loss sharing\nin SBA 7(a) lending", fontsize=15
    )
    caption = (
        "Layer 1 descriptors are reconstructed from a snapshot; feature vintages remain unverified. "
        + SCENARIO
        + ".\n"
        + "Assumption-based loss proxies; see the technical report, Section 6."
        + "\nRaw Firth calibration error can affect levels, differences and ratios. Bands exclude LGD/path/vintage uncertainty."
    )
    fig.text(0.04, 0.02, "\n".join(textwrap.wrap(caption, 150)), fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.20, 1, 0.89))
    fig.savefig(target / "headline.png", dpi=300)
    fig.savefig(target / "headline.pdf")
    plt.close(fig)
    (target / "headline_caption.txt").write_text(caption + "\n")
    # Existing groups and bands only: no refitting/rebinning/prediction.
    fig, axs = plt.subplots(2, 2, figsize=(10.5, 7.5))
    bins = json.loads((root / OUT / "claims_registry.json").read_text())
    _ = bins
    combos = [
        ("layer1", "firth_raw", "crisis_2007_2009", "Layer 1 Firth, 2007–2009"),
        ("layer1", "firth_raw", "additional_cohort_2011_2013", "Layer 1 Firth, 2011–2013"),
        (
            "layer2",
            "firth_raw",
            "post_amendment_validation_2013_2014",
            "Layer 2 raw Firth, 2013–2014",
        ),
        (
            "layer2",
            "lightgbm_calibrated",
            "post_amendment_validation_2013_2014",
            "Layer 2 calibrated LightGBM, 2013–2014",
        ),
    ]
    for ax, (variant, model, cohort, title) in zip(axs.flat, combos, strict=True):
        saved = [
            a
            for a in rows(root / BASE / "calibration_deciles.csv")
            if (a["variant"], a["model"], a["cohort"]) == (variant, model, cohort)
        ]
        for row in saved:
            sel = {"variant": variant, "model": model, "cohort": cohort, "bin": row["bin"]}
            key = r.lookup_id("calibration_deciles.csv", sel, "recorded_rate")
            entry = r.resolve(key)
            interval = entry["interval"]
            pred = r.value(r.lookup_id("calibration_deciles.csv", sel, "predicted_pd"))
            if pred is None or entry["raw_value"] is None:
                continue
            a, b = 100 * pred, 100 * entry["raw_value"]
            ax.scatter(a, b, color=COLORS["blue"], s=25)
            if interval["lower"] is not None and interval["upper"] is not None:
                ax.vlines(
                    a, 100 * interval["lower"], 100 * interval["upper"], color=COLORS["blue"], lw=1
                )
            ax.annotate(row["bin"], (a, b), xytext=(3, 2), textcoords="offset points", fontsize=7)
        _lo, hi = ax.get_xlim()
        _vlo, vhi = ax.get_ylim()
        lim = max(hi, vhi)
        ax.plot([0, lim], [0, lim], "--", color="gray", lw=1)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Mean predicted probability (%)")
        ax.set_ylabel("Recorded rate (%)")
    cap = "Training-score decile cutoffs: original edges, counts and empty bins retained in the tables. Stored 95% state-cluster bands condition on fitted models (999 evaluation draws); no binomial intervals. Layer 2 uses future realized macro paths, not real-time information."
    fig.text(0.03, 0.01, "\n".join(textwrap.wrap(cap, 145)), fontsize=8)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(target / "calibration_groups.png", dpi=300)
    fig.savefig(target / "calibration_groups.pdf")
    plt.close(fig)
    (target / "calibration_caption.txt").write_text(cap + "\n")
    fig = plt.figure(figsize=(4, 4))
    fig.patch.set_facecolor("#F6F4EF")
    fig.text(0.07, 0.90, "SBA 7(a) lending", fontsize=17, color=COLORS["blue"], weight="bold")
    fig.text(
        0.07, 0.81, "Calibration matters\nbefore interpreting scenarios", fontsize=12, weight="bold"
    )
    bullets = [
        "Crisis: "
        + r.display("pd_crisis", 100)
        + "% predicted\nvs "
        + r.display("rate_crisis", 100)
        + "% recorded.",
        "Conditional +1 pp unemployment change:\n"
        + r.display("endpoint", digits=3, interval=True)
        + " pp.",
        "Fixed-portfolio EL proxy:\n"
        + chr(92)
        + "$"
        + r.display("baseline_expected_loss_usd", 1e-6, 1)
        + "m → "
        + chr(92)
        + "$"
        + r.display("adverse_expected_loss_usd", 1e-6, 1)
        + "m.",
    ]
    for y, t in zip([0.61, 0.43, 0.25], bullets, strict=True):
        fig.text(0.07, y, t, fontsize=10, color="#222222")
    fig.text(
        0.07,
        0.025,
        "Local draft; not causal or measured fiscal costs.\n" + "\n".join(textwrap.wrap(LOSS, 72)),
        fontsize=5.1,
    )
    path = root / "figures/linkedin/g5"
    path.mkdir(parents=True, exist_ok=True)
    fig.savefig(path / "linkedin_draft.png", dpi=300)
    plt.close(fig)


def prose(r: Registry) -> None:
    root = r.root
    q = "How do recorded charge-off risk and assumption-based loss sharing vary across cohorts and fixed macroeconomic scenarios in SBA 7(a) lending?"
    findings = [
        f"Out-of-time discrimination is modest: Term-free Firth crisis AUC {r.display('auc_crisis', digits=3, interval=True)} and later-cohort AUC {r.display('auc_later', digits=3, interval=True)}. Crisis prediction is {r.display('pd_crisis', 100)}% versus {r.display('rate_crisis', 100)}% recorded; later prediction is {r.display('pd_later', 100)}% versus {r.display('rate_later', 100)}% recorded.",
        f"On the observed fixed portfolio, a conditional +1 pp endpoint unemployment change is associated with {r.display('endpoint', digits=3, interval=True)} pp higher probability; the separately estimated peak-path sensitivity gives {r.display('peak', digits=3, interval=True)} pp. Neither is causal or a derivative.",
        f"Baseline/adverse EL proxies are ${r.display('baseline_expected_loss_usd', 1e-6, 1)}m / ${r.display('adverse_expected_loss_usd', 1e-6, 1)}m. The paired difference is ${r.display('adverse_minus_baseline_expected_loss_usd_change', 1e-6, 1, True)}m; pro-rata SBA shares are {r.display('baseline_sba_share', 100)}% / {r.display('adverse_sba_share', 100)}%, not measured public costs.",
    ]
    readme = [
        "# Local economic conditions and public–lender loss sharing in SBA 7(a) lending",
        "",
        q,
        "",
        "![Discrimination, calibration and conditional scenarios](figures/g5/headline.png)",
        "",
        "## Findings",
        "",
        *[str(i + 1) + ". " + s for i, s in enumerate(findings)],
        "",
        "## Method",
        "",
        "We estimate Term-free Firth logistic scorecards for recorded charge-off within 36 months of first disbursement. Layer 1 reconstructs approval descriptors from a snapshot; Layer 2 adds future realized or stipulated state unemployment and house-price paths and is a conditional exercise. ElasticNet/LightGBM benchmark tuning occurred on 2003H1 in G2, and the selected settings and boosting rounds were inherited unchanged by G2-bis; benchmark calibration uses separate cohorts. Training-state multiplier refits and fitted-model conditional evaluation bands measure different uncertainty components.",
        "",
        "## Data and chronology",
        "",
        "Official SBA 7(a) FOIA, snapshot 30 June 2026, plus direct BLS LAUS and FHFA all-transactions state HPI. No FRED observations; see [DATA.md](DATA.md) for source terms and frozen hashes. This product uses FHFA data but is neither endorsed nor certified by FHFA.",
        "",
        "Layer 1: fit 1991–2002; tune 2003H1 in G2; calibrate benchmarks 2003H2; evaluate 2007–2009 and 2011–2013. Layer 2: fit 1991–2009; calibrate LightGBM on 2010; check 2013–2014. **Retrospective conditional validation using realized macro paths.** Calibration labels extend to end-2013; the 2013 cohort was seen previously. The fixed 2006 scenario portfolio enters Layer 2 estimation.",
        "",
        HISTORY,
        "",
        "## Read and reproduce",
        "",
        "[Two-page policy note](report/policy_note.pdf) · [Technical report](report/technical_report.pdf) · [Claims/provenance](CLAIMS.md)",
        "",
        "```sh",
        "make report        # frozen aggregates + local renderer only",
        "make report-test   # reporting tests; no fitting",
        "make report-check  # scope/provenance/preservation checks",
        "```",
        "",
        "Python 3.11 with pandas/NumPy/Matplotlib/PyYAML/pytest/ruff/mypy; a cached local Tectonic executable is required (set TECTONIC if needed). Builds use offline cached TeX packages. No raw loans, private predictions or fitted models are needed. [Build and provenance notes](docs/G5_REPRODUCTION.md) list aggregate inputs, rendering dependencies and a private-data-free rehearsal. Legacy research commands remain historical and are not part of reporting reproduction.",
        "",
        "## What changed from v1",
        "",
        "The resolved-loans extract was replaced by official FOIA status coverage because selection on final loan outcome cannot be repaired with an age filter. The analysis defines complete calendar-month charge-off windows, uses separate temporal roles, excludes reported Term from primary specifications and distinguishes prediction from future-path conditioning. Failed ordinary logit fits led to an explicitly post-results protocol amendment and Firth estimation. These are joint changes in source, estimand and design; legacy and current metrics are not like-for-like performance comparisons. [Pre-G5 surfaces](versions/pre-g5-2026-10-08/) and the `v1-original` tag remain available.",
        "",
        "## Limitations and future work",
        "",
        "- Administrative charge-off and mature EXEMPT classification do not measure delinquency or verify performance; the sample excludes rejected applicants.",
        "- Descriptor/Term vintages remain unverified, rates are largely missing, and revised macro data are not historical information sets.",
        "- Calibration fails across cohorts; average agreement in calibrated Layer 2 LightGBM does not establish group calibration. Post-results amendments and reused/calendar-overlapping cohorts limit confirmatory claims.",
        "- "
        + LOSS
        + " Recoveries, amortization, actual payouts and loss-assumption uncertainty are absent; CCF 100% does not make the combined EL necessarily conservative.",
        "- Independent-state/successful-draw conditioning and univariate support checks leave broader dependence and joint path plausibility unresolved. Future rolling-origin recalibration, block Shapley accounting, competing risks or separately authorized policy design require new protocols; none is executed here.",
        "",
        "## Local status and source rights",
        "",
        "Prepared for local review only. External release needs Hakan’s separate written approval. Layers 3–4, publication/rename, uploads and CV-file edits are outside this work. Source rights remain in DATA.md; no borrower data are distributed. Legacy work and its history remain preserved; G5 does not redistribute source datasets.",
        "",
        "Hakan Zeki Gülmez · M.Sc. Management & Technology (Economics & Econometrics), Technical University of Munich · [GitHub](https://github.com/hakangulmez) · [LinkedIn](https://www.linkedin.com/in/hakan-zeki-g%C3%BClmez-088700180/)",
    ]
    (root / "README.md").write_text("\n".join(readme) + "\n")
    summary = [
        f"A Term-free SBA scorecard has modest crisis discrimination, AUC {r.display('auc_crisis', digits=3, interval=True)}, and calibration fails across cohorts.",
        f"A conditional endpoint unemployment increase of one percentage point is associated with {r.display('endpoint', digits=3, interval=True)} probability percentage points on the fixed portfolio, without causal interpretation.",
        f"Under fixed loss-sharing assumptions, baseline and adverse expected-loss proxies are ${r.display('baseline_expected_loss_usd', 1e-6, 1)}m and ${r.display('adverse_expected_loss_usd', 1e-6, 1)}m, rather than measured public costs.",
    ]
    (root / "figures/linkedin/g5/LINKEDIN_DRAFT.md").write_text(
        "# LinkedIn summary — local draft, not posted\n\n"
        + "\n\n".join(summary)
        + "\n\nQualifications: retrospective feature/revised-macro vintages; calibration failure; fixed-portfolio assumptions; conditional intervals. "
        + LOSS
        + "\n"
    )
    (root / "CV_BULLET_DRAFT.md").write_text(
        "# CV bullet alternatives — draft only\n\n- Validation/calibration: Built a temporally separated SBA charge-off study; documented modest crisis discrimination (AUC "
        + r.display("auc_crisis", digits=3)
        + ") and calibration failure ("
        + r.display("pd_crisis", 100)
        + "% predicted versus "
        + r.display("rate_crisis", 100)
        + "% recorded), with traceable state-cluster inference.\n- Conditional scenarios: Built a fixed-portfolio macro-conditioned loss-proxy exercise with paired uncertainty and assumption-based public/lender allocation; baseline/adverse projections of $"
        + r.display("baseline_expected_loss_usd", 1e-6, 1)
        + "m/$"
        + r.display("adverse_expected_loss_usd", 1e-6, 1)
        + "m are conditional scenarios, not causal effects or measured fiscal costs.\n\nLocal alternatives only; no CV file edited or material sent.\n"
    )


def compile_pdfs(root: Path) -> None:
    compiler = (
        os.environ.get("TECTONIC")
        or shutil.which("tectonic")
        or str(ROOT.parent / ".tools/tectonic/tectonic")
    )
    work = root / "data/g5-2026-10-08/build"
    work.mkdir(parents=True, exist_ok=True)
    for name in ["policy_note", "technical_report"]:
        subprocess.run(
            [
                compiler,
                "--only-cached",
                "--keep-logs",
                "--outdir",
                str(work.resolve()),
                name + ".tex",
            ],
            cwd=root / "report/g5",
            check=True,
        )
        shutil.copyfile(work / (name + ".pdf"), root / "report" / (name + ".pdf"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    r = load(root)
    tables(r)
    graphics(r)
    prose(r)
    (root / OUT / "rendered_claims.json").write_text(json.dumps(r.render_log, indent=2) + "\n")
    if not args.no_pdf:
        compile_pdfs(root)
    print("G5 results-only rendering complete. No research pipeline imported.")


if __name__ == "__main__":
    main()
