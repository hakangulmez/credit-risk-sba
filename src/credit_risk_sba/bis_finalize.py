"""Aggregate scheduled fits without treating failed draws as zero-valued estimates."""

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

from .bis_analysis import FixedAnalysis, average_associations
from .bis_data import NAME, VALIDATION_LABEL, js, table
from .bis_runner import VARIANTS, data, training
from .io import sha256

INTERVAL = "95% percentile, positive state-weighted multiplier bootstrap; Firth re-estimated; fixed preprocessing/LGD/portfolio/scenarios"


def interval(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    lower, upper = (
        np.quantile(finite, [0.025, 0.975], method="linear")
        if len(finite) >= 2
        else (np.nan, np.nan)
    )
    return {"lower": float(lower), "upper": float(upper), "effective_interval_draws": len(finite)}


def combine(point, draws, keys, variant):
    """Require unique keys and complete corresponding statistics before intervals."""
    frame = pd.DataFrame(point)
    if frame.duplicated(keys).any():
        raise ValueError("Duplicate point-statistic identity")
    samples = []
    for rows in draws:
        sample = pd.DataFrame(rows)
        if sample.duplicated(keys).any() or set(map(tuple, sample[keys].to_numpy())) != set(
            map(tuple, frame[keys].to_numpy())
        ):
            raise ValueError("Draw and point statistic identities differ")
        samples.append(sample.set_index(keys).value.to_dict())
    joined = frame.set_index(keys)
    result = []
    for key, row in joined.iterrows():
        values = [s[key] for s in samples]
        record = row.to_dict()
        record.update(dict(zip(keys, key if isinstance(key, tuple) else (key,), strict=True)))
        record.update(interval(values))
        record.update(
            variant=variant,
            attempted_draws=199,
            successful_model_draws=len(draws),
            interval=INTERVAL,
            outcome="recorded charge-off within 36 months",
            layer_interpretation=VALIDATION_LABEL
            if variant.startswith("layer2")
            else "Approval-descriptor prediction",
        )
        result.append(record)
    return result


def aggregate(root):
    cfg = yaml.safe_load((root / "config/g2_bis_2026-10-08.yaml").read_text())
    f, reference, scenario = data(root)
    analysis = FixedAnalysis(root, training(f, "layer1"), reference, scenario)
    private = root / "models" / NAME
    schedules = pd.read_csv(root / "results" / NAME / "scheduled_state_multipliers.csv")
    coef, ordinary, associations, macro, stress, summary, manifests = [], [], [], [], [], [], []
    for variant in VARIANTS:
        design = joblib.load(private / f"{variant}_design.joblib")
        point = joblib.load(private / f"{variant}_firth_point.joblib")
        names = np.asarray(design.names)[design.keep]
        estimation_n = len(training(f, variant))
        valid = []
        failures = []
        for attempt in range(1, cfg["bootstrap"]["attempts"] + 1):
            path = private / f"{variant}_draw_{attempt:03}.joblib"
            if not path.exists():
                raise ValueError(f"Missing scheduled attempt: {variant} {attempt}")
            payload = joblib.load(path)
            raw = schedules.drop(columns="attempt").iloc[attempt - 1].to_numpy(dtype=float)
            # CSV decimals may round at the last bit; compare regenerated RNG below, not CSV byte hashes.
            rng_draw = np.random.default_rng(cfg["seed"]).exponential(1.0, (199, len(raw)))[
                attempt - 1
            ]
            if payload["state_weight_sha256"] != hashlib.sha256(rng_draw.tobytes()).hexdigest():
                raise ValueError("Scheduled state weights changed")
            if payload["attempt"] != attempt or not payload["all_states_present_positive"]:
                raise ValueError("Attempt identity/positive states invalid")
            if not np.isclose(payload["weight_sum"], estimation_n, rtol=1e-12):
                raise ValueError("Weight normalization invalid")
            manifests.append(
                {
                    "variant": variant,
                    "attempt": attempt,
                    "relative_private_path": str(path.relative_to(root)),
                    "sha256": sha256(path),
                    "config_sha256": payload["config_sha256"],
                    "preprocessing_sha256": payload["preprocessing_sha256"],
                    "state_weight_sha256": payload["state_weight_sha256"],
                    "successful": payload["model"].diagnostics["converged"],
                }
            )
            if payload["model"].diagnostics["converged"]:
                valid.append(payload)
            else:
                failures.append({"attempt": attempt, **payload["model"].diagnostics})
        summary.append(
            {
                "variant": variant,
                "attempted": 199,
                "successful": len(valid),
                "failed": len(failures),
                "failure_reasons": dict(
                    pd.Series([x["message"] for x in failures], dtype=str).value_counts()
                ),
                "point_converged": point.diagnostics["converged"],
            }
        )
        if not point.diagnostics["converged"]:
            continue
        for j, name in enumerate(names):
            coef.append(
                {
                    "variant": variant,
                    "coefficient": name,
                    "value": float(point.beta[j]),
                    **interval([x["model"].beta[j] for x in valid]),
                    "attempted_draws": 199,
                    "successful_model_draws": len(valid),
                    "interval": INTERVAL,
                    "units": "log odds; numeric coefficients on train-standardized feature scale; categorical versus stated training reference",
                    "outcome": cfg["outcome"],
                    "layer_interpretation": VALIDATION_LABEL
                    if variant.startswith("layer2")
                    else "Approval-descriptor prediction",
                }
            )
        role = training(f, variant) if variant.startswith("layer1") else reference
        associations.extend(
            combine(
                average_associations(design, point.beta, role),
                [x["average_associations"] for x in valid],
                ["feature", "contrast"],
                variant,
            )
        )
        mle = joblib.load(private / f"{variant}_mle.joblib")
        if mle.diagnostics["converged"]:
            for j, name in enumerate(names):
                se = np.sqrt(mle.covariance[j, j])
                ordinary.append(
                    {
                        "variant": variant,
                        "coefficient": name,
                        "value": float(mle.beta[j]),
                        "se": float(se),
                        "lower": float(mle.beta[j] - 1.96 * se),
                        "upper": float(mle.beta[j] + 1.96 * se),
                        "interval": "same-design unpenalized logit state-cluster sandwich normal interval; not Firth multiplier interval",
                    }
                )
        if variant.startswith("layer2"):
            stress.extend(
                combine(
                    analysis.evaluate(design, point.beta),
                    [x["stress"] for x in valid],
                    ["scenario", "lgd_variant", "group", "group_value", "metric"],
                    variant,
                )
            )
            macro.extend(
                combine(
                    analysis.macro_associations(design, point.beta, variant.endswith("peak")),
                    [x["macro_associations"] for x in valid],
                    ["feature", "group", "group_value"],
                    variant,
                )
            )
    table(root, "firth_coefficients", coef)
    table(
        root,
        "unpenalized_valid_coefficients",
        pd.DataFrame(
            ordinary,
            columns=["variant", "coefficient", "value", "se", "lower", "upper", "interval"],
        ),
    )
    table(root, "firth_average_associations", associations)
    table(root, "firth_macro_associations", macro)
    table(root, "firth_stress", stress)
    js(root / "results" / NAME / "bootstrap_summary.json", summary)
    js(
        root / "results" / NAME / "private_run_lineage.json",
        {"raw_private_files_not_committed": True, "scheduled_attempts": manifests},
    )


def label_outputs(root):
    """Apply interpretation metadata to every layer-specific aggregate table."""
    for path in sorted((root / "results" / NAME).glob("*.csv")):
        frame = pd.read_csv(path)
        scenario_output = path.name in {
            "firth_stress.csv",
            "benchmark_stress_point.csv",
            "portfolio_allocation_70pct.csv",
            "scenario_support_summary.csv",
            "scenario_support_by_feature.csv",
            "scenario_paths.csv",
        }
        if scenario_output:
            frame["macro_information_context"] = (
                "Stipulated baseline/adverse paths; fixed 2006 scenario portfolio; "
                "not out-of-sample realized-path validation"
            )
        elif path.name == "firth_macro_associations.csv":
            frame["macro_information_context"] = (
                "Fixed 2006 observed macro reference with +1 pp conditional contrast; "
                "not an approval-time forecast or causal effect"
            )
        if "variant" in frame:
            names = frame.variant.astype(str)
            frame["specification_role"] = np.select(
                [names.str.endswith("_term"), names.str.endswith("_peak")],
                [
                    "With-Term sensitivity; reported-term timing unverified",
                    "Term-free peak-unemployment sensitivity",
                ],
                default="Term-free primary specification",
            )
            layer2 = frame.variant.astype(str).str.startswith("layer2")
            frame["layer_interpretation"] = np.where(
                layer2, VALIDATION_LABEL, "Approval-descriptor prediction"
            )
        elif path.name.startswith("layer2"):
            frame["layer_interpretation"] = VALIDATION_LABEL
        elif "layer" in frame:
            layer2 = frame.layer.astype(str).eq("layer2")
            frame["layer_interpretation"] = np.where(
                layer2,
                VALIDATION_LABEL,
                frame.get("interpretation", "Layer 1 / fixed portfolio accounting"),
            )
        elif not scenario_output:
            continue
        frame.to_csv(path, index=False)


def preservation(root):
    ledger = json.loads((root / "docs/G2_FROZEN_HASHES_2026-10-08.json").read_text())
    checks = []
    for scope in ["public", "private"]:
        for path, expected in ledger[scope].items():
            actual = root / path
            if path == "DECISIONS.md":
                old = root / "docs/versions/DECISIONS_G2_2026-10-08.md"
                passed = sha256(old) == expected and actual.read_bytes().startswith(
                    old.read_bytes()
                )
                action = "original exact bytes retained; new dated decision appended"
            else:
                passed = actual.exists() and sha256(actual) == expected
                action = "unchanged"
            checks.append(
                {
                    "scope": scope,
                    "path": path,
                    "expected_sha256": expected,
                    "current_sha256": sha256(actual) if actual.exists() else None,
                    "passed": passed,
                    "action": action,
                }
            )
    table(root, "preservation_checks", checks)
    if not all(x["passed"] for x in checks):
        raise ValueError("Frozen G2 preservation failure")
    return checks


if __name__ == "__main__":
    aggregate(Path.cwd())
    label_outputs(Path.cwd())
    preservation(Path.cwd())
