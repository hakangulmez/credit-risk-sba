"""Fixed 2006 portfolio, clustered coefficient resampling, explicit loss proxies."""
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.special import expit

from .fitting import active_data
from .io import config, table, write_json
from .losses import EAD_LABEL, LGD_LABEL, SPLIT_LABEL, assign_lgd, lgd_tables
from .macro import MACRO, PEAK_MACRO, load, scenarios

GROUPS = ["loan_type", "size_band", "naics2", "age_group", "maturity_group"]


def coefficient_draws(model, count, seed):
    values, vectors = np.linalg.eigh((model.covariance + model.covariance.T) / 2)
    if values.min() < -1e-6 * max(values.max(), 1):
        raise ValueError("State-cluster covariance is materially non-PSD")
    root = vectors @ np.diag(np.sqrt(np.maximum(values, 0)))
    draws = model.beta + np.random.default_rng(seed).normal(size=(count, len(values))) @ root.T
    return np.vstack([model.beta, draws]), float(values.min())


def group_matrix(frame):
    names = [("overall", "all")]
    members = [np.arange(len(frame))]
    for key in GROUPS:
        for level in sorted(frame[key].unique()):
            names.append((key, str(level)))
            members.append(np.flatnonzero(frame[key].eq(level)))
    row = np.concatenate([np.full(len(m), i) for i, m in enumerate(members)])
    col = np.concatenate(members)
    matrix = sparse.csr_matrix((np.ones(len(row)), (row, col)), shape=(len(names), len(frame)))
    return names, matrix


def support_flags(train, scenario, variables):
    rows = []
    for state, values in scenario.groupby("ProjectState"):
        t = train.loc[train.ProjectState.eq(state)]
        for _, obs in values.iterrows():
            for col in variables:
                local_min, local_max = t[col].min(), t[col].max()
                global_min, global_max = train[col].min(), train[col].max()
                rows.append({"ProjectState": state, "scenario": obs.scenario, "feature": col,
                             "value": obs[col], "state_min": local_min, "state_max": local_max,
                             "global_min": global_min, "global_max": global_max,
                             "outside_state_support": bool(obs[col] < local_min or obs[col] > local_max),
                             "outside_global_support": bool(obs[col] < global_min or obs[col] > global_max)})
    return pd.DataFrame(rows)


def summaries(x, coefficients, groups, ead, lgd, guarantee, batch=16):
    n_groups, n_draws = groups.shape[0], len(coefficients)
    result = np.zeros((n_groups, n_draws, 4))
    loss_weight = ead * lgd
    weights = [np.ones(len(ead)), loss_weight, loss_weight * guarantee, loss_weight * (1 - guarantee)]
    for start in range(0, n_draws, batch):
        p = expit(np.asarray(x @ coefficients[start:start + batch].T))
        for m, weight in enumerate(weights):
            result[:, start:start + batch, m] = groups @ (p * weight[:, None])
    counts = np.asarray(groups.sum(axis=1)).ravel()
    result[:, :, 0] /= counts[:, None]
    return result


