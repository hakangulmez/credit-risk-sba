"""Snapshot-wide timing audit, including charge-offs outside the label window."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .bis_data import NAME, js, table
from .io import sha256

CONVENTION = "(event_date - FirstDisbursementDate).days / (365.25 / 12)"


def classify(audit, metadata_verified=False):
    """A low match share never verifies approval-time measurement."""
    if metadata_verified:
        return "Verified as an approval-time value."
    charge = audit.loc[audit.LoanStatus.eq("CHGOFF") & audit.valid]
    if len(charge) >= 100 and charge.match.mean() >= 0.5:
        return "Strong evidence of later updating."
    return "Timing unverifiable."


def audit_frame(frame, raw_terms):
    f = frame.loc[frame.LoanStatus.isin(["CHGOFF", "PIF"])].copy()
    text = f.row_id.map(raw_terms).astype("string")
    missing_term = text.isna() | text.fillna("").str.strip().eq("")
    term = pd.to_numeric(text, errors="coerce").astype(float)
    finite_term = np.isfinite(term) & term.gt(0)
    event = f.ChargeOffDate.where(f.LoanStatus.eq("CHGOFF"), f.PaidInFullDate)
    missing_date = event.isna() | f.d.isna()
    valid_date = ~missing_date & event.ge(f.d)
    f["raw_term"] = term
    f["event_date"] = event
    f["elapsed_months"] = (event - f.d).dt.days / (365.25 / 12)
    f["difference_months"] = term - f.elapsed_months
    f["date_status"] = np.select(
        [missing_date, valid_date], ["missing", "valid"], default="invalid"
    )
    f["term_status"] = np.select(
        [missing_term, finite_term], ["missing", "valid"], default="invalid"
    )
    f["valid"] = valid_date & finite_term
    f["match"] = f.valid & f.difference_months.abs().le(3)
    f["charge_off_after_label_window"] = f.LoanStatus.eq("CHGOFF") & event.gt(f.w)
    f["approval_year"] = f.ApprovalDate.dt.year.astype("Int64")
    return f


def summaries(frame):
    rows = []
    groups = [("overall", "all", frame)]
    for status, g in frame.groupby("LoanStatus", dropna=False):
        groups.append(("status", str(status), g))
    for (year, kind, status), g in frame.groupby(
        ["approval_year", "loan_type", "LoanStatus"], dropna=False
    ):
        groups.append(("approval_year_loan_type_status", f"{year}|{kind}|{status}", g))
    for scope, key, g in groups:
        valid = g.loc[g.valid]
        x = valid.difference_months.to_numpy()
        row = {
            "scope": scope,
            "group": key,
            "n": len(g),
            "valid_n": len(valid),
            "date_valid_n": int(g.date_status.eq("valid").sum()),
            "term_valid_n": int(g.term_status.eq("valid").sum()),
            "date_missing_n": int(g.date_status.eq("missing").sum()),
            "date_invalid_n": int(g.date_status.eq("invalid").sum()),
            "term_missing_n": int(g.term_status.eq("missing").sum()),
            "term_invalid_n": int(g.term_status.eq("invalid").sum()),
            "missing_either_n": int(
                (g.date_status.eq("missing") | g.term_status.eq("missing")).sum()
            ),
            "invalid_either_n": int(
                (g.date_status.eq("invalid") | g.term_status.eq("invalid")).sum()
            ),
            "match_abs_le_3_n": int(valid.match.sum()),
            "match_abs_le_3_share": float(valid.match.mean()) if len(valid) else np.nan,
            "charge_off_after_label_window_n": int(g.charge_off_after_label_window.sum()),
            "elapsed_month_convention": CONVENTION,
            "difference_definition": "TermInMonths minus elapsed months",
            "verdict": classify(g),
            "metadata_or_original_vintage_verification": False,
        }
        for probability, label in [
            (0, "min"),
            (0.01, "p01"),
            (0.05, "p05"),
            (0.25, "p25"),
            (0.5, "median"),
            (0.75, "p75"),
            (0.95, "p95"),
            (0.99, "p99"),
            (1, "max"),
        ]:
            row["difference_" + label] = float(np.quantile(x, probability)) if len(x) else np.nan
        row["difference_mean"] = float(np.mean(x)) if len(x) else np.nan
        row["difference_sd"] = float(np.std(x, ddof=1)) if len(x) > 1 else np.nan
        rows.append(row)
    return rows


def run(root):
    eligible = pd.read_parquet(root / "data/derived/g2-2026-10-08/eligible.parquet")
    manifest = json.loads((root / "docs/g1_foia_manifest_2026-06-30.json").read_text())
    pieces = []
    sources = []
    for item in manifest["files"]:
        path = root / item["relative_raw_path"]
        if sha256(path) != item["sha256"]:
            raise ValueError("Term audit frozen source hash mismatch")
        raw = pd.read_csv(path, usecols=["TermInMonths"], dtype=str, keep_default_na=False)
        pieces.append(
            pd.Series(
                raw.TermInMonths.to_numpy(),
                index=path.name + ":" + pd.Series(np.arange(len(raw))).astype(str),
            )
        )
        sources.append(
            {
                "path": item["relative_raw_path"],
                "sha256": item["sha256"],
                "columns_read": ["TermInMonths"],
            }
        )
    terms = pd.concat(pieces)
    if not terms.index.is_unique or not eligible.row_id.isin(terms.index).all():
        raise ValueError("Term source row identity mismatch")
    audit = audit_frame(eligible, terms)
    private = root / "data" / NAME
    audit[
        [
            "row_id",
            "LoanStatus",
            "approval_year",
            "loan_type",
            "date_status",
            "term_status",
            "raw_term",
            "elapsed_months",
            "difference_months",
            "valid",
            "match",
            "charge_off_after_label_window",
        ]
    ].to_parquet(private / "term_audit.parquet", index=False)
    table(root, "term_audit_summary", summaries(audit))
    table(
        root,
        "term_audit_status_counts",
        audit.groupby(["LoanStatus", "date_status", "term_status"], dropna=False)
        .size()
        .rename("n")
        .reset_index(),
    )
    js(
        root / "results" / NAME / "term_audit_evidence.json",
        {
            "eligible_n": len(eligible),
            "applicable_n": len(audit),
            "verdict": classify(audit),
            "approval_time_metadata_or_vintage_evidence": "None verified. Current snapshot field description is insufficient to establish original approval-time values.",
            "elapsed_month_convention": CONVENTION,
            "primary_term_free_regardless_of_verdict": True,
            "all_charge_offs_included_even_after_36_months": True,
            "PIF_coincidence_cannot_alone_prove_updating": True,
            "sources_read_only": sources,
        },
    )


if __name__ == "__main__":
    run(Path.cwd())
