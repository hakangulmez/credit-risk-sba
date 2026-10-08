import numpy as np
import pytest
from scipy import optimize, sparse
from scipy.special import logit

from credit_risk_sba.bis_firth import (
    fit_firth,
    likelihood_score,
    multiplier_weights,
    observation_weights,
)


def test_intercept_weighted_analytic_solution():
    y = np.r_[np.ones(4), np.zeros(16)]
    w = np.linspace(0.3, 2, len(y))
    x = np.ones((len(y), 1))
    model = fit_firth(x, y, w)
    assert model.diagnostics["converged"]
    expected = logit((w @ y + 0.5) / (w.sum() + 1))
    np.testing.assert_allclose(model.beta, [expected], atol=1e-7)


def test_fractional_weight_score_finite_difference_and_replication():
    rng = np.random.default_rng(44)
    x = np.c_[np.ones(40), rng.normal(size=(40, 2))]
    y = rng.binomial(1, 0.25, 40)
    w = rng.uniform(0.2, 3, 40)
    b = np.array([-0.8, 0.3, -0.5])
    objective, score, info = likelihood_score(x, y, b, w)
    numeric = optimize._numdiff.approx_derivative(
        lambda z: np.array([likelihood_score(x, y, z, w, score=False)[0]]), b, method="3-point"
    ).ravel()
    np.testing.assert_allclose(score, numeric, atol=1e-6, rtol=1e-6)
    counts = np.tile([1, 2, 3, 4], 10)
    a = fit_firth(x, y, counts)
    c = fit_firth(np.repeat(x, counts, axis=0), np.repeat(y, counts))
    assert a.diagnostics["converged"] and c.diagnostics["converged"]
    np.testing.assert_allclose(a.beta, c.beta, atol=1e-7)
    assert np.linalg.eigvalsh(info).min() > 0 and np.isfinite(objective)


def test_separation_finite_and_dense_sparse_equal():
    x = np.c_[np.ones(100), np.r_[np.zeros(50), np.ones(50)]]
    y = x[:, 1]
    a = fit_firth(x, y)
    b = fit_firth(sparse.csr_matrix(x), y)
    assert a.diagnostics["converged"] and np.isfinite(a.beta).all()
    np.testing.assert_allclose(a.beta, b.beta, atol=1e-10)
    np.testing.assert_allclose(a.predict(x)[:50], 0.5 / 51, atol=1e-7)


def test_state_multipliers_positive_paired_and_normalized():
    states = np.array(["CA", "NY", "CA", "TX", "CA"])
    levels, draws = multiplier_weights(states)
    assert draws.shape == (199, 3) and (draws > 0).all()
    np.testing.assert_array_equal(draws, multiplier_weights(states)[1])
    for draw in draws[:5]:
        w = observation_weights(states, levels, draw)
        assert w.sum() == pytest.approx(len(states)) and (w > 0).all()
        assert w[0] == w[2] == w[4]
        other = observation_weights(states[::-1], levels, draw)
        np.testing.assert_allclose(other, w[::-1])


def test_failure_never_supplies_valid_predictions():
    x = np.ones((10, 2))
    y = np.r_[np.zeros(5), np.ones(5)]
    model = fit_firth(x, y)
    assert not model.diagnostics["converged"]
    with pytest.raises(ValueError):
        model.predict(x)
    with pytest.raises(ValueError):
        likelihood_score(np.ones((10, 1)), y, np.zeros(1), np.zeros(10))


def test_numerical_limits_are_failures_without_alternative_fit():
    from copy import deepcopy
    from pathlib import Path

    import yaml

    from credit_risk_sba.bis_firth import fit_firth

    cfg = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / "config/g2_bis_2026-10-08.yaml").read_text()
    )["firth"]
    x = np.c_[np.ones(30), np.linspace(-2, 2, 30)]
    y = np.r_[np.ones(10), np.zeros(20)]
    short = deepcopy(cfg)
    short["max_iter"] = 1
    assert fit_firth(x, y, settings=short).diagnostics["message"] == "iteration limit"
    condition = deepcopy(cfg)
    condition["information_condition_limit"] = 1
    assert "condition exceeds" in fit_firth(x, y, settings=condition).diagnostics["message"]
    with pytest.raises(ValueError, match="Binary outcomes"):
        fit_firth(x, np.full(30, 2))
    with pytest.raises(ValueError, match="weights"):
        likelihood_score(x, y, np.zeros(2), np.full(30, np.nan))


def test_compiled_leverage_matches_explicit_projection_and_python(monkeypatch):
    from credit_risk_sba import bis_firth

    rng = np.random.default_rng(12)
    x = sparse.csr_matrix(np.c_[np.ones(30), rng.normal(size=(30, 2))])
    y = rng.binomial(1, 0.25, 30)
    w = rng.uniform(0.1, 3, 30)
    b = np.array([-1.0, 0.2, -0.3])
    objective, score, info = likelihood_score(x, y, b, w)
    compiled = bis_firth._quadratic_rows(x.indptr, x.indices, x.data, np.linalg.inv(info))
    python = bis_firth._quadratic_rows.py_func(x.indptr, x.indices, x.data, np.linalg.inv(info))
    expected = np.diag(x.toarray() @ np.linalg.inv(info) @ x.toarray().T)
    np.testing.assert_allclose(compiled, expected, atol=1e-12)
    np.testing.assert_allclose(python, expected, atol=1e-12)
    monkeypatch.setattr(bis_firth, "_quadratic_rows", bis_firth._quadratic_rows.py_func)
    other, python_score, _ = likelihood_score(x, y, b, w)
    assert other == pytest.approx(objective)
    np.testing.assert_allclose(python_score, score, atol=1e-12)
