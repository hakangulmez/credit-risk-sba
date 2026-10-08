"""Small synthetic end-to-end check; no production data or API calls in CI."""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from credit_risk_sba.data import build
from credit_risk_sba.evaluation import evaluate_all
from credit_risk_sba.fitting import active_data, fit_all, predict
from credit_risk_sba.io import config, sha256, write_json
from credit_risk_sba.macro import crosswalk, join, load
from credit_risk_sba.plots import figures
from credit_risk_sba.reporting import summary
from credit_risk_sba.stress import secondary_tree_scenarios, stress_all


def synthetic_repo(root):
    (root / "docs").mkdir()
    (root / "config").mkdir()
    (root / "data/raw/macros").mkdir(parents=True)
    (root / "data/derived/g2-2026-10-08").mkdir(parents=True)
    original = Path(__file__).resolve().parents[1]
    shutil.copyfile(original / "docs/MACRO_SERIES.md", root / "docs/MACRO_SERIES.md")
    cfg = config(original)
    # Test fixture budget only; the production frozen YAML is neither touched nor inferred.
    cfg["bootstrap_draws"] = 9
    cfg["shap_max_rows"] = 50
    cfg["elasticnet"].update(c_count=2, c_max=1, l1_ratios=[0], max_iter=200)
    cfg["lightgbm"].update(trials=1, max_rounds=40, early_stopping=5, leaves=[15], min_child=[5], threads=1)
    (root / "config/g2.yaml").write_text(yaml.safe_dump(cfg))
    rng = np.random.default_rng(18)
    states = ["CA", "TX", "NY", "FL", "DC"]
    uframes, hframes = [], []
    for j, state in enumerate(states):
        m = np.arange(1990 * 12, 2017 * 12)
        uframes.append(pd.DataFrame({"state": state, "month": m,
                                    "u": 5 + j / 2 + np.sin(m / 20) + .002 * (m - m[0])}))
        q = np.arange(1980 * 4, 2020 * 4)
        hframes.append(pd.DataFrame({"state": state, "year": q // 4, "q": q % 4 + 1,
                                    "hpi": np.exp(.015 * (q - q[0]) + .1 * np.sin(q / 7))}))
    u = pd.concat(uframes)
    h = pd.concat(hframes)
    u.to_parquet(root / "data/raw/macros/unemployment.parquet", index=False)
    h.to_csv(root / "data/raw/macros/hpi_at_state.csv", index=False, header=False)
    records = []
    blocks = [(1200, 1991, 2002, 1), (300, 2003, 2003, 1), (300, 2003, 2003, 7),
              (300, 2006, 2006, 1), (400, 2007, 2009, 1), (300, 2011, 2013, 1)]
    for n, first, last, month in blocks:
        for i in range(n):
            year = first + i % (last - first + 1)
            d = pd.Timestamp(year, month, 15)
            approval = float(np.exp(rng.uniform(10, 14)))
            y = int(rng.random() < 1 / (1 + np.exp(4 - .3 * np.log(approval))))
            records.append({"AsOfDate": "2026-06-30", "Program": "7A", "GrossApproval": approval,
                "SBAGuaranteedApproval": .75 * approval, "ApprovalDate": str(d.date()), "FirstDisbursementDate": str(d.date()),
                "ProcessingMethod": "A" if i % 2 else "B", "InitialInterestRate": "", "FixedorVariableInterestInd": "",
                "TermInMonths": 60 + int(rng.integers(1, 240)), "NaicsCode": "541111", "FranchiseCode": "00000",
                "ProjectState": states[i % 5], "BusinessType": "CORPORATION", "BusinessAge": "Existing, 5 or more years old",
                "LoanStatus": "CHGOFF" if y else "EXEMPT", "PaidInFullDate": "",
                "ChargeOffDate": str((d + pd.DateOffset(months=12)).date()) if y else "",
                "GrossChargeOffAmount": .6 * approval if y else "", "RevolverStatus": "N" if i % 3 else "Y",
                "JobsSupported": int(rng.integers(0, 10))})
    path = root / "data/raw/synthetic.csv"
    pd.DataFrame(records).to_csv(path, index=False)
    write_json(root / "docs/g1_foia_manifest_2026-06-30.json", {"files": [{"relative_raw_path": "data/raw/synthetic.csv", "sha256": sha256(path)}]})
    (root / "docs/versions").mkdir()
    (root / "docs/PROTOCOL.md").write_text("Synthetic retained protocol")
    (root / "docs/versions/PROTOCOL_v1_2026-10-08.md").write_text("Synthetic retained protocol")
    write_json(root / "docs/gate1_review_evidence.json", {"original_tracked_file_sha256": {"docs/PROTOCOL.md": sha256(root / "docs/PROTOCOL.md")}})


def test_synthetic_frozen_pipeline(tmp_path):
    synthetic_repo(tmp_path)
    assert len(crosswalk(tmp_path)) == 51
    f = build(tmp_path, "2026-06-30")
    u, h = load(tmp_path)
    matched = join(f, u, h)
    matched.to_parquet(tmp_path / "data/derived/g2-2026-10-08/matched.parquet", index=False)
    assert len(active_data(tmp_path)) == len(f)
    fit_all(tmp_path)
    # Resume uses persisted model objects, not renewed tuning/model search.
    fit_all(tmp_path)
    evaluate_all(tmp_path)
    evaluate_all(tmp_path)  # Validated metric cache resumes without new bootstrap calculations.
    stress_all(tmp_path)
    secondary_tree_scenarios(tmp_path)
    figures(tmp_path)
    summary(tmp_path)
    assert (tmp_path / "docs/G2_REPORT_2026-10-08.md").is_file()
    assert len(list((tmp_path / "results/g2-2026-10-08/figures").glob("*.pdf"))) == 4
    results = tmp_path / "results/g2-2026-10-08"
    metrics = pd.read_csv(results / "evaluation_metrics.csv")
    assert set(metrics.role) == {"crisis", "oot"}
    assert metrics.bootstrap_draws.eq(9).all()
    stress = pd.read_csv(results / "stress_results.csv")
    assert set(stress.scenario) == {"baseline", "adverse", "adverse_minus_baseline"}
    assert stress.coefficient_draws.eq(9).all()
    assert stress.ead_definition.notna().all()
    lgd = pd.read_csv(results / "lgd_downturn.csv")
    assert lgd.cohorts.eq("1991,2000,2001").all()
    failed = {"status": {"converged": False}}
    with pytest.raises(ValueError):
        predict(failed, None, None, "logit")
    # Malformed primary input hash is rejected before preprocessing or fitting.
    manifest = json.loads((tmp_path / "docs/g1_foia_manifest_2026-06-30.json").read_text())
    manifest["files"][0]["sha256"] = "not_the_source_hash"
    write_json(tmp_path / "docs/g1_foia_manifest_2026-06-30.json", manifest)
    with pytest.raises(ValueError, match="hash mismatch"):
        build(tmp_path, "2026-06-30")
