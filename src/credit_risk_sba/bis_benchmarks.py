"""Fixed-setting benchmarks and diagnostics; no search or primary recalibration."""

import resource
import time
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import yaml
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from .bis_analysis import FixedAnalysis
from .bis_data import NAME, VALIDATION_LABEL, js, table
from .bis_runner import VARIANTS, data, training
from .io import sha256
from .metrics import calibration_bins, evaluate
from .models import calibrate


def subsets(f, layer):
    if layer == "layer1":
        return {
            "training_1991_2002": training(f, layer),
            "calibration_2003H2": f.loc[f.year.eq(2003) & f.d.dt.month.ge(7)],
            "crisis_2007_2009": f.loc[f.year.between(2007, 2009)],
            "additional_cohort_2011_2013": f.loc[f.year.between(2011, 2013)],
        }
    return {
        "training_1991_2009": training(f, layer),
        "calibration_2010": f.loc[f.year.eq(2010)],
        "post_amendment_validation_2013_2014": f.loc[f.year.between(2013, 2014)],
    }


def preprocessing_counts(design, frame, variant, cohort):
    rows = []
    for col in design.categorical:
        s = frame[col].fillna("__missing__").replace("", "__missing__").astype(str)
        unseen = ~s.isin(design.maps[col])
        rows.append(
            {
                "variant": variant,
                "cohort": cohort,
                "feature": col,
                "n": len(frame),
                "missing_n": int(s.eq("__missing__").sum()),
                "unseen_n": int(unseen.sum()),
                "unseen_action": "fitted Other"
                if "Other" in design.maps[col].values()
                else "zero one-hot dummy vector; native tree missing category",
                "layer_interpretation": VALIDATION_LABEL
                if variant.startswith("layer2")
                else "Approval-descriptor prediction",
            }
        )
    for col in design.numeric:
        rows.append(
            {
                "variant": variant,
                "cohort": cohort,
                "feature": col,
                "n": len(frame),
                "missing_n": int((~np.isfinite(frame[col])).sum()),
                "unseen_n": 0,
                "unseen_action": "training median plus missing flag for logit; native missing for tree",
                "layer_interpretation": VALIDATION_LABEL
                if variant.startswith("layer2")
                else "Approval-descriptor prediction",
            }
        )
    return rows


def benchmark_fit(root, variant, family, tr, calibration, design, settings):
    path = root / "models" / NAME / f"{variant}_{family}_benchmark.joblib"
    if path.exists():
        return joblib.load(path)
    tick = time.perf_counter()
    warnings_text = []
    if family == "elasticnet":
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = LogisticRegression(**settings["settings"])
            model.fit(design.transform(tr, reduced=True)[:, 1:], tr.Y)
        warnings_text = [str(w.message) for w in caught]
        converged = not any(issubclass(w.category, ConvergenceWarning) for w in caught)
        predict = model.predict_proba(design.transform(calibration, reduced=True)[:, 1:])[:, 1]
        rounds = int(model.n_iter_[0])
    else:
        choice = settings["settings"]
        model = lgb.train(
            choice["parameters"],
            lgb.Dataset(design.tree(tr), label=tr.Y),
            num_boost_round=choice["num_boost_round"],
        )
        predict = model.predict(design.tree(calibration), num_threads=4)
        rounds, converged = model.current_iteration(), True
        if rounds != choice["num_boost_round"]:
            warnings_text.append(
                "LightGBM terminated before fixed round count; recorded explicitly"
            )
    calibrator = None
    calibration_failure = None
    if converged:
        try:
            calibrator = calibrate(calibration.Y.to_numpy(), predict)
        except ValueError as exc:
            calibration_failure = str(exc)
    record = {
        "model": model,
        "calibrator": calibrator,
        "status": {
            "variant": variant,
            "family": family,
            "converged": converged,
            "n": len(tr),
            "events": int(tr.Y.sum()),
            "calibration_n": len(calibration),
            "calibration_start": str(calibration.d.min().date()),
            "calibration_end": str(calibration.d.max().date()),
            "calibration_failure": calibration_failure,
            "iterations_or_rounds": rounds,
            "settings": settings,
            "warnings": warnings_text,
            "seconds": time.perf_counter() - tick,
            "calibration_intercept": calibrator.intercept if calibrator else None,
            "calibration_slope": calibrator.slope if calibrator else None,
            "layer_interpretation": VALIDATION_LABEL
            if variant.startswith("layer2")
            else "Approval-descriptor prediction",
        },
    }
    joblib.dump(record, path)
    return record


