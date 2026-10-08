"""Nonstatistical provenance, accounting, preservation and language checks."""

from __future__ import annotations

import ast
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .registry import LOSS, OUT, ROOT, SCENARIO, Registry, digest, rows, scalar


def verify_claims(root: Path, payload: dict[str, Any]) -> dict[str, int]:
    claims = payload["claims"]
    sources = {}
    csv_cache = {}
    checked = 0
    for key, c in claims.items():
        assert c["id"] == key
        if c.get("formula"):
            f = c["formula"]
            values = [claims[k]["raw_value"] for k in f["inputs"]]
            expected = (values[0] / values[1] if f["operation"] == "divide" else 1 - values[0]) * f[
                "scale"
            ]
            assert math.isclose(c["raw_value"], expected, rel_tol=1e-12)
            assert c["interval"] is None
            continue
        path = c["source_path"]
        if path not in sources:
            sources[path] = digest(root / path)
        assert sources[path] == c["source_sha256"], path
        if "json_record_selector" in c:
            records = json.loads((root / path).read_text())
            sel = c["json_record_selector"]
            found = [a for a in records if all(a[k] == v for k, v in sel.items())]
            assert len(found) == 1
            actual = found[0][c["column"]]
        elif "yaml_path" in c:
            actual = yaml.safe_load((root / path).read_text())
            for part in c["yaml_path"]:
                actual = actual[part]
        elif "text_pattern" in c:
            matches = re.findall(c["text_pattern"], (root / path).read_text())
            assert len(matches) == 1
            actual = scalar(matches[0])
        else:
            if path not in csv_cache:
                csv_cache[path] = rows(root / path)
            sel = c["selector"]
            found = [a for a in csv_cache[path] if all(str(a[k]) == str(v) for k, v in sel.items())]
            assert len(found) == 1, (key, sel)
            row = found[0]
            actual = scalar(row[c["column"]])
            if "raw_source_text" in c:
                assert row[c["column"]] == c["raw_source_text"]
            interval = c.get("interval")
            if interval:
                assert interval["lower"] == scalar(row[interval["lower_column"]])
                assert interval["upper"] == scalar(row[interval["upper_column"]])
            if Path(path).name in {"firth_stress.csv", "scenario_support_summary.csv"}:
                assert c["source_macro_information_context"] == row["macro_information_context"]
                assert c["supported_interpretation"] == SCENARIO
            assert c["units"]
        assert actual == c["raw_value"], (key, actual, c["raw_value"])
        checked += 1
    r = Registry(root)
    r.entries = claims
    r.aliases = payload["aliases"]
    for scenario in ["baseline", "adverse"]:
        total = r.value(scenario + "_expected_loss_usd")
        assert math.isclose(
            total,
            r.value(scenario + "_sba_loss_usd") + r.value(scenario + "_lender_loss_usd"),
            abs_tol=1e-5,
        )
        assert math.isclose(
            r.value(scenario + "_sba_share") + r.value(scenario + "_lender_share"), 1
        )
    for metric in ["expected_loss_usd", "sba_loss_usd", "lender_loss_usd"]:
        entry = r.resolve("adverse_minus_baseline_" + metric + "_change")
        assert entry["selector"]["scenario"] == "adverse_minus_baseline"
        assert math.isclose(
            entry["raw_value"],
            r.value("adverse_" + metric) - r.value("baseline_" + metric),
            abs_tol=1e-5,
        )
    return {
        "verified_cells": checked,
        "derived_cells": len(claims) - checked,
        "source_files": len(sources),
    }


def preservation(root: Path = ROOT) -> dict[str, int]:
    inv = json.loads((root / OUT / "preservation_inventory.json").read_text())
    mapping = {a["original_path"]: a for a in inv["archive_mappings"]}
    for path, h in inv["protected_tracked"].items():
        if path in {"README.md", "Makefile"}:
            assert digest(root / mapping[path]["archive_path"]) == h
        elif path == "DECISIONS.md":
            assert (
                (root / path)
                .read_bytes()
                .startswith((root / inv["decisions_prefix_archive"]).read_bytes())
            )
        else:
            assert digest(root / path) == h, path
    for path, h in inv["protected_private"].items():
        assert digest(root / path) == h, path
    for a in inv["archive_mappings"]:
        assert digest(root / a["archive_path"]) == a["sha256"]
    return {
        "protected_tracked": len(inv["protected_tracked"]),
        "protected_private": len(inv["protected_private"]),
        "archive_mappings": len(mapping),
        "authorized_surface_replacements": 2,
        "append_only_decisions": 1,
    }


