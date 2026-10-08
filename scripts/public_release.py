"""Validate a public snapshot or rebuild reports from frozen aggregates only."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reporting import checks
from reporting.registry import OUT
from scripts.notebook_policy import NOTEBOOK, validate_notebook


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate() -> dict:
    manifest = json.loads((ROOT / "PUBLIC_RELEASE_MANIFEST.json").read_text())
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
            path.suffix == ".ipynb" and name != NOTEBOOK
        ):
            raise ValueError(f"Private artifact included: {name}")
        if path.name.startswith(".env"):
            raise ValueError(f"Credential file included: {name}")
    registry = json.loads((ROOT / OUT / "claims_registry.json").read_text())
    claim_check = checks.verify_claims(ROOT, registry)
    table_check = checks.rendered_check(ROOT)
    page_check = checks.pages(ROOT)
    for name in ["README.md", "report/g5/policy_note.tex", "report/g5/technical_report.tex"]:
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
        "credential_pattern_scan": "passed",
        "private_data_or_models_distributed": False,
        "new_empirical_runs": 0,
    }
    print(json.dumps(result, indent=2))
    return result


def build() -> None:
    validate()
    payload = json.loads((ROOT / OUT / "claims_registry.json").read_text())
    inputs = {c["source_path"] for c in payload["claims"].values() if "source_path" in c}
    inputs.add(str(OUT / "claims_registry.json"))
    output = ROOT / "data/public-report-rebuild"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isolated-", dir=output) as temporary:
        stage = Path(temporary)
        for name in sorted(inputs):
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        shutil.copytree(ROOT / "report/g5", stage / "report/g5")
        if (stage / "models").exists() or (stage / "data").exists():
            raise ValueError("Private inputs present before report rebuild")
        subprocess.run(
            [sys.executable, "-m", "reporting.g5", "--root", str(stage)],
            cwd=ROOT,
            env=os.environ.copy(),
            check=True,
        )
        checks.pages(stage)
        checks.rendered_check(stage)
        for name in ["policy_note.pdf", "technical_report.pdf"]:
            shutil.copyfile(stage / "report" / name, output / name)
        for directory in ["report/g5/generated", "figures/g5"]:
            shutil.copytree(stage / directory, output / directory, dirs_exist_ok=True)
    print(f"Results-only rebuild saved under {output}; accepted release files unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "build"])
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        validate()
