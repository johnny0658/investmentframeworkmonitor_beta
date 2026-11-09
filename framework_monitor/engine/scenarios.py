"""PRD Step 3: signposts and scenario probabilities.

Each active signpost multiplies each scenario's probability by its likelihood
ratio, and the result is renormalised:

    P'(S_k) = P(S_k) * prod_f L_f(S_k) / sum_j P(S_j) * prod_f L_f(S_j)

Guards:
1. **Family cap.** Within a family, only the strongest LR per scenario counts:
   the one furthest from 1 in log terms. Correlated signals are not
   independent evidence.
2. **Shrinkage.** final = (1 - lambda) * posterior + lambda * prior, with
   lambda = ``shrinkage_to_prior`` (0.2).

The update always starts from my last *confirmed* priors (scenarios.yaml),
not from yesterday's output. Probabilities therefore reflect the signposts
active today and cannot compound away. I confirm a new prior by editing
scenarios.yaml.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from framework_monitor.schemas import Signpost


@dataclass
class ScenarioUpdate:
    prior: dict[str, float]
    multiplier: dict[str, float]  # product over families of the capped LRs
    posterior: dict[str, float]
    final: dict[str, float]
    family_lrs: dict[str, dict[str, float]]  # family -> scenario -> LR used


def family_capped_lrs(active: list[Signpost]) -> dict[str, dict[str, float]]:
    fam: dict[str, dict[str, float]] = {}
    for sp in active:
        cur = fam.setdefault(sp.family, {})
        for k, lr in sp.lr.items():
            if k not in cur or abs(math.log(lr)) > abs(math.log(cur[k])):
                cur[k] = lr
    return fam


def update(prior: dict[str, float], active: list[Signpost], shrinkage: float) -> ScenarioUpdate:
    fam = family_capped_lrs(active)
    mult = {k: 1.0 for k in prior}
    for lrs in fam.values():
        for k in mult:
            mult[k] *= lrs.get(k, 1.0)
    unnorm = {k: prior[k] * mult[k] for k in prior}
    z = sum(unnorm.values())
    posterior = {k: v / z for k, v in unnorm.items()} if z > 0 else dict(prior)
    final = {k: (1 - shrinkage) * posterior[k] + shrinkage * prior[k] for k in prior}
    return ScenarioUpdate(dict(prior), mult, posterior, final, fam)