def run(root):
    cfg = yaml.safe_load((root / "config/g2_bis_2026-10-08.yaml").read_text())
    f, reference, scenario = data(root)
    private = root / "models" / NAME
    output = root / "results" / NAME
    tick = time.perf_counter()
    evaluation, deciles, means, counts, fit_status, stress = [], [], [], [], [], []
    analysis = FixedAnalysis(root, training(f, "layer1"), reference, scenario)
    with threadpool_limits(limits=4):
        for variant in VARIANTS:
            layer = "layer1" if variant.startswith("layer1") else "layer2"
            tr = training(f, variant)
            design = joblib.load(private / f"{variant}_design.joblib")
            cohorts = subsets(f, layer)
            point = joblib.load(private / f"{variant}_firth_point.joblib")
            mle = joblib.load(private / f"{variant}_mle.joblib")
            models = []
            if point.diagnostics["converged"]:
                models.append(("firth_raw", point, None))
            if mle.diagnostics["converged"]:
                models.append(("unpenalized_raw", mle, None))
            if variant != "layer2_peak":
                source = "layer1_term" if variant.endswith("term") else "layer1"
                calibration = cohorts[
                    "calibration_2003H2" if layer == "layer1" else "calibration_2010"
                ]
                families = ["elasticnet", "lightgbm"] if layer == "layer1" else ["lightgbm"]
                for family in families:
                    result = benchmark_fit(
                        root,
                        variant,
                        family,
                        tr,
                        calibration,
                        design,
                        cfg["benchmark_frozen_settings"][source][family],
                    )
                    fit_status.append(result["status"])
                    js(output / "benchmark_status.json", fit_status)
                    if result["status"]["converged"]:
                        models.append((family + "_raw", result["model"], None))
                        if result["calibrator"] is not None:
                            models.append(
                                (family + "_calibrated", result["model"], result["calibrator"])
                            )
            for cohort, frame in cohorts.items():
                counts.extend(preprocessing_counts(design, frame, variant, cohort))
            for name, model, calibrator in models:

                def predict(frame, name=name, model=model, design=design, calibrator=calibrator):
                    if name.startswith("lightgbm"):
                        p = model.predict(design.tree(frame), num_threads=4)
                    elif name.startswith("elasticnet"):
                        p = model.predict_proba(design.transform(frame, reduced=True)[:, 1:])[:, 1]
                    else:
                        p = model.predict(design.transform(frame, reduced=True))
                    return calibrator.predict(p) if calibrator is not None else p

                train_p = predict(tr)
                for cohort, frame in cohorts.items():
                    cache = private / f"{variant}_{name}_{cohort}_evaluation.joblib"
                    if cache.exists():
                        score, bins, mean = joblib.load(cache)
                    else:
                        p = predict(frame)
                        # Training diagnostics are point-only. Validation uses unchanged conditional 999-draw inference.
                        draw_n = (
                            0
                            if cohort.startswith("training")
                            else cfg["evaluation"]["conditional_frozen_fit_state_cluster_draws"]
                        )
                        score, _ = evaluate(frame.Y, p, frame.ProjectState, draws=draw_n)
                        bins = calibration_bins(
                            train_p, frame.Y, p, frame.ProjectState, draws=draw_n
                        )
                        mean = {
                            "n": len(frame),
                            "events": int(frame.Y.sum()),
                            "mean_predicted": float(p.mean()),
                            "recorded_rate": float(frame.Y.mean()),
                            "start": str(frame.d.min().date()),
                            "end": str(frame.d.max().date()),
                        }
                        joblib.dump((score, bins, mean), cache)
                    meta = {
                        "variant": variant,
                        "model": name,
                        "cohort": cohort,
                        "outcome": cfg["outcome"],
                        "probabilities": "raw"
                        if name.endswith("raw")
                        else "2003H2 sigmoid calibrated"
                        if layer == "layer1"
                        else "2010 sigmoid calibrated",
                        "layer_interpretation": VALIDATION_LABEL
                        if layer == "layer2"
                        else "Approval-descriptor prediction",
                        "training_row_sha256": design.row_hash,
                    }
                    evaluation.extend([{**row, **meta} for row in score])
                    deciles.extend([{**row, **meta} for row in bins])
                    means.append({**mean, **meta})
                    print(variant, name, cohort, mean, flush=True)
                    table(root, "evaluation_metrics", evaluation)
                    table(root, "calibration_deciles", deciles)
                    table(root, "calibration_means", means)
                if layer == "layer2" and name.startswith("lightgbm"):
                    # Benchmark stress is point-only; no training-refit interval is assigned to a frozen tree.
                    for scenario_name, frame in analysis.scenario_frames().items():
                        p = predict(frame)
                        # Direct vector aggregation to avoid a fictitious coefficient fit.
                        for lgd_name in (
                            ["primary", "capped", "downturn"]
                            if scenario_name == "adverse"
                            else ["primary"]
                        ):
                            losses = np.where(
                                analysis.valid, p * analysis.severity[lgd_name] * analysis.ead, 0
                            )
                            g = np.where(analysis.valid, analysis.guarantee, 0)
                            for metric, values in [
                                ("pd", np.asarray(analysis.groups @ p).ravel() / analysis.counts),
                                ("expected_loss_usd", np.asarray(analysis.groups @ losses).ravel()),
                                (
                                    "sba_loss_usd",
                                    np.asarray(analysis.groups @ (losses * g)).ravel(),
                                ),
                                (
                                    "lender_loss_usd",
                                    np.asarray(analysis.groups @ (losses * (1 - g))).ravel(),
                                ),
                            ]:
                                for index, (group, group_value) in enumerate(analysis.names):
                                    from .bis_data import LOSS_LABEL

                                    stress.append(
                                        {
                                            "variant": variant,
                                            "model": name,
                                            "scenario": scenario_name,
                                            "lgd_variant": lgd_name,
                                            "group": group,
                                            "group_value": group_value,
                                            "metric": metric,
                                            "value": float(values[index]),
                                            "interval": "none: secondary fixed-tree point estimate",
                                            "loss_accounting": LOSS_LABEL,
                                            "layer_interpretation": VALIDATION_LABEL,
                                        }
                                    )
    table(root, "preprocessing_application_counts", counts)
    table(root, "benchmark_stress_point", stress)
    js(
        output / "benchmark_runtime.json",
        {
            "seconds": time.perf_counter() - tick,
            "peak_rss_GiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**3,
            "config_sha256": sha256(root / "config/g2_bis_2026-10-08.yaml"),
            "no_search_or_early_stopping": True,
            "training_diagnostics_intervals": "point only",
            "evaluation_intervals": "999 state-cluster draws conditional on frozen fitted models; distinct from 199 re-estimated Firth draws",
        },
    )


if __name__ == "__main__":
    run(Path.cwd())
