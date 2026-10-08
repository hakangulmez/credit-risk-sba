"""Scientific figures from aggregate G2 tables: Okabe–Ito, PNG 300 dpi and PDF."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, ORANGE, GREEN, VERMILLION = "#0072B2", "#E69F00", "#009E73", "#D55E00"
NOTICE = "This product uses FHFA data but is neither endorsed nor certified by FHFA."


def save(root: Path, fig, name):
    path = root / "results/g2-2026-10-08/figures"
    path.mkdir(parents=True, exist_ok=True)
    fig.savefig(path / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(path / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def figures(root: Path):
    result = root / "results/g2-2026-10-08"
    bins = pd.read_csv(result / "calibration_bins.csv")
    metric = pd.read_csv(result / "evaluation_metrics.csv")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "savefig.facecolor": "white"})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), constrained_layout=True)
    for ax, calibration in zip(axes, ["raw", "sigmoid_2003H2"], strict=True):
        for family, color in [("elasticnet", BLUE), ("lightgbm", VERMILLION)]:
            for variant, marker, style in [("layer1", "o", "-"), ("layer1_term", "s", "--")]:
                group = bins.loc[bins.role.eq("crisis") & bins.variant.eq(variant) &
                                 bins.family.eq(family) & bins.calibration.eq(calibration) & bins.n.gt(0)].sort_values("bin")
                if group.empty:
                    continue
                name = f"{family.title()}, {'with' if variant.endswith('term') else 'without'} Term"
                ax.errorbar(100 * group.predicted_pd, 100 * group.recorded_rate,
                             yerr=100 * np.vstack([group.recorded_rate - group.lower, group.upper - group.recorded_rate]),
                             color=color, marker=marker, linestyle=style, capsize=2, linewidth=1, label=name)
        maximum = max(ax.get_xlim()[1], ax.get_ylim()[1], 20)
        ax.plot([0, maximum], [0, maximum], color="#777777", linestyle=":", linewidth=1)
        ax.set(xlabel="Predicted probability (%)", ylabel="Recorded charge-off within 36 months (%)",
               title="Raw scores" if calibration == "raw" else "Sigmoid calibrated on 2003H2", xlim=(0, maximum), ylim=(0, maximum))
        ax.legend(fontsize=7, loc="upper left")
    fig.suptitle("Crisis-cohort calibration: 2007–2009 disbursements", fontsize=13)
    fig.supxlabel("95% paired state-cluster intervals; frozen fits. Unpenalized logit unavailable (quasi-separation).", fontsize=8)
    save(root, fig, "layer1_crisis_calibration")

    selected = metric.loc[metric.role.eq("crisis") & metric.calibration.eq("sigmoid_2003H2") &
                          metric.variant.isin(["layer1", "layer1_term"])]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), constrained_layout=True)
    for ax, measure in zip(axes, ["auc", "brier"], strict=True):
        data = selected.loc[selected.metric.eq(measure)].sort_values(["family", "variant"])
        records = data.to_dict("records")
        labels = [f"{r['family'].title()}\n{'with' if r['variant'].endswith('term') else 'without'} Term" for r in records]
        for i, r in enumerate(records):
            ax.errorbar(i, r['value'], yerr=[[r['value'] - r['lower']], [r['upper'] - r['value']]], fmt="o",
                         color=BLUE if r['family'] == "elasticnet" else VERMILLION, capsize=4)
        ax.set_xticks(range(len(data)), labels, fontsize=8)
        ax.set(title="AUC (higher is better)" if measure == "auc" else "Brier score (lower is better)")
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Origination scorecards: crisis-cohort performance", fontsize=13)
    fig.supxlabel("95% paired state-cluster intervals, conditional on frozen models and calibration", fontsize=8)
    save(root, fig, "layer1_crisis_metrics")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), constrained_layout=True)
    for ax, role in zip(axes, ["crisis", "oot"], strict=True):
        group = bins.loc[bins.role.eq(role) & bins.variant.eq("layer2") & bins.family.eq("lightgbm") &
                         bins.calibration.eq("sigmoid_2003H2") & bins.n.gt(0)].sort_values("bin")
        ax.errorbar(100 * group.predicted_pd, 100 * group.recorded_rate,
                    yerr=100 * np.vstack([group.recorded_rate - group.lower, group.upper - group.recorded_rate]),
                    color=GREEN, marker="o", capsize=3, linewidth=1)
        maximum = max(ax.get_xlim()[1], ax.get_ylim()[1], 15)
        ax.plot([0, maximum], [0, maximum], color="#777777", linestyle=":")
        ax.set(title="Crisis 2007–2009" if role == "crisis" else "Later OOT 2011–2013",
               xlabel="Conditional predicted probability (%)", ylabel="Recorded charge-off within 36 months (%)",
               xlim=(0, maximum), ylim=(0, maximum))
    fig.suptitle("Macro LightGBM robustness: realized-path conditional calibration", fontsize=13)
    fig.supxlabel("Future realized macros are scenario inputs. 95% state-cluster intervals; frozen fits.\n" + NOTICE, fontsize=8)
    save(root, fig, "layer2_conditional_calibration")

    secondary = pd.read_csv(result / "stress_lightgbm_secondary.csv")
    subset = secondary.loc[secondary.variant.eq("layer2") & secondary.group.eq("overall") & secondary.lgd_variant.eq("primary")].set_index("scenario")
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    x = np.arange(2)
    sba = subset.reindex(["baseline", "adverse"]).sba_loss_usd.to_numpy() / 1e6
    lender = subset.reindex(["baseline", "adverse"]).lender_loss_usd.to_numpy() / 1e6
    ax.bar(x, sba, color=BLUE, label="SBA pro-rata share")
    ax.bar(x, lender, bottom=sba, color=ORANGE, label="Lender-retained pro-rata share")
    ax.set_xticks(x, ["Baseline", "Fixed 2007–2010 adverse"])
    ax.set(ylabel="Gross charge-off loss proxy (USD millions)", title="Secondary fixed-tree scenario projections on the 2006 portfolio")
    ax.legend()
    fig.supxlabel("Point projections only: primary logit failed; coefficient intervals unavailable.\nEAD = GrossApproval; CCF = 100%; gross LGD proxy; pro-rata allocation.\n" + NOTICE, fontsize=8)
    save(root, fig, "secondary_scenario_loss_split")
