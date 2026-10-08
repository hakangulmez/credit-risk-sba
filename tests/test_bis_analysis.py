"""Statistical identities for fixed loss accounting, associations and intervals."""

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from test_bis_design import fixture

from credit_risk_sba.bis_analysis import FixedAnalysis, average_associations, support
from credit_risk_sba.bis_data import LOSS_LABEL, VALIDATION_LABEL
from credit_risk_sba.bis_design import PooledDesign
from credit_risk_sba.bis_finalize import combine, interval
from credit_risk_sba.bis_term import audit_frame, classify, summaries


def test_associations_match_derivative_and_reference_contrasts():
    f = fixture()
    d = PooledDesign(["x"]).fit(f)
    b = np.linspace(-0.7, 0.4, len(d.keep))
    rows = pd.DataFrame(average_associations(d, b, f))
    x = d.transform(f, reduced=True)
    shifted = f.assign(x=f.x + 1e-5)
    derivative = 100 * np.mean(
        (expit(d.transform(shifted, reduced=True) @ b) - expit(x @ b)) / 1e-5
    )
    assert rows.loc[rows.feature.eq("x"), "value"].iloc[0] == pytest.approx(derivative, rel=1e-5)
    reference_state = d.encoder.categories_[-1][0]
    for state in d.encoder.categories_[-1][1:]:
        delta = (
            100
            * (
                expit(d.transform(f.assign(ProjectState=state), reduced=True) @ b)
                - expit(d.transform(f.assign(ProjectState=reference_state), reduced=True) @ b)
            ).mean()
        )
        assert rows.loc[rows.feature.eq("ProjectState_" + state), "value"].iloc[0] == pytest.approx(
            delta
        )


def test_percentiles_use_successful_defined_values_and_require_two():
    assert interval([1, 2, np.nan]) == {
        "lower": 1.025,
        "upper": 1.975,
        "effective_interval_draws": 2,
    }
    assert np.isnan(interval([2])["lower"])
    point = [{"scenario": "base", "value": 2}, {"scenario": "adverse", "value": 3}]
    draws = [
        [{"scenario": "adverse", "value": 4}, {"scenario": "base", "value": 1}],
        [{"scenario": "base", "value": 3}, {"scenario": "adverse", "value": 6}],
    ]
    out = combine(point, draws, ["scenario"], "layer2")
    assert out[0]["effective_interval_draws"] == 2 and out[0]["lower"] == pytest.approx(1.05)
    assert out[0]["layer_interpretation"] == VALIDATION_LABEL
    with pytest.raises(ValueError, match="identities"):
        combine(point, [[{"scenario": "base", "value": 1}]], ["scenario"], "layer2")
    with pytest.raises(ValueError, match="Duplicate"):
        combine(point + point, draws, ["scenario"], "layer1")


def test_term_audit_includes_later_events_and_never_verifies_low_match():
    dates = pd.to_datetime(["2000-01-01"] * 105)
    frame = pd.DataFrame(
        {
            "row_id": np.arange(105).astype(str),
            "LoanStatus": ["CHGOFF"] * 100 + ["PIF"] * 5,
            "d": dates,
            "w": dates + pd.DateOffset(months=36),
            "ChargeOffDate": dates + pd.DateOffset(months=60),
            "PaidInFullDate": dates + pd.DateOffset(months=60),
            "ApprovalDate": dates,
            "loan_type": "term",
        }
    )
    terms = pd.Series(["60"] * 101 + ["", "garbage", "0", "-1"], index=frame.row_id)
    audit = audit_frame(frame, terms)
    assert audit.charge_off_after_label_window.sum() == 100
    assert audit.valid.sum() == 101
    assert audit.term_status.value_counts().to_dict() == {"valid": 101, "invalid": 3, "missing": 1}
    assert classify(audit) == "Strong evidence of later updating."
    assert classify(audit, metadata_verified=True) == "Verified as an approval-time value."
    assert classify(audit.assign(match=False)) == "Timing unverifiable."
    rows = summaries(audit)
    assert rows[0]["match_abs_le_3_n"] == 101 and rows[0]["valid_n"] == 101
    assert rows[1]["charge_off_after_label_window_n"] == 100
    empty = audit.assign(valid=False, match=False)
    assert np.isnan(summaries(empty)[0]["difference_mean"])


