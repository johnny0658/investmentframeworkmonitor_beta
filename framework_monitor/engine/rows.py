"""PRD Step 2: row score and confidence, plus my overrides.

* Row score = weighted mean of the row's available signals (weights from
  indicators.yaml; indicators with weight 0 are monitor-only).
* Freshness = share of the row's total weight whose data is fresh and
  produced a signal. Missing data counts as not fresh.
* Agreement = max(0, 1 - std(signals) / 2), using population std over the
  row's available signals. One signal gives agreement 1.
* Confidence = freshness x agreement.
* Override (judgements.yaml): applied while ``expires >= as_of``. Past its
  expiry it is dropped and flagged. The computed score is always kept, so the
  gap stays visible.

Only indicators that can produce data count towards a row: enabled, weight
> 0, and for derived indicators every input enabled. That way a row is not
penalised for sources that arrive in a later phase.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import numpy as np

from framework_monitor.engine.signals import Signal
from framework_monitor.schemas import Config, Indicator, Judgement


@dataclass
class RowScore:
    row_id: str
    layer: int
    computed_score: float | None
    confidence: float
    freshness: float
    agreement: float | None
    n_signals: int
    override_score: float | None = None
    override_confidence: float | None = None
    override_reason: str | None = None
    override_active: bool = False
    override_expired: bool = False

    @property
    def final_score(self) -> float | None:
        return self.override_score if self.override_active else self.computed_score

    @property
    def final_confidence(self) -> float:
        return self.override_confidence if self.override_active else self.confidence


def can_produce(ind: Indicator, cfg: Config) -> bool:
    if not ind.enabled:
        return False
    if ind.source == "derived":
        by = cfg.by_id
        return all(can_produce(by[i], cfg) for i in ind.formula_inputs)
    return True


def score_row(weights: dict[str, float], signals: dict[str, Signal]) -> tuple[float | None, float, float | None, int]:
    """Returns (score, freshness, agreement, n_signals) for one row."""
    total_w = sum(weights.values())
    used = {i: signals[i] for i in weights if i in signals and signals[i].available}
    if total_w <= 0 or not used:
        return None, 0.0, None, 0
    w_used = sum(weights[i] for i in used)
    score = sum(weights[i] * used[i].signal for i in used) / w_used
    freshness = sum(weights[i] for i in used if used[i].fresh) / total_w
    agreement = max(0.0, 1.0 - float(np.std([s.signal for s in used.values()])) / 2.0)
    return score, freshness, agreement, len(used)


def active_override(row_id: str, judgements: list[Judgement], as_of: dt.date) -> tuple[Judgement | None, bool]:
    """(override in force, whether an expired one was dropped). The last entry for a row wins."""
    mine = [j for j in judgements if j.row == row_id]
    if not mine:
        return None, False
    j = mine[-1]
    return (j, False) if j.expires >= as_of else (None, True)


def score_rows(cfg: Config, signals: dict[str, Signal], as_of: dt.date) -> list[RowScore]:
    out = []
    for row in cfg.rows.rows:
        weights = {i.id: i.weight for i in cfg.indicators if i.row == row.id and i.weight > 0 and can_produce(i, cfg)}
        score, fresh, agree, n = score_row(weights, signals)
        conf = fresh * agree if agree is not None else 0.0
        rs = RowScore(row.id, row.layer, score, conf, fresh, agree, n)
        j, expired = active_override(row.id, cfg.judgements, as_of)
        rs.override_expired = expired
        if j is not None:
            rs.override_score, rs.override_confidence, rs.override_reason = j.score, j.confidence, j.reason
            rs.override_active = True
        out.append(rs)
    return out


def fmt(x: float | None, nd: int = 2) -> str:
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.{nd}f}"
