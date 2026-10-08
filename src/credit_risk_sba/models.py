"""Frozen estimators and budgets; no substitution after a fit failure."""
import time
import warnings
from dataclasses import dataclass

import lightgbm as lgb
import numpy as np
import optuna
from scipy import optimize, sparse
from scipy.special import expit, logit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss


@dataclass
class MLE:
    beta: np.ndarray
    covariance: np.ndarray
    diagnostics: dict

    def predict(self, x):
        return expit(np.asarray(x @ self.beta).ravel())


def fit_mle(x, y, clusters, settings=None) -> MLE:
    settings = settings or {"max_iter": 500, "tolerance": 1e-8,
                            "normalized_gradient_limit": 1e-5,
                            "separation_coefficient_limit": 50}
    n, k = x.shape
    y = np.asarray(y, dtype=float)
    if len(np.unique(y)) != 2:
        raise ValueError("Unpenalized logit requires both outcomes")
    start = np.zeros(k)
    # Solve the same unpenalized binomial likelihood, without adding a penalty.
    def objective(beta):
        eta = np.asarray(x @ beta).ravel()
        value = float(np.mean(np.logaddexp(0, eta) - y * eta))
        gradient = np.asarray(x.T @ (expit(eta) - y)).ravel() / n
        return value, gradient
    tick = time.perf_counter()
    fit = optimize.minimize(objective, start, method="L-BFGS-B", jac=True,
                            options={"maxiter": settings["max_iter"],
                                     "ftol": settings["tolerance"] * 1e-3,
                                     "gtol": settings["tolerance"], "maxls": 40, "maxcor": 30})
    beta = fit.x
    gradient = float(np.max(np.abs(objective(beta)[1])))
    p = expit(np.asarray(x @ beta).ravel())
    if sparse.issparse(x):
        hessian = (x.T @ x.multiply((p * (1 - p))[:, None])).toarray()
    else:
        hessian = x.T @ ((p * (1 - p))[:, None] * x)
    eigen = np.linalg.eigvalsh(hessian)
    condition = float(eigen[-1] / max(eigen[0], 1e-300))
    minimum = x.min(axis=0).toarray().ravel() if sparse.issparse(x) else x.min(axis=0)
    maximum = x.max(axis=0).toarray().ravel() if sparse.issparse(x) else x.max(axis=0)
    binary = (minimum == 0) & (maximum == 1)
    positive_counts = np.asarray(x.T @ y).ravel()
    negative_counts = np.asarray(x.T @ (1 - y)).ravel()
    witnesses = np.flatnonzero(binary & ((positive_counts == 0) | (negative_counts == 0)))
    separated = bool(len(witnesses) or np.max(np.abs(beta)) > settings["separation_coefficient_limit"] or eigen[0] <= 1e-10)
    converged = bool(fit.success and gradient <= settings["normalized_gradient_limit"] and not separated)
    codes, labels = np.unique(clusters, return_inverse=True)
    scores = np.zeros((len(codes), k))
    for j in range(len(codes)):
        index = labels == j
        scores[j] = np.asarray(x[index].T @ (y[index] - p[index])).ravel()
    if converged and len(codes) > 1 and n > k:
        bread = np.linalg.inv(hessian)
        correction = len(codes) / (len(codes) - 1) * (n - 1) / (n - k)
        covariance = correction * bread @ (scores.T @ scores) @ bread
        covariance = (covariance + covariance.T) / 2
    else:
        covariance = np.full((k, k), np.nan)
    return MLE(beta, covariance, {"converged": converged, "separation_flag": separated,
              "optimizer_success": bool(fit.success), "message": str(fit.message),
              "normalized_gradient": gradient, "iterations": int(fit.nit),
              "hessian_condition": condition, "n": n, "k": k, "clusters": len(codes),
              "seconds": time.perf_counter() - tick,
              "binary_separation_witness_columns": witnesses.tolist()})


@dataclass
class Sigmoid:
    intercept: float
    slope: float

    def predict(self, p):
        return expit(self.intercept + self.slope * logit(np.clip(p, 1e-12, 1 - 1e-12)))


