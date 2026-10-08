"""Read-only scope checks for the single public research notebook."""

from __future__ import annotations

import ast
import json
from pathlib import Path

NOTEBOOK = "notebooks/research_walkthrough.ipynb"


def validate_notebook(path: Path, require_outputs: bool = True) -> dict[str, int | bool]:
    notebook = json.loads(path.read_text())
    mode = notebook["metadata"].get("portfolio", {})
    if (
        mode.get("mode") != "frozen-aggregate-walkthrough"
        or mode.get("empirical_execution") is not False
    ):
        raise ValueError("Notebook must declare frozen-results mode")
    allowed = {
        "pathlib",
        "json",
        "sys",
        "matplotlib",
        "numpy",
        "pandas",
        "yaml",
        "IPython",
        "reporting",
    }
    forbidden = {
        "fit",
        "fit_transform",
        "predict",
        "predict_proba",
        "load_model",
        "system",
        "run",
        "Popen",
        "post",
        "request",
        "write_text",
        "write_bytes",
        "to_csv",
        "to_parquet",
    }
    counts = {"code_cells": 0, "output_items": 0, "manual_guide_disabled": False}
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        counts["code_cells"] += 1
        source = "".join(cell["source"])
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [item.name.split(".")[0] for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
                if names == ["reporting"] and node.module not in {
                    "reporting.checks",
                    "reporting.registry",
                }:
                    raise ValueError("Notebook imports an unapproved reporting module")
            else:
                names = []
            if any(name not in allowed for name in names):
                raise ValueError("Notebook imports a network, execution or model package")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden:
                    raise ValueError("Notebook contains a fit, network, shell or file-write call")
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "exec",
                    "eval",
                    "compile",
                    "__import__",
                }:
                    raise ValueError("Notebook contains dynamic code execution")
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "ENABLE_PRIVATE_REESTIMATION_GUIDE"
                    ):
                        if (
                            not isinstance(node.value, ast.Constant)
                            or node.value.value is not False
                        ):
                            raise ValueError("Private guide must be disabled by default")
                        counts["manual_guide_disabled"] = True
        if require_outputs and cell.get("execution_count") is None:
            raise ValueError("Published code cell has not been executed")
        for output in cell.get("outputs", []):
            counts["output_items"] += 1
            if output["output_type"] == "error":
                raise ValueError("Notebook contains an execution error")
            if "application/javascript" in output.get("data", {}):
                raise ValueError("Executable JavaScript output is not allowed")
    if not counts["manual_guide_disabled"]:
        raise ValueError("Notebook is missing its disabled manual-guide flag")
    return counts
