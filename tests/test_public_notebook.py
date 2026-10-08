"""Guard the public notebook against accidentally executing empirical work."""

import json
from pathlib import Path

import pytest

from scripts.notebook_policy import NOTEBOOK, validate_notebook

ROOT = Path(__file__).resolve().parents[1]


def altered(tmp_path, code):
    notebook = json.loads((ROOT / NOTEBOOK).read_text())
    notebook["cells"].append(
        {
            "cell_type": "code",
            "source": [code],
            "metadata": {},
            "execution_count": 99,
            "outputs": [],
        }
    )
    path = tmp_path / "altered.ipynb"
    path.write_text(json.dumps(notebook))
    return path


@pytest.mark.parametrize(
    "code",
    [
        "import requests",
        "from credit_risk_sba.bis_runner import run",
        "model.fit(X, y)",
        "exec('pass')",
        "ROOT.write_text('replace')",
    ],
)
def test_network_models_dynamic_execution_and_writes_rejected(tmp_path, code):
    with pytest.raises(ValueError):
        validate_notebook(altered(tmp_path, code))


def test_private_guide_cannot_be_enabled_in_published_source(tmp_path):
    with pytest.raises(ValueError):
        validate_notebook(altered(tmp_path, "ENABLE_PRIVATE_REESTIMATION_GUIDE = True"))


def test_unexecuted_published_cells_rejected(tmp_path):
    path = altered(tmp_path, "pass")
    notebook = json.loads(path.read_text())
    notebook["cells"][-1]["execution_count"] = None
    path.write_text(json.dumps(notebook))
    with pytest.raises(ValueError):
        validate_notebook(path)


def test_error_outputs_rejected(tmp_path):
    path = altered(tmp_path, "pass")
    notebook = json.loads(path.read_text())
    notebook["cells"][-1]["outputs"] = [{"output_type": "error", "ename": "ValueError"}]
    path.write_text(json.dumps(notebook))
    with pytest.raises(ValueError):
        validate_notebook(path)


def test_accepted_notebook_is_executed_and_read_only():
    result = validate_notebook(ROOT / NOTEBOOK)
    assert result["code_cells"] > 10 and result["output_items"] > 10
    assert result["manual_guide_disabled"]
