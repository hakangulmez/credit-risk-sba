"""Reporting-only regression checks; never fits a statistical model."""

import ast
import copy
import json

import pytest

from reporting import checks, g5
from reporting.registry import (
    BASE,
    OUT,
    ROOT,
    SCENARIO,
    Registry,
    digest,
    rows,
    scalar,
    select,
    units,
)


@pytest.fixture(scope="module")
def payload():
    return json.loads((ROOT / OUT / "claims_registry.json").read_text())


@pytest.fixture
def registry(payload):
    r = Registry()
    r.entries = copy.deepcopy(payload["claims"])
    r.aliases = payload["aliases"].copy()
    return r


def test_all_claims_unique_hash_bound_and_accounting(payload):
    result = checks.verify_claims(ROOT, payload)
    assert result["verified_cells"] > 4500
    assert result["derived_cells"] == 5


@pytest.mark.parametrize("name", ["endpoint", "auc_crisis", "baseline_expected_loss_usd"])
def test_raw_number_tampering_fails(payload, name):
    bad = copy.deepcopy(payload)
    bad["claims"][bad["aliases"][name]]["raw_value"] += 1
    with pytest.raises(AssertionError):
        checks.verify_claims(ROOT, bad)


def test_source_hash_tampering_fails(payload):
    bad = copy.deepcopy(payload)
    bad["claims"][bad["aliases"]["auc_crisis"]]["source_sha256"] = "bad"
    with pytest.raises(AssertionError):
        checks.verify_claims(ROOT, bad)


def test_scenario_label_tampering_fails(payload):
    bad = copy.deepcopy(payload)
    bad["claims"][bad["aliases"]["baseline_pd"]]["supported_interpretation"] = (
        "Retrospective conditional validation using realized macro paths"
    )
    with pytest.raises(AssertionError):
        checks.verify_claims(ROOT, bad)


def test_saved_paired_interval_not_marginal_subtraction(registry):
    change = registry.resolve("adverse_minus_baseline_expected_loss_usd_change")
    assert change["selector"]["scenario"] == "adverse_minus_baseline"
    assert (
        change["interval"]["lower"]
        != registry.resolve("adverse_expected_loss_usd")["interval"]["lower"]
        - registry.resolve("baseline_expected_loss_usd")["interval"]["upper"]
    )


def test_format_units_scope_and_point_only_ratio(registry):
    assert registry.display("pd_crisis", 100, 2) == "5.73"
    assert registry.display("auc_crisis", digits=3, interval=True) == "0.607 [0.587, 0.626]"
    assert "[" not in registry.display("el_ratio", interval=True)
    assert registry.resolve("endpoint")["units"] == "probability percentage points"
    assert registry.resolve("baseline_pd")["supported_interpretation"] == SCENARIO
    assert units("firth_stress.csv", "value", {"metric": "expected_loss_usd"}) == "USD"


@pytest.mark.parametrize(
    "raw,expected",
    [("", None), ("inf", "inf"), ("-inf", "-inf"), ("2", 2), ("1.5", 1.5), ("True", "True")],
)
def test_missing_values_do_not_become_zero(raw, expected):
    assert scalar(raw) == expected


def test_unavailable_and_stored_bins(registry):
    registry.entries["empty"] = {"id": "empty", "raw_value": None, "interval": None}
    assert registry.display("empty", interval=True) == "unavailable"
    bins = [
        v
        for v in registry.entries.values()
        if v.get("source_path") == str(BASE / "calibration_deciles.csv") and v.get("column") == "n"
    ]
    assert len(bins) == 40
    for e in bins:
        row = select(ROOT / BASE / "calibration_deciles.csv", e["selector"])
        assert e["raw_value"] == int(row["n"])
    assert sum(e["raw_value"] for e in bins) == sum(
        int(a["n"])
        for a in rows(ROOT / BASE / "calibration_deciles.csv")
        if (a["variant"], a["model"], a["cohort"])
        in {
            ("layer1", "firth_raw", "crisis_2007_2009"),
            ("layer1", "firth_raw", "additional_cohort_2011_2013"),
            ("layer2", "firth_raw", "post_amendment_validation_2013_2014"),
            ("layer2", "lightgbm_calibrated", "post_amendment_validation_2013_2014"),
        }
    )


