"""Train-only preprocessing; both future cohorts and scenarios use frozen transforms."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import linalg, sparse
from sklearn.preprocessing import OneHotEncoder

from .data import ALLOWLIST, CAT, NUM


@dataclass
class Design:
    numeric: list[str]
    categorical: list[str]
    median: np.ndarray = field(init=False)
    mean: np.ndarray = field(init=False)
    scale: np.ndarray = field(init=False)
    encoder: OneHotEncoder = field(init=False)
    names: list[str] = field(init=False)
    train_ids: np.ndarray = field(init=False)
    keep: np.ndarray = field(init=False)
    dropped: list[str] = field(init=False)

    @classmethod
    def create(cls, term=False, macro=None):
        return cls(NUM + (["TermInMonths"] if term else []) + (macro or []), CAT.copy())

    def fit(self, frame: pd.DataFrame):
        if not frame.role.eq("train").all():
            raise ValueError("Preprocessing may only fit on frozen training rows")
        if not set(self.numeric + self.categorical).issubset(ALLOWLIST):
            raise ValueError("A post-approval or nonallowlisted predictor was requested")
        raw = frame[self.numeric].to_numpy(dtype=float)
        self.median = np.array([np.median(v[np.isfinite(v)]) if np.isfinite(v).any() else 0
                                for v in raw.T])
        imputed = np.where(np.isfinite(raw), raw, self.median)
        self.mean = imputed.mean(axis=0)
        self.scale = imputed.std(axis=0)
        self.scale[self.scale < 1e-12] = 1
        self.encoder = OneHotEncoder(drop="first", handle_unknown="ignore", dtype=np.float64)
        self.encoder.fit(frame[self.categorical])
        self.names = (["intercept"] + self.numeric + [f"{n}__missing" for n in self.numeric]
                      + list(self.encoder.get_feature_names_out(self.categorical)))
        self.train_ids = frame.row_id.to_numpy()
        full = self.transform(frame)
        gram = (full.T @ full).toarray() / len(frame)
        _, r, pivot = linalg.qr(gram, pivoting=True)
        diagonal = np.abs(np.diag(r))
        rank = int((diagonal > max(diagonal.max(), 1) * 1e-10).sum())
        self.keep = np.sort(pivot[:rank])
        self.dropped = [self.names[i] for i in range(len(self.names)) if i not in self.keep]
        return self

    def transform(self, frame: pd.DataFrame, reduced=False):
        raw = frame[self.numeric].to_numpy(dtype=float)
        missing = ~np.isfinite(raw)
        values = (np.where(missing, self.median, raw) - self.mean) / self.scale
        x = sparse.hstack([np.ones((len(frame), 1)), values, missing.astype(float),
                           self.encoder.transform(frame[self.categorical])], format="csr")
        return x[:, self.keep] if reduced else x

    def tree(self, frame: pd.DataFrame):
        # Native categorical codes use -1 for unseen values, with train-only vocabularies.
        x = frame[self.numeric].copy()
        for col, categories in zip(self.categorical, self.encoder.categories_, strict=True):
            x[col] = pd.Categorical(frame[col], categories=categories)
        return x

    def support(self, train: pd.DataFrame, target: pd.DataFrame):
        rows = []
        for col in self.numeric:
            values = train[col]
            rows.append({"feature": col, "n": len(target), "missing": int(target[col].isna().sum()),
                         "outside_train_range": int((target[col].lt(values.min()) |
                                                     target[col].gt(values.max())).sum()),
                         "unseen_category": 0})
        for col, categories in zip(self.categorical, self.encoder.categories_, strict=True):
            rows.append({"feature": col, "n": len(target), "missing": 0,
                         "outside_train_range": 0,
                         "unseen_category": int((~target[col].isin(categories)).sum())})
        return rows
