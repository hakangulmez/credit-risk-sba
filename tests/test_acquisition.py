"""Source-contract tests exercise bounded requests without contacting providers."""
import json
from pathlib import Path

import pytest

from credit_risk_sba import macro


class Response:
    def __init__(self, payload, failure=""):
        series = []
        for sid in payload["seriesid"]:
            data = [{"year": str(year), "period": f"M{month:02}", "value": "5.0"}
                    for year in range(int(payload["startyear"]), int(payload["endyear"]) + 1)
                    for month in range(1, 13)]
            data.append({"year": payload["endyear"], "period": "M13", "value": "5.0"})
            if failure == "coverage":
                data = data[1:]
            if failure == "duplicate":
                data.append(data[0])
            series.append({"seriesID": sid, "data": data})
        if failure == "series":
            series = series[:-1]
        self.obj = {"status": "FAILED" if failure == "status" else "REQUEST_SUCCEEDED",
                    "message": [], "Results": {"series": series}}
        self.content = b"x" * 8_000_001 if failure == "size" else json.dumps(self.obj).encode()

    def raise_for_status(self):
        return None

    def json(self):
        return self.obj


def acquisition_fixture(tmp_path, monkeypatch, failure=""):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "data/raw/macros").mkdir(parents=True)
    src = Path(__file__).resolve().parents[1]
    (root / "docs/MACRO_SERIES.md").write_text((src / "docs/MACRO_SERIES.md").read_text())
    (root / "data/raw/macros/hpi_at_state.csv").write_text("synthetic HPI fixture")
    calls = []
    def post(url, json, timeout):
        assert url == "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        assert len(json["seriesid"]) <= 25
        assert int(json["endyear"]) - int(json["startyear"]) < 10
        assert timeout == 45
        assert "registrationkey" not in json
        calls.append(json)
        return Response(json, failure)
    monkeypatch.setattr(macro.requests, "post", post)
    original_sha = macro.sha256
    monkeypatch.setattr(macro, "sha256", lambda p: "b6bf3687c230c2ad008657fdb0c2b7489b5f99b6d1193f72c46c68d88df83d90" if p.name == "hpi_at_state.csv" else original_sha(p))
    return root, calls


def test_bounded_cached_agency_acquisition(tmp_path, monkeypatch):
    root, calls = acquisition_fixture(tmp_path, monkeypatch)
    macro.acquire(root)
    assert len(calls) == 9
    macro.acquire(root)
    assert len(calls) == 9  # Complete cached requests are reused, not repeated.
    manifest = json.loads((root / "docs/g2_macro_manifest.json").read_text())
    assert manifest["bls_rows"] == 16524
    assert manifest["macros_are_revised_not_real_time"]
    file = root / "data/raw/macros/bls_1990_1999_0.json"
    obj = json.loads(file.read_text())
    obj["Results"]["series"][0]["data"][0]["value"] = "15.0"
    file.write_text(json.dumps(obj))
    with pytest.raises(ValueError, match="frozen G2 vintage"):
        macro.acquire(root)


@pytest.mark.parametrize("failure,match", [("status", "request failed"), ("size", "large BLS"),
                                           ("series", "incomplete series"), ("coverage", "Incomplete BLS coverage"),
                                           ("duplicate", "Duplicate unemployment")])
def test_acquisition_fails_closed(tmp_path, monkeypatch, failure, match):
    root, _ = acquisition_fixture(tmp_path, monkeypatch, failure)
    with pytest.raises(ValueError, match=match):
        macro.acquire(root)


def test_crosswalk_fails_closed(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/MACRO_SERIES.md").write_text("not a verified state crosswalk")
    with pytest.raises(ValueError, match="51-state"):
        macro.crosswalk(tmp_path)
