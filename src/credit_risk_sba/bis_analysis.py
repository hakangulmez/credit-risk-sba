"""Fixed-portfolio associations and paired scenario summaries for each fitted draw."""

import numpy as np
import pandas as pd
from scipy.special import expit

from .bis_data import LOSS_LABEL, VALIDATION_LABEL, table
from .losses import assign_lgd, lgd_tables
from .macro import MACRO
from .stress import group_matrix


class FixedAnalysis:
    def __init__(self, root, training, reference, scenario):
        self.reference = reference.reset_index(drop=True)
        self.scenario = scenario
        self.names, self.groups = group_matrix(self.reference)
        self.counts = np.asarray(self.groups.sum(axis=1)).ravel()
        self.ead = self.reference.GrossApproval.to_numpy()
        self.guarantee = self.reference.guarantee_share.to_numpy()
        self.valid = np.isfinite(self.guarantee) & (self.guarantee >= 0) & (self.guarantee <= 1)
        self.exposures = np.asarray(self.groups @ np.where(self.valid, self.ead, 0)).ravel()
        self.valid_counts = np.asarray(self.groups @ self.valid.astype(float)).ravel()
        self.severity = {}
        for name, down, cap in [
            ("primary", False, False),
            ("capped", False, True),
            ("downturn", True, False),
        ]:
            f, mapping = lgd_tables(training.assign(role="train"), down, cap)
            f["loss_accounting"] = LOSS_LABEL
            table(root, "lgd_" + name, f)
            self.severity[name] = assign_lgd(self.reference, mapping)
            old = pd.read_csv(root / "results/g2-2026-10-08" / f"lgd_{name}.csv")
            for col in ["valid_cell_n", "pooled_n", "lgd_proxy", "excluded_severity_n"]:
                np.testing.assert_allclose(f[col], old[col], rtol=1e-12, atol=1e-12)
        table(
            root,
            "loss_population",
            [
                {
                    "reference_n": len(reference),
                    "valid_loss_n": int(self.valid.sum()),
                    "excluded_invalid_share_n": int((~self.valid).sum()),
                    "loss_accounting": LOSS_LABEL,
                    "reference_role": "Fixed 2006 scenario portfolio; included in Layer 2 estimation, not OOS validation",
                }
            ],
        )

    def scenario_frames(self):
        frames = {}
        for name in ["baseline", "adverse"]:
            frames[name] = self.reference.drop(columns=MACRO + ["peak_du"]).merge(
                self.scenario.loc[self.scenario.scenario.eq(name)].drop(columns="scenario"),
                on="ProjectState",
                how="left",
                sort=False,
                validate="many_to_one",
            )
            assert frames[name].row_id.equals(self.reference.row_id)
        return frames

    def evaluate(self, design, beta):
        result = []
        frames = self.scenario_frames()
        scenario_result = {}
        for scenario, inputs in frames.items():
            p = expit(np.asarray(design.transform(inputs, reduced=True) @ beta).ravel())
            pdmean = np.asarray(self.groups @ p).ravel() / self.counts
            for severity in (
                ["primary", "capped", "downturn"] if scenario == "adverse" else ["primary"]
            ):
                loss = p * self.severity[severity] * self.ead
                loss = np.where(self.valid, loss, 0.0)
                g = np.where(self.valid, self.guarantee, 0.0)
                total = np.asarray(self.groups @ loss).ravel()
                sba = np.asarray(self.groups @ (loss * g)).ravel()
                lender = np.asarray(self.groups @ (loss * (1 - g))).ravel()
                if not np.allclose(total, sba + lender, rtol=1e-12, atol=1e-5):
                    raise ValueError("Loss allocation does not reconcile")
                vals = {
                    "pd": pdmean,
                    "expected_loss_usd": total,
                    "sba_loss_usd": sba,
                    "lender_loss_usd": lender,
                    "loss_rate": total / self.exposures,
                }
                scenario_result[(scenario, severity)] = vals
                for i, (group, value) in enumerate(self.names):
                    for metric, values in vals.items():
                        result.append(
                            {
                                "scenario": scenario,
                                "lgd_variant": severity,
                                "group": group,
                                "group_value": value,
                                "metric": metric,
                                "value": float(values[i]),
                                "pd_n": int(self.counts[i]),
                                "loss_n": int(self.valid_counts[i]),
                                "approval_exposure_usd": float(self.exposures[i]),
                                "loss_accounting": LOSS_LABEL,
                                "layer_interpretation": VALIDATION_LABEL,
                            }
                        )
        for i, (group, value) in enumerate(self.names):
            for metric in scenario_result[("baseline", "primary")]:
                scale = 100 if metric == "pd" else 1
                delta = (
                    scenario_result[("adverse", "primary")][metric][i]
                    - scenario_result[("baseline", "primary")][metric][i]
                ) * scale
                result.append(
                    {
                        "scenario": "adverse_minus_baseline",
                        "lgd_variant": "primary",
                        "group": group,
                        "group_value": value,
                        "metric": "pd_change_pp" if metric == "pd" else metric + "_change",
                        "value": float(delta),
                        "pd_n": int(self.counts[i]),
                        "loss_n": int(self.valid_counts[i]),
                        "approval_exposure_usd": float(self.exposures[i]),
                        "loss_accounting": LOSS_LABEL,
                        "layer_interpretation": VALIDATION_LABEL,
                    }
                )
        return result

    def macro_associations(self, design, beta, peak=False):
        feature = "peak_du" if peak else "du"
        names = np.array(design.names)[design.keep]
        positions = np.flatnonzero(names == feature)
        if len(positions) != 1:
            raise ValueError("Unemployment association not identifiable")
        eta = np.asarray(design.transform(self.reference, reduced=True) @ beta).ravel()
        step = beta[positions[0]] / design.scale[design.numeric.index(feature)]
        changes = 100 * (expit(eta + step) - expit(eta))
        means = np.asarray(self.groups @ changes).ravel() / self.counts
        return [
            {
                "feature": feature,
                "group": group,
                "group_value": value,
                "value": float(means[i]),
                "n": int(self.counts[i]),
                "change": "+1 percentage point " + feature,
                "evaluation": "2006 fixed portfolio observed macro paths",
                "interpretation": "conditional finite-change association, not causal",
                "layer_interpretation": VALIDATION_LABEL,
            }
            for i, (group, value) in enumerate(self.names)
        ]


