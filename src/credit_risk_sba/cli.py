"""G2 commands only. G3 and publication are deliberately separate gates."""
import argparse
from pathlib import Path

from .data import build
from .fitting import fit_all
from .io import config
from .macro import acquire, join, load, scenarios


def prepare(root):
    acquire(root)
    f = build(root, config(root)["snapshot"])
    u, h = load(root)
    join(f, u, h).to_parquet(root / "data/derived/g2-2026-10-08/matched.parquet", index=False)
    scenarios(u, h).to_csv(root / "results/g2-2026-10-08/scenario_macro_inputs.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Frozen G2 SBA 7(a) analysis")
    parser.add_argument("command", choices=["data", "fit", "evaluate", "stress", "figures", "summary", "all"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command in {"data", "all"}:
        prepare(root)
    if args.command in {"fit", "all"}:
        fit_all(root)
    if args.command in {"evaluate", "all"}:
        from .evaluation import evaluate_all
        evaluate_all(root)
    if args.command in {"stress", "all"}:
        from .stress import secondary_tree_scenarios, stress_all
        stress_all(root)
        secondary_tree_scenarios(root)
    if args.command in {"figures", "all"}:
        from .plots import figures
        figures(root)
    if args.command in {"summary", "all"}:
        from .reporting import summary
        summary(root)


if __name__ == "__main__":
    main()
