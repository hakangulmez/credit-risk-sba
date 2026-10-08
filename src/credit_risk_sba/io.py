"""Private raw inputs; only aggregate outputs are published."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str, allow_nan=False) + "\n")


def config(root: Path) -> dict:
    return yaml.safe_load((root / "config/g2.yaml").read_text())


def table(root: Path, name: str, rows) -> pd.DataFrame:
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    destination = root / "results/g2-2026-10-08" / f"{name}.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    return frame
