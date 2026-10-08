"""Layer-specific training-frequency pooling, frozen before weighted inference."""

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import linalg, sparse
from sklearn.preprocessing import OneHotEncoder

from .data import CAT


@dataclass
class PooledDesign:
    numeric: list[str]
    categorical: list[str] = field(default_factory=lambda: CAT.copy())
    maps: dict = field(default_factory=dict)
    threshold: float = 0.001
    rank_tolerance: float = 1e-10

    def mapped(self, frame):
        out = frame[self.categorical].copy()
        for col in self.categorical:
            s = out[col].fillna("__missing__").replace("", "__missing__").astype(str)
            mapping = self.maps[col]
            levels = set(mapping.values())
            fallback = "Other" if "Other" in levels else "__unseen_not_fitted__"
            out[col] = s.map(mapping).fillna(fallback)
        return out

    def fit(self, frame):
        if not frame.role.eq("train").all():
            raise ValueError("Pooling/preprocessing requires layer estimation rows only")
        records = []
        for col in self.categorical:
            s = frame[col].fillna("__missing__").replace("", "__missing__").astype(str)
            counts = s.value_counts()
            mapping = {
                level: (
                    "Other" if col != "ProjectState" and n / len(frame) < self.threshold else level
                )
                for level, n in counts.items()
            }
            self.maps[col] = mapping
            for level, n in counts.items():
                records.append(
                    {
                        "feature": col,
                        "original_level": level,
                        "pooled_level": mapping[level],
                        "training_n": int(n),
                        "frequency": n / len(frame),
                        "threshold": self.threshold,
                        "state_exempt": col == "ProjectState",
                    }
                )
        self.map_records = pd.DataFrame(records)
        pooled = self.mapped(frame)
        level_records = []
        for col in self.categorical:
            q = pd.DataFrame({"level": pooled[col], "Y": frame.Y.to_numpy()})
            for level, g in q.groupby("level"):
                level_records.append(
                    {
                        "feature": col,
                        "level": level,
                        "n": len(g),
                        "events": int(g.Y.sum()),
                        "non_events": int(len(g) - g.Y.sum()),
                    }
                )
        self.level_records = pd.DataFrame(level_records)
        raw = frame[self.numeric].to_numpy(dtype=float)
        self.median = np.array(
            [np.median(x[np.isfinite(x)]) if np.isfinite(x).any() else 0 for x in raw.T]
        )
        vals = np.where(np.isfinite(raw), raw, self.median)
        self.mean = vals.mean(axis=0)
        self.scale = vals.std(axis=0)
        self.scale[self.scale < 1e-12] = 1
        self.encoder = OneHotEncoder(drop="first", handle_unknown="ignore", dtype=np.float64).fit(
            pooled
        )
        self.names = (
            ["intercept"]
            + self.numeric
            + [n + "__missing" for n in self.numeric]
            + list(self.encoder.get_feature_names_out(self.categorical))
        )
        x = self.transform(frame)
        gram = (x.T @ x).toarray() / len(frame)
        # Intercept/state effects receive outcome-independent basis priority.
        state = [i for i, n in enumerate(self.names) if n.startswith("ProjectState_")]
        order = [0] + state + [i for i in range(1, len(self.names)) if i not in state]
        keep: list[int] = []
        cut = max(float(np.max(np.diag(gram))), 1) * self.rank_tolerance
        for i in order:
            residual = gram[i, i]
            if keep:
                residual -= gram[i, keep] @ linalg.solve(
                    gram[np.ix_(keep, keep)], gram[keep, i], assume_a="pos"
                )
            if residual > cut:
                keep.append(i)
        self.keep = np.sort(keep)
        self.dropped = [n for i, n in enumerate(self.names) if i not in keep]
        if not set(state) <= set(self.keep):
            raise ValueError("A supported state fixed effect was lost")
        self.row_hash = hashlib.sha256("\n".join(frame.row_id.astype(str)).encode()).hexdigest()
        return self

    def transform(self, frame, reduced=False):
        raw = frame[self.numeric].to_numpy(dtype=float)
        missing = ~np.isfinite(raw)
        vals = (np.where(missing, self.median, raw) - self.mean) / self.scale
        x = sparse.hstack(
            [
                np.ones((len(frame), 1)),
                vals,
                missing.astype(float),
                self.encoder.transform(self.mapped(frame)),
            ],
            format="csr",
        )
        return x[:, self.keep] if reduced else x

    def tree(self, frame):
        out = frame[self.numeric].copy()
        pooled = self.mapped(frame)
        for col, levels in zip(self.categorical, self.encoder.categories_, strict=True):
            out[col] = pd.Categorical(pooled[col], categories=levels)
        return out

    def contract(self):
        return {
            "training_row_sha256": self.row_hash,
            "numeric": self.numeric,
            "categorical": self.categorical,
            "maps": self.maps,
            "full_columns": self.names,
            "columns": [self.names[i] for i in self.keep],
            "dropped_constant_or_redundant": self.dropped,
            "rank": len(self.keep),
            "median": self.median.tolist(),
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "category_references": {
                c: str(v[0])
                for c, v in zip(self.categorical, self.encoder.categories_, strict=True)
            },
            "unknown": "fitted Other else zero dummy vector; no unsupported level coefficients",
        }
