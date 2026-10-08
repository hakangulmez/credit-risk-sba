import numpy as np
import pandas as pd
import pytest
from scipy import sparse
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from credit_risk_sba.data import features, normalize, roles
from credit_risk_sba.features import Design
from credit_risk_sba.losses import accepted_mask, allocate, assign_lgd, lgd_tables
from credit_risk_sba.macro import join, panel, scenarios
from credit_risk_sba.metrics import calibration_bins, evaluate, psi
from credit_risk_sba.models import MLE, Sigmoid, calibrate, fit_mle
from credit_risk_sba.stress import coefficient_draws, group_matrix, summaries, support_flags


def source(**changes):
    row = {"AsOfDate": "2026-06-30", "Program": " 7A", "GrossApproval": "100000",
               "SBAGuaranteedApproval": "85000", "ApprovalDate": "2006-01-01",
               "FirstDisbursementDate": "2006-01-31", "ProcessingMethod": "Standard 7(a)",
               "InitialInterestRate": "", "FixedorVariableInterestInd": "", "TermInMonths": "120",
               "NaicsCode": "541111", "FranchiseCode": "00000", "ProjectState": "CA",
               "BusinessType": "CORPORATION", "BusinessAge": "New, Less than 1 year old",
               "LoanStatus": "EXEMPT", "PaidInFullDate": "", "ChargeOffDate": "",
               "GrossChargeOffAmount": "", "RevolverStatus": "N", "JobsSupported": "0", "row_id": "test:0"}
    row.update(changes)
    return row


@pytest.mark.parametrize("event,expected", [("2006-01-31", 1), ("2009-01-31", 1), ("2009-02-01", 0)])
def test_label_inclusive_calendar_window(event, expected):
    f, _, _ = normalize(pd.DataFrame([source(LoanStatus="CHGOFF", ChargeOffDate=event)]),
                        "2026-06-30", {"CA"})
    assert f.Y.iloc[0] == expected
    assert f.w.iloc[0] == pd.Timestamp("2009-01-31")


def test_month_end_clamping_and_mature_exempt():
    f, _, _ = normalize(pd.DataFrame([source(FirstDisbursementDate="2008-02-29")]), "2026-06-30", {"CA"})
    assert f.w.iloc[0] == pd.Timestamp("2011-02-28")
    assert f.Y.iloc[0] == 0


@pytest.mark.parametrize("change,flag", [
    ({"LoanStatus": "CANCLD"}, "cancelled_or_committed"),
    ({"LoanStatus": "COMMIT"}, "cancelled_or_committed"),
    ({"LoanStatus": "BAD"}, "unknown_status"),
    ({"Program": "504"}, "wrong_program"),
    ({"ProjectState": "PR"}, "unmapped_state"),
    ({"GrossApproval": "0"}, "invalid_approval_amount"),
    ({"FirstDisbursementDate": ""}, "missing_disbursement"),
    ({"FirstDisbursementDate": "2023-07-01"}, "incomplete_window"),
    ({"LoanStatus": "CHGOFF"}, "date_or_status_contradiction"),
    ({"ChargeOffDate": "2007-01-01"}, "date_or_status_contradiction"),
    ({"PaidInFullDate": "2007-01-01"}, "date_or_status_contradiction"),
    ({"ApprovalDate": "2007-01-01"}, "date_or_status_contradiction"),
    ({"ApprovalDate": "malformed"}, "date_or_status_contradiction"),
    ({"LoanStatus": "P I F", "PaidInFullDate": "2005-01-01"}, "date_or_status_contradiction"),
    ({"LoanStatus": "CHGOFF", "ChargeOffDate": "2005-01-01"}, "date_or_status_contradiction"),
    ({"LoanStatus": "PIF", "PaidInFullDate": "2027-01-01"}, "date_or_status_contradiction"),
])
def test_exclusion_accounting(change, flag):
    f, waterfall, overlap = normalize(pd.DataFrame([source(**change)]), "2026-06-30", {"CA"})
    assert len(f) == 0
    assert next(row["n"] for row in overlap if row["flag"] == flag) == 1
    assert sum(row["excluded"] for row in waterfall) == 1


