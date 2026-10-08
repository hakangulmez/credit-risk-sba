"""Append-only BLS acquisition and frozen vintage protection."""

import json

import numpy as np
import pandas as pd
import pytest

from credit_risk_sba import bis_data
from credit_risk_sba.bis_data import NAME, macros
from credit_risk_sba.io import sha256


def source_fixture(tmp_path, monkeypatch, failure=None):
    states = [f"S{i:02}" for i in range(51)]
    ids = {f"BLS{i:02}": state for i, state in enumerate(states)}
    old = pd.DataFrame(
        [
            {"state": state, "month": 2016 * 12 + m, "u": 3.0 + i / 10, "series": f"BLS{i:02}"}
            for i, state in enumerate(states)
            for m in range(12)
        ]
    )
    hp = pd.DataFrame({"state": states, "quarter": 2017 * 4, "hpi": 100.0})
    (tmp_path / "data/raw/macros").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    old.to_parquet(tmp_path / "data/raw/macros/unemployment.parquet", index=False)
    hp.to_csv(tmp_path / "data/raw/macros/hpi_at_state.csv", index=False)
    (tmp_path / "docs/g2_macro_manifest.json").write_text("{}")
    monkeypatch.setattr(bis_data, "load", lambda root: (old, hp))
    monkeypatch.setattr(bis_data, "crosswalk", lambda root: ids)
    requests = []

    class Response:
        def __init__(self, payload):
            series = []
            for sid in payload["seriesid"]:
                months = (
                    range(1, 12) if failure == "missing_month" and sid == "BLS00" else range(1, 13)
                )
                observations = [
                    {
                        "year": "2018" if failure == "wrong_year" else "2017",
                        "period": f"M{m:02}",
                        "value": "4.5",
                    }
                    for m in months
                ]
                observations.append({"year": "2017", "period": "M13", "value": "4.5"})
                series.append({"seriesID": sid, "data": observations})
            if failure == "missing_state":
                series = series[:-1]
            self.obj = {
                "status": "FAIL" if failure == "status" else "REQUEST_SUCCEEDED",
                "Results": {"series": series},
            }
            self.content = json.dumps(self.obj).encode()

        def raise_for_status(self):
            return None

        def json(self):
            return self.obj

    def post(endpoint, **kwargs):
        assert endpoint == "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        assert kwargs["json"]["startyear"] == kwargs["json"]["endyear"] == "2017"
        assert len(kwargs["json"]["seriesid"]) <= 25
        requests.append(kwargs["json"])
        return Response(kwargs["json"])

    monkeypatch.setattr(bis_data.requests, "post", post)
    return old, requests


def test_only_missing_2017_is_added_and_resume_does_not_retrieve(tmp_path, monkeypatch):
    old, requests = source_fixture(tmp_path, monkeypatch)
    frozen = sha256(tmp_path / "data/raw/macros/unemployment.parquet")
    result, _ = macros(tmp_path)
    assert len(requests) == 3 and len(result) == len(old) + 612
    pd.testing.assert_frame_equal(
        result.loc[result.month.lt(2017 * 12)].reset_index(drop=True), old
    )
    assert sha256(tmp_path / "data/raw/macros/unemployment.parquet") == frozen
    result2, _ = macros(tmp_path)
    assert len(requests) == 3
    pd.testing.assert_frame_equal(result, result2)
    manifest = json.loads((tmp_path / "results" / NAME / "source_manifest.json").read_text())
    assert not manifest["FRED_acquisition"] and not manifest["FHFA_refresh"]
    assert manifest["added_BLS_2017_rows"] == 612
    for item in manifest["additions"]:
        assert item["sha256"] == sha256(tmp_path / item["file"])
        assert item["retrieval"]["retrieved_at"]


@pytest.mark.parametrize(
    "failure,message",
    [
        ("wrong_year", "unauthorized"),
        ("missing_state", "state batch"),
        ("missing_month", "Incomplete 2017"),
        ("status", "BLS failed"),
    ],
)
def test_macro_addition_fails_closed(tmp_path, monkeypatch, failure, message):
    source_fixture(tmp_path, monkeypatch, failure)
    with pytest.raises(ValueError, match=message):
        macros(tmp_path)


def test_json_never_records_nonfinite_as_valid(tmp_path):
    bis_data.js(
        tmp_path / "result.json",
        {
            "a": np.inf,
            "b": np.float64(np.nan),
            "c": np.int64(5),
            "d": np.bool_(True),
            "array": np.array([1.0, np.nan]),
        },
    )
    assert json.loads((tmp_path / "result.json").read_text()) == {
        "a": None,
        "b": None,
        "c": 5,
        "d": True,
        "array": [1.0, None],
    }


def test_cached_new_source_cannot_be_silently_replaced(tmp_path, monkeypatch):
    source_fixture(tmp_path, monkeypatch)
    macros(tmp_path)
    path = tmp_path / "data" / NAME / "macro/bls_2017_0.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="addition hash mismatch"):
        macros(tmp_path)
