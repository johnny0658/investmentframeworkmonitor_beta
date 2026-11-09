"""Indicator transforms (PRD Step 1), applied before z-scoring.

All series are pandas Series on a sorted DatetimeIndex. Lags use calendar
offsets, so one rule works for any frequency: the lagged value is the last
observation on or before ``t - offset``, and it must lie within a tolerance
of that target (otherwise there is a gap in the data and the result is NaN).

  level         x
  yoy           (x / x[t - 1 year] - 1) * 100          percent
  ann_3m        ((x / x[t - 3 months]) ** 4 - 1) * 100  percent, annualised
  diff_4w       x - x[t - 4 weeks]                     units of x
  diff_13w_pct  (x / x[t - 13 weeks] - 1) * 100         percent
  pct_rank      x  (ranked against its window in the signal step)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OFFSETS = {
    "yoy": pd.DateOffset(years=1),
    "ann_3m": pd.DateOffset(months=3),
    "diff_4w": pd.DateOffset(weeks=4),
    "diff_13w_pct": pd.DateOffset(weeks=13),
}

# How far the lagged observation may sit before its target date.
LAG_TOLERANCE_DAYS = {
    "daily": 7,
    "weekly": 10,
    "monthly": 20,
    "quarterly": 50,
    "per_auction": 45,
    "annual": 120,
    "irregular": 60,
}


def lagged(x: pd.Series, offset: pd.DateOffset, tolerance_days: int) -> pd.Series:
    """Value of x at (t - offset), aligned to x's own index."""
    if x.empty:
        return x.copy()
    targets = x.index - offset
    pos = x.index.searchsorted(targets, side="right") - 1
    vals = np.full(len(x), np.nan)
    ok = pos >= 0
    vals[ok] = x.to_numpy()[pos[ok]]
    gap = np.zeros(len(x), dtype=bool)
    gap[ok] = (targets[ok] - x.index[pos[ok]]).days > tolerance_days
    vals[gap] = np.nan
    return pd.Series(vals, index=x.index)


def transform(x: pd.Series, kind: str, frequency: str = "daily") -> pd.Series:
    x = x.dropna().sort_index()
    if kind in ("level", "pct_rank"):
        return x
    tol = LAG_TOLERANCE_DAYS.get(frequency, 30)
    lag = lagged(x, OFFSETS[kind], tol)
    with np.errstate(divide="ignore", invalid="ignore"):
        if kind == "yoy":
            out = (x / lag - 1) * 100
        elif kind == "ann_3m":
            out = ((x / lag) ** 4 - 1) * 100
        elif kind == "diff_4w":
            out = x - lag
        elif kind == "diff_13w_pct":
            out = (x / lag - 1) * 100
        else:  # pragma: no cover - schema restricts the values
            raise ValueError(kind)
    return out.replace([np.inf, -np.inf], np.nan).dropna()
