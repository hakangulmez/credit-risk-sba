"""Sequential denominator accounting, labels, and fixed chronological roles."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .io import sha256, table
from .macro import crosswalk

SOURCE_COLUMNS = [
    "AsOfDate", "Program", "GrossApproval", "SBAGuaranteedApproval", "ApprovalDate",
    "FirstDisbursementDate", "ProcessingMethod", "InitialInterestRate",
    "FixedorVariableInterestInd", "TermInMonths", "NaicsCode", "FranchiseCode",
    "ProjectState", "BusinessType", "BusinessAge", "LoanStatus", "PaidInFullDate",
    "ChargeOffDate", "GrossChargeOffAmount", "RevolverStatus", "JobsSupported",
]
NUMERIC_SOURCE = ["GrossApproval", "SBAGuaranteedApproval", "InitialInterestRate",
                  "TermInMonths", "JobsSupported", "GrossChargeOffAmount"]
CAT = ["ProcessingMethod", "FixedorVariableInterestInd", "naics2", "BusinessType",
       "BusinessAge", "franchise", "loan_type", "ProjectState"]
NUM = ["log_approval", "guarantee_share", "InitialInterestRate", "log_jobs"]
ALLOWLIST = set(NUM + CAT + ["TermInMonths", "u0", "du", "h0", "dh", "peak_du", "year_trend"])


def normalize(frame: pd.DataFrame, snapshot: str, states: set[str]):
    f = frame.copy()
    for col in f.select_dtypes(include=["str", "object", "string"]).columns:
        f[col] = f[col].fillna("").astype(str).str.strip()
    f["LoanStatus"] = f.LoanStatus.str.replace(r"\s+", "", regex=True)
    for col in NUMERIC_SOURCE:
        f[col] = pd.to_numeric(f[col], errors="coerce")
    datecols = ["ApprovalDate", "FirstDisbursementDate", "PaidInFullDate", "ChargeOffDate"]
    invalid_date = np.zeros(len(f), dtype=bool)
    for col in datecols:
        source = f[col]
        converted = pd.to_datetime(source, format="%Y-%m-%d", errors="coerce")
        invalid_date |= (source.ne("") & converted.isna()).to_numpy()
        f[col] = converted
    f["d"] = f.FirstDisbursementDate
    f["w"] = f.d + pd.DateOffset(months=36)
    cutoff = pd.Timestamp(snapshot)
    flags = {
        "wrong_program": f.Program.ne("7A"),
        "cancelled_or_committed": f.LoanStatus.isin(["CANCLD", "COMMIT"]),
        "unknown_status": ~f.LoanStatus.isin(["PIF", "CHGOFF", "EXEMPT", "CANCLD", "COMMIT"]),
        "missing_disbursement": f.d.isna(),
        "incomplete_window": f.w.gt(cutoff),
        "invalid_approval_amount": f.GrossApproval.isna() | f.GrossApproval.le(0),
        "unmapped_state": ~f.ProjectState.isin(states),
        "date_or_status_contradiction": pd.Series(invalid_date, index=f.index)
        | f.d.lt(f.ApprovalDate) | f.ChargeOffDate.lt(f.d) | f.PaidInFullDate.lt(f.d)
        | f[datecols].apply(lambda dates: dates.gt(cutoff)).any(axis=1)
        | (f.LoanStatus.eq("CHGOFF") & f.ChargeOffDate.isna())
        | (~f.LoanStatus.eq("CHGOFF") & f.ChargeOffDate.notna())
        | (~f.LoanStatus.eq("PIF") & f.PaidInFullDate.notna()),
    }
    remaining = pd.Series(True, index=f.index)
    waterfall = [{"step": "all_source_rows", "excluded": 0, "remaining": len(f)}]
    overlaps = []
    for name, flag in flags.items():
        overlaps.append({"flag": name, "n": int(flag.sum())})
        removed = remaining & flag
        remaining &= ~flag
        waterfall.append({"step": name, "excluded": int(removed.sum()),
                          "remaining": int(remaining.sum())})
    f["Y"] = (f.ChargeOffDate.ge(f.d) & f.ChargeOffDate.le(f.w)).astype("int8")
    f["year"] = f.d.dt.year
    return f.loc[remaining].copy(), waterfall, overlaps


def roles(f: pd.DataFrame) -> pd.Series:
    year = f.d.dt.year
    month = f.d.dt.month
    return pd.Series(np.select([
        year.between(1991, 2002), year.eq(2003) & month.le(6),
        year.eq(2003) & month.ge(7), year.eq(2006), year.isin([2004, 2005]),
        year.between(2007, 2009), year.between(2011, 2013),
    ], ["train", "tune", "calibrate", "reference", "buffer", "crisis", "oot"],
        default="outside_frozen_cohorts"), index=f.index)


def features(f: pd.DataFrame) -> pd.DataFrame:
    f = f.copy()
    f["log_approval"] = np.log(f.GrossApproval)
    f["guarantee_share"] = (f.SBAGuaranteedApproval / f.GrossApproval)
    f.loc[~f.guarantee_share.between(0, 1), "guarantee_share"] = np.nan
    for col in ["InitialInterestRate", "TermInMonths", "JobsSupported"]:
        f.loc[f[col].lt(0), col] = np.nan
    f["log_jobs"] = np.log1p(f.JobsSupported)
    naics = f.NaicsCode.str.replace(r"\.0$", "", regex=True)
    f["naics2"] = naics.where(naics.str.fullmatch(r"\d{6}"), "").str[:2]
    f["loan_type"] = f.RevolverStatus.map({"N": "term", "Y": "revolving", "0": "term", "1": "revolving"}).fillna("unknown")
    franchise = f.FranchiseCode.str.replace(r"\.0$", "", regex=True)
    f["franchise"] = np.select([franchise.eq(""), franchise.isin(["00000", "000000"])],
                                ["missing", "absent"], default="present")
    f["size_band"] = pd.cut(f.GrossApproval, [-np.inf, 150000, 350000, 1000000, np.inf],
                            labels=["<=150k", "150k-350k", "350k-1m", ">1m"]).astype(str)
    age = f.BusinessAge.str.lower()
    f["age_group"] = np.select([
        age.str.contains("change of ownership"), age.eq(""),
        age.str.contains("unanswered"),
        age.str.contains("startup|new business|new, less|2 or less", regex=True),
    ], ["change_of_ownership", "missing", "unanswered", "new"], default="existing")
    f["maturity_group"] = np.select([f.TermInMonths.isna(), f.TermInMonths.ge(240)],
                                    ["missing", ">=240_months"], default="<240_months")
    f["year_trend"] = f.year - 2000
    for col in CAT:
        f[col] = f[col].replace("", "__missing__").fillna("__missing__")
    return f


def build(root: Path, snapshot: str) -> pd.DataFrame:
    manifest = json.loads((root / "docs/g1_foia_manifest_2026-06-30.json").read_text())
    chunks = []
    states = set(crosswalk(root).values())
    waterfalls, overlaps = [], []
    total_rows = 0
    for item in manifest["files"]:
        path = root / item["relative_raw_path"]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".part")
            with requests.get(item["url"], stream=True, timeout=(15, 60)) as response:
                response.raise_for_status()
                received = 0
                with temporary.open("wb") as stream:
                    for block in response.iter_content(chunk_size=16 * 1024 * 1024):
                        received += len(block)
                        if received > item["bytes"]:
                            raise ValueError("FOIA download exceeded the frozen file size")
                        stream.write(block)
            if received != item["bytes"] or sha256(temporary) != item["sha256"]:
                raise ValueError("FOIA download failed frozen size/hash verification")
            temporary.replace(path)
        if sha256(path) != item["sha256"]:
            raise ValueError(f"Frozen FOIA hash mismatch: {path.name}")
        raw = pd.read_csv(path, usecols=SOURCE_COLUMNS, dtype=str, keep_default_na=False)
        raw["row_id"] = path.name + ":" + pd.Series(np.arange(len(raw))).astype(str)
        eligible, waterfall, flags = normalize(raw, snapshot, states)
        total_rows += len(raw)
        for row in waterfall:
            row["file"] = path.name
            waterfalls.append(row)
        for row in flags:
            row["file"] = path.name
            overlaps.append(row)
        chunks.append(eligible)
        print(f"FOIA {path.name}: {len(raw)} -> {len(eligible)} eligible", flush=True)
    table(root, "sample_waterfall_by_file", waterfalls)
    total = pd.DataFrame(waterfalls).groupby("step", sort=False)[["excluded", "remaining"]].sum().reset_index()
    table(root, "sample_waterfall", total)
    table(root, "exclusion_flags_overlapping", overlaps)
    f = features(pd.concat(chunks, ignore_index=True))
    f["role"] = roles(f)
    if not f.row_id.is_unique:
        raise ValueError("Synthetic file/row IDs not unique")
    table(root, "cohort_status_counts", f.groupby(["year", "LoanStatus", "role"], dropna=False)
          .agg(n=("Y", "size"), recorded_charge_offs_36m=("Y", "sum")).reset_index())
    table(root, "frozen_split_counts", f.groupby("role").agg(
        n=("Y", "size"), recorded_charge_offs_36m=("Y", "sum"),
        earliest_d=("d", "min"), latest_d=("d", "max"), latest_window=("w", "max"),
    ).reset_index())
    table(root, "predictor_missingness", [{"role": role, "feature": col,
         "n": len(g), "missing": int(g[col].isna().sum())} for role, g in f.groupby("role")
         for col in NUM + ["TermInMonths"]])
    key = [c for c in SOURCE_COLUMNS if c != "AsOfDate"]
    table(root, "row_identity_qa", [{"raw_rows": total_rows, "eligible_rows": len(f),
          "unique_file_row_ids": f.row_id.nunique(),
          "indistinguishable_disclosed_nonidentifier_rows": int(f.duplicated(key, keep=False).sum()),
          "action": "No deduplication: source lacks a stable loan ID; these fields cannot prove identity"}])
    private = root / "data/derived/g2-2026-10-08"
    private.mkdir(parents=True, exist_ok=True)
    f.to_parquet(private / "eligible.parquet", index=False)
    return f
