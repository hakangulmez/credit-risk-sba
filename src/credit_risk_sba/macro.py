"""Direct-agency macro inputs, exact frozen alignment, and fixed scenarios."""
import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .io import sha256, write_json

MACRO = ["u0", "du", "h0", "dh"]
PEAK_MACRO = ["u0", "peak_du", "h0", "dh"]


def crosswalk(root: Path) -> dict[str, str]:
    pairs = re.findall(
        r"\|[^\n|]+\|\s*(LASST\d+)\s*\|\s*([A-Z]{2})\s*\|",
        (root / "docs/MACRO_SERIES.md").read_text(),
    )
    if len(pairs) != 51:
        raise ValueError("Expected the verified 51-state crosswalk")
    return dict(pairs)


def acquire(root: Path) -> None:
    """Nine bounded, cached requests; no API key or FRED observations."""
    dest = root / "data/raw/macros"
    dest.mkdir(parents=True, exist_ok=True)
    mapping = crosswalk(root)
    manifest_path = root / "docs/g2_macro_manifest.json"
    frozen = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    identifiers = list(mapping)
    evidence = []
    observations = []
    for start, end in [(1990, 1999), (2000, 2009), (2010, 2016)]:
        for batch in range(3):
            wanted = identifiers[batch * 25 : (batch + 1) * 25]
            path = dest / f"bls_{start}_{end}_{batch}.json"
            payload = {"seriesid": wanted, "startyear": str(start), "endyear": str(end)}
            if not path.exists():
                response = requests.post(
                    "https://api.bls.gov/publicAPI/v2/timeseries/data/",
                    json=payload, timeout=45,
                )
                response.raise_for_status()
                if len(response.content) > 8_000_000:
                    raise ValueError("Unexpectedly large BLS response")
                obj = response.json()
                if obj.get("status") != "REQUEST_SUCCEEDED":
                    raise ValueError(f"BLS request failed: {obj.get('message')}")
                path.write_bytes(response.content)
            obj = json.loads(path.read_text())
            found = set()
            for series in obj["Results"]["series"]:
                sid = series["seriesID"]
                found.add(sid)
                for obs in series["data"]:
                    month = int(obs["period"][1:])
                    if 1 <= month <= 12:
                        observations.append({"state": mapping[sid],
                                             "month": int(obs["year"]) * 12 + month - 1,
                                             "u": float(obs["value"]), "series": sid})
            if found != set(wanted):
                raise ValueError("BLS returned an incomplete series batch")
            evidence.append({"file": path.name, "request": payload,
                             "sha256": sha256(path), "bytes": path.stat().st_size,
                             "messages": obj.get("message", [])})
            print(f"BLS verified {start}-{end} batch {batch + 1}/3", flush=True)
    unemployment = pd.DataFrame(observations).sort_values(["state", "month"])
    if unemployment.duplicated(["state", "month"]).any():
        raise ValueError("Duplicate unemployment month")
    expected = 51 * 27 * 12
    if len(unemployment) != expected:
        raise ValueError(f"Incomplete BLS coverage: {len(unemployment)} != {expected}")
    canonical = unemployment[["state", "month", "u"]].to_csv(index=False, float_format="%.8g")
    observation_hash = hashlib.sha256(canonical.encode()).hexdigest()
    if frozen.get("bls_observation_sha256", observation_hash) != observation_hash:
        raise ValueError("BLS revised observations differ from frozen G2 vintage; restore archived inputs")
    unemployment.to_parquet(dest / "unemployment.parquet", index=False)
    hpi_path = dest / "hpi_at_state.csv"
    if not hpi_path.exists():
        cached = root.parent / ".cache/credit-risk-gate1/hpi_at_state.csv"
        if cached.exists():
            if sha256(cached) != "b6bf3687c230c2ad008657fdb0c2b7489b5f99b6d1193f72c46c68d88df83d90":
                raise ValueError("G1 FHFA frozen-file hash mismatch")
            shutil.copyfile(cached, hpi_path)
        else:
            response = requests.get("https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv", timeout=45)
            response.raise_for_status()
            if len(response.content) > 1_000_000:
                raise ValueError("Unexpected FHFA file size")
            if __import__("hashlib").sha256(response.content).hexdigest() != "b6bf3687c230c2ad008657fdb0c2b7489b5f99b6d1193f72c46c68d88df83d90":
                raise ValueError("FHFA current release differs from frozen vintage; restore authorized archived input")
            hpi_path.write_bytes(response.content)
    if sha256(hpi_path) != "b6bf3687c230c2ad008657fdb0c2b7489b5f99b6d1193f72c46c68d88df83d90":
        raise ValueError("Frozen FHFA input hash mismatch")
    write_json(root / "docs/g2_macro_manifest.json", {
        "access_date": "2026-10-08", "bls_source": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        "bls_files": evidence, "bls_rows": len(unemployment), "years": [1990, 2016],
        "bls_observation_sha256": observation_hash,
        "states": 51, "macros_are_revised_not_real_time": True,
        "fhfa_source": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv",
        "fhfa_sha256": sha256(hpi_path), "fhfa_frozen_at_g1": True,
        "notice": "This product uses FHFA data but is neither endorsed nor certified by FHFA.",
    })


