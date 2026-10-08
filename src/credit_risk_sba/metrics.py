"""Exact score metrics and paired state-cluster uncertainty, conditional on fits."""
import numpy as np
import pandas as pd
from numba import njit
from scipy.special import logit

METRICS = ["auc", "average_precision", "brier", "calibration_intercept", "calibration_slope"]


@njit(cache=True)
def _scores(y, p, z, state, multiplicities):
    result = np.empty((len(multiplicities), 5))
    for draw in range(len(multiplicities)):
        weights = multiplicities[draw]
        positive, negative, total, brier = 0.0, 0.0, 0.0, 0.0
        for i in range(len(y)):
            w = weights[state[i]]
            positive += w * y[i]
            negative += w * (1 - y[i])
            total += w
            brier += w * (y[i] - p[i]) ** 2
        if positive <= 0 or negative <= 0:
            result[draw, :] = np.nan
            continue
        cumpos, cumneg, aucnum, ap = 0.0, 0.0, 0.0, 0.0
        i = 0
        while i < len(y):
            j, gp, gn = i, 0.0, 0.0
            while j < len(y) and p[j] == p[i]:
                w = weights[state[j]]
                gp += w * y[j]
                gn += w * (1 - y[j])
                j += 1
            cumpos += gp
            cumneg += gn
            aucnum += gp * (negative - cumneg + 0.5 * gn)
            if cumpos + cumneg > 0:
                ap += gp / positive * cumpos / (cumpos + cumneg)
            i = j
        result[draw, 0] = aucnum / (positive * negative)
        result[draw, 1] = ap
        result[draw, 2] = brier / total
        alpha, beta, converged = 0.0, 1.0, False
        for _ in range(100):
            g0, g1, h00, h01, h11 = 0.0, 0.0, 0.0, 0.0, 0.0
            for i in range(len(y)):
                eta = min(35.0, max(-35.0, alpha + beta * z[i]))
                q = 1.0 / (1.0 + np.exp(-eta))
                w = weights[state[i]]
                error = w * (y[i] - q)
                v = w * q * (1 - q)
                g0 += error
                g1 += error * z[i]
                h00 += v
                h01 += v * z[i]
                h11 += v * z[i] * z[i]
            det = h00 * h11 - h01 * h01
            if det <= 1e-14:
                break
            da = (h11 * g0 - h01 * g1) / det
            db = (h00 * g1 - h01 * g0) / det
            damping = min(1.0, 5.0 / max(abs(da), abs(db), 1e-30))
            alpha += damping * da
            beta += damping * db
            if max(abs(da), abs(db)) < 1e-8:
                converged = True
                break
        result[draw, 3] = alpha if converged else np.nan
        result[draw, 4] = beta if converged else np.nan
    return result


def cluster_draws(states, draws, seed):
    levels = np.sort(np.unique(states))
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(levels), np.full(len(levels), 1 / len(levels)), size=draws)
    return levels, weights


def evaluate(y, p, states, draws=999, seed=20261008):
    y, p, states = np.asarray(y, dtype=float), np.asarray(p, dtype=float), np.asarray(states)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid probability")
    levels, weights = cluster_draws(states, draws, seed)
    code = np.searchsorted(levels, states)
    order = np.argsort(-p, kind="stable")
    z = logit(np.clip(p[order], 1e-12, 1 - 1e-12))
    all_weights = np.vstack([np.ones(len(levels), dtype=int), weights])
    output = _scores(y[order], p[order], z, code[order], all_weights)
    rows = []
    for i, metric in enumerate(METRICS):
        valid = output[1:, i][np.isfinite(output[1:, i])]
        lo, hi = np.quantile(valid, [0.025, 0.975]) if len(valid) else [np.nan, np.nan]
        rows.append({"metric": metric, "value": output[0, i], "lower": lo, "upper": hi,
                     "bootstrap_draws": draws, "undefined_draws": draws - len(valid),
                     "n": len(y), "recorded_charge_offs_36m": int(y.sum()),
                     "states": len(levels), "interval": "paired state-cluster, frozen fits"})
    return rows, output[1:]


def calibration_bins(train_p, test_y, test_p, states, draws=999, seed=20261008):
    boundaries = np.unique(np.quantile(train_p, np.linspace(0, 1, 11)))
    edges = np.r_[-np.inf, boundaries[1:-1], np.inf]
    bins = np.searchsorted(edges[1:-1], test_p, side="right")
    levels, multiplicities = cluster_draws(states, draws, seed)
    code = np.searchsorted(levels, states)
    rows = []
    for b in range(len(edges) - 1):
        index = bins == b
        n = np.bincount(code[index], minlength=len(levels))
        sums = np.bincount(code[index], weights=np.asarray(test_y)[index], minlength=len(levels))
        den = multiplicities @ n
        num = multiplicities @ sums
        valid = den > 0
        lo, hi = np.quantile(num[valid] / den[valid], [0.025, 0.975]) if valid.any() else [np.nan, np.nan]
        rows.append({"bin": b + 1, "lower_edge": edges[b], "upper_edge": edges[b + 1],
                     "n": int(index.sum()), "predicted_pd": float(np.mean(np.asarray(test_p)[index])) if index.any() else np.nan,
                     "recorded_rate": float(np.mean(np.asarray(test_y)[index])) if index.any() else np.nan,
                     "lower": lo, "upper": hi, "undefined_draws": int((~valid).sum())})
    return rows


def psi(train: pd.Series, test: pd.Series, categorical=False):
    if categorical:
        levels = list(pd.unique(train.fillna("__missing__"))) + ["__unseen__"]
        a = train.fillna("__missing__")
        b = test.fillna("__missing__").where(test.fillna("__missing__").isin(levels), "__unseen__")
        left = a.value_counts().reindex(levels, fill_value=0).to_numpy()
        right = b.value_counts().reindex(levels, fill_value=0).to_numpy()
    else:
        finite = train.dropna()
        cuts = np.unique(np.quantile(finite, np.linspace(0, 1, 11))) if len(finite) else np.array([], dtype=float)
        edges = np.r_[-np.inf, cuts[1:-1], np.inf]
        left = np.r_[np.histogram(train.dropna(), edges)[0], train.isna().sum()]
        right = np.r_[np.histogram(test.dropna(), edges)[0], test.isna().sum()]
    a = np.maximum(left / max(left.sum(), 1), 1e-6)
    b = np.maximum(right / max(right.sum(), 1), 1e-6)
    a, b = a / a.sum(), b / b.sum()
    return float(np.sum((b - a) * np.log(b / a)))
