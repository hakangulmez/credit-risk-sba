"""Retained state, drift, TreeSHAP and fixed score-allocation diagnostics."""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .bis_benchmarks import subsets
from .bis_data import LOSS_LABEL, NAME, VALIDATION_LABEL, table
from .bis_runner import VARIANTS, data, training
from .losses import accepted_mask, allocate, assign_lgd, lgd_tables
from .metrics import METRICS, evaluate, psi


def loaded_models(root, variant):
    private = root / "models" / NAME
    models = {}
    for family, suffix in [("firth", "firth_point"), ("unpenalized", "mle")]:
        m = joblib.load(private / f"{variant}_{suffix}.joblib")
        if m.diagnostics["converged"]:
            models[family + "_raw"] = (m, None)
    for family in ["elasticnet", "lightgbm"]:
        path = private / f"{variant}_{family}_benchmark.joblib"
        if path.exists():
            m = joblib.load(path)
            if m["status"]["converged"]:
                models[family + "_raw"] = (m["model"], None)
                if m["calibrator"] is not None:
                    models[family + "_calibrated"] = (m["model"], m["calibrator"])
    return models


def predict(name, model, calibration, design, frame):
    if name.startswith("lightgbm"):
        p = model.predict(design.tree(frame), num_threads=4)
    elif name.startswith("elasticnet"):
        p = model.predict_proba(design.transform(frame, reduced=True)[:, 1:])[:, 1]
    else:
        p = model.predict(design.transform(frame, reduced=True))
    return calibration.predict(p) if calibration is not None else p