def panel(unemployment: pd.DataFrame, hpi: pd.DataFrame) -> pd.DataFrame:
    """One state/origin-month record, including the full 37-level peak path."""
    frames = []
    for state, group in unemployment.groupby("state", sort=True):
        group = group.set_index("month").sort_index()
        idx = np.arange(int(group.index.min()), int(group.index.max()) + 1)
        u = group.u.reindex(idx)
        future = pd.concat([u.shift(-k) for k in range(37)], axis=1)
        q = idx // 3
        hp = hpi.loc[hpi.state == state].set_index("quarter").hpi
        h_start = hp.reindex(q).to_numpy()
        h_previous = hp.reindex(q - 4).to_numpy()
        h_end = hp.reindex(q + 12).to_numpy()
        frames.append(pd.DataFrame({
            "ProjectState": state, "month": idx, "u0": u.to_numpy(),
            "du": (u.shift(-36) - u).to_numpy(),
            "peak_du": (future.max(axis=1) - u).where(future.notna().all(axis=1)).to_numpy(),
            "h0": 100 * np.log(h_start / h_previous),
            "dh": 100 * np.log(h_end / h_start),
        }))
    return pd.concat(frames, ignore_index=True)


def load(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    u = pd.read_parquet(root / "data/raw/macros/unemployment.parquet")
    hp = pd.read_csv(root / "data/raw/macros/hpi_at_state.csv", header=None,
                     names=["state", "year", "q", "hpi"])
    hp["quarter"] = hp.year * 4 + hp.q - 1
    return u, hp


def join(loans: pd.DataFrame, unemployment: pd.DataFrame, hpi: pd.DataFrame) -> pd.DataFrame:
    loans = loans.copy()
    loans["month"] = loans.d.dt.year * 12 + loans.d.dt.month - 1
    return loans.merge(panel(unemployment, hpi), on=["ProjectState", "month"],
                       how="left", validate="many_to_one")


def scenarios(unemployment: pd.DataFrame, hpi: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state in sorted(unemployment.state.unique()):
        u = unemployment.loc[unemployment.state == state].set_index("month").u
        hp = hpi.loc[hpi.state == state].set_index("quarter").hpi
        quarters = np.arange(2004 * 4, 2007 * 4)
        h0 = float(np.mean(100 * np.log(hp.reindex(quarters).to_numpy() /
                                        hp.reindex(quarters - 4).to_numpy())))
        path = u.reindex(np.arange(2007 * 12, 2010 * 12 + 1))
        if path.isna().any():
            raise ValueError("Adverse scenario lacks an endpoint or interior month")
        rows.extend([
            {"ProjectState": state, "scenario": "baseline",
             "u0": float(u.reindex(np.arange(2004 * 12, 2007 * 12)).mean()),
             "du": 0.0, "peak_du": 0.0, "h0": h0, "dh": 3 * h0},
            {"ProjectState": state, "scenario": "adverse", "u0": float(path.iloc[0]),
             "du": float(path.iloc[-1] - path.iloc[0]),
             "peak_du": float(path.max() - path.iloc[0]),
             "h0": float(100 * np.log(hp.loc[2007 * 4] / hp.loc[2006 * 4])),
             "dh": float(100 * np.log(hp.loc[2010 * 4] / hp.loc[2007 * 4]))},
        ])
    result = pd.DataFrame(rows)
    if result[MACRO + ["peak_du"]].isna().any().any():
        raise ValueError("Incomplete scenarios")
    return result