def test_severity_anomaly_does_not_remove_outcomes():
    f, _, _ = normalize(pd.DataFrame([source(LoanStatus="CHGOFF", ChargeOffDate="2007-01-01", GrossChargeOffAmount="150000")]), "2026-06-30", {"CA"})
    assert len(f) == 1 and f.Y.iloc[0] == 1


@pytest.mark.parametrize("date,role", [("1991-01-01", "train"), ("2002-12-31", "train"),
                                      ("2003-06-30", "tune"), ("2003-07-01", "calibrate"),
                                      ("2006-01-01", "reference"), ("2007-01-01", "crisis"),
                                      ("2009-12-31", "crisis"), ("2011-01-01", "oot"),
                                      ("2013-12-31", "oot"), ("2010-01-01", "outside_frozen_cohorts"),
                                      ("1990-12-31", "outside_frozen_cohorts"), ("2005-01-01", "buffer")])
def test_frozen_roles(date, role):
    assert roles(pd.DataFrame({"d": [pd.Timestamp(date)]})).iloc[0] == role


def feature_sample(n=100):
    raw = pd.DataFrame([source(row_id=f"test:{i}", GrossApproval=str(50000 + i * 1000),
                              SBAGuaranteedApproval=str(.85 * (50000 + i * 1000)),
                              JobsSupported=str(i % 7), ProcessingMethod="A" if i % 2 else "B") for i in range(n)])
    frame, _, _ = normalize(raw, "2026-06-30", {"CA"})
    frame = features(frame)
    frame["role"] = "train"
    return frame


def test_feature_vintage_allowlist_and_no_test_preprocessing():
    f = feature_sample()
    design = Design.create().fit(f)
    assert "TermInMonths" not in design.numeric
    assert "LoanStatus" not in design.names
    assert set(design.categorical).isdisjoint({"BankName", "SoldSecMrktInd", "CollateralInd"})
    test = f.copy().assign(role="crisis", log_approval=100.0, BusinessType="unseen")
    before = design.median.copy()
    x = design.transform(test)
    assert np.array_equal(before, design.median)
    assert np.isfinite(x.data).all()
    assert design.support(f, test)[0]["outside_train_range"] == len(test)
    with pytest.raises(ValueError):
        Design.create().fit(test)
    with pytest.raises(ValueError):
        Design(["GrossChargeOffAmount"], []).fit(f)
    assert "TermInMonths" in Design.create(term=True).numeric
    assert len(design.keep) < len(design.names)  # Constant rate and missing flags are unidentifiable.


def test_feature_group_boundaries_and_invalid_values():
    f = feature_sample(8)
    f.loc[0, "SBAGuaranteedApproval"] = 1e8
    f.loc[1, "InitialInterestRate"] = -1
    f.loc[2, "JobsSupported"] = -1
    f.loc[3, "RevolverStatus"] = "Y"
    f.loc[4, "FranchiseCode"] = "12345"
    f.loc[5, "FranchiseCode"] = ""
    f.loc[6, "BusinessAge"] = "Change of Ownership"
    f.loc[7, "BusinessAge"] = "Unanswered"
    f = features(f)
    assert np.isnan(f.guarantee_share.iloc[0])
    assert np.isnan(f.InitialInterestRate.iloc[1])
    assert np.isnan(f.log_jobs.iloc[2])
    assert f.loan_type.iloc[3] == "revolving"
    assert list(f.franchise.iloc[4:6]) == ["present", "missing"]
    assert list(f.age_group.iloc[6:]) == ["change_of_ownership", "unanswered"]


def macro_sample():
    months = np.arange(1989 * 12, 2017 * 12)
    values = np.full(len(months), 5.0)
    values[months == 2008 * 12] = 10.0
    u = pd.DataFrame({"state": "CA", "month": months, "u": values})
    quarters = np.arange(1980 * 4, 2020 * 4)
    h = pd.DataFrame({"state": "CA", "quarter": quarters, "hpi": np.exp((quarters - quarters[0]) / 100)})
    return u, h


