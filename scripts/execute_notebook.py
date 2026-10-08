"""Execute the public notebook without registering a system-wide kernel."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.notebook_policy import NOTEBOOK, validate_notebook


def execute(publish: bool = False) -> dict:
    source = ROOT / NOTEBOOK
    validate_notebook(source, require_outputs=False)
    notebook = nbformat.read(source, as_version=4)
    nbformat.validate(notebook)
    output = ROOT / "data/notebook-check"
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="kernel-", dir=output) as temporary:
        kernel_root = Path(temporary)
        kernel = kernel_root / "sba-walkthrough"
        kernel.mkdir()
        (kernel / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                    "display_name": "SBA frozen-results validation",
                    "language": "python",
                }
            )
        )
        manager = KernelManager(
            kernel_name="sba-walkthrough",
            kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_root)]),
        )
        client = NotebookClient(
            notebook,
            km=manager,
            timeout=180,
            record_timing=False,
            resources={"metadata": {"path": str(ROOT / "notebooks")}},
        )
        try:
            client.execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
                manager.cleanup_resources()
    destination = source if publish else output / "research_walkthrough.executed.ipynb"
    nbformat.write(notebook, destination)
    counts = validate_notebook(destination)
    result = {
        **counts,
        "runtime_seconds": round(time.monotonic() - start, 2),
        "execution_mode": "frozen aggregates only",
        "new_model_runs": 0,
        "accepted_notebook_replaced": publish,
    }
    (output / "execution.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--publish-output",
        action="store_true",
        help="Store the checked outputs in the public notebook (explicit authoring only)",
    )
    execute(parser.parse_args().publish_output)