def stress_all(root):
    cfg = config(root)
    f = active_data(root)
    train, reference = f.loc[f.role.eq("train")], f.loc[f.role.eq("reference")].copy()
    # PD remains eligible even if guarantee is invalid; losses require a valid share.
    valid = reference.guarantee_share.between(0, 1)
    table(root, "loss_population", [{"role": "reference", "pd_eligible": len(reference),
          "valid_loss_n": int(valid.sum()), "invalid_guarantee_excluded_from_loss_only": int((~valid).sum()),
          "ead_definition": EAD_LABEL, "lgd_definition": LGD_LABEL, "allocation": SPLIT_LABEL}])
    reference = reference.loc[valid].reset_index(drop=True)
    mappings = {}
    for name, downturn, capped in [("primary", False, False), ("capped", False, True), ("downturn", True, False)]:
        lgd_frame, mappings[name] = lgd_tables(train, downturn, capped)
        table(root, f"lgd_{name}", lgd_frame)
    u, hp = load(root)
    scenario = scenarios(u, hp)
    names, groups = group_matrix(reference)
    counts = np.asarray(groups.sum(axis=1)).ravel()
    ead = reference.GrossApproval.to_numpy()
    guarantee = reference.guarantee_share.to_numpy()
    exposures = np.asarray(groups @ ead).ravel()
    rows, associations, coefficients_rows, status = [], [], [], []
    support_rows = []
    basepath = root / "models/g2-2026-10-08"
    for variant in ["layer2", "layer2_term", "layer2_peak"]:
        variables = PEAK_MACRO if variant.endswith("peak") else MACRO
        flags = support_flags(train, scenario, variables)
        flags["variant"] = variant
        table(root, f"scenario_support_{variant}", flags)
        for scenario_name, group_flags in flags.groupby("scenario"):
            for scope, column in [("state", "outside_state_support"), ("global", "outside_global_support")]:
                states = group_flags.loc[group_flags[column], "ProjectState"].unique()
                flagged = reference.ProjectState.isin(states)
                support_rows.append({"variant": variant, "scenario": scenario_name, "scope": scope,
                    "flagged_states": len(states), "flagged_loan_n": int(flagged.sum()),
                    "reference_n": len(reference), "flagged_loan_fraction": float(flagged.mean()),
                    "flagged_approval_usd": float(reference.loc[flagged, "GrossApproval"].sum()),
                    "reference_approval_usd": float(reference.GrossApproval.sum()),
                    "definition": "univariate training min/max; not joint-support proof", "ead_definition": EAD_LABEL})
        bundle = joblib.load(basepath / f"{variant}_logit.joblib")
        if not bundle["status"]["converged"]:
            status.append({"variant": variant, "supported": False, "reason": "Frozen unpenalized fit failed; no substituted stress estimate"})
            continue
        design = joblib.load(basepath / f"{variant}_design.joblib")
        model = bundle["model"]
        coefficients, min_eigen = coefficient_draws(model, cfg["bootstrap_draws"], cfg["seed"])
        feature_names = np.asarray(design.names)[design.keep]
        for index, name in enumerate(feature_names):
            se = float(np.sqrt(max(model.covariance[index, index], 0)))
            coefficients_rows.append({"variant": variant, "feature": name, "coefficient": model.beta[index],
                 "clustered_se": se, "lower": model.beta[index] - 1.96 * se,
                 "upper": model.beta[index] + 1.96 * se, "interpretation": "association; numeric features standardized",
                 "states": model.diagnostics["clusters"]})
        for scenario_name in ["baseline", "adverse"]:
            flagged_states = flags.loc[flags.scenario.eq(scenario_name) & flags.outside_state_support, "ProjectState"].unique()
            status.append({"variant": variant, "scenario": scenario_name, "supported": True,
                 "minimum_covariance_eigenvalue": min_eigen,
                 "state_support_flagged_states": len(flagged_states),
                 "reference_loans_in_flagged_states": int(reference.ProjectState.isin(flagged_states).sum()),
                 "flagged_approval_dollars": float(reference.loc[reference.ProjectState.isin(flagged_states), "GrossApproval"].sum()),
                 "reason": "Computed without truncating out-of-support scenario values"})
        scenario_results = {}
        for scenario_name in ["baseline", "adverse"]:
            inputs = reference.drop(columns=MACRO + ["peak_du"]).merge(
                scenario.loc[scenario.scenario.eq(scenario_name)].drop(columns="scenario"),
                on="ProjectState", how="left", sort=False, validate="many_to_one")
            if not inputs.row_id.equals(reference.row_id):
                raise ValueError("Scenario application changed portfolio identity/order")
            x = design.transform(inputs, reduced=True)
            for severity in (["primary", "capped", "downturn"] if variant == "layer2" and scenario_name == "adverse" else ["primary"]):
                result = summaries(x, coefficients, groups, ead, assign_lgd(reference, mappings[severity]), guarantee)
                scenario_results[(scenario_name, severity)] = result
                for g, (group, value) in enumerate(names):
                    for metric, col in [("pd", 0), ("expected_loss_usd", 1), ("sba_loss_usd", 2), ("lender_loss_usd", 3), ("loss_rate", 1)]:
                        values = result[g, :, col] / exposures[g] if metric == "loss_rate" else result[g, :, col]
                        lo, hi = np.quantile(values[1:], [.025, .975])
                        rows.append({"variant": variant, "scenario": scenario_name, "lgd_variant": severity,
                            "group": group, "group_value": value, "metric": metric, "value": values[0],
                            "lower": lo, "upper": hi, "n": int(counts[g]), "approval_exposure_usd": exposures[g],
                            "coefficient_draws": cfg["bootstrap_draws"], "ead_definition": EAD_LABEL,
                            "lgd_definition": LGD_LABEL, "allocation": SPLIT_LABEL,
                            "uncertainty": "conditional on fixed portfolio, LGD and paths; state-cluster coefficient draws"})
        difference = scenario_results[("adverse", "primary")] - scenario_results[("baseline", "primary")]
        for g, (group, value) in enumerate(names):
            for metric, col in [("pd_change_pp", 0), ("expected_loss_change_usd", 1), ("sba_loss_change_usd", 2), ("lender_loss_change_usd", 3)]:
                vals = difference[g, :, col] * (100 if col == 0 else 1)
                lo, hi = np.quantile(vals[1:], [.025, .975])
                rows.append({"variant": variant, "scenario": "adverse_minus_baseline", "lgd_variant": "primary",
                   "group": group, "group_value": value, "metric": metric, "value": vals[0],
                   "lower": lo, "upper": hi, "n": int(counts[g]), "approval_exposure_usd": exposures[g],
                   "coefficient_draws": cfg["bootstrap_draws"], "ead_definition": EAD_LABEL,
                   "lgd_definition": LGD_LABEL, "allocation": SPLIT_LABEL,
                   "uncertainty": "paired conditional coefficient draws"})
        exposure_feature = "peak_du" if variant.endswith("peak") else "du"
        pos = np.flatnonzero(feature_names == exposure_feature)
        if len(pos) != 1:
            raise ValueError("Unemployment association not identifiable in the frozen design")
        native_scale = design.scale[design.numeric.index(exposure_feature)]
        observed_x = design.transform(reference, reduced=True)
        effects = np.zeros((len(names), len(coefficients)))
        for begin in range(0, len(coefficients), 16):
            chunk = coefficients[begin:begin + 16]
            eta = np.asarray(observed_x @ chunk.T)
            delta = expit(eta + chunk[:, pos[0]][None, :] / native_scale) - expit(eta)
            effects[:, begin:begin + 16] = 100 * (groups @ delta) / counts[:, None]
        for g, (group, value) in enumerate(names):
            lo, hi = np.quantile(effects[g, 1:], [.025, .975])
            associations.append({"variant": variant, "group": group, "group_value": value,
                 "n": int(counts[g]), "evaluation_portfolio": "2006 observed macro paths",
                 "change": f"+1 pp {exposure_feature}", "pd_change_pp": effects[g, 0],
                 "lower": lo, "upper": hi, "interpretation": "conditional association, not causal"})
    table(root, "stress_results", pd.DataFrame(rows, columns=["variant", "scenario", "lgd_variant", "group", "group_value", "metric", "value", "lower", "upper", "n", "approval_exposure_usd", "coefficient_draws", "ead_definition", "lgd_definition", "allocation", "uncertainty"]))
    table(root, "macro_associations", pd.DataFrame(associations, columns=["variant", "group", "group_value", "n", "evaluation_portfolio", "change", "pd_change_pp", "lower", "upper", "interpretation"]))
    table(root, "layer2_coefficients", pd.DataFrame(coefficients_rows, columns=["variant", "feature", "coefficient", "clustered_se", "lower", "upper", "interpretation", "states"]))
    table(root, "stress_status", status)
    table(root, "scenario_support_summary", support_rows)
    write_json(root / "results/g2-2026-10-08/conditional_sensitivities.json", {
        "old_extract_ccf": {"done": False, "reason": "G1 licence and exact administrative cutoff unverified; maturity-qualified population cannot be established. No extract CSV acquired or substituted."},
        "urban_rural": {"done": False, "reason": "Not disclosed in primary source; no unverified geographic crosswalk"},
        "initial_interest_rate": {"done": False, "reason": "Entire frozen training cohort missing; coefficient is unidentified"},
    })


