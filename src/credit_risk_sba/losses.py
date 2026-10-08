"""Gross approval-denominator loss proxies; exact pro-rata public/lender split."""
import numpy as np
import pandas as pd

EAD_LABEL = "GrossApproval full-disbursement proxy; CCF=100%"
LGD_LABEL = "gross charged-off balance / GrossApproval; not net-of-recovery LGD"
SPLIT_LABEL = "pro-rata guarantee share; not observed payout or fiscal cost"


def lgd_tables(train: pd.DataFrame, downturn=False, capped=False, minimum=50):
    if not train.role.eq("train").all():
        raise ValueError("LGD may use training rows only")
    f = train.loc[train.Y.eq(1)].copy()
    if downturn:
        f = f.loc[f.year.isin([1991, 2000, 2001])].copy()
    valid = f.GrossChargeOffAmount.notna() & f.GrossChargeOffAmount.ge(0)
    f["severity"] = f.GrossChargeOffAmount.clip(upper=f.GrossApproval) if capped else f.GrossChargeOffAmount
    good = f.loc[valid]
    rows = []
    mapping = {}
    for kind in ["term", "revolving", "unknown"]:
        for band in ["<=150k", "150k-350k", "350k-1m", ">1m"]:
            cell = f.loan_type.eq(kind) & f.size_band.eq(band)
            sample = good.loc[good.loan_type.eq(kind) & good.size_band.eq(band)]
            n_cell = len(sample)
            pool = "cell"
            if len(sample) < minimum:
                sample = good.loc[good.loan_type.eq(kind)]
                pool = "loan_type"
            if len(sample) < minimum:
                sample = good
                pool = "overall_selected_training_cohorts"
            proxy = float(sample.severity.sum() / sample.GrossApproval.sum()) if len(sample) else np.nan
            mapping[(kind, band)] = proxy
            rows.append({"loan_type": kind, "size_band": band,
                         "variant": "downturn" if downturn else "capped" if capped else "primary",
                         "cohorts": "1991,2000,2001" if downturn else "1991-2002",
                         "cell_recorded_charge_offs": int(cell.sum()), "valid_cell_n": n_cell,
                         "excluded_severity_n": int((cell & ~valid).sum()),
                         "pool": pool, "pooled_n": len(sample), "lgd_proxy": proxy,
                         "ratios_above_one": int((sample.GrossChargeOffAmount > sample.GrossApproval).sum()),
                         "ead_definition": EAD_LABEL, "lgd_definition": LGD_LABEL})
    return pd.DataFrame(rows), mapping


def assign_lgd(frame, mapping):
    return np.array([mapping[(kind, band)] for kind, band in zip(frame.loan_type, frame.size_band, strict=True)])


def allocate(pd_score, lgd, ead, guarantee):
    p, l, e, g = map(np.asarray, [pd_score, lgd, ead, guarantee])
    if not (np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()):
        raise ValueError("Invalid PD")
    if not (np.isfinite(e).all() and (e > 0).all() and np.isfinite(l).all() and (l >= 0).all()):
        raise ValueError("Invalid exposure or severity")
    if not (np.isfinite(g).all() and ((g >= 0) & (g <= 1)).all()):
        raise ValueError("Invalid guarantee share")
    total = p * l * e
    sba = total * g
    lender = total * (1 - g)
    return total, sba, lender


def accepted_mask(p, row_ids, fraction=0.70):
    order = np.lexsort((np.asarray(row_ids), np.asarray(p)))
    accepted = np.zeros(len(p), dtype=bool)
    accepted[order[:int(np.floor(fraction * len(p)))]] = True
    return accepted
