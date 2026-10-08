"""Resumable fixed 199-attempt inference; first five attempts are the pilot."""

import argparse
import hashlib
import json
import os
import resource
import subprocess
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from threadpoolctl import threadpool_limits

from .bis_analysis import FixedAnalysis, average_associations, support
from .bis_data import NAME, VALIDATION_LABEL, js, table
from .bis_design import PooledDesign
from .bis_firth import fit_firth, multiplier_weights, observation_weights
from .io import sha256
from .macro import MACRO, PEAK_MACRO
from .models import fit_mle

VARIANTS = {
    "layer1": (False, []),
    "layer1_term": (True, []),
    "layer2": (False, MACRO + ["year_trend"]),
    "layer2_term": (True, MACRO + ["year_trend"]),
    "layer2_peak": (False, PEAK_MACRO + ["year_trend"]),
}


def data(root):
    f = pd.read_parquet(root / "data" / NAME / "matched.parquet")
    f = f.loc[f.macro_complete].copy()
    reference = pd.read_parquet(root / "data" / NAME / "reference.parquet")
    scenario = pd.read_csv(root / "results" / NAME / "scenario_paths.csv")
    return f, reference, scenario


def training(f, variant):
    return (
        f.loc[f.year.between(1991, 2002 if variant.startswith("layer1") else 2009)]
        .assign(role="train")
        .reset_index(drop=True)
    )


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**3


def freeze_designs(root, f, cfg):
    private = root / "models" / NAME
    private.mkdir(parents=True, exist_ok=True)
    records = []
    separation = []
    levels, draws = multiplier_weights(
        f.loc[f.year.between(1991, 2009), "ProjectState"], cfg["bootstrap"]["attempts"], cfg["seed"]
    )
    table(
        root,
        "scheduled_state_multipliers",
        pd.DataFrame(draws, columns=levels).assign(attempt=np.arange(1, len(draws) + 1)),
    )
    for variant, (term, macro) in VARIANTS.items():
        tr = training(f, variant)
        path = private / (variant + "_design.joblib")
        if path.exists():
            design = joblib.load(path)
        else:
            design = PooledDesign(
                ["log_approval", "guarantee_share", "log_jobs"]
                + (["TermInMonths"] if term else [])
                + macro
            ).fit(tr)
            joblib.dump(design, path)
            contract = design.contract()
            contract.update(
                layer="layer1" if variant.startswith("layer1") else "layer2",
                variant=variant,
                config_sha256=sha256(root / "config/g2_bis_2026-10-08.yaml"),
                firth_source_sha256=sha256(root / "src/credit_risk_sba/bis_firth.py"),
                estimation_n=len(tr),
                events=int(tr.Y.sum()),
                non_events=int(len(tr) - tr.Y.sum()),
                states=len(tr.ProjectState.unique()),
                layer_interpretation=VALIDATION_LABEL
                if variant.startswith("layer2")
                else "Approval-descriptor prediction",
            )
            js(root / "results" / NAME / (variant + "_preprocessing.json"), contract)
            table(root, variant + "_original_to_pooled_levels", design.map_records)
            table(root, variant + "_pooled_level_counts", design.level_records)
        contract = json.loads(
            (root / "results" / NAME / (variant + "_preprocessing.json")).read_text()
        )
        if contract["config_sha256"] != sha256(root / "config/g2_bis_2026-10-08.yaml") or contract[
            "firth_source_sha256"
        ] != sha256(root / "src/credit_risk_sba/bis_firth.py"):
            raise ValueError("Frozen preprocessing/source mismatch")
        records.append(
            {
                "variant": variant,
                "n": len(tr),
                "events": int(tr.Y.sum()),
                "full_columns": len(design.names),
                "rank": len(design.keep),
                "states": len(tr.ProjectState.unique()),
                "state_dummy_columns": sum(
                    str(design.names[i]).startswith("ProjectState_") for i in design.keep
                ),
                "dropped": " | ".join(design.dropped),
                "preprocessing_sha256": sha256(
                    root / "results" / NAME / (variant + "_preprocessing.json")
                ),
            }
        )
        bad = design.level_records.loc[
            design.level_records.events.eq(0) | design.level_records.non_events.eq(0)
        ].copy()
        bad["variant"] = variant
        separation.extend(bad.to_dict("records"))
    table(root, "design_rank_checks", records)
    table(
        root,
        "post_pooling_separation_witnesses",
        pd.DataFrame(
            separation, columns=["variant", "feature", "level", "n", "events", "non_events"]
        ),
    )
    return levels, draws


