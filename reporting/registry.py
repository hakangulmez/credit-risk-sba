"""Unique, hash-bound claims from saved aggregates; no statistical estimation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("results/g5-2026-10-08")
BASE = Path("results/g2-bis-2026-10-08")
SCENARIO = "Scenario projections on the fixed 2006 portfolio; not out-of-sample validation"
OUTCOME = "recorded charge-off within 36 months"
LOSS = (
    "EAD = GrossApproval; full-disbursement proxy, CCF = 100%. LGD is the gross "
    "charge-off proxy on the same approval denominator. SBA/lender amounts use "
    "assumption-based pro-rata guarantee allocation."
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def scalar(raw: str) -> Any:
    if raw == "":
        return None
    try:
        number = float(raw)
        if not math.isfinite(number):
            return raw
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def select(path: Path, selector: dict[str, Any]) -> dict[str, str]:
    found = [r for r in rows(path) if all(str(r[k]) == str(v) for k, v in selector.items())]
    if len(found) != 1:
        raise ValueError(f"Expected one source row, found {len(found)}: {path} {selector}")
    return found[0]


def identifier(file: str, selector: dict[str, Any], column: str) -> str:
    key = json.dumps([file, selector, column], sort_keys=True)
    return "N" + hashlib.sha256(key.encode()).hexdigest()[:14]


def units(file: str, column: str, row: dict[str, str]) -> str:
    metric = row.get("metric", "")
    if "usd" in column or "usd" in metric or column == "flagged_approval_usd":
        return "USD"
    if column in {
        "n",
        "events",
        "non_events",
        "eligible_n",
        "macro_excluded_n",
        "excluded",
        "remaining",
        "attempted_draws",
        "effective_interval_draws",
        "bootstrap_draws",
        "undefined_draws",
        "recorded_charge_offs_36m",
        "states",
        "rank",
        "full_columns",
        "state_dummy_columns",
        "iterations",
        "flagged_loan_n",
        "pd_n",
        "loss_n",
    } or column.endswith("_n"):
        return "count"
    if file == "firth_macro_associations.csv" or "pd_change_pp" in metric:
        return "probability percentage points"
    if file == "firth_average_associations.csv":
        return "probability percentage points per native input unit"
    if metric in {
        "calibration_intercept",
        "calibration_slope",
        "auc",
        "average_precision",
        "brier",
    }:
        return "unitless " + metric
    if column in {
        "lower_edge",
        "upper_edge",
        "mean_predicted",
        "recorded_rate",
        "predicted_pd",
        "match_abs_le_3_share",
        "flagged_fraction",
        "missing_share",
    } or metric in {"pd", "loss_rate", "loss_rate_change"}:
        return "fraction"
    if file == "firth_coefficients.csv":
        return "log odds; train-standardized numeric columns"
    if column == "lgd_proxy":
        return "gross charged-off dollars per approved dollar"
    return "source-defined; see source column and protocol"


class Registry:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.entries: dict[str, dict[str, Any]] = {}
        self.aliases: dict[str, str] = {}
        self.render_log: list[dict[str, Any]] = []

    def add_csv(self, name: str, keys: list[str], columns: list[str], keep: Any = None) -> None:
        path = BASE / name
        source_hash = digest(self.root / path)
        seen = set()
        for row in rows(self.root / path):
            if keep is not None and not keep(row):
                continue
            selector = {k: row[k] for k in keys}
            identity = tuple(selector.items())
            if identity in seen:
                raise ValueError(("Non-unique source selector", name, selector))
            seen.add(identity)
            for col in columns:
                if col not in row:
                    continue
                value = scalar(row[col])
                claim_id = identifier(name, selector, col)
                scenario = name in {
                    "firth_stress.csv",
                    "scenario_support_summary.csv",
                    "scenario_support_by_feature.csv",
                }
                scope = (
                    SCENARIO
                    if scenario
                    else row.get(
                        "layer_interpretation",
                        row.get("interpretation", "Saved aggregate diagnostic"),
                    )
                )
                source_context = row.get("macro_information_context") if scenario else None
                if scenario and not source_context:
                    raise ValueError("Missing stipulated-path source interpretation")
                interval = None
                if col == "value" and "lower" in row:
                    interval = {
                        "source_path": str(path),
                        "sha256": source_hash,
                        "selector": selector,
                        "lower_column": "lower",
                        "upper_column": "upper",
                        "lower": scalar(row["lower"]),
                        "upper": scalar(row["upper"]),
                        "scope": row.get(
                            "interval",
                            "State-cluster evaluation interval conditional on the fitted model",
                        ),
                        "successful_draws": scalar(row.get("effective_interval_draws", "")),
                        "attempted_draws": scalar(
                            row.get("attempted_draws", row.get("bootstrap_draws", ""))
                        ),
                    }
                if name == "calibration_deciles.csv" and col == "recorded_rate":
                    interval = {
                        "source_path": str(path),
                        "sha256": source_hash,
                        "selector": selector,
                        "lower_column": "lower",
                        "upper_column": "upper",
                        "lower": scalar(row["lower"]),
                        "upper": scalar(row["upper"]),
                        "scope": "999 state-cluster evaluation draws conditional on the fitted model; stored training-score decile edges; no binomial intervals",
                        "attempted_draws": 999,
                        "undefined_draws": scalar(row["undefined_draws"]),
                    }
                if interval and name == "evaluation_metrics.csv":
                    interval["successful_draws"] = scalar(row["bootstrap_draws"]) - scalar(
                        row["undefined_draws"]
                    )
                    interval["effective_count_formula"] = (
                        "bootstrap_draws - undefined_draws; saved aggregate counts"
                    )
                if interval and name == "calibration_deciles.csv":
                    interval["successful_draws"] = 999 - scalar(row["undefined_draws"])
                    interval["effective_count_formula"] = (
                        "999 - undefined_draws; saved aggregate counts"
                    )
                self.entries[claim_id] = {
                    "id": claim_id,
                    "source_path": str(path),
                    "source_sha256": source_hash,
                    "selector": selector,
                    "column": col,
                    "raw_source_text": row[col],
                    "raw_value": value,
                    "units": units(name, col, row),
                    "model_variant": row.get("variant", row.get("layer")),
                    "model": row.get("model"),
                    "cohort_portfolio": row.get(
                        "cohort", row.get("scenario", row.get("years", "source population"))
                    ),
                    "outcome": row.get("outcome", OUTCOME),
                    "role": row.get("specification_role", "sample/diagnostic metadata"),
                    "denominator": {
                        k: scalar(row[k])
                        for k in ["n", "pd_n", "loss_n", "valid_n", "eligible_n"]
                        if k in row
                    },
                    "supported_interpretation": scope,
                    "source_macro_information_context": source_context,
                    "interval": interval,
                    "display": {
                        "conversion": "identity; percentage/million conversions explicitly chosen by renderer",
                        "rounding": "renderer-specified decimals; no new intervals",
                    },
                    "locations": ["technical tables/appendix", "claims registry"],
                    "qualifications": [
                        "Associational retrospective evidence; frozen outputs, not new estimation",
                        "Training refit intervals hold preprocessing, portfolio, LGD and paths fixed"
                        if name.startswith("firth_")
                        else "Conditional evaluation intervals do not include training uncertainty",
                    ],
                    "prohibited_interpretations": [
                        "causal macro/guarantee effect",
                        "strong transportability",
                        "calibration solved",
                        "actual fiscal cost",
                        "joint support established",
                        "real-time Layer 2 forecast",
                    ],
                    "formula": None,
                }

    def lookup_id(self, file: str, selector: dict[str, Any], column: str = "value") -> str:
        row = select(self.root / BASE / file, selector)
        matches = [
            k
            for k, c in self.entries.items()
            if c.get("source_path") == str(BASE / file)
            and c.get("column") == column
            and all(str(row[a]) == str(b) for a, b in c["selector"].items())
        ]
        if len(matches) != 1:
            raise ValueError(("Claim identity not unique", file, selector, column, matches))
        return matches[0]

    def alias(
        self,
        alias: str,
        file: str,
        selector: dict[str, Any],
        column: str = "value",
        finding: str = "",
    ) -> None:
        key = self.lookup_id(file, selector, column)
        self.aliases[alias] = key
        self.entries[key]["finding"] = finding
        self.entries[key]["locations"] += ["README/policy/headline/LinkedIn/CV as applicable"]

    def derive(
        self,
        alias: str,
        operation: str,
        inputs: list[str],
        scale: float = 1.0,
        unit: str = "unitless",
    ) -> None:
        refs = [self.aliases.get(x, x) for x in inputs]
        vals = [self.entries[x]["raw_value"] for x in refs]
        value = (vals[0] / vals[1] if operation == "divide" else 1 - vals[0]) * scale
        self.entries[alias] = {
            "id": alias,
            "source_claims": refs,
            "formula": {"operation": operation, "inputs": refs, "scale": scale},
            "raw_value": value,
            "units": unit,
            "interval": None,
            "supported_interpretation": SCENARIO,
            "locations": ["policy/technical/README/headline"],
            "qualifications": [
                "Arithmetic of saved point aggregates; no ratio/share interval is available",
                LOSS,
            ],
            "prohibited_interpretations": [
                "calibration-invariant ratio",
                "actual guarantee payouts",
            ],
        }
        self.aliases[alias] = alias

    def resolve(self, name: str) -> dict[str, Any]:
        return self.entries[self.aliases.get(name, name)]

    def value(self, name: str) -> Any:
        return self.resolve(name)["raw_value"]

    def display(
        self,
        name: str,
        scale: float = 1,
        digits: int = 2,
        interval: bool = False,
        integer: bool = False,
    ) -> str:
        entry = self.resolve(name)
        raw = entry["raw_value"]
        if raw is None:
            val = "unavailable"
        elif isinstance(raw, str):
            val = raw
        else:
            val = f"{raw * scale:,.0f}" if integer else f"{raw * scale:.{digits}f}"
        self.render_log.append(
            {
                "id": entry["id"],
                "scale": scale,
                "digits": digits,
                "interval": interval,
                "integer": integer,
                "display": val,
            }
        )
        if raw is None or isinstance(raw, str):
            return val
        if isinstance(raw, str):
            return raw
        val = f"{raw * scale:,.0f}" if integer else f"{raw * scale:.{digits}f}"
        bounds = entry.get("interval")
        if interval and bounds and bounds["lower"] is not None and bounds["upper"] is not None:
            val += f" [{bounds['lower'] * scale:.{digits}f}, {bounds['upper'] * scale:.{digits}f}]"
        self.render_log[-1]["display"] = val
        return val

    def human_display(self, name: str) -> tuple[str, str]:
        """Units and precision for the claims ledger; leave registry values unchanged."""
        entry = self.resolve(name)
        unit = entry["units"]
        interval = entry.get("interval") is not None
        if name == "method_pool_cutoff":
            return self.display(name, digits=3), "fraction of training observations"
        if name == "method_seed":
            return self.display(name, digits=0), "integer seed"
        method_units = {
            "method_horizon_months": "calendar months",
            "method_attempts": "attempted training-refit draws",
            "method_evaluation_draws": "conditional evaluation draws",
            "method_max_iterations": "iterations",
            "method_state_count": "states",
            "method_lgd_min_cell": "valid charge-offs (count)",
        }
        if name in method_units:
            return self.display(name, integer=True), method_units[name]
        if unit == "count":
            return self.display(name, integer=True), "count"
        if unit == "fraction":
            return self.display(name, scale=100, digits=2, interval=interval), "percent (%)"
        if unit == "probability percentage points":
            return self.display(
                name, digits=3, interval=interval
            ), "probability percentage points (pp)"
        if unit == "unitless auc":
            return self.display(name, digits=3, interval=interval), "AUC (unitless)"
        if unit == "USD":
            return self.display(name, scale=1e-6, digits=2, interval=interval), "USD millions"
        if unit.startswith("unitless calibration_"):
            return self.display(name, digits=3, interval=interval), unit.replace(
                "unitless ", ""
            ) + " (unitless)"
        return self.display(name, interval=interval), unit

    def save(self) -> None:
        payload = {
            "accepted_release": "8f7343584d55a14f8cae47c3e9fded3ed56503d4",
            "scope": "Frozen aggregate reporting only",
            "stress_support_mapping": {
                "source_field": "macro_information_context",
                "ignored_inherited_field": "layer_interpretation",
                "display_label": SCENARIO,
            },
            "aliases": self.aliases,
            "claims": self.entries,
        }
        (self.root / OUT / "claims_registry.json").write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n"
        )
        paragraphs = [
            "# Claims and provenance — 8 October 2026",
            "",
            "Research release: `8f7343584d55a14f8cae47c3e9fded3ed56503d4`. Created before G5 report prose. All research numbers in reporting are selected from saved aggregates; no new empirical computation.",
            "",
            "The [machine-readable registry](results/g5-2026-10-08/claims_registry.json) includes exact source hashes, unique selectors/columns, raw values, units, model/role/denominator, interval scope, display rules and arithmetic dependencies. Named findings below are aliases into that cell-level registry. Unavailable cells stay unavailable.",
            "",
            "**Stress/support mapping:** use `macro_information_context` and display “"
            + SCENARIO
            + "”. Ignore the inherited retrospective-validation label in these scenario rows. Calibration-group displays preserve training-score bins, stored edges/counts and conditional state-cluster bands.",
            "",
            "Calibration error can change probability levels, differences and ratios. No derived share/ratio interval is invented. All primary models are Term-free; with-Term remains a timing-unverified sensitivity. Coefficients/finite changes are not causal.",
            "",
            "| Claim alias | Display value (stored interval where available) | Units | Source cell ID | Interpretation |",
            "|---|---|---|---|---|",
        ]
        for alias, key in self.aliases.items():
            value, unit = self.human_display(alias)
            paragraphs.append(
                f"| {alias} | {value} | {unit} | `{key}` | {self.entries[key].get('finding', self.entries[key]['supported_interpretation'])} |"
            )
        paragraphs += [
            "",
            "The registry also covers samples/waterfall, benchmark AP/Brier and calibration intervals, all four saved calibration-group displays, convergence/failed fits, sensitivities/support, coefficients and Term audit counts. Dates, section/page numbers and source identifiers are metadata, distinguished from estimates.",
            "",
            "Prohibited stronger interpretations: strong transported model; calibration solved; causal macro/guarantee effects; measured tail risk; actual public spending or guarantee payments; joint support or path plausibility established; real-time macro forecast; IFRS 9/CECL implementation. Negated qualifications and discussion-only future methods are permitted.",
        ]
        (self.root / "CLAIMS.md").write_text("\n".join(paragraphs) + "\n")