def average_associations(design, beta, frame):
    x = design.transform(frame, reduced=True)
    eta = np.asarray(x @ beta).ravel()
    p = expit(eta)
    names = np.array(design.names)[design.keep]
    records = []
    for col, scale in zip(design.numeric, design.scale, strict=True):
        pos = np.flatnonzero(names == col)
        if len(pos):
            records.append(
                {
                    "feature": col,
                    "contrast": "derivative per unit of native feature (log variables remain log units)",
                    "value": float(100 * np.mean(p * (1 - p)) * beta[pos[0]] / scale),
                    "n": len(frame),
                    "interpretation": "average marginal association in percentage points; not causal",
                }
            )
    for cat in design.categorical:
        columns = np.flatnonzero(np.char.startswith(names.astype(str), cat + "_"))
        if len(columns):
            base = eta - np.asarray(x[:, columns] @ beta[columns]).ravel()
            reference = expit(base)
            for column_position in columns:
                records.append(
                    {
                        "feature": str(names[column_position]),
                        "contrast": "discrete contrast against training reference category",
                        "value": float(
                            100 * np.mean(expit(base + beta[column_position]) - reference)
                        ),
                        "n": len(frame),
                        "interpretation": "average marginal association in percentage points; not causal",
                    }
                )
    return records


def support(root, variant, training, design, analysis):
    rows = []
    summaries = []
    for scenario, inputs in analysis.scenario_frames().items():
        for scope in ["state_specific", "pooled_global"]:
            flagged = np.zeros(len(inputs), dtype=bool)
            for feature in design.numeric:
                if scope == "state_specific":
                    bounds = training.groupby("ProjectState")[feature].agg(["min", "max"])
                    lo = inputs.ProjectState.map(bounds["min"]).to_numpy()
                    hi = inputs.ProjectState.map(bounds["max"]).to_numpy()
                else:
                    lo = np.full(len(inputs), training[feature].min())
                    hi = np.full(len(inputs), training[feature].max())
                value = inputs[feature].to_numpy()
                outside = (value < lo) | (value > hi)
                flagged |= outside
                rows.append(
                    {
                        "variant": variant,
                        "scenario": scenario,
                        "scope": scope,
                        "feature": feature,
                        "flagged_loan_n": int(outside.sum()),
                        "flagged_fraction": float(outside.mean()),
                        "flagged_approval_usd": float(inputs.loc[outside, "GrossApproval"].sum()),
                        "n": len(inputs),
                        "definition": "Univariate training range; not evidence of joint support",
                        "loss_accounting": LOSS_LABEL,
                        "layer_interpretation": VALIDATION_LABEL,
                    }
                )
            summaries.append(
                {
                    "variant": variant,
                    "scenario": scenario,
                    "scope": scope,
                    "feature": "any_numeric",
                    "flagged_loan_n": int(flagged.sum()),
                    "flagged_fraction": float(flagged.mean()),
                    "flagged_approval_usd": float(inputs.loc[flagged, "GrossApproval"].sum()),
                    "n": len(inputs),
                    "definition": "Union of univariate numeric training-range flags; not joint-support evidence",
                    "loss_accounting": LOSS_LABEL,
                    "layer_interpretation": VALIDATION_LABEL,
                }
            )
    return rows, summaries
