"""Checkpointed fixed-budget estimation. Failed models remain failed."""
import time
from pathlib import Path

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits

from .data import CAT
from .features import Design
from .io import config, sha256, table, write_json
from .macro import MACRO, PEAK_MACRO
from .models import boosting, calibrate, elasticnet, fit_mle

VARIANTS = {
    "layer1": (False, []), "layer1_term": (True, []),
    "layer2": (False, MACRO + ["year_trend"]),
    "layer2_term": (True, MACRO + ["year_trend"]),
    "layer2_peak": (False, PEAK_MACRO + ["year_trend"]),
}


def active_data(root: Path):
    f = pd.read_parquet(root / "data/derived/g2-2026-10-08/matched.parquet")
    f = f.loc[f.role.isin(["train", "tune", "calibrate", "reference", "crisis", "oot"])].copy()
    complete = f[MACRO + ["peak_du"]].notna().all(axis=1)
    table(root, "macro_match_waterfall", f.assign(matched=complete).groupby("role").agg(
        eligible=("Y", "size"), macro_matched=("matched", "sum"), recorded_charge_offs_36m=("Y", "sum")
    ).reset_index())
    return f.loc[complete].reset_index(drop=True)


def fit_all(root: Path):
    cfg = config(root)
    f = active_data(root)
    train = f.loc[f.role.eq("train")]
    tune = f.loc[f.role.eq("tune")]
    calibration = f.loc[f.role.eq("calibrate")]
    private = root / "models/g2-2026-10-08"
    private.mkdir(parents=True, exist_ok=True)
    status = []
    witnesses = []
    for feature in CAT:
        for category, group in train.groupby(feature):
            cases = int(group.Y.sum())
            if cases == 0 or cases == len(group):
                witnesses.append({"feature": feature, "category": category, "n": len(group),
                   "recorded_charge_offs_36m": cases,
                   "diagnosis": "one-category quasi-separation witness; finite unpenalized MLE does not exist",
                   "action": "No category pooling, dropping, penalty, or specification replacement"})
    table(root, "separation_witnesses", witnesses)
    tick = time.perf_counter()
    with threadpool_limits(limits=cfg["lightgbm"]["threads"]):
        for variant, (term, macro) in VARIANTS.items():
            path = private / f"{variant}_design.joblib"
            design = Design.create(term, macro).fit(train)
            joblib.dump(design, path)
            write_json(private / f"{variant}_preprocessing.json", {
                "training_n": len(train), "train_id_sha256": __import__("hashlib").sha256(
                    "\n".join(train.row_id).encode()).hexdigest(),
                "numeric": design.numeric, "categorical": design.categorical,
                "names": design.names, "mle_omitted_train_constant_or_redundant": design.dropped,
                "config_sha256": sha256(root / "config/g2.yaml"),
            })
            for role in ["crisis", "oot", "reference"]:
                support = design.support(train, f.loc[f.role.eq(role)])
                for row in support:
                    row.update(variant=variant, role=role)
                table(root, f"support_{variant}_{role}", support)
        # Every unpenalized model is attempted before regularized tuning.
        for variant in VARIANTS:
            design = joblib.load(private / f"{variant}_design.joblib")
            path = private / f"{variant}_logit.joblib"
            if path.exists():
                bundle = joblib.load(path)
                if bundle.get("config_sha256") != sha256(root / "config/g2.yaml"):
                    raise ValueError("Frozen model checkpoint/config mismatch")
            else:
                model = fit_mle(design.transform(train, reduced=True), train.Y,
                                train.ProjectState, cfg["logit"])
                bundle = {"model": model, "status": model.diagnostics,
                          "config_sha256": sha256(root / "config/g2.yaml")}
                if model.diagnostics["converged"]:
                    bundle["calibrator"] = calibrate(calibration.Y, model.predict(
                        design.transform(calibration, reduced=True)))
                joblib.dump(bundle, path)
            bundle["status"]["categorical_quasi_separation_witness"] = bool(witnesses)
            status.append({"variant": variant, "family": "logit", **bundle["status"]})
            print(f"{variant} logit: {bundle['status']}", flush=True)
            table(root, "fit_status", status)
        for variant in ["layer1", "layer1_term", "layer2", "layer2_term"]:
            design = joblib.load(private / f"{variant}_design.joblib")
            families = ["elasticnet", "lightgbm"] if variant.startswith("layer1") else ["lightgbm"]
            for family in families:
                path = private / f"{variant}_{family}.joblib"
                if path.exists():
                    bundle = joblib.load(path)
                    if bundle.get("config_sha256") != sha256(root / "config/g2.yaml"):
                        raise ValueError("Frozen model checkpoint/config mismatch")
                else:
                    try:
                        if family == "elasticnet":
                            model, tuning = elasticnet(design.transform(train)[:, 1:], train.Y,
                                design.transform(tune)[:, 1:], tune.Y, cfg[family], cfg["seed"])
                            calibration_p = model.predict_proba(design.transform(calibration)[:, 1:])[:, 1]
                        else:
                            model, tuning = boosting(design.tree(train), train.Y, design.tree(tune),
                                                     tune.Y, cfg[family], cfg["seed"])
                            calibration_p = model.predict(design.tree(calibration))
                        table(root, f"tuning_{variant}_{family}", tuning)
                        sigmoid = calibrate(calibration.Y, calibration_p)
                        bundle = {"model": model, "calibrator": sigmoid,
                                  "status": {"converged": True, "n": len(train), "trials": len(tuning),
                                             "failed_trials": sum(not r.get("converged", True) for r in tuning)},
                                  "config_sha256": sha256(root / "config/g2.yaml")}
                    except (ValueError, RuntimeError) as exc:
                        bundle = {"status": {"converged": False, "message": str(exc)}}
                    joblib.dump(bundle, path)
                status.append({"variant": variant, "family": family, **bundle["status"]})
                table(root, "fit_status", status)
                print(f"Completed {variant} {family}: {bundle['status']}", flush=True)
    write_json(root / "results/g2-2026-10-08/fitting_runtime.json", {
        "seconds_this_execution": time.perf_counter() - tick,
        "models": len(status), "seed": cfg["seed"], "config_sha256": sha256(root / "config/g2.yaml"),
    })


def predict(bundle, design, frame, family):
    if not bundle["status"]["converged"]:
        raise ValueError("A failed fit cannot supply reported predictions")
    if family == "logit":
        return bundle["model"].predict(design.transform(frame, reduced=True))
    if family == "elasticnet":
        return bundle["model"].predict_proba(design.transform(frame)[:, 1:])[:, 1]
    if family == "lightgbm":
        return bundle["model"].predict(design.tree(frame))
    raise ValueError(f"Unknown family {family}")
