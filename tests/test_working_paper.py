"""Protect the empirical and results-only boundaries of the separate manuscript."""

import ast
import json
import shutil

import pytest

from scripts.working_paper import ROOT, check, digest


def test_accepted_evidence_and_manuscript_inputs_remain_unchanged():
    result = check()
    assert result["pages"] <= 15
    assert result["new_empirical_runs"] == 0
    assert digest(ROOT / "report/policy_note.pdf") == (
        "742d9377b6e4bed14188d9b67f58b0189d866a98e445c24435c42b3cba9c162f"
    )
    assert digest(
        ROOT
        / "docs/releases/technical-report-before-editorial-2026-10-09/report/technical_report.pdf"
    ) == ("bfa6f907f578ed4f4566c8b18a86b60ec2eece2e02a86a82ec410a642e861428")


def test_changed_research_input_is_rejected_before_rendering(tmp_path):
    (tmp_path / "report/paper").mkdir(parents=True)
    provenance = json.loads((ROOT / "report/paper/provenance.json").read_text())
    # An incorrect public aggregate must fail even if the manuscript itself is intact.
    name = "report/g5/generated/numbers.tex"
    provenance["frozen_inputs"] = {name: provenance["frozen_inputs"][name]}
    (tmp_path / name).parent.mkdir(parents=True)
    (tmp_path / name).write_text("altered numerical claims")
    (tmp_path / "report/paper/provenance.json").write_text(json.dumps(provenance))
    shutil.copyfile(
        ROOT / "report/paper/working_paper.tex", tmp_path / "report/paper/working_paper.tex"
    )
    with pytest.raises(ValueError, match="Working-paper input changed"):
        check(tmp_path)


def test_builder_has_no_empirical_or_network_execution():
    tree = ast.parse((ROOT / "scripts/working_paper.py").read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Attribute):
            assert node.attr not in {
                "fit",
                "predict",
                "predict_proba",
                "load_model",
                "urlopen",
                "post",
            }
    assert not imports.intersection(
        {"credit_risk_sba", "requests", "urllib", "joblib", "lightgbm", "statsmodels"}
    )