def test_macro_association_and_loss_pairs_reconcile(tmp_path):
    # FixedAnalysis is fitted in the integration test; use its existing algebra on a small fixed portfolio.
    from scipy import sparse

    a = FixedAnalysis.__new__(FixedAnalysis)
    ref = fixture().iloc[:6].copy()
    ref["GrossApproval"] = np.arange(1, 7) * 1000.0
    ref["du"] = np.linspace(-1, 1, 6)
    ref["peak_du"] = np.linspace(0, 2, 6)
    a.reference = ref
    a.names = [("overall", "all"), ("type", "sub")]
    a.groups = sparse.csr_matrix(np.array([[1] * 6, [1, 1, 1, 0, 0, 0]], dtype=float))
    a.counts = np.array([6, 3])
    a.ead = ref.GrossApproval.to_numpy()
    a.guarantee = np.full(6, 0.75)
    a.valid = np.ones(6, dtype=bool)
    a.exposures = a.groups @ a.ead
    a.valid_counts = a.counts
    a.severity = {
        "primary": np.full(6, 0.6),
        "downturn": np.full(6, 0.7),
        "capped": np.full(6, 0.5),
    }
    a.scenario_frames = lambda: {"baseline": ref.assign(du=0), "adverse": ref.assign(du=1)}
    train = fixture().assign(du=2 * np.sin(np.arange(3000)))
    design = PooledDesign(["x", "du"]).fit(train)
    beta = np.zeros(len(design.keep))
    beta[0] = -2
    pos = list(np.array(design.names)[design.keep]).index("du")
    beta[pos] = 0.4
    out = pd.DataFrame(a.evaluate(design, beta))
    base = out.loc[out.scenario.eq("baseline") & out.group.eq("overall")].set_index("metric").value
    adv = (
        out.loc[
            out.scenario.eq("adverse") & out.lgd_variant.eq("primary") & out.group.eq("overall")
        ]
        .set_index("metric")
        .value
    )
    delta = (
        out.loc[out.scenario.eq("adverse_minus_baseline") & out.group.eq("overall")]
        .set_index("metric")
        .value
    )
    assert base.expected_loss_usd == pytest.approx(base.sba_loss_usd + base.lender_loss_usd)
    assert delta.expected_loss_usd_change == pytest.approx(
        adv.expected_loss_usd - base.expected_loss_usd
    )
    assert delta.pd_change_pp == pytest.approx(100 * (adv.pd - base.pd))
    assert out.loss_accounting.eq(LOSS_LABEL).all()
    mac = a.macro_associations(design, beta)
    assert mac[0]["value"] > 0
    with pytest.raises(ValueError, match="not identifiable"):
        a.macro_associations(design, beta, peak=True)
    perfeature, union = support(tmp_path, "layer2", train, design, a)
    assert {r["scope"] for r in union} == {"state_specific", "pooled_global"}
    assert all(r["flagged_loan_n"] == 0 for r in union)
    assert all(r["loss_accounting"] == LOSS_LABEL for r in perfeature)


def test_layer_specific_metadata_is_explicit(tmp_path):
    from credit_risk_sba.bis_data import NAME
    from credit_risk_sba.bis_finalize import label_outputs

    path = tmp_path / "results" / NAME
    path.mkdir(parents=True)
    pd.DataFrame(
        {"variant": ["layer1", "layer2", "layer2_term", "layer2_peak"], "value": [1, 2, 3, 4]}
    ).to_csv(path / "status.csv", index=False)
    pd.DataFrame({"feature": ["x"], "n": [10]}).to_csv(
        path / "layer2_level_counts.csv", index=False
    )
    label_outputs(tmp_path)
    f = pd.read_csv(path / "status.csv")
    assert f.loc[f.variant.eq("layer2"), "layer_interpretation"].eq(VALIDATION_LABEL).all()
    assert (
        pd.read_csv(path / "layer2_level_counts.csv")
        .layer_interpretation.eq(VALIDATION_LABEL)
        .all()
    )


def test_qualified_sensitivity_metadata(tmp_path):
    from credit_risk_sba.bis_data import NAME
    from credit_risk_sba.bis_finalize import label_outputs

    path = tmp_path / "results" / NAME
    path.mkdir(parents=True)
    pd.DataFrame({"variant": ["layer2", "layer2_term", "layer2_peak"]}).to_csv(
        path / "models.csv", index=False
    )
    label_outputs(tmp_path)
    f = pd.read_csv(path / "models.csv")
    assert f.layer_interpretation.eq(VALIDATION_LABEL).all()
    assert f.specification_role.iloc[0] == "Term-free primary specification"
    assert "timing unverified" in f.specification_role.iloc[1]
    assert "sensitivity" in f.specification_role.iloc[2]


def test_stipulated_stress_is_distinct_from_realized_validation(tmp_path):
    from credit_risk_sba.bis_data import NAME
    from credit_risk_sba.bis_finalize import label_outputs

    path = tmp_path / "results" / NAME
    path.mkdir(parents=True)
    pd.DataFrame({"variant": ["layer2"], "scenario": ["adverse"]}).to_csv(
        path / "firth_stress.csv", index=False
    )
    pd.DataFrame({"scenario": ["baseline"]}).to_csv(path / "scenario_paths.csv", index=False)
    pd.DataFrame({"variant": ["layer2"], "feature": ["du"]}).to_csv(
        path / "firth_macro_associations.csv", index=False
    )
    label_outputs(tmp_path)
    stress = pd.read_csv(path / "firth_stress.csv")
    assert stress.layer_interpretation.eq(VALIDATION_LABEL).all()
    assert "Stipulated" in stress.macro_information_context.iloc[0]
    assert "not out-of-sample" in stress.macro_information_context.iloc[0]
    assert (
        "Stipulated" in pd.read_csv(path / "scenario_paths.csv").macro_information_context.iloc[0]
    )
    assert (
        "+1 pp conditional contrast"
        in pd.read_csv(path / "firth_macro_associations.csv").macro_information_context.iloc[0]
    )
