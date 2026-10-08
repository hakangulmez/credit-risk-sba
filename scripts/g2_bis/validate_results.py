"""Validate completed inference identities and frozen lineage, without estimation."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from credit_risk_sba.bis_data import LOSS_LABEL, NAME, js
from credit_risk_sba.bis_finalize import preservation
from credit_risk_sba.bis_runner import VARIANTS
from credit_risk_sba.io import sha256

root = Path.cwd()
out = root / "results" / NAME
attempts = pd.read_csv(out / "bootstrap_attempts.csv")
lineage = json.loads((out / "private_run_lineage.json").read_text())["scheduled_attempts"]
assert len(attempts) == len(VARIANTS) * 199 == len(lineage)
assert not attempts.duplicated(["variant", "attempt"]).any()
assert attempts.all_states_present_positive.all()
assert pd.read_csv(out / "unpenalized_valid_coefficients.csv").empty
config_hash = sha256(root / "config/g2_bis_2026-10-08.yaml")
weights_by_attempt = {}
checks = []
for variant in VARIANTS:
    rows = attempts.loc[attempts.variant.eq(variant)]
    assert sorted(rows.attempt) == list(range(1, 200))
    records = [r for r in lineage if r["variant"] == variant]
    success = []
    for record in records:
        path = root / record["relative_private_path"]
        assert sha256(path) == record["sha256"]
        assert record["config_sha256"] == config_hash
        assert record["preprocessing_sha256"] == sha256(out / f"{variant}_preprocessing.json")
        weights_by_attempt.setdefault(record["attempt"], set()).add(record["state_weight_sha256"])
        payload = joblib.load(path)
        assert payload["model"].diagnostics["converged"] == record["successful"]
        if record["successful"]:
            assert np.isfinite(payload["model"].beta).all()
            assert all(np.isfinite(r["value"]) for r in payload["average_associations"])
            if variant.startswith("layer2"):
                frame = pd.DataFrame(payload["stress"])
                assert np.isfinite(frame.value).all()
                assert frame.loss_accounting.eq(LOSS_LABEL).all()
                pivot = frame.pivot(
                    index=["scenario", "lgd_variant", "group", "group_value"],
                    columns="metric",
                    values="value",
                )
                direct = pivot.loc[
                    pivot.index.get_level_values("scenario") != "adverse_minus_baseline"
                ]
                np.testing.assert_allclose(
                    direct.expected_loss_usd,
                    direct.sba_loss_usd + direct.lender_loss_usd,
                    rtol=1e-12,
                    atol=1e-5,
                )
                for metric in [
                    "pd",
                    "expected_loss_usd",
                    "sba_loss_usd",
                    "lender_loss_usd",
                    "loss_rate",
                ]:
                    change = "pd_change_pp" if metric == "pd" else metric + "_change"
                    scale = 100 if metric == "pd" else 1
                    actual = pivot.xs(("adverse_minus_baseline", "primary"))[change]
                    expected = scale * (
                        pivot.xs(("adverse", "primary"))[metric]
                        - pivot.xs(("baseline", "primary"))[metric]
                    )
                    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-5)
            success.append(payload)
    coefficients = pd.read_csv(out / "firth_coefficients.csv")
    coefficients = coefficients.loc[coefficients.variant.eq(variant)]
    quantiles = np.quantile(
        np.stack([p["model"].beta for p in success]), [0.025, 0.975], axis=0, method="linear"
    )
    np.testing.assert_allclose(coefficients.lower, quantiles[0], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(coefficients.upper, quantiles[1], rtol=1e-12, atol=1e-12)
    for name in ["firth_coefficients", "firth_average_associations"] + (
        ["firth_macro_associations", "firth_stress"] if variant.startswith("layer2") else []
    ):
        frame = pd.read_csv(out / (name + ".csv"))
        frame = frame.loc[frame.variant.eq(variant)]
        assert frame.attempted_draws.eq(199).all()
        assert frame.effective_interval_draws.eq(len(success)).all()
        assert np.isfinite(frame[["value", "lower", "upper"]]).all().all()
    checks.append(
        {
            "variant": variant,
            "attempts": len(rows),
            "successful": len(success),
            "failed": len(rows) - len(success),
            "private_hashes_and_config_verified": True,
            "finite_draw_statistics_and_interval_denominators_verified": True,
            "paired_loss_and_allocation_verified": variant.startswith("layer2"),
        }
    )
assert all(len(hashes) == 1 for hashes in weights_by_attempt.values())
assert all(r["passed"] for r in preservation(root))
js(
    out / "statistical_completion_checks.json",
    {
        "checks": checks,
        "same_state_weights_across_all_models": True,
        "no_new_estimation": True,
        "validator_sha256": sha256(Path(__file__)),
    },
)
print(json.dumps(checks, indent=2))
