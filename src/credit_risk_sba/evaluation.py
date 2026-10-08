"""Frozen crisis/OOT evaluation, interpretation, drift and portfolio allocation."""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .data import CAT, NUM
from .fitting import active_data, predict
from .io import config, sha256, table
from .losses import (
    EAD_LABEL,
    LGD_LABEL,
    SPLIT_LABEL,
    accepted_mask,
    allocate,
    assign_lgd,
    lgd_tables,
)
from .metrics import METRICS, calibration_bins, evaluate, psi


def evaluate_all(root: Path):
    cfg = config(root)
    f = active_data(root)
    training = f.loc[f.role.eq("train")]
    _, lgd = lgd_tables(training)
    private = root / "models/g2-2026-10-08"
    metric_rows, bin_rows, state_rows, portfolio_rows, interpretation_rows = [], [], [], [], []
    comparisons = {}
    for path in sorted(private.glob("*.joblib")):
        if path.stem.endswith("_design"):
            continue
        variant, family = path.stem.rsplit("_", 1)
        if family not in {"logit", "elasticnet", "lightgbm"}:
            continue
        bundle = joblib.load(path)
        if not bundle["status"]["converged"]:
            continue
        design = joblib.load(private / f"{variant}_design.joblib")
        train_raw = predict(bundle, design, training, family)
        train_cal = bundle["calibrator"].predict(train_raw)
        for role in ["crisis", "oot"]:
            test = f.loc[f.role.eq(role)]
            p = predict(bundle, design, test, family)
            q = bundle["calibrator"].predict(p)
            predictions_path = root / "data/derived/g2-2026-10-08" / f"predictions_{path.stem}_{role}.parquet"
            pd.DataFrame({"row_id": test.row_id, "Y": test.Y, "state": test.ProjectState,
                          "raw": p, "calibrated": q}).to_parquet(predictions_path, index=False)
            for calibration, scores, train_scores in [("raw", p, train_raw), ("sigmoid_2003H2", q, train_cal)]:
                cached = private / f"metrics_{path.stem}_{role}_{calibration}.joblib"
                fingerprint = (sha256(path), sha256(root / "config/g2.yaml"),
                               sha256(root / "data/derived/g2-2026-10-08/matched.parquet"))
                if cached.exists():
                    payload = joblib.load(cached)
                    if payload["fingerprint"] != fingerprint:
                        raise ValueError("Evaluation cache does not match the frozen model/config/data")
                    records, samples, bins = payload["records"], payload["samples"], payload["bins"]
                else:
                    records, samples = evaluate(test.Y, scores, test.ProjectState,
                                                cfg["bootstrap_draws"], cfg["seed"])
                    bins = calibration_bins(train_scores, test.Y.to_numpy(), scores,
                                            test.ProjectState.to_numpy(), cfg["bootstrap_draws"], cfg["seed"])
                    joblib.dump({"fingerprint": fingerprint, "records": records,
                                 "samples": samples, "bins": bins}, cached)
                for record in records:
                    record.update(variant=variant, family=family, role=role, calibration=calibration,
                                  outcome=cfg["outcome"])
                metric_rows.extend(records)
                comparisons[(variant, family, role, calibration)] = (np.array([r["value"] for r in records]), samples)
                for row in bins:
                    row.update(variant=variant, family=family, role=role, calibration=calibration,
                               outcome=cfg["outcome"])
                bin_rows.extend(bins)
                state_data = test[["ProjectState", "Y"]].assign(predicted=scores).groupby("ProjectState").agg(
                    n=("Y", "size"), recorded_charge_offs_36m=("Y", "sum"), recorded_rate=("Y", "mean"),
                    predicted_pd=("predicted", "mean")).reset_index()
                state_data = state_data.assign(variant=variant, family=family, role=role, calibration=calibration)
                state_rows.extend(state_data.to_dict("records"))
            mask = accepted_mask(q, test.row_id, cfg["acceptance_fraction"])
            selected = test.loc[mask].copy()
            valid = selected.guarantee_share.between(0, 1)
            selected = selected.loc[valid]
            selected_p = q[mask][valid.to_numpy()]
            losses = allocate(selected_p, assign_lgd(selected, lgd), selected.GrossApproval, selected.guarantee_share)
            portfolio_rows.append({"variant": variant, "family": family, "role": role,
               "rule": "70% lowest calibrated PD; floor(n*0.70); file/row ties", "test_n": len(test),
               "accepted_n": int(mask.sum()), "valid_loss_n": len(selected),
               "accepted_recorded_rate": float(test.loc[mask, "Y"].mean()),
               "accepted_mean_pd": float(q[mask].mean()), "approval_exposure_usd": float(selected.GrossApproval.sum()),
               "expected_loss_usd": float(losses[0].sum()), "sba_loss_usd": float(losses[1].sum()),
               "lender_loss_usd": float(losses[2].sum()), "ead_definition": EAD_LABEL,
               "lgd_definition": LGD_LABEL, "allocation": SPLIT_LABEL,
               "interpretation": "fixed score allocation diagnostic; no operational approval claim"})
            print(f"Evaluated {path.stem} {role} ({len(test)} rows, {cfg['bootstrap_draws']} paired state draws)", flush=True)
            table(root, "evaluation_metrics", metric_rows)
            table(root, "calibration_bins", bin_rows)
        if family == "lightgbm":
            crisis = f.loc[f.role.eq("crisis")].sample(n=min(cfg["shap_max_rows"], int(f.role.eq("crisis").sum())), random_state=cfg["seed"])
            tree_x = design.tree(crisis)
            contributions = bundle["model"].predict(tree_x, pred_contrib=True)
            raw = bundle["model"].predict(tree_x, raw_score=True)
            if not np.allclose(contributions.sum(axis=1), raw, atol=1e-8):
                raise ValueError("TreeSHAP contributions do not sum to raw log odds")
            for name, value in zip(tree_x.columns, np.abs(contributions[:, :-1]).mean(axis=0), strict=True):
                interpretation_rows.append({"variant": variant, "feature": name, "mean_absolute_treeshap_log_odds": value,
                                             "crisis_sample_n": len(crisis), "interpretation": "prediction attribution; no causal interpretation"})
        if family == "logit":
            model = bundle["model"]
            mean_slope = np.mean(train_raw * (1 - train_raw))
            names = np.asarray(design.names)[design.keep]
            rows = []
            for j, name in enumerate(names):
                se = float(np.sqrt(max(model.covariance[j, j], 0)))
                marginal = (model.beta[j] / design.scale[design.numeric.index(name)] * mean_slope
                            if name in design.numeric else np.nan)
                rows.append({"variant": variant, "feature": name, "coefficient": model.beta[j],
                             "clustered_se": se, "lower": model.beta[j] - 1.96 * se,
                             "upper": model.beta[j] + 1.96 * se,
                             "average_marginal_association_native_unit": marginal,
                             "interpretation": "association; numeric derivative on training population"})
            table(root, f"coefficients_{variant}", rows)
    table(root, "state_validation", state_rows)
    table(root, "portfolio_allocation_70pct", portfolio_rows)
    table(root, "treeshap", interpretation_rows)
    difference_rows = []
    for key, (point, samples) in comparisons.items():
        variant, family, role, cal = key
        if variant.endswith("_term"):
            primary = variant.removesuffix("_term")
            comparator = (primary, family, role, cal)
            if comparator in comparisons:
                point0, samples0 = comparisons[comparator]
                delta = samples - samples0
                for j, metric in enumerate(METRICS):
                    valid = delta[:, j][np.isfinite(delta[:, j])]
                    lo, hi = np.quantile(valid, [.025, .975]) if len(valid) else [np.nan, np.nan]
                    difference_rows.append({"comparison": f"{variant} minus {primary}", "family": family,
                         "role": role, "calibration": cal, "metric": metric,
                         "difference": point[j] - point0[j], "lower": lo, "upper": hi,
                         "undefined_draws": cfg["bootstrap_draws"] - len(valid)})
    table(root, "paired_term_differences", difference_rows)
    drift = []
    for role in ["crisis", "oot"]:
        test = f.loc[f.role.eq(role)]
        for col in NUM + CAT + ["TermInMonths", "u0", "du", "peak_du", "h0", "dh", "year_trend"]:
            drift.append({"feature": col, "role": role, "psi": psi(training[col], test[col], col in CAT),
                          "training_n": len(training), "test_n": len(test), "epsilon": 1e-6})
    table(root, "population_stability", drift)
    joblib.dump(comparisons, private / "paired_metric_draws.joblib")
