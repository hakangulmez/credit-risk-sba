"""Weighted Jeffreys-penalized binomial logit, with explicit convergence failures."""

import time
from dataclasses import dataclass

import numba
import numpy as np
from scipy import linalg, sparse
from scipy.special import expit


@numba.njit(parallel=True, cache=True)
def _quadratic_rows(indptr, indices, values, inverse):
    out = np.zeros(len(indptr) - 1)
    for i in numba.prange(len(out)):
        for a in range(indptr[i], indptr[i + 1]):
            subtotal = 0.0
            for b in range(indptr[i], indptr[i + 1]):
                subtotal += inverse[indices[a], indices[b]] * values[b]
            out[i] += values[a] * subtotal
    return out


@dataclass
class FirthFit:
    beta: np.ndarray
    diagnostics: dict

    def predict(self, x):
        if not self.diagnostics["converged"]:
            raise ValueError("Failed Firth fit cannot supply valid predictions")
        return expit(np.asarray(x @ self.beta).ravel())


def likelihood_score(x, y, beta, weights=None, score=True):
    """Frequency-weighted likelihood plus one half log determinant of weighted I.

    Fractional case weights enter both likelihood and expected information. The
    leverage adjustment is not multiplied by weights a second time.
    """
    x = sparse.csr_matrix(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.ones(len(y)) if weights is None else np.asarray(weights, dtype=float)
    if len(w) != len(y) or not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError("All case weights must be finite and strictly positive")
    eta = np.asarray(x @ beta).ravel()
    p = expit(eta)
    variance = w * p * (1 - p)
    info = (x.T @ x.multiply(variance[:, None])).toarray()
    factor = linalg.cho_factor(info, lower=True, check_finite=True)
    logdet = 2 * np.log(np.diag(factor[0])).sum()
    objective = float(np.dot(w, y * eta - np.logaddexp(0, eta)) + 0.5 * logdet)
    if not np.isfinite(objective):
        raise ValueError("Nonfinite penalized likelihood")
    if not score:
        return objective, None, info
    inverse = linalg.cho_solve(factor, np.eye(x.shape[1]))
    h = variance * _quadratic_rows(x.indptr, x.indices, x.data, inverse)
    adjusted = np.asarray(x.T @ (w * (y - p) + h * (0.5 - p))).ravel()
    return objective, adjusted, info


def fit_firth(x, y, weights=None, settings=None, start=None):
    cfg = settings or {
        "max_iter": 100,
        "max_step": 5.0,
        "max_halvings": 25,
        "score_tolerance": 1e-5,
        "coefficient_tolerance": 1e-5,
        "likelihood_tolerance": 1e-5,
        "information_condition_limit": 1e14,
        "threads": 4,
    }
    numba.set_num_threads(cfg["threads"])
    x = sparse.csr_matrix(x, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = np.ones(len(y)) if weights is None else np.asarray(weights, dtype=float)
    if x.shape[0] != len(y) or not np.isin(y, [0, 1]).all():
        raise ValueError("Binary outcomes and matching design rows required")
    beta = np.zeros(x.shape[1]) if start is None else np.asarray(start, dtype=float).copy()
    if start is None:
        rate = (np.dot(weights, y) + 0.5) / (weights.sum() + 1)
        beta[0] = np.log(rate / (1 - rate))
    tick = time.perf_counter()
    converged = False
    message = "iteration limit"
    iteration = 0
    step_change = np.inf
    ll_change = np.inf
    max_score = np.inf
    condition = np.inf
    objective = np.nan
    try:
        objective, score, info = likelihood_score(x, y, beta, weights)
        for iteration in range(1, cfg["max_iter"] + 1):
            condition = float(np.linalg.cond(info))
            if not np.isfinite(condition) or condition > cfg["information_condition_limit"]:
                message = "information condition exceeds frozen limit"
                break
            max_score = float(np.max(np.abs(score)))
            if (
                max_score <= cfg["score_tolerance"]
                and step_change <= cfg["coefficient_tolerance"]
                and ll_change <= cfg["likelihood_tolerance"]
            ):
                converged = True
                message = "all three numerical criteria satisfied"
                break
            step = linalg.solve(info, score, assume_a="pos")
            step *= min(1.0, cfg["max_step"] / max(float(np.max(np.abs(step))), 1e-30))
            accepted = False
            for halving in range(cfg["max_halvings"] + 1):
                candidate = beta + step / (2**halving)
                try:
                    proposed, _, _ = likelihood_score(x, y, candidate, weights, score=False)
                except (ValueError, linalg.LinAlgError):
                    continue
                if proposed >= objective - 1e-8:
                    accepted = True
                    break
            if not accepted:
                message = "line-search exhaustion"
                break
            step_change = float(np.max(np.abs(candidate - beta)))
            ll_change = abs(proposed - objective)
            beta = candidate
            objective, score, info = likelihood_score(x, y, beta, weights)
        if not np.isfinite(beta).all():
            converged = False
            message = "nonfinite coefficients"
    except (ValueError, linalg.LinAlgError, FloatingPointError) as exc:
        message = type(exc).__name__ + ": " + str(exc)
    return FirthFit(
        beta,
        {
            "converged": bool(converged),
            "message": message,
            "iterations": iteration,
            "score_max": max_score,
            "coefficient_change": step_change,
            "likelihood_change": ll_change,
            "penalized_loglikelihood": objective,
            "information_condition": condition,
            "n": len(y),
            "columns": x.shape[1],
            "seconds": time.perf_counter() - tick,
            "weight_sum": float(weights.sum()),
            "min_weight": float(weights.min()),
            "max_weight": float(weights.max()),
        },
    )


def multiplier_weights(states, attempts=199, seed=20261008):
    levels = np.sort(np.unique(states))
    raw = np.random.default_rng(seed).exponential(1.0, (attempts, len(levels)))
    if not (raw > 0).all():
        raise ValueError("A nonpositive scheduled state multiplier occurred")
    return levels, raw


def observation_weights(states, levels, draw):
    code = np.searchsorted(levels, np.asarray(states))
    w = np.asarray(draw)[code]
    return w * len(w) / w.sum()