def calibrate(y, p) -> Sigmoid:
    z = logit(np.clip(p, 1e-12, 1 - 1e-12))
    x = np.column_stack([np.ones(len(z)), z])
    model = fit_mle(x, y, np.arange(len(z)) % 51)
    if not model.diagnostics["converged"]:
        raise ValueError("Unpenalized sigmoid calibration failed")
    return Sigmoid(float(model.beta[0]), float(model.beta[1]))


def elasticnet(x, y, valid_x, valid_y, cfg, seed):
    records = []
    selected = None
    minimum = np.inf
    for ratio in cfg["l1_ratios"]:
        # Warm starts are numerical acceleration only; every frozen C is evaluated.
        estimator = LogisticRegression(solver="saga", l1_ratio=float(ratio),
                    fit_intercept=True, random_state=seed, warm_start=True,
                    max_iter=cfg["max_iter"], tol=cfg["tolerance"])
        for c in np.logspace(np.log10(cfg["c_min"]), np.log10(cfg["c_max"]), cfg["c_count"]):
            estimator.set_params(C=float(c))
            tick = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                estimator.fit(x, y)
            converged = not any(issubclass(w.category, ConvergenceWarning) for w in caught)
            value = float(log_loss(valid_y, estimator.predict_proba(valid_x)[:, 1]))
            records.append({"C": float(c), "l1_ratio": ratio, "log_loss": value,
                            "converged": converged, "iterations": int(estimator.n_iter_[0]),
                            "seconds": time.perf_counter() - tick})
            if converged and value < minimum:
                import copy
                selected = copy.deepcopy(estimator)
                minimum = value
            print(f"ElasticNet C={c:.6g} ratio={ratio} loss={value:.6g} converged={converged}", flush=True)
    if selected is None:
        raise ValueError("All frozen ElasticNet fits failed convergence")
    return selected, records


def boosting(x, y, valid_x, valid_y, cfg, seed, trial_count=None):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    train_set = lgb.Dataset(x, label=y, free_raw_data=False)
    validation = lgb.Dataset(valid_x, label=valid_y, reference=train_set, free_raw_data=False)
    models = {}
    records = []
    def objective(trial):
        params = {"objective": "binary", "metric": "binary_logloss", "verbosity": -1,
                  "num_threads": cfg["threads"], "deterministic": True, "force_col_wise": True,
                  "seed": seed, "bagging_seed": seed, "feature_fraction_seed": seed,
                  "num_leaves": trial.suggest_categorical("num_leaves", cfg["leaves"]),
                  "min_data_in_leaf": trial.suggest_categorical("min_data_in_leaf", cfg["min_child"]),
                  "learning_rate": trial.suggest_float("learning_rate", *cfg["learning_rate"], log=True),
                  "feature_fraction": trial.suggest_float("feature_fraction", *cfg["fractions"]),
                  "bagging_fraction": trial.suggest_float("bagging_fraction", *cfg["fractions"]),
                  "bagging_freq": 1, "feature_pre_filter": False,
                  "lambda_l1": trial.suggest_float("lambda_l1", *cfg["penalties"], log=True),
                  "lambda_l2": trial.suggest_float("lambda_l2", *cfg["penalties"], log=True)}
        tick = time.perf_counter()
        model = lgb.train(params, train_set, num_boost_round=cfg["max_rounds"],
                          valid_sets=[validation], callbacks=[lgb.early_stopping(cfg["early_stopping"], verbose=False)])
        value = float(log_loss(valid_y, model.predict(valid_x)))
        models[trial.number] = model
        records.append({"trial": trial.number, "log_loss": value,
                        "best_iteration": model.best_iteration,
                        "seconds": time.perf_counter() - tick, **params})
        print(f"LightGBM trial={trial.number} loss={value:.6g} rounds={model.best_iteration}", flush=True)
        return value
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=trial_count or cfg["trials"], catch=(ValueError, RuntimeError))
    if not models:
        raise ValueError("All frozen LightGBM trials failed")
    return models[study.best_trial.number], records