def secondary_tree_scenarios(root):
    """Descriptive fixed-tree scenario projections; never replace the primary logit.

    No coefficient-resampling interval is claimed for a tree ensemble. These are
    explicitly secondary checks, alongside failed primary stress status.
    """
    f = active_data(root)
    train = f.loc[f.role.eq("train")]
    reference = f.loc[f.role.eq("reference") & f.guarantee_share.between(0, 1)].copy()
    mappings = {}
    for name, down, cap in [("primary", False, False), ("capped", False, True), ("downturn", True, False)]:
        _, mappings[name] = lgd_tables(train, down, cap)
    u, h = load(root)
    scenario = scenarios(u, h)
    names, groups = group_matrix(reference)
    count = np.asarray(groups.sum(axis=1)).ravel()
    ead = reference.GrossApproval.to_numpy()
    g = reference.guarantee_share.to_numpy()
    exposure = np.asarray(groups @ ead).ravel()
    rows = []
    base = root / "models/g2-2026-10-08"
    for variant in ["layer2", "layer2_term"]:
        bundle = joblib.load(base / f"{variant}_lightgbm.joblib")
        if not bundle["status"]["converged"]:
            continue
        design = joblib.load(base / f"{variant}_design.joblib")
        for name in ["baseline", "adverse"]:
            inputs = reference.drop(columns=MACRO + ["peak_du"]).merge(
                scenario.loc[scenario.scenario.eq(name)].drop(columns="scenario"),
                on="ProjectState", how="left", sort=False, validate="many_to_one")
            if not inputs.row_id.reset_index(drop=True).equals(reference.row_id.reset_index(drop=True)):
                raise ValueError("Secondary scenario altered reference portfolio")
            # Macro robustness uses its frozen 2003H2 calibration; logit primary stays uncalibrated.
            p = bundle["calibrator"].predict(bundle["model"].predict(design.tree(inputs)))
            for severity in (["primary", "capped", "downturn"] if name == "adverse" and variant == "layer2" else ["primary"]):
                weight = assign_lgd(reference, mappings[severity]) * ead
                total = np.asarray(groups @ (p * weight)).ravel()
                sba = np.asarray(groups @ (p * weight * g)).ravel()
                lender = np.asarray(groups @ (p * weight * (1 - g))).ravel()
                pd_mean = np.asarray(groups @ p).ravel() / count
                for j, (group, value) in enumerate(names):
                    rows.append({"variant": variant, "family": "LightGBM secondary robustness",
                       "scenario": name, "lgd_variant": severity, "group": group, "group_value": value,
                       "n": int(count[j]), "pd": pd_mean[j], "approval_exposure_usd": exposure[j],
                       "expected_loss_usd": total[j], "sba_loss_usd": sba[j], "lender_loss_usd": lender[j],
                       "loss_rate": total[j] / exposure[j], "ead_definition": EAD_LABEL,
                       "lgd_definition": LGD_LABEL, "allocation": SPLIT_LABEL,
                       "uncertainty": "Point projection only; tree coefficient resampling unavailable",
                       "primary_status": "Not a substitute for failed primary unpenalized logit"})
    table(root, "stress_lightgbm_secondary", rows)
