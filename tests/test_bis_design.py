import numpy as np
import pandas as pd
import pytest

from credit_risk_sba.bis_design import PooledDesign
from credit_risk_sba.data import CAT


def fixture():
    n = 3000
    f = pd.DataFrame({c: ["ordinary"] * n for c in CAT})
    f["ProjectState"] = np.tile(["CA", "NY", "TX"], n // 3)
    f["ProcessingMethod"] = ["rare"] * 2 + ["boundary"] * 3 + ["ordinary"] * (n - 5)
    f["x"] = np.linspace(-1, 1, n)
    f["constant"] = 2.0
    f["Y"] = np.arange(n) % 2
    f["role"] = "train"
    f["row_id"] = np.arange(n).astype(str)
    return f


def test_strict_training_frequency_and_state_exemption():
    f = fixture()
    d = PooledDesign(["x", "constant"]).fit(f)
    assert d.maps["ProcessingMethod"]["rare"] == "Other"
    assert d.maps["ProcessingMethod"]["boundary"] == "boundary"
    assert set(d.maps["ProjectState"].values()) == {"CA", "NY", "TX"}
    assert "constant" in d.dropped
    assert {"ProjectState_NY", "ProjectState_TX"} <= set(d.contract()["columns"])
    q = f.copy()
    q.Y = 1 - q.Y
    e = PooledDesign(["x", "constant"]).fit(q)
    assert d.maps == e.maps
    np.testing.assert_array_equal(d.keep, e.keep)
    assert d.transform(f, reduced=True).shape[1] == d.contract()["rank"]
    assert np.linalg.matrix_rank(d.transform(f, reduced=True).toarray()) == d.contract()["rank"]


def test_unseen_and_missing_no_unsupported_columns():
    f = fixture()
    d = PooledDesign(["x"]).fit(f)
    q = f.iloc[:2].copy()
    q["ProcessingMethod"] = ["never-seen", None]
    q["BusinessType"] = "unseen"
    mapped = d.mapped(q)
    assert mapped.ProcessingMethod.eq("Other").all()
    assert mapped.BusinessType.eq("__unseen_not_fitted__").all()
    assert not any("__unseen_not_fitted__" in x for x in d.names)
    assert d.transform(q, reduced=True).shape[1] == len(d.keep)
    with pytest.raises(ValueError):
        PooledDesign(["x"]).fit(f.assign(role="heldout"))


def test_separate_layer_maps_and_future_data_do_not_change_training():
    f = fixture()
    a = PooledDesign(["x"]).fit(f)
    b = f.copy()
    b.loc[:6, "ProcessingMethod"] = "rare"
    b = PooledDesign(["x"]).fit(b)
    assert a.maps["ProcessingMethod"]["rare"] == "Other"
    assert b.maps["ProcessingMethod"]["rare"] == "rare"
    before = a.contract()
    q = f.assign(x=1e6, ProcessingMethod="future")
    a.transform(q)
    assert a.contract() == before
