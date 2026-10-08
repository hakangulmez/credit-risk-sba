"""Small synthetic G2-bis integration; production specifications are never changed."""

import hashlib
import json
import shutil
from pathlib import Path

import joblib
import pandas as pd
import pytest
import yaml
from test_pipeline import synthetic_repo

from credit_risk_sba import bis_data
from credit_risk_sba.bis_analysis import FixedAnalysis
from credit_risk_sba.bis_benchmarks import run as benchmarks
from credit_risk_sba.bis_data import NAME
from credit_risk_sba.bis_diagnostics import run as diagnostics
from credit_risk_sba.bis_finalize import aggregate, preservation
from credit_risk_sba.bis_runner import data, run, training
from credit_risk_sba.bis_term import run as audit_terms
from credit_risk_sba.data import build
from credit_risk_sba.io import sha256
from credit_risk_sba.losses import lgd_tables
from credit_risk_sba.macro import load, scenarios


def setup(tmp_path, monkeypatch):
    synthetic_repo(tmp_path)
    original = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((original / "config/g2_bis_2026-10-08.yaml").read_text())
    # Fixed small synthetic budgets are solely test fixtures; no empirical configuration is altered.
    for source in cfg["benchmark_frozen_settings"].values():
        source["elasticnet"]["settings"].update(max_iter=500, tol=0.001)
        source["lightgbm"]["settings"]["num_boost_round"] = 10
        source["lightgbm"]["settings"]["parameters"].update(num_threads=1, min_data_in_leaf=10)
    cfg["evaluation"]["conditional_frozen_fit_state_cluster_draws"] = 9
    (tmp_path / "config/g2_bis_2026-10-08.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "src/credit_risk_sba").mkdir(parents=True)
    shutil.copyfile(
        original / "src/credit_risk_sba/bis_firth.py", tmp_path / "src/credit_risk_sba/bis_firth.py"
    )
    f = build(tmp_path, "2026-06-30")
    additions = []
    # Calibration and check cohorts absent from the original synthetic fixture are created explicitly.
    for year in [2010, 2014]:
        g = f.loc[f.year.eq(2003)].iloc[:160].copy()
        offset = pd.DateOffset(years=year - 2003)
        for col in [
            "d",
            "w",
            "ApprovalDate",
            "FirstDisbursementDate",
            "ChargeOffDate",
            "PaidInFullDate",
        ]:
            g[col] = g[col] + offset
        g["row_id"] += f"added{year}"
        g["year"] = year
        g["year_trend"] = year - 2000
        additions.append(g)
    # New row identities belong only to derived synthetic data; term audit gets the original fixture separately.
    f = pd.concat([f, *additions], ignore_index=True)
    f.to_parquet(tmp_path / "data/derived/g2-2026-10-08/eligible.parquet", index=False)
    u, h = load(tmp_path)
    tail = u.loc[u.month.between(2014 * 12, 2016 * 12 + 11)].copy()
    tail["month"] += 36
    u = pd.concat([u, tail], ignore_index=True)
    monkeypatch.setattr(bis_data, "macros", lambda root: (u, h))
    scenario = scenarios(u, h)
    results = tmp_path / "results/g2-2026-10-08"
    results.mkdir(parents=True, exist_ok=True)
    scenario.to_csv(results / "scenario_macro_inputs.csv", index=False)
    f.to_parquet(tmp_path / "data/derived/g2-2026-10-08/matched.parquet", index=False)
    tr = f.loc[f.year.between(1991, 2002)]
    for name, down, cap in [
        ("primary", False, False),
        ("capped", False, True),
        ("downturn", True, False),
    ]:
        lgd_tables(tr, down, cap)[0].to_csv(results / f"lgd_{name}.csv", index=False)
    return f, u, h


def test_small_bis_pipeline_resume_and_labels(tmp_path, monkeypatch):
    f, _, _ = setup(tmp_path, monkeypatch)
    bis_data.prepare(tmp_path)
    run(tmp_path, pilot=True)
    initial = {p.name: sha256(p) for p in (tmp_path / "models" / NAME).glob("*draw*.joblib")}
    assert len(initial) == 25
    run(tmp_path, pilot=True)
    assert initial == {
        p.name: sha256(p) for p in (tmp_path / "models" / NAME).glob("*draw*.joblib")
    }
    rank = pd.read_csv(tmp_path / "results" / NAME / "design_rank_checks.csv")
    assert rank.state_dummy_columns.eq(4).all()
    frame, ref, scenario = data(tmp_path)
    assert training(frame, "layer2").year.max() == 2009
    assert training(frame, "layer1").year.max() == 2002
    # Trees use the fixed rounds and only the predeclared calibration cohorts.
    benchmarks(tmp_path)
    fit = json.loads((tmp_path / "results" / NAME / "benchmark_status.json").read_text())
    assert all(
        r["calibration_start"].startswith("2010") for r in fit if r["variant"].startswith("layer2")
    )
    assert all(
        r["calibration_start"].startswith("2003") for r in fit if r["variant"].startswith("layer1")
    )
    assert all(r["iterations_or_rounds"] == 10 for r in fit if r["family"] == "lightgbm")
    diagnostics(tmp_path)
    checked = pd.read_csv(tmp_path / "results" / NAME / "evaluation_metrics.csv")
    assert (
        checked.loc[checked.variant.str.startswith("layer2"), "layer_interpretation"]
        .eq(bis_data.VALIDATION_LABEL)
        .all()
    )
    assert checked.loc[checked.model.eq("firth_raw"), "probabilities"].eq("raw").all()
    pdtest = pd.read_csv(tmp_path / "results" / NAME / "portfolio_allocation_70pct.csv")
    assert pdtest.loss_accounting.eq(bis_data.LOSS_LABEL).all()
    a = FixedAnalysis(tmp_path, training(frame, "layer1"), ref, scenario)
    model = joblib.load(tmp_path / "models" / NAME / "layer2_firth_point.joblib")
    assert model.diagnostics["converged"]
    design = joblib.load(tmp_path / "models" / NAME / "layer2_design.joblib")
    assert len(a.evaluate(design, model.beta)) > 0
    # An incomplete inference run cannot masquerade as 199 attempted draws.
    with pytest.raises(ValueError, match="Missing scheduled attempt"):
        aggregate(tmp_path)
    # Complete the fixed scheduled attempts on tiny synthetic inputs and exercise aggregation.
    run(tmp_path)
    aggregate(tmp_path)
    summary = json.loads((tmp_path / "results" / NAME / "bootstrap_summary.json").read_text())
    assert all(r["attempted"] == 199 and r["successful"] + r["failed"] == 199 for r in summary)
    result = pd.read_csv(tmp_path / "results" / NAME / "firth_stress.csv")
    assert result.attempted_draws.eq(199).all()
    assert result.loss_accounting.eq(bis_data.LOSS_LABEL).all()
    assert (result.effective_interval_draws <= result.successful_model_draws).all()
    assert initial == {
        p.name: sha256(p) for p in (tmp_path / "models" / NAME).glob("*draw_00[1-5].joblib")
    }
    # Recover the exact original synthetic population for the read-only term source audit.
    f.loc[~f.row_id.str.contains("added")].to_parquet(
        tmp_path / "data/derived/g2-2026-10-08/eligible.parquet", index=False
    )
    audit_terms(tmp_path)
    assert (tmp_path / "results" / NAME / "term_audit_summary.csv").exists()


def test_preservation_checks_exact_versions_and_unchanged_private(tmp_path):
    (tmp_path / "docs/versions").mkdir(parents=True)
    (tmp_path / "docs/PROTOCOL.md").write_text("original protocol\n")
    (tmp_path / "DECISIONS.md").write_text("original decision\nnew appendix\n")
    (tmp_path / "docs/versions/DECISIONS_G2_2026-10-08.md").write_text("original decision\n")
    (tmp_path / "private").write_text("private original")
    hash_original = hashlib.sha256(b"original decision\n").hexdigest()
    ledger = {
        "public": {
            "docs/PROTOCOL.md": sha256(tmp_path / "docs/PROTOCOL.md"),
            "DECISIONS.md": hash_original,
        },
        "private": {"private": sha256(tmp_path / "private")},
    }
    (tmp_path / "docs/G2_FROZEN_HASHES_2026-10-08.json").write_text(json.dumps(ledger))
    assert all(r["passed"] for r in preservation(tmp_path))
    (tmp_path / "private").write_text("changed")
    with pytest.raises(ValueError, match="preservation"):
        preservation(tmp_path)