def unsupported_claims(text: str) -> list[str]:
    """Check affirmative phrases within clauses, permitting negation and proposals."""
    patterns = [
        r"calibration (?:is |has been )?solved",
        r"(?:establishes|demonstrates|proves|identifies) (?:a |the )?causal (?:effect|macro|guarantee)",
        r"(?:strong|stable) transportability",
        r"(?:measures|measured|actual) (?:fiscal costs|public spending|tail risk)",
        r"(?:implements|is an implementation of) (?:IFRS 9|CECL)",
        r"calibration-invariant (?:differences|ratios)",
    ]
    bad = []
    for clause in re.split(r"[.;\n]|\b(?:but|however|yet)\b", text, flags=re.IGNORECASE):
        for pattern in patterns:
            if re.search(pattern, clause, re.IGNORECASE) and not re.search(
                r"\b(?:not|no|neither|without|cannot|rather than|future|would|require|prohibited)\b",
                clause,
                re.IGNORECASE,
            ):
                bad.append(clause.strip())
    return bad


def scope_check(root: Path = ROOT) -> dict[str, int]:
    allowed = {
        "__future__",
        "argparse",
        "ast",
        "csv",
        "hashlib",
        "json",
        "math",
        "os",
        "pathlib",
        "re",
        "shutil",
        "subprocess",
        "textwrap",
        "typing",
        "matplotlib",
        "numpy",
        "yaml",
        "registry",
        "checks",
    }
    for name in ["g5.py", "registry.py", "checks.py", "create_claims.py"]:
        tree = ast.parse((root / "reporting" / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [a.name.split(".")[0] for a in node.names]
                    if isinstance(node, ast.Import)
                    else [(node.module or "").split(".")[0]]
                )
                assert all(n in allowed for n in names), (name, names)
            if isinstance(node, ast.Attribute):
                assert node.attr not in {
                    "fit",
                    "predict",
                    "predict_proba",
                    "fit_transform",
                    "load_model",
                }, (name, node.attr)
    for name in ["stress", "sensitivities", "support"]:
        source = (root / "report/g5/technical_report.tex").read_text()
        caption = re.search(r"\\tbl\{" + name + r"\}\{([^\n]+)", source)
        assert caption and r"\scenario" in caption[1]
        assert "Retrospective conditional validation" not in caption[1]
    assert LOSS in (root / "figures/g5/headline_caption.txt").read_text()
    surfaces = [
        root / "README.md",
        root / "CV_BULLET_DRAFT.md",
        root / "report/g5/policy_note.tex",
        root / "report/g5/technical_report.tex",
        root / "figures/linkedin/g5/LINKEDIN_DRAFT.md",
    ]
    for path in surfaces:
        assert not unsupported_claims(path.read_text()), (
            path,
            unsupported_claims(path.read_text()),
        )
    return {
        "isolated_reporting_modules": 4,
        "language_surfaces": len(surfaces),
        "scenario_captions": 3,
    }


def rendered_check(root: Path = ROOT) -> dict[str, int]:
    payload = json.loads((root / OUT / "claims_registry.json").read_text())
    r = Registry(root)
    r.entries = payload["claims"]
    r.aliases = payload["aliases"]
    records = json.loads((root / OUT / "rendered_claims.json").read_text())
    for a in records:
        assert (
            r.display(a["id"], a["scale"], a["digits"], a["interval"], a["integer"]) == a["display"]
        )
    pairs = {(a["id"], a["display"]) for a in records}
    tables = 0
    for path in (root / OUT).glob("*_provenance.json"):
        payload = json.loads(path.read_text())
        if "cells" not in payload:
            continue
        assert payload["registry_sha256"] == digest(root / OUT / "claims_registry.json")
        data = rows(path.with_name(path.name.replace("_provenance.json", ".csv")))
        assert len(data) == len(payload["cells"])
        for row, keys in zip(data, payload["cells"], strict=True):
            for value, key in zip(row.values(), keys, strict=True):
                if key:
                    assert (key, value) in pairs or str(
                        r.resolve(key).get("interval", {}).get("successful_draws")
                    ) == value, (path, key, value)
        tables += 1
    return {"rendered_snippets": len(records), "generated_tables": tables}


def pages(root: Path = ROOT) -> dict[str, int]:
    result = {}
    for name in ["policy_note", "technical_report"]:
        output = subprocess.check_output(
            ["pdfinfo", str(root / "report" / (name + ".pdf"))], text=True
        )
        match = re.search(r"Pages:\s+(\d+)", output)
        assert match is not None
        result[name] = int(match[1])
    assert result["policy_note"] == 2, result
    assert result["technical_report"] <= 15, result
    return result


def main() -> None:
    root = ROOT
    result = {
        "claims": verify_claims(
            root, json.loads((root / OUT / "claims_registry.json").read_text())
        ),
        "preservation": preservation(root),
        "scope": scope_check(root),
        "rendered": rendered_check(root),
        "pages": pages(root),
        "new_empirical_runs": 0,
    }
    (root / OUT / "validation_checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