def run(root):
    f, _, _ = data(root)
    _, lgd = lgd_tables(training(f, "layer1"))
    private = root / "data" / NAME / "predictions"
    private.mkdir(parents=True, exist_ok=True)
    state_rows, allocations, attribution, drift, paired = [], [], [], [], []
    pairs = {}
    for variant in VARIANTS:
        layer = "layer1" if variant.startswith("layer1") else "layer2"
        design = joblib.load(root / "models" / NAME / f"{variant}_design.joblib")
        cohorts = subsets(f, layer)
        tr = training(f, variant)
        for cohort, frame in cohorts.items():
            if cohort.startswith(("training", "calibration")):
                continue
            for col in design.numeric + design.categorical:
                drift.append(
                    {
                        "variant": variant,
                        "cohort": cohort,
                        "feature": col,
                        "psi": psi(tr[col], frame[col], col in design.categorical),
                        "training_n": len(tr),
                        "test_n": len(frame),
                        "epsilon": 1e-6,
                        "layer_interpretation": VALIDATION_LABEL
                        if layer == "layer2"
                        else "Approval-descriptor prediction",
                    }
                )
        for name, (model, calibrator) in loaded_models(root, variant).items():
            for cohort, frame in cohorts.items():
                if cohort.startswith(("training", "calibration")):
                    continue
                p = predict(name, model, calibrator, design, frame)
                pd.DataFrame(
                    {
                        "row_id": frame.row_id,
                        "state": frame.ProjectState,
                        "Y": frame.Y,
                        "probability": p,
                    }
                ).to_parquet(private / f"{variant}_{name}_{cohort}.parquet", index=False)
                state = (
                    frame[["ProjectState", "Y"]]
                    .assign(predicted=p)
                    .groupby("ProjectState")
                    .agg(
                        n=("Y", "size"),
                        events=("Y", "sum"),
                        recorded_rate=("Y", "mean"),
                        mean_predicted=("predicted", "mean"),
                    )
                    .reset_index()
                )
                meta = {
                    "variant": variant,
                    "model": name,
                    "cohort": cohort,
                    "outcome": "recorded charge-off within 36 months",
                    "layer_interpretation": VALIDATION_LABEL
                    if layer == "layer2"
                    else "Approval-descriptor prediction",
                }
                state_rows.extend(state.assign(**meta).to_dict("records"))
                selected = accepted_mask(p, frame.row_id, 0.7)
                selected_frame = frame.loc[selected]
                valid = selected_frame.guarantee_share.between(0, 1)
                loans = selected_frame.loc[valid]
                selected_p = p[selected][valid.to_numpy()]
                loss = allocate(
                    selected_p, assign_lgd(loans, lgd), loans.GrossApproval, loans.guarantee_share
                )
                allocations.append(
                    {
                        **meta,
                        "test_n": len(frame),
                        "accepted_n": int(selected.sum()),
                        "rule": "70% lowest score, floor(n * .70), file/row deterministic ties",
                        "accepted_recorded_rate": float(selected_frame.Y.mean()),
                        "accepted_mean_pd": float(p[selected].mean()),
                        "valid_loss_n": len(loans),
                        "approval_exposure_usd": float(loans.GrossApproval.sum()),
                        "expected_loss_usd": float(loss[0].sum()),
                        "sba_loss_usd": float(loss[1].sum()),
                        "lender_loss_usd": float(loss[2].sum()),
                        "loss_accounting": LOSS_LABEL,
                        "interpretation": "Fixed score allocation diagnostic; not an operational approval rule",
                    }
                )
                # Preserve paired Term differences with the unchanged 999 conditional state draws.
                if variant != "layer2_peak":
                    cache = (
                        root / "models" / NAME / f"{variant}_{name}_{cohort}_paired_samples.joblib"
                    )
                    if cache.exists():
                        score, samples = joblib.load(cache)
                    else:
                        score, samples = evaluate(frame.Y, p, frame.ProjectState)
                        joblib.dump((score, samples), cache)
                    pairs[(variant, name, cohort)] = (
                        np.array([r["value"] for r in score]),
                        samples,
                    )
            if name == "lightgbm_raw":
                cohort = (
                    "crisis_2007_2009"
                    if layer == "layer1"
                    else "post_amendment_validation_2013_2014"
                )
                frame = cohorts[cohort].sample(
                    n=min(5000, len(cohorts[cohort])), random_state=20261008
                )
                x = design.tree(frame)
                shap = model.predict(x, pred_contrib=True, num_threads=4)
                raw = model.predict(x, raw_score=True, num_threads=4)
                if not np.allclose(shap.sum(axis=1), raw, atol=1e-8):
                    raise ValueError("Exact TreeSHAP sum mismatch")
                attribution.extend(
                    [
                        {
                            "variant": variant,
                            "cohort": cohort,
                            "feature": col,
                            "mean_absolute_treeshap_log_odds": float(v),
                            "sample_n": len(frame),
                            "max_abs_sum_error": float(np.max(np.abs(shap.sum(axis=1) - raw))),
                            "interpretation": "Predictive attribution; not a causal effect",
                            "layer_interpretation": VALIDATION_LABEL
                            if layer == "layer2"
                            else "Approval-descriptor prediction",
                        }
                        for col, v in zip(x.columns, np.abs(shap[:, :-1]).mean(axis=0), strict=True)
                    ]
                )
        print("Retained diagnostics", variant, flush=True)
    for (variant, name, cohort), (point, samples) in pairs.items():
        if not variant.endswith("_term"):
            continue
        key = (variant.removesuffix("_term"), name, cohort)
        if key not in pairs:
            continue
        before, draws = pairs[key]
        for j, metric in enumerate(METRICS):
            delta = samples[:, j] - draws[:, j]
            good = delta[np.isfinite(delta)]
            lo, hi = np.quantile(good, [0.025, 0.975]) if len(good) else (np.nan, np.nan)
            paired.append(
                {
                    "comparison": variant + " minus " + key[0],
                    "model": name,
                    "cohort": cohort,
                    "metric": metric,
                    "difference": float(point[j] - before[j]),
                    "lower": float(lo),
                    "upper": float(hi),
                    "draws": 999,
                    "undefined_draws": 999 - len(good),
                    "interval": "paired state-cluster, conditional on frozen fitted models; not Firth training-refit interval",
                    "layer_interpretation": VALIDATION_LABEL
                    if variant.startswith("layer2")
                    else "Approval-descriptor prediction",
                }
            )
    table(root, "state_validation", state_rows)
    table(root, "portfolio_allocation_70pct", allocations)
    table(root, "treeshap", attribution)
    table(root, "population_stability", drift)
    table(root, "paired_term_differences", paired)


if __name__ == "__main__":
    run(Path.cwd())
