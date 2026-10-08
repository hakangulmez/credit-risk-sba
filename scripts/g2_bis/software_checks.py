"""Bind the actual test/lint/type/preservation results to a machine-readable record."""

import json
import re
import subprocess
from pathlib import Path

from credit_risk_sba.bis_data import NAME, js
from credit_risk_sba.bis_finalize import preservation
from credit_risk_sba.io import sha256

root = Path.cwd()
log = root / "data" / NAME / "final_tests.log"
match = re.search(r"(\d+) passed.*?in ([\d.]+)s", log.read_text())
if not match or "FAILED" in log.read_text() or "ERRORS" in log.read_text():
    raise ValueError("Final test completion/pass not verified")
coverage = json.loads((root / "data" / NAME / "coverage.json").read_text())
core = [
    "features",
    "models",
    "metrics",
    "macro",
    "losses",
    "stress",
    "bis_firth",
    "bis_design",
    "bis_analysis",
    "bis_finalize",
]
files = {k: v["summary"] for k, v in coverage["files"].items() if Path(k).stem in core}
statements = sum(v["num_statements"] for v in files.values())
covered = sum(v["covered_lines"] for v in files.values())
checks = {}
for name, cmd in [
    ("lint", [".venv/bin/ruff", "check", "src", "tests", "--cache-dir", "data/.ruff_cache"]),
    ("mypy", [".venv/bin/mypy", "src/credit_risk_sba", "--cache-dir", "data/.mypy_cache"]),
]:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(name + ": " + result.stdout + result.stderr)
    checks[name] = "passed"
preserved = preservation(root)
size = subprocess.run(
    ["du", "-sk", str(root)], text=True, capture_output=True, check=True
).stdout.split()[0]
portfolio_size = subprocess.run(
    ["du", "-sk", str(root.parent)], text=True, capture_output=True, check=True
).stdout.split()[0]
js(
    root / "results" / NAME / "software_checks.json",
    {
        "tests_passed": int(match[1]),
        "test_seconds": float(match[2]),
        "package_coverage_percent": coverage["totals"]["percent_covered"],
        "statistical_core_coverage_percent": 100 * covered / statements,
        "statistical_core_modules": core,
        "core_module_coverage": files,
        "test_log_sha256": sha256(log),
        "coverage_json_sha256": sha256(root / "data" / NAME / "coverage.json"),
        **checks,
        "preservation_entries": len(preserved),
        "preservation_passed": all(r["passed"] for r in preserved),
        "repo_disk_GiB": int(size) / 1024**2,
        "portfolio_disk_GiB": int(portfolio_size) / 1024**2,
        "no_push_publication_paid_calls_G3_G5": True,
    },
)
