"""Validate a public snapshot or rebuild reports from frozen aggregates only."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reporting import checks, editorial
from reporting.registry import OUT
from scripts.notebook_policy import NOTEBOOK, validate_notebook
from scripts.working_paper import check as check_paper


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate() -> dict:
    manifest_path = ROOT / "PUBLIC_EDITORIAL_MANIFEST_2026-10-09.json"
    if not manifest_path.exists():
        manifest_path = ROOT / "PUBLIC_RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    for name, item in manifest["files"].items():
        path = ROOT / name
        if digest(path) != item["sha256"]:
            raise ValueError(f"Public release hash mismatch: {name}")
        parts = Path(name).parts
        if parts[0] in {"data", "models", ".venv", "versions"}:
            raise ValueError(f"Undistributed directory included: {name}")
        if parts[0] == "notebooks" and name != NOTEBOOK:
            raise ValueError(f"Notebook not on the public allowlist: {name}")
        if path.suffix in {".joblib", ".pkl", ".pickle", ".parquet"} or (
            path.suffix == ".ipynb" and name not in {NOTEBOOK, str(editorial.ARCHIVE / NOTEBOOK)}
        ):
            raise ValueError(f"Private artifact included: {name}")
        if path.name.startswith(".env"):
            raise ValueError(f"Credential file included: {name}")
    registry = json.loads((ROOT / OUT / "claims_registry.json").read_text())
    claim_check = checks.verify_claims(ROOT, registry)
    table_check = checks.rendered_check(ROOT)
    page_check = checks.pages(ROOT)
    for name in [
        "README.md",
        "report/g5/policy_note.tex",
        "report/g5/technical_report.tex",
        "report/paper/working_paper.tex",
    ]:
        bad = checks.unsupported_claims((ROOT / name).read_text())
        if bad:
            raise ValueError(f"Unsupported affirmative claims in {name}: {bad}")
    # The unchanged renderer's scope contract excludes empirical imports/actions.
    for name in ["g5.py", "registry.py", "checks.py", "create_claims.py"]:
        tree = ast.parse((ROOT / "reporting" / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "fit",
                "predict",
                "predict_proba",
                "fit_transform",
                "load_model",
            }:
                raise ValueError(f"Empirical action in reporting module: {name}")
            if isinstance(node, ast.Import):
                imports = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or ""]
            else:
                imports = []
            if any("credit_risk_sba" in module for module in imports):
                raise ValueError(f"Research package imported by renderer: {name}")
    secret = re.compile(
        rb"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}"
        rb"|sk-(?:proj-)?[A-Za-z0-9_-]{30,}"
        rb"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    )
    for name in manifest["files"]:
        if secret.search((ROOT / name).read_bytes()):
            raise ValueError(f"Possible credential in distributed file: {name}")
    result = {
        "release_files_verified": len(manifest["files"]),
        "claims": claim_check,
        "rendered": table_check,
        "pages": page_check,
        "notebook": validate_notebook(ROOT / NOTEBOOK),
        "working_paper": check_paper(ROOT),
        "editorial": editorial.check(ROOT),
        "credential_pattern_scan": "passed",
        "private_data_or_models_distributed": False,
        "new_empirical_runs": 0,
    }
    print(json.dumps(result, indent=2))
    return result


def build() -> None:
    validate()
    output = editorial.build(ROOT)
    print(f"Editorial rebuild saved under {output}; distributed files unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "build"])
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        validate()