def test_peak_vs_endpoint_and_37_month_complete_path():
    u, h = macro_sample()
    p = panel(u, h)
    point = p.loc[p.month.eq(2007 * 12)].iloc[0]
    assert point.du == 0 and point.peak_du == 5
    assert point.h0 == pytest.approx(4)
    assert point.dh == pytest.approx(12)
    missing = u.loc[~u.month.eq(2008 * 12)]
    point = panel(missing, h).loc[lambda t: t.month.eq(2007 * 12)].iloc[0]
    assert np.isnan(point.peak_du) and point.du == 0
    loans = feature_sample(2)
    result = join(loans, u, h)
    assert result.row_id.equals(loans.row_id)


def test_fixed_scenario_dates_no_worst_date_search():
    u, h = macro_sample()
    s = scenarios(u, h).set_index("scenario")
    assert s.loc["baseline", "du"] == 0
    assert s.loc["baseline", "peak_du"] == 0
    assert s.loc["adverse", "du"] == 0
    assert s.loc["adverse", "peak_du"] == 5
    assert s.loc["adverse", "dh"] == pytest.approx(12)
    with pytest.raises(ValueError):
        scenarios(u.loc[~u.month.eq(2008 * 12)], h)


def lgd_sample():
    f = feature_sample(100)
    f["Y"] = 1
    f["GrossApproval"] = 100
    f["GrossChargeOffAmount"] = np.r_[np.full(60, 120), np.full(40, 40)]
    f["size_band"] = np.r_[np.full(60, "<=150k"), np.full(40, ">1m")]
    f["year"] = np.r_[np.full(10, 1990), np.full(30, 1991), np.full(30, 2000), np.full(30, 2002)]
    return f


def test_lgd_training_only_pooling_counts_cap_and_1990_exclusion():
    f = lgd_sample()
    rows, mapping = lgd_tables(f)
    assert mapping[("term", "<=150k")] == pytest.approx(1.2)
    assert mapping[("term", ">1m")] == pytest.approx(.88)
    assert rows.loc[rows.loan_type.eq("term") & rows.size_band.eq(">1m"), "pool"].iloc[0] == "loan_type"
    _, cap = lgd_tables(f, capped=True)
    assert cap[("term", "<=150k")] == 1
    d, downturn = lgd_tables(f, downturn=True)
    assert d.loc[d.loan_type.eq("term"), "cell_recorded_charge_offs"].sum() == 60
    assert downturn[("term", "<=150k")] == pytest.approx(1.2)  # Exactly 50: no pooling.
    assert downturn[("term", ">1m")] == pytest.approx((50 * 120 + 10 * 40) / 6000)
    assert assign_lgd(f, mapping).shape == (100,)
    f.loc[0, "GrossChargeOffAmount"] = -1
    f.loc[1, "GrossChargeOffAmount"] = np.nan
    rows, _ = lgd_tables(f)
    assert rows.excluded_severity_n.sum() == 2
    with pytest.raises(ValueError):
        lgd_tables(f.assign(role="crisis"))


def test_exact_loss_allocation_and_deterministic_acceptance():
    total, sba, lender = allocate([.1, .2], [.5, .75], [100, 200], [.85, .75])
    assert np.allclose(total, [5, 30])
    assert np.allclose(total, sba + lender)
    assert accepted_mask([.1, .1, .1, .2], ["b", "a", "c", "d"], .5).tolist() == [True, True, False, False]
    for args in [([-.1], [.5], [100], [.8]), ([.1], [.5], [0], [.8]), ([.1], [-1], [100], [.8]), ([.1], [.5], [100], [1.1])]:
        with pytest.raises(ValueError):
            allocate(*args)