def test_nonunique_selector_rejected(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("key,value\nx,1\nx,2\n")
    with pytest.raises(ValueError):
        select(p, {"key": "x"})
    with pytest.raises(ValueError):
        select(p, {"key": "missing"})


@pytest.mark.parametrize(
    "text",
    [
        "Calibration is solved.",
        "The effect is not causal, but this demonstrates a causal effect.",
        "This demonstrates a causal effect.",
        "We establish strong transportability.",
        "This measures fiscal costs.",
        "This implements IFRS 9.",
        "The differences are calibration-invariant differences.",
    ],
)
def test_unsupported_affirmative_claims_rejected(text):
    assert checks.unsupported_claims(text)


@pytest.mark.parametrize(
    "text",
    [
        "Calibration is not solved.",
        "Neither measured fiscal costs nor actual public spending are available.",
        "This is not an implementation of IFRS 9.",
        "There is no strong transportability claim.",
        "Future causal forests require identification; we do not identify a causal effect.",
        "A future design would assess calibration-invariant differences, rather than assume them.",
    ],
)
def test_negation_and_future_discussion_pass(text):
    assert not checks.unsupported_claims(text)


def test_research_pipeline_not_in_report_build():
    commands = (ROOT / "Makefile").read_text().split("report:\n", 1)[1].split("report-test:", 1)[0]
    assert "reporting.g5" in commands and "sba-g2" not in commands
    tree = ast.parse((ROOT / "reporting/g5.py").read_text())
    assert not any(
        isinstance(n, ast.Attribute) and n.attr in {"fit", "predict", "predict_proba"}
        for n in ast.walk(tree)
    )


def test_protected_originals_and_archive_exceptions():
    result = checks.preservation()
    assert result["authorized_surface_replacements"] == 2
    assert result["protected_private"] == 1170


def test_presentation_traceability_and_scope():
    assert checks.rendered_check()["generated_tables"] >= 18
    assert checks.scope_check()["scenario_captions"] == 3
    assert checks.pages()["policy_note"] == 2


def test_headline_dimensions_and_summary():
    from matplotlib import image

    assert image.imread(ROOT / "figures/linkedin/g5/linkedin_draft.png").shape[:2] == (1200, 1200)
    paragraphs = (ROOT / "figures/linkedin/g5/LINKEDIN_DRAFT.md").read_text().split("\n\n")
    assert len(paragraphs[1:4]) == 3
    assert all(p.endswith(".") for p in paragraphs[1:4])


def test_escaping_and_saved_metadata(registry):
    assert r"\%" in g5.escape("12%")
    assert r"\_" in g5.escape("a_b")
    assert registry.value("method_attempts") == 199
    assert registry.value("method_evaluation_draws") == 999
    assert digest(ROOT / OUT / "claims_registry.json")


def test_full_results_only_renderer_with_no_private_inputs(tmp_path, monkeypatch, payload):
    """Exercise reporting arithmetic/rendering, including offline PDF compilation."""
    import os
    import shutil
    import sys

    from reporting.create_claims import create

    required = {c["source_path"] for c in payload["claims"].values() if "source_path" in c}
    for name in required:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    (tmp_path / OUT).mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "report/g5", tmp_path / "report/g5", dirs_exist_ok=True)
    assert not (tmp_path / "models").exists() and not (tmp_path / "data").exists()
    fresh = create(tmp_path)
    assert fresh.entries == payload["claims"]
    monkeypatch.setenv("TECTONIC", str(ROOT.parent / ".tools/tectonic/tectonic"))
    monkeypatch.setattr(sys, "argv", ["reporting.g5", "--root", str(tmp_path)])
    g5.main()
    assert checks.pages(tmp_path)["technical_report"] <= 15
    assert checks.rendered_check(tmp_path)["generated_tables"] == 18
    assert (
        checks.verify_claims(
            tmp_path, json.loads((tmp_path / OUT / "claims_registry.json").read_text())
        )["derived_cells"]
        == 5
    )
    # Repeat the permitted renderer without a PDF compile, not research execution.
    monkeypatch.setattr(sys, "argv", ["reporting.g5", "--root", str(tmp_path), "--no-pdf"])
    g5.main()
    assert not (tmp_path / "models").exists() and not (tmp_path / ".env").exists()
    assert os.environ["TECTONIC"]


