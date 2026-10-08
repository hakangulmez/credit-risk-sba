"""Verify editorial wording without refitting, rebinding cells or relaxing lineage."""

import ast
import json
import shutil
from pathlib import Path

import pytest

from reporting import editorial
from reporting.registry import ROOT


@pytest.mark.parametrize(
    "text",
    [
        "G1 stage",
        "G2 findings",
        "G2-bis estimates",
        "G5 checks",
        "Local review draft",
        "External release requires separate approval.",
    ],
)
def test_internal_names_and_obsolete_status_rejected(text):
    with pytest.raises(ValueError):
        editorial.reject_reader_labels(text)


@pytest.mark.parametrize(
    "text",
    [
        r"See \nolinkurl{docs/G2_REPORT_2026-10-08.md}.",
        "[Report build notes](docs/G5_REPRODUCTION.md)",
        "`results/g2-bis-2026-10-08/calibration_deciles.csv`",
        editorial.HISTORY,
    ],
)
def test_paths_and_plain_history_allowed(text):
    editorial.reject_reader_labels(text)


def test_sources_protect_history_and_scenario_loss_qualifications():
    assert editorial.source_checks(ROOT)["prose_cell_uses"] == 30


def test_originals_and_frozen_ledgers_retained():
    assert editorial.frozen_checks(ROOT)["frozen_files"] >= 200


def test_pdf_status_labels_full_loss_once_and_page_limits():
    pages = editorial.pdf_checks(ROOT)
    assert pages["policy_note"] == 2
    assert pages["technical_report"] <= 15
    if "working_paper" in pages:
        assert pages["working_paper"] <= 14


def minimal_sources(tmp_path: Path) -> None:
    for name in [
        "README.md",
        "report/g5/policy_note.tex",
        "report/g5/technical_report.tex",
        "CLAIMS.md",
        "report/g5/generated/editorial_numbers.tex",
        "report/editorial/calibration_prose_claims.json",
    ]:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)


@pytest.mark.parametrize(
    "change", ["duplicated_loss", "missing_history", "missing_loss_reference", "validation_label"]
)
def test_weakened_qualifications_fail_before_rendering(tmp_path, change):
    minimal_sources(tmp_path)
    p = tmp_path / "report/g5/technical_report.tex"
    text = p.read_text()
    if change == "duplicated_loss":
        text += r"\losslabel"
    elif change == "missing_history":
        text = text.replace(editorial.HISTORY, "Specification fixed.")
    elif change == "missing_loss_reference":
        text = text.replace("Assumption-based loss proxies; see Section 6.", "Losses.")
    else:
        text = text.replace(
            r"\tbl{support}{", r"\tbl{support}{Retrospective conditional validation. "
        )
    p.write_text(text)
    with pytest.raises(ValueError):
        editorial.source_checks(tmp_path)


def test_supplementary_macro_tampering_rejected(tmp_path):
    names = [
        "CLAIMS.md",
        "report/editorial/calibration_prose_claims.json",
        "report/g5/generated/editorial_numbers.tex",
        "results/g5-2026-10-08/claims_registry.json",
    ]
    payload = json.loads((ROOT / names[-1]).read_text())
    names += sorted({c["source_path"] for c in payload["claims"].values() if "source_path" in c})
    for name in names:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    p = tmp_path / "report/g5/generated/editorial_numbers.tex"
    p.write_text(p.read_text().replace("{0.70}", "{0.71}", 1))
    with pytest.raises(ValueError, match="macros disagree"):
        editorial.calibration_claims(tmp_path)


def test_editorial_build_has_no_empirical_or_network_imports():
    tree = ast.parse((ROOT / "reporting/editorial.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {
                "fit",
                "predict",
                "predict_proba",
                "fit_transform",
                "load_model",
                "urlopen",
                "request",
                "post",
            }
        if isinstance(node, ast.Import):
            assert not any(
                a.name.split(".")[0]
                in {"credit_risk_sba", "requests", "urllib", "joblib", "lightgbm", "statsmodels"}
                for a in node.names
            )