def test_exact_bootstrap_metrics_ties_pairing_calibration(monkeypatch):
    rng = np.random.default_rng(9)
    p = np.round(rng.uniform(.01, .7, 1000), 2)
    y = rng.binomial(1, expit(-.5 + .8 * np.log(p / (1 - p))))
    state = np.repeat(["CA", "TX", "NY", "DC"], 250)
    rows, draws = evaluate(y, p, state, draws=19)
    import credit_risk_sba.metrics as module
    monkeypatch.setattr(module, "_scores", module._scores.py_func)
    python_rows, python_draws = evaluate(y, p, state, draws=19)
    assert np.allclose(draws, python_draws)
    assert rows == python_rows
    actual = {r["metric"]: r["value"] for r in rows}
    assert actual["auc"] == pytest.approx(roc_auc_score(y, p), abs=1e-12)
    assert actual["average_precision"] == pytest.approx(average_precision_score(y, p), abs=1e-12)
    assert actual["brier"] == pytest.approx(brier_score_loss(y, p), abs=1e-12)
    fitted = calibrate(y, p)
    assert actual["calibration_intercept"] == pytest.approx(fitted.intercept, abs=1e-5)
    assert actual["calibration_slope"] == pytest.approx(fitted.slope, abs=1e-5)
    _, same = evaluate(y, p, state, draws=19)
    assert np.allclose(draws, same)
    bins = calibration_bins(p, y, p, state, draws=19)
    assert sum(b["n"] for b in bins) == len(y)
    assert psi(pd.Series(p), pd.Series(p)) == 0
    assert psi(pd.Series(["a", "b"]), pd.Series(["unseen", "b"]), True) > 0
    with pytest.raises(ValueError):
        evaluate(y, np.full(len(y), 2), state, draws=2)
    failed, _ = evaluate(np.zeros(len(y)), p, state, draws=2)
    assert failed[0]["undefined_draws"] == 2


def test_unpenalized_logit_cluster_covariance_and_separation():
    rng = np.random.default_rng(9)
    x = np.c_[np.ones(3000), rng.normal(size=(3000, 2))]
    y = rng.binomial(1, expit(x @ [-1, .3, -.5]))
    model = fit_mle(x, y, np.arange(len(y)) % 51)
    assert model.diagnostics["converged"]
    assert np.allclose(model.beta, [-1, .3, -.5], atol=.12)
    assert np.isfinite(model.covariance).all()
    import statsmodels.api as sm
    reference = sm.Logit(y, x).fit(disp=False, cov_type="cluster",
                                  cov_kwds={"groups": np.arange(len(y)) % 51,
                                            "use_correction": True})
    assert np.allclose(model.beta, reference.params, atol=1e-5)
    assert np.allclose(model.covariance, reference.cov_params(), atol=1e-6)
    assert np.allclose(model.predict(x), expit(x @ model.beta))
    assert np.allclose(Sigmoid(0, 1).predict([.2, .3]), [.2, .3])
    bad_x = sparse.csr_matrix(np.c_[np.ones(100), np.r_[np.ones(10), np.zeros(90)]])
    bad_y = np.r_[np.zeros(10), np.tile([0, 1], 45)]
    failed = fit_mle(bad_x, bad_y, np.arange(100) % 5)
    assert not failed.diagnostics["converged"]
    assert failed.diagnostics["separation_flag"]
    assert failed.diagnostics["binary_separation_witness_columns"] == [1]
    with pytest.raises(ValueError):
        fit_mle(x, np.zeros(3000), np.arange(3000) % 51)


def test_coefficient_draws_groups_and_conditional_summaries():
    f = feature_sample(10)
    names, groups = group_matrix(f)
    model = MLE(np.array([-.5, .2]), np.array([[.1, .02], [.02, .03]]), {})
    draws, _ = coefficient_draws(model, 19, 1)
    x = np.c_[np.ones(len(f)), np.linspace(-1, 1, len(f))]
    results = summaries(x, draws, groups, f.GrossApproval.to_numpy(), np.full(len(f), .5), f.guarantee_share.to_numpy())
    assert names[0] == ("overall", "all")
    assert results[0, 0, 0] == pytest.approx(expit(x @ model.beta).mean())
    assert np.allclose(results[:, :, 1], results[:, :, 2] + results[:, :, 3])
    invalid = MLE(model.beta, -np.eye(2), {})
    with pytest.raises(ValueError):
        coefficient_draws(invalid, 19, 1)
    train = f.assign(u0=5., du=0., h0=2., dh=6.)
    scenario = pd.DataFrame([{"ProjectState": "CA", "scenario": "adverse", "u0": 7., "du": 3., "h0": -2., "dh": -10.}])
    flags = support_flags(train, scenario, ["u0", "du", "h0", "dh"])
    assert flags.outside_state_support.all()