def test_registry_rejects_duplicate_identity_and_missing_context(tmp_path):
    (tmp_path / BASE).mkdir(parents=True)
    p = tmp_path / BASE / "a.csv"
    p.write_text("key,value\nx,1\nx,2\n")
    with pytest.raises(ValueError):
        Registry(tmp_path).add_csv("a.csv", ["key"], ["value"])
    p = tmp_path / BASE / "firth_stress.csv"
    p.write_text("key,value\nx,1\n")
    with pytest.raises(ValueError):
        Registry(tmp_path).add_csv(p.name, ["key"], ["value"])


def test_lookup_empty_and_unknown_claim(registry):
    with pytest.raises(ValueError):
        registry.lookup_id("evaluation_metrics.csv", {"variant": "missing"})
    with pytest.raises(KeyError):
        registry.resolve("absent")


def test_check_entrypoint(monkeypatch):
    checks.main()
    assert (
        json.loads((ROOT / OUT / "validation_checks.json").read_text())["new_empirical_runs"] == 0
    )


def test_new_presentation_csvs_use_lf():
    for path in (ROOT / OUT).glob("*.csv"):
        assert b"\r\n" not in path.read_bytes()


@pytest.mark.parametrize(
    "name, expected_value, expected_unit",
    [
        ("method_pool_cutoff", "0.001", "fraction of training observations"),
        ("method_seed", "20261008", "integer seed"),
        ("method_attempts", "199", "attempted training-refit draws"),
        ("pd_crisis", "5.73", "percent (%)"),
        ("baseline_sba_share", "62.80", "percent (%)"),
        ("auc_crisis", "0.607 [0.587, 0.626]", "AUC (unitless)"),
        ("endpoint", "0.535 [0.266, 0.772]", "probability percentage points (pp)"),
        ("peak", "0.679 [0.439, 0.933]", "probability percentage points (pp)"),
        ("term_CHGOFF_valid_n", "216,172", "count"),
    ],
)
def test_human_claim_units_and_precision(registry, name, expected_value, expected_unit):
    before = copy.deepcopy(registry.entries)
    assert registry.human_display(name) == (expected_value, expected_unit)
    assert registry.entries == before


def test_correction_keeps_registry_and_archives_immutable():
    archive = ROOT / "versions/pre-g5-correction-2026-10-08"
    manifest = json.loads((archive / "ARCHIVE_MANIFEST.json").read_text())
    for record in manifest["archive_mappings"]:
        assert digest(ROOT / record["archive_path"]) == record["sha256"]
    assert digest(ROOT / OUT / "claims_registry.json") == digest(
        archive / OUT / "claims_registry.json"
    )


def test_peak_convergence_label_does_not_change_source_role():
    original = select(
        ROOT / BASE / "fit_status.csv", {"variant": "layer2_peak", "family": "Firth primary"}
    )
    generated = select(
        ROOT / OUT / "convergence.csv",
        {"Specification / estimator": "layer2_peak / Firth peak sensitivity"},
    )
    assert generated["Valid convergence"] == original["converged"]
    assert generated["Iterations"] == original["iterations"]
    assert all(
        row["Specification / estimator"] != "layer2_peak / Firth primary"
        for row in rows(ROOT / OUT / "convergence.csv")
    )