def run(root, pilot=False):
    cfg = yaml.safe_load((root / "config/g2_bis_2026-10-08.yaml").read_text())
    f, reference, scenario = data(root)
    levels, draws = freeze_designs(root, f, cfg)
    private = root / "models" / NAME
    analysis = FixedAnalysis(root, training(f, "layer1"), reference, scenario)
    statuses = []
    runtime = []
    started = time.perf_counter()
    limit = 5 if pilot else cfg["bootstrap"]["attempts"]
    point_status = []
    subprocess.Popen(
        ["caffeinate", "-dimsu", "-w", str(os.getpid())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    support_rows = []
    support_summary = []
    with threadpool_limits(limits=cfg["firth"]["threads"]):
        for variant in VARIANTS:
            tr = training(f, variant)
            design = joblib.load(private / (variant + "_design.joblib"))
            x = design.transform(tr, reduced=True)
            pointpath = private / (variant + "_firth_point.joblib")
            mlepath = private / (variant + "_mle.joblib")
            if pointpath.exists():
                point = joblib.load(pointpath)
            else:
                point = fit_firth(x, tr.Y, settings=cfg["firth"])
                joblib.dump(point, pointpath)
            point_status.append(
                {
                    "variant": variant,
                    "family": "Firth primary"
                    if not variant.endswith("term")
                    else "Firth with-Term sensitivity",
                    **point.diagnostics,
                    "peak_rss_GiB": rss(),
                }
            )
            print(variant, "unit Firth", point.diagnostics, "RSS", rss(), flush=True)
            if mlepath.exists():
                mle = joblib.load(mlepath)
            else:
                mle = fit_mle(x, tr.Y, tr.ProjectState, cfg["unpenalized"])
                joblib.dump(mle, mlepath)
            point_status.append(
                {
                    "variant": variant,
                    "family": "unpenalized same-design comparator",
                    **mle.diagnostics,
                    "valid_estimate": mle.diagnostics["converged"],
                }
            )
            table(root, "fit_status", point_status)
            if variant.startswith("layer2"):
                a, b = support(root, variant, tr, design, analysis)
                support_rows.extend(a)
                support_summary.extend(b)
            role_frame = tr if variant.startswith("layer1") else reference
            drawtimes = []
            for attempt in range(limit):
                if pilot and (
                    time.perf_counter() - started > cfg["pilot"]["timing_bound_seconds"]
                    or rss() > cfg["pilot"]["memory_limit_GiB"]
                ):
                    js(
                        root / "results" / NAME / "pilot_runtime.json",
                        {
                            "complete": False,
                            "reason": "predeclared timing/memory bound reached",
                            "seconds": time.perf_counter() - started,
                            "peak_rss_GiB": rss(),
                            "no_budget_change": True,
                        },
                    )
                    return
                target = private / f"{variant}_draw_{attempt + 1:03}.joblib"
                if target.exists():
                    payload = joblib.load(target)
                else:
                    t = time.perf_counter()
                    w = observation_weights(tr.ProjectState.to_numpy(), levels, draws[attempt])
                    model = fit_firth(
                        x,
                        tr.Y,
                        w,
                        cfg["firth"],
                        point.beta if point.diagnostics["converged"] else None,
                    )
                    payload = {
                        "attempt": attempt + 1,
                        "variant": variant,
                        "model": model,
                        "config_sha256": sha256(root / "config/g2_bis_2026-10-08.yaml"),
                        "preprocessing_sha256": sha256(
                            root / "results" / NAME / (variant + "_preprocessing.json")
                        ),
                        "state_weight_sha256": hashlib.sha256(draws[attempt].tobytes()).hexdigest(),
                        "weight_sum": float(w.sum()),
                        "all_states_present_positive": bool((w > 0).all()),
                    }
                    if model.diagnostics["converged"]:
                        payload["average_associations"] = average_associations(
                            design, model.beta, role_frame
                        )
                        if variant.startswith("layer2"):
                            payload["stress"] = analysis.evaluate(design, model.beta)
                            payload["macro_associations"] = analysis.macro_associations(
                                design, model.beta, variant.endswith("peak")
                            )
                    payload["total_seconds"] = time.perf_counter() - t
                    joblib.dump(payload, target)
                if payload["config_sha256"] != sha256(
                    root / "config/g2_bis_2026-10-08.yaml"
                ) or payload["preprocessing_sha256"] != sha256(
                    root / "results" / NAME / (variant + "_preprocessing.json")
                ):
                    raise ValueError("Draw checkpoint mismatch")
                row = {
                    "variant": variant,
                    "attempt": attempt + 1,
                    **payload["model"].diagnostics,
                    "total_seconds": payload["total_seconds"],
                    "peak_rss_GiB": rss(),
                    "all_states_present_positive": payload["all_states_present_positive"],
                }
                statuses.append(row)
                drawtimes.append(payload["total_seconds"])
                table(root, "bootstrap_attempts", statuses)
                if attempt < 5 or (attempt + 1) % 10 == 0:
                    print(
                        variant,
                        "attempt",
                        attempt + 1,
                        "successful",
                        payload["model"].diagnostics["converged"],
                        "seconds",
                        payload["total_seconds"],
                        flush=True,
                    )
            runtime.append(
                {
                    "variant": variant,
                    "attempts_completed": limit,
                    "unit_fit_seconds": point.diagnostics["seconds"],
                    "mean_draw_total_seconds": float(np.mean(drawtimes)),
                    "projected_remaining_draw_seconds": float(
                        np.mean(drawtimes) * max(199 - limit, 0)
                    ),
                }
            )
    table(root, "scenario_support_by_feature", support_rows)
    table(root, "scenario_support_summary", support_summary)
    js(
        root / "results" / NAME / ("pilot_runtime.json" if pilot else "bootstrap_runtime.json"),
        {
            "complete": True,
            "seconds_this_execution": time.perf_counter() - started,
            "peak_rss_GiB": rss(),
            "pid": os.getpid(),
            "caffeinate": True,
            "attempts_per_model": limit,
            "models": runtime,
            "projected_remaining_seconds": sum(
                r["projected_remaining_draw_seconds"] for r in runtime
            ),
            "draws_remain_part_of_199": True,
            "source_protocol_commit": "1d39a458ee1bbd0e1604a5b78a2e6f8372fb1c53",
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    run(Path.cwd(), args.pilot)


if __name__ == "__main__":
    main()
