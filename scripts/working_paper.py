"""Check and compile a manuscript using frozen public aggregates; no empirical work."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "report/paper"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root: Path = ROOT) -> dict:
    paper = root / "report/paper"
    provenance = json.loads((paper / "provenance.json").read_text())
    for name, expected in provenance["frozen_inputs"].items():
        if digest(root / name) != expected:
            raise ValueError(f"Working-paper input changed: {name}")
    source = (paper / "working_paper.tex").read_text()
    references = set(re.findall(r"\\bibitem\[[^\]]+\]\{([^}]+)\}", source))
    citations = set()
    for group in re.findall(r"\\cite[tp]?\{([^}]+)\}", source):
        citations.update(group.split(","))
    if citations - references:
        raise ValueError(f"Missing references: {sorted(citations - references)}")
    required = [
        "recorded charge-off within 36 months",
        "after the G2 results had been seen",
        "before any G2-bis model was estimated",
        "retrospective",
        "not an intercept-only calibration-in-the-large",
        "Calibration error can alter",
        "pro-rata",
        "Timing unverifiable",
        "Scenario projections on the fixed 2006 portfolio",
    ]
    combined = source + (paper / "preamble.tex").read_text()
    for phrase in required:
        if phrase not in combined:
            raise ValueError(f"Missing interpretation qualification: {phrase}")
    if "Credit-Scoring-EDA" in combined or "local review draft" in combined:
        raise ValueError("Obsolete front matter in working paper")
    replacements = provenance["label_replacements"]
    for name in re.findall(r"\\(?:inline)?tbl\{([^}]+)\}", source):
        original = replacements.get(name, {}).get("original", name)
        if not (root / f"report/g5/generated/{original}.tex").is_file():
            raise ValueError(f"Unavailable saved table: {original}")
    result = {
        "frozen_inputs_verified": len(provenance["frozen_inputs"]),
        "bibliography_entries": len(references),
        "new_empirical_runs": 0,
        "working_paper_basis_unchanged": True,
    }
    pdf = root / "report/working_paper.pdf"
    if pdf.exists():
        info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
        match = re.search(r"Pages:\s+(\d+)", info)
        if match is None:
            raise ValueError("Cannot read working-paper page count")
        pages = int(match.group(1))
        if not 1 <= pages <= 15:
            raise ValueError(f"Working-paper page limit exceeded: {pages}")
        result["pages"] = pages
    return result


def build() -> None:
    check()
    output = ROOT / "data/working-paper-build"
    stage = output / "source"
    stage.mkdir(parents=True, exist_ok=True)
    for name in ["working_paper.tex", "preamble.tex"]:
        shutil.copyfile(PAPER / name, stage / name)
    shutil.copytree(ROOT / "report/g5/generated", stage / "generated", dirs_exist_ok=True)
    provenance = json.loads((PAPER / "provenance.json").read_text())
    for name, rule in provenance["label_replacements"].items():
        text = (stage / "generated" / (rule["original"] + ".tex")).read_text()
        for old, new in rule["replacements"]:
            text = text.replace(old, new)
        (stage / "generated" / (name + ".tex")).write_text(text)
    (stage / "figures").mkdir(exist_ok=True)
    shutil.copyfile(
        ROOT / "figures/g5/calibration_groups.pdf", stage / "figures/calibration_groups.pdf"
    )
    compiler = (
        os.environ.get("TECTONIC")
        or shutil.which("tectonic")
        or str(ROOT.parent / ".tools/tectonic/tectonic")
    )
    subprocess.run(
        [compiler, "--only-cached", "--keep-logs", "--outdir", str(output), "working_paper.tex"],
        cwd=stage,
        check=True,
    )
    print(f"Working-paper rebuild saved under {output}; accepted files unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "build"])
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        print(json.dumps(check(), indent=2))
