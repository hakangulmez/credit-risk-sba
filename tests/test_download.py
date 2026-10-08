"""Bounded primary-source streaming and hash rejection, with synthetic bytes."""
import json

import pytest
from test_pipeline import synthetic_repo

from credit_risk_sba import data
from credit_risk_sba.io import write_json


class Stream:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        assert chunk_size == 16 * 1024 * 1024
        yield self.payload


@pytest.mark.parametrize("corrupt", [False, True])
def test_primary_streaming_contract(tmp_path, monkeypatch, corrupt):
    synthetic_repo(tmp_path)
    path = tmp_path / "data/raw/synthetic.csv"
    payload = path.read_bytes()
    path.unlink()
    manifest_path = tmp_path / "docs/g1_foia_manifest_2026-06-30.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][0].update(url="https://data.sba.gov/synthetic-fixture.csv", bytes=len(payload))
    write_json(manifest_path, manifest)
    def get(url, stream, timeout):
        assert stream and timeout == (15, 60)
        return Stream(payload[:-1] + b"x" if corrupt else payload)
    monkeypatch.setattr(data.requests, "get", get)
    if corrupt:
        with pytest.raises(ValueError, match="frozen size/hash"):
            data.build(tmp_path, "2026-06-30")
        assert not path.exists()
    else:
        frame = data.build(tmp_path, "2026-06-30")
        assert len(frame) == 2800
