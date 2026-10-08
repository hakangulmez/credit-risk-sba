"""Frozen loans and macro vintages; append only missing direct BLS 2017 levels."""

import datetime as dt
import json

import numpy as np
import pandas as pd
import requests

from .io import sha256
from .macro import MACRO, crosswalk, load, panel, scenarios

NAME = "g2-bis-2026-10-08"
VALIDATION_LABEL = "Retrospective conditional validation using realized macro paths."
LOSS_LABEL = "EAD = GrossApproval, full-disbursement proxy, CCF = 100%; gross charge-off LGD proxy; assumption-based pro-rata guarantee allocation."


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def js(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_json(value), indent=2, default=str, allow_nan=False) + "\n")


def table(root, name, rows):
    f = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    path = root / "results" / NAME / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    f.to_csv(path, index=False)
    return f


def macros(root):
    old, hp = load(root)
    mapping = crosswalk(root)
    dest = root / "data" / NAME / "macro"
    dest.mkdir(parents=True, exist_ok=True)
    existing = set(zip(old.state, old.month))
    missing = [
        sid
        for sid, state in mapping.items()
        if any((state, 2017 * 12 + m) not in existing for m in range(12))
    ]
    additions = []
    records = []
    for batch in range(0, len(missing), 25):
        ids = missing[batch : batch + 25]
        path = dest / f"bls_2017_{batch // 25}.json"
        payload = {"seriesid": ids, "startyear": "2017", "endyear": "2017"}
        if not path.exists():
            response = requests.post(
                "https://api.bls.gov/publicAPI/v2/timeseries/data/", json=payload, timeout=45
            )
            response.raise_for_status()
            if len(response.content) > 8_000_000:
                raise ValueError("BLS response exceeded frozen bound")
            obj = response.json()
            if obj.get("status") != "REQUEST_SUCCEEDED":
                raise ValueError("BLS failed: " + str(obj.get("message")))
            path.write_bytes(response.content)
            js(
                path.with_suffix(".retrieval.json"),
                {
                    "retrieved_at": dt.datetime.now(dt.UTC).isoformat(),
                    "bytes": len(response.content),
                    "sha256": sha256(path),
                },
            )
        retrieval = json.loads(path.with_suffix(".retrieval.json").read_text())
        if sha256(path) != retrieval["sha256"]:
            raise ValueError("Cached dated BLS addition hash mismatch")
        obj = json.loads(path.read_text())
        found = set()
        for series in obj["Results"]["series"]:
            sid = series["seriesID"]
            found.add(sid)
            for obs in series["data"]:
                year = int(obs["year"])
                month = int(obs["period"][1:])
                if year != 2017:
                    raise ValueError("BLS returned unauthorized reference year")
                if 1 <= month <= 12:
                    key = (mapping[sid], year * 12 + month - 1)
                    if key not in existing:
                        additions.append(
                            {
                                "state": key[0],
                                "month": key[1],
                                "u": float(obs["value"]),
                                "series": sid,
                            }
                        )
        if found != set(ids):
            raise ValueError("Incomplete BLS state batch")
        records.append(
            {
                "file": str(path.relative_to(root)),
                "request": payload,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "retrieval": json.loads(path.with_suffix(".retrieval.json").read_text()),
                "messages": obj.get("message", []),
            }
        )
    extra = pd.DataFrame(additions)
    u = (
        pd.concat([old, extra], ignore_index=True)
        .sort_values(["state", "month"])
        .reset_index(drop=True)
    )
    if u.duplicated(["state", "month"]).any():
        raise ValueError("Duplicated macro keys")
    preserved = (
        u.loc[u.month <= 2016 * 12 + 11].sort_values(["state", "month"]).reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(
        preserved, old.sort_values(["state", "month"]).reset_index(drop=True)
    )
    coverage = u.loc[u.month.between(2017 * 12, 2017 * 12 + 11)].groupby("state").size()
    if len(coverage) != 51 or not coverage.eq(12).all():
        raise ValueError("Incomplete 2017 unemployment path")
    u.to_parquet(dest / "unemployment_plus_2017.parquet", index=False)
    js(
        root / "results" / NAME / "source_manifest.json",
        {
            "existing_macro_manifest_sha256": sha256(root / "docs/g2_macro_manifest.json"),
            "frozen_unemployment_sha256": sha256(root / "data/raw/macros/unemployment.parquet"),
            "frozen_FHFA_sha256": sha256(root / "data/raw/macros/hpi_at_state.csv"),
            "added_BLS_2017_rows": len(extra),
            "additions": records,
            "frozen_observations_unchanged": True,
            "revision_vintage_qualification": "2017 levels were retrieved separately on the stated dates from revised BLS data. Earlier frozen observations are never replaced; this is a mixed retrieval vintage, not a historical real-time vintage.",
            "FHFA_refresh": False,
            "FRED_acquisition": False,
        },
    )
    return u, hp


def prepare(root):
    eligible = pd.read_parquet(root / "data/derived/g2-2026-10-08/eligible.parquet")
    u, hp = macros(root)
    p = panel(u, hp)
    # Require every HPI quarter in the window, plus the lagged annual-growth base.
    completeness = []
    for state, g in hp.groupby("state"):
        series = g.set_index("quarter").hpi
        starts = p.loc[p.ProjectState.eq(state), "month"].to_numpy() // 3
        for q in np.unique(starts):
            needed = np.r_[q - 4, np.arange(q, q + 13)]
            v = series.reindex(needed)
            completeness.append(
                {
                    "ProjectState": state,
                    "quarter": int(q),
                    "hpi_complete": bool(v.notna().all() and v.gt(0).all()),
                }
            )
    p["quarter"] = p.month // 3
    p = p.merge(pd.DataFrame(completeness), on=["ProjectState", "quarter"], validate="many_to_one")
    f = eligible.copy()
    f["month"] = f.d.dt.year * 12 + f.d.dt.month - 1
    f = f.merge(
        p.drop(columns="quarter"), on=["ProjectState", "month"], how="left", validate="many_to_one"
    )
    f["macro_complete"] = f[MACRO + ["peak_du"]].notna().all(axis=1) & f.hpi_complete.fillna(False)
    counts = (
        f.groupby("year")
        .agg(eligible=("Y", "size"), events=("Y", "sum"), macro_matched=("macro_complete", "sum"))
        .reset_index()
    )
    counts["non_events"] = counts.eligible - counts.events
    counts["macro_exclusions"] = counts.eligible - counts.macro_matched
    table(root, "cohort_counts", counts)
    table(
        root,
        "source_population_waterfall",
        pd.read_csv(root / "results/g2-2026-10-08/sample_waterfall.csv"),
    )
    summary = []
    for layer, role, a, b in [
        ("layer1", "estimation", 1991, 2002),
        ("layer1", "crisis", 2007, 2009),
        ("layer1", "additional_check", 2011, 2013),
        ("layer2", "estimation", 1991, 2009),
        ("layer2", "tree_calibration", 2010, 2010),
        ("layer2", "heldout_check", 2013, 2014),
        ("scenario", "reference", 2006, 2006),
    ]:
        rows = f.loc[f.year.between(a, b)]
        matched = rows.loc[rows.macro_complete]
        summary.append(
            {
                "layer": layer,
                "role": role,
                "years": f"{a}-{b}",
                "eligible_n": len(rows),
                "macro_excluded_n": len(rows) - len(matched),
                "n": len(matched),
                "events": int(matched.Y.sum()),
                "non_events": int(len(matched) - matched.Y.sum()),
                "earliest_disbursement": str(matched.d.min()),
                "latest_disbursement": str(matched.d.max()),
                "latest_label_window": str(matched.w.max()),
                "latest_required_unemployment_year": b + 3,
                "full_monthly_path_levels": 37,
                "full_HPI_window_quarters": 13,
                "interpretation": VALIDATION_LABEL
                if layer == "layer2"
                else "Approval-descriptor prediction"
                if layer == "layer1"
                else "Fixed scenario portfolio; included in Layer 2 estimation, not OOS validation",
            }
        )
    table(root, "final_sample_waterfall", summary)
    table(
        root,
        "initial_interest_rate_missingness",
        [
            {
                "years": f"{a}-{b}",
                "eligible_n": len(g),
                "missing_n": int(g.InitialInterestRate.isna().sum()),
                "missing_share": float(g.InitialInterestRate.isna().mean()),
                "specification": "Excluded from all shared specifications for historical comparability",
            }
            for a, b in [(1991, 2002), (1991, 2009)]
            for g in [f.loc[f.year.between(a, b)]]
        ],
    )
    # Preserve G2 reference row order and verify exact scenario values.
    old = pd.read_parquet(root / "data/derived/g2-2026-10-08/matched.parquet")
    reference_ids = old.loc[old.role.eq("reference"), "row_id"].to_numpy()
    reference = f.set_index("row_id", drop=False).loc[reference_ids].reset_index(drop=True)
    if not reference.macro_complete.all():
        raise ValueError("Fixed reference lost macro support")
    scenario = scenarios(u, hp)
    old_scenario = pd.read_csv(root / "results/g2-2026-10-08/scenario_macro_inputs.csv")
    for col in ["ProjectState", "scenario", *MACRO, "peak_du"]:
        if col in old_scenario:
            if col in ["ProjectState", "scenario"]:
                assert scenario[col].tolist() == old_scenario[col].tolist()
            else:
                np.testing.assert_allclose(scenario[col], old_scenario[col], rtol=1e-12, atol=1e-12)
    table(root, "scenario_paths", scenario)
    private = root / "data" / NAME
    private.mkdir(parents=True, exist_ok=True)
    f.loc[f.year.between(1991, 2014)].to_parquet(private / "matched.parquet", index=False)
    reference.to_parquet(private / "reference.parquet", index=False)
    return f, reference, scenario
