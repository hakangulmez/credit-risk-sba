"""Independent synthetic weighted Firth checks; no loan observations."""

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse

from credit_risk_sba.bis_data import NAME, js
from credit_risk_sba.bis_firth import fit_firth

root = Path.cwd()
dest = root / "data" / NAME / "validation"
dest.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261008)
n = 180
x = np.c_[np.ones(n), rng.normal(size=n), np.r_[np.zeros(n - 12), np.ones(12)]]
y = rng.binomial(1, 0.2, n)
y[-12:] = 0
w = rng.uniform(0.15, 2.5, n)
pd.DataFrame({"Y": y, "x": x[:, 1], "rare": x[:, 2], "weight": w}).to_csv(
    dest / "synthetic.csv", index=False
)
r = """args=commandArgs(TRUE); .libPaths(c(args[1],.libPaths())); library(brglm2)
d=read.csv(args[2]); f=glm(Y~x+rare,data=d,weights=weight,family=binomial(),method=brglmFit,type="AS_mean",control=brglmControl(maxit=100,epsilon=1e-10)); write.csv(data.frame(coefficient=coef(f)),args[3],row.names=FALSE); cat(as.character(packageVersion("brglm2")),f$converged,"\\n")"""
result = subprocess.run(
    [
        "Rscript",
        "-e",
        r,
        str(root / "data" / NAME / "R-library"),
        str(dest / "synthetic.csv"),
        str(dest / "reference.csv"),
    ],
    capture_output=True,
    text=True,
    check=True,
)
f = fit_firth(sparse.csr_matrix(x), y, w)
reference = pd.read_csv(dest / "reference.csv").coefficient.to_numpy()
assert f.diagnostics["converged"]
np.testing.assert_allclose(f.beta, reference, atol=1e-5, rtol=1e-5)
report = {
    "validation": "synthetic fractional case weights and rare zero-event category",
    "independent_reference": "R brglm2 binomial AS_mean (Firth adjusted score)",
    "R_result": result.stdout.strip(),
    "reference_warnings": result.stderr.strip(),
    "max_coefficient_difference": float(np.max(np.abs(f.beta - reference))),
    "Python_coefficients": f.beta.tolist(),
    "reference_coefficients": reference.tolist(),
    "Python_status": f.diagnostics,
    "passed": True,
    "supplementary_tests": "analytic weighted intercept, finite-difference score, integer-weight replication, dense/sparse equivalence, exact separation, positive shared multipliers",
}
js(root / "results" / NAME / "firth_implementation_validation.json", report)
print(json.dumps(report))
