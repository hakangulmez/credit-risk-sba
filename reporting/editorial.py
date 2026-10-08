"""Compile and validate presentation edits from saved cells, without empirical actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import textwrap
import unicodedata
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .g5 import COLORS, load
from .registry import LOSS, OUT, ROOT, SCENARIO, Registry

ARCHIVE = Path("docs/releases/pre-editorial-2026-10-09")
HISTORY = (
    "The final estimation protocol was frozen after first-round results had been seen "
    "and before any final-round model was estimated. Deviations are logged in DECISIONS.md."
)
SHORT_LOSS = "Assumption-based loss proxies; see"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_input(root: Path, name: str, expected: str) -> Path:
    """Verify the original basis, including authorized archived presentation inputs."""
    current = root / name
    if current.exists() and digest(current) == expected:
        return current
    archive = root / ARCHIVE / "ARCHIVE_MANIFEST.json"
    if archive.exists():
        payload = json.loads(archive.read_text())
        for record in payload["archive_mappings"]:
            if record["original_path"] == name and record["sha256"] == expected:
                saved = root / record["archive_path"]
                if saved.exists() and digest(saved) == expected:
                    return saved
    raise ValueError(f"Working-paper input changed: {name}")


def prose_without_paths(text: str) -> str:
    text = re.sub(r"\\(?:url|nolinkurl)\{[^}]+\}", "", text)
    text = re.sub(r"(\\href\{)[^}]+\}", r"\1}", text)
    text = re.sub(r"(?<=\]\()[^)]+", "", text)
    text = re.sub(r"`[^`]*(?:/|\.md|\.json|\.csv|\.pdf|\.ipynb)[^`]*`", "", text)
    return re.sub(r"\S*(?:/|\.(?:md|json|csv|pdf|ipynb))\S*", "", text)


def reject_reader_labels(text: str) -> None:
    prose = prose_without_paths(text)
    if re.search(r"\b(?:G2-bis|G[125])\b", prose):
        raise ValueError("Internal estimation-stage label in reader-facing prose")
    if re.search(
        r"local review(?: draft| only)?|local drafts?|external release (?:requires|needs)"
        r"|not released|requires approval",
        prose,
        re.IGNORECASE,
    ):
        raise ValueError("Obsolete release status in reader-facing prose")


def calibration_claims(root: Path) -> int:
    from .checks import verify_claims

    registry = json.loads((root / OUT / "claims_registry.json").read_text())
    verify_claims(root, registry)
    r = Registry(root)
    r.entries, r.aliases = registry["claims"], registry["aliases"]
    proof = json.loads((root / "report/editorial/calibration_prose_claims.json").read_text())
    macros = []
    for record in proof["records"]:
        entry = r.resolve(record["id"])
        for key in ["selector", "column", "source_path", "source_sha256"]:
            if record[key] != entry[key]:
                raise ValueError(f"Editorial prose source mismatch: {record['id']}")
        display = r.display(
            record["id"], record["scale"], record["digits"], integer=record["integer"]
        )
        if display != record["display"]:
            raise ValueError(f"Editorial prose display mismatch: {record['id']}")
        if "macro" in record:
            if record["id"] not in (root / "CLAIMS.md").read_text():
                raise ValueError("Editorial prose cell missing from CLAIMS.md")
            macros.append("\\newcommand{\\" + record["macro"] + "}{" + display + "}")
    if (root / "report/g5/generated/editorial_numbers.tex").read_text() != "\n".join(macros) + "\n":
        raise ValueError("Editorial numerical macros disagree with registered cells")
    return len(proof["records"])


def source_checks(root: Path) -> dict[str, Any]:
    names = ["README.md", "report/g5/policy_note.tex", "report/g5/technical_report.tex"]
    if (root / "report/paper/working_paper.tex").exists():
        names.append("report/paper/working_paper.tex")
    for name in names:
        text = (root / name).read_text()
        reject_reader_labels(text)
        if HISTORY not in text:
            raise ValueError(f"Required post-results history missing: {name}")
        if name == "README.md" and text.count(LOSS) != 1:
            raise ValueError("Full loss statement must appear once in README")
        if name.endswith(".tex") and text.count(r"\losslabel") != 1:
            raise ValueError(f"Full loss label must be used once: {name}")
        for line in text.splitlines():
            loss_caption = line.startswith(
                (r"\tbl{stress}", r"\tbl{sensitivities}", r"\inlinetbl{sensitivities")
            )
            support_caption = line.startswith((r"\tbl{support}", r"\inlinetbl{support}"))
            if loss_caption and (SHORT_LOSS not in line or r"\scenario" not in line):
                raise ValueError(f"Loss-table interpretation missing: {name}")
            if support_caption and r"\scenario" not in line:
                raise ValueError("Support caption must identify the scenario portfolio")
            if (loss_caption or support_caption) and "Retrospective conditional validation" in line:
                raise ValueError("Validation label inherited by a scenario caption")
            if r"\caption{" in line and r"\scenario" in line and SHORT_LOSS not in line:
                raise ValueError("Scenario figure must carry a short loss-assumption reference")
    notebook = root / "notebooks/research_walkthrough.ipynb"
    if notebook.exists():
        n = json.loads(notebook.read_text())
        markdown = "\n".join(
            "".join(c["source"]) for c in n["cells"] if c["cell_type"] == "markdown"
        )
        if markdown.count(LOSS) != 1:
            raise ValueError("Full loss statement must appear once in notebook markdown")
        reject_reader_labels(markdown)
    citation = root / "CITATION.cff"
    if citation.exists():
        reject_reader_labels(citation.read_text())
    return {"reader_surfaces": len(names), "prose_cell_uses": calibration_claims(root)}


def frozen_checks(root: Path) -> dict[str, int]:
    payload = json.loads((root / ARCHIVE / "ARCHIVE_MANIFEST.json").read_text())
    for name in payload["frozen_paths"]:
        if digest(root / name) != payload["before_hashes"][name]:
            raise ValueError(f"Frozen result or hash ledger changed: {name}")
    for record in payload["archive_mappings"]:
        if digest(root / record["archive_path"]) != record["sha256"]:
            raise ValueError(f"Archived original changed: {record['original_path']}")
    decisions = next(a for a in payload["archive_mappings"] if a["original_path"] == "DECISIONS.md")
    if (
        not (root / "DECISIONS.md")
        .read_bytes()
        .startswith((root / decisions["archive_path"]).read_bytes())
    ):
        raise ValueError("DECISIONS.md must remain append-only")
    before_nb = root / ARCHIVE / "notebooks/research_walkthrough.ipynb"
    current_nb = root / "notebooks/research_walkthrough.ipynb"
    if before_nb.exists():
        before, current = json.loads(before_nb.read_text()), json.loads(current_nb.read_text())
        old_code = [c for c in before["cells"] if c["cell_type"] == "code"]
        new_code = [c for c in current["cells"] if c["cell_type"] == "code"]
        if old_code != new_code:
            raise ValueError("Notebook code and saved outputs changed")
    return {
        "frozen_files": len(payload["frozen_paths"]),
        "archived_originals": len(payload["archive_mappings"]),
    }


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def pdf_checks(root: Path) -> dict[str, int]:
    pages = {}
    for name, limit in [("policy_note", 2), ("technical_report", 15), ("working_paper", 14)]:
        path = root / "report" / (name + ".pdf")
        if not path.exists():
            continue
        text = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
        reject_reader_labels(text)
        if normalized(text).count(normalized(LOSS)) != 1:
            raise ValueError(f"Full assumption statement must appear once in PDF: {name}")
        if normalized(HISTORY) not in normalized(text):
            raise ValueError(f"Post-results history missing from PDF: {name}")
        info = subprocess.check_output(["pdfinfo", str(path)], text=True)
        match = re.search(r"Pages:\s+(\d+)", info)
        if match is None:
            raise ValueError("PDF page count unavailable")
        pages[name] = int(match[1])
        if pages[name] > limit or (name == "policy_note" and pages[name] != 2):
            raise ValueError(f"Page limit exceeded: {name} = {pages[name]}")
    return pages


def check(root: Path = ROOT, include_pdfs: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "frozen": frozen_checks(root),
        "sources": source_checks(root),
        "new_empirical_runs": 0,
    }
    caption = (root / "figures/g5/headline_caption.txt").read_text()
    if SHORT_LOSS not in caption or SCENARIO not in caption or LOSS in caption:
        raise ValueError("Headline caption requires the short loss reference and scenario label")
    reject_reader_labels(caption)
    if include_pdfs:
        result["pages"] = pdf_checks(root)
    return result


def render_headline(r: Registry, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.8))
    x = np.arange(2)
    axes[0].bar(
        x - 0.18,
        [r.value("pd_crisis") * 100, r.value("pd_later") * 100],
        0.36,
        color=COLORS["blue"],
        label="Raw Firth predicted",
    )
    axes[0].bar(
        x + 0.18,
        [r.value("rate_crisis") * 100, r.value("rate_later") * 100],
        0.36,
        color=COLORS["orange"],
        label="Recorded outcome",
    )
    axes[0].set_xticks(x, ["2007–2009", "2011–2013"])
    axes[0].set_ylabel("Recorded charge-off within 36 months (%)")
    axes[0].set_title("Layer 1: calibration does not transport")
    axes[0].legend(fontsize=9)
    sba = np.array([r.value("baseline_sba_loss_usd"), r.value("adverse_sba_loss_usd")]) / 1e6
    lender = (
        np.array([r.value("baseline_lender_loss_usd"), r.value("adverse_lender_loss_usd")]) / 1e6
    )
    axes[1].bar(x, sba, color=COLORS["blue"], label="Assumed SBA allocation")
    axes[1].bar(x, lender, bottom=sba, color=COLORS["green"], label="Assumed lender allocation")
    for i, s in enumerate(["baseline", "adverse"]):
        ci = r.resolve(s + "_expected_loss_usd")["interval"]
        axes[1].vlines(i, ci["lower"] / 1e6, ci["upper"] / 1e6, color="black", lw=1.6)
    axes[1].set_xticks(x, ["Baseline", "Adverse"])
    axes[1].set_ylabel("Gross expected-loss proxy (USD million)")
    axes[1].set_title("Layer 2: fixed 2006 scenario portfolio")
    axes[1].legend(fontsize=8, loc="upper left")
    axes[1].text(
        0.04,
        0.65,
        "Paired EL difference, not a level interval:\n$"
        + r.display("adverse_minus_baseline_expected_loss_usd_change", 1e-6, 1, True)
        + "m",
        transform=axes[1].transAxes,
        fontsize=8,
        bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "none"},
    )
    fig.suptitle(
        "Local economic conditions and public–lender loss sharing\nin SBA 7(a) lending", fontsize=15
    )
    caption = (
        "Layer 1 descriptors are reconstructed from a snapshot; feature vintages remain unverified. "
        + SCENARIO
        + ".\n"
        + "Assumption-based loss proxies; see the technical report, Section 6."
        + "\nRaw Firth calibration error can affect levels, differences and ratios. Bands exclude LGD/path/vintage uncertainty."
    )
    fig.text(0.04, 0.02, "\n".join(textwrap.wrap(caption, 150)), fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.20, 1, 0.89))
    fig.savefig(target / "headline.png", dpi=300)
    fig.savefig(target / "headline.pdf")
    plt.close(fig)
    (target / "headline_caption.txt").write_text(caption + "\n")


def build(root: Path = ROOT) -> Path:
    """Build from existing source cells; output only into ignored presentation staging."""
    source_checks(root)
    frozen_checks(root)
    output = root / "data/editorial-2026-10-09"
    stage = output / "source"
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "report/g5", stage / "report/g5", dirs_exist_ok=True)
    shutil.copytree(root / "figures/g5", stage / "figures/g5", dirs_exist_ok=True)
    render_headline(load(root), stage / "figures/g5")
    compiler = (
        os.environ.get("TECTONIC")
        or shutil.which("tectonic")
        or str(root.parent / ".tools/tectonic/tectonic")
    )
    for name in ["policy_note", "technical_report"]:
        subprocess.run(
            [
                compiler,
                "--only-cached",
                "--keep-logs",
                "--outdir",
                str(output),
                str(stage / "report/g5" / (name + ".tex")),
            ],
            check=True,
        )
    paper = root / "report/paper"
    if paper.exists():
        shutil.copytree(paper, stage / "report/paper", dirs_exist_ok=True)
        generated = stage / "report/paper/generated"
        shutil.copytree(root / "report/g5/generated", generated, dirs_exist_ok=True)
        provenance = json.loads((paper / "provenance.json").read_text())
        for name, rule in provenance["label_replacements"].items():
            text = (generated / (rule["original"] + ".tex")).read_text()
            for old, new in rule["replacements"]:
                text = text.replace(old, new)
            (generated / (name + ".tex")).write_text(text)
        (stage / "report/paper/figures").mkdir(exist_ok=True)
        shutil.copyfile(
            root / "figures/g5/calibration_groups.pdf",
            stage / "report/paper/figures/calibration_groups.pdf",
        )
        subprocess.run(
            [
                compiler,
                "--only-cached",
                "--keep-logs",
                "--outdir",
                str(output),
                str(stage / "report/paper/working_paper.tex"),
            ],
            check=True,
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "build"])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.command == "build":
        print(build(args.root))
    else:
        print(json.dumps(check(args.root), indent=2))


if __name__ == "__main__":
    main()
