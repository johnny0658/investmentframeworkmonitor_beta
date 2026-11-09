"""PRD Step 1: indicator signal.

    s_i = clip(d_i * (x_i - mu_i) / sigma_i, -2, 2)

x_i is the transformed value at the latest observation on or before as_of.
mu_i and sigma_i are the mean and standard deviation of the transformed series
over its trailing window ending at that observation, inclusive: 3 years for
daily and weekly series, 10 years for monthly and slower ones.

For ``pct_rank`` the z-score is replaced by the percentile p of x_i within
the same window (ties count half), mapped linearly to -2..+2:
s = clip(d * (4p - 2), -2, 2).
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from framework_monitor.engine.transforms import transform
from framework_monitor.schemas import Indicator

CLIP = 2.0
WINDOW_YEARS = {"daily": 3, "weekly": 3}  # everything slower: 10 years
SLOW_WINDOW_YEARS = 10
MIN_WINDOW_OBS = 20


@dataclass
class Signal:
    indicator_id: str
    obs_date: dt.date | None
    raw: float | None
    transformed: float | None
    percentile: float | None
    z: float | None
    signal: float | None
    fresh: bool

    @property
    def available(self) -> bool:
        return self.signal is not None and not math.isnan(self.signal)


def window_years(frequency: str) -> int:
    return WINDOW_YEARS.get(frequency, SLOW_WINDOW_YEARS)


def clip(x: float) -> float:
    return float(max(-CLIP, min(CLIP, x)))


def compute_signal(ind: Indicator, raw: pd.Series, as_of: dt.date, stale_override: bool | None = None) -> Signal:
    """Signal for one indicator. `raw` is its series as known at as_of (held values removed)."""
    asof_ts = pd.Timestamp(as_of)
    raw = raw[raw.index <= asof_ts].dropna()
    empty = Signal(ind.id, None, None, None, None, None, None, False)
    if raw.empty:
        return empty
    last_raw_date = raw.index[-1]
    fresh = (asof_ts - last_raw_date).days <= ind.stale_after_days if stale_override is None else stale_override

    x = transform(raw, ind.transform, ind.frequency)
    if x.empty:
        return Signal(ind.id, last_raw_date.date(), float(raw.iloc[-1]), None, None, None, None, fresh)
    t = x.index[-1]
    xv = float(x.iloc[-1])
    window = x[x.index > t - pd.DateOffset(years=window_years(ind.frequency))]
    base = Signal(ind.id, last_raw_date.date(), float(raw.iloc[-1]), xv, None, None, None, fresh)
    if len(window) < MIN_WINDOW_OBS:
        return base
    vals = window.to_numpy()
    if ind.transform == "pct_rank":
        p = (np.sum(vals < xv) + 0.5 * np.sum(vals == xv)) / len(vals)
        base.percentile = float(p)
        base.signal = clip(ind.direction * (4 * p - 2)) if ind.direction else None
        return base
    mu, sigma = float(vals.mean()), float(vals.std(ddof=1))
    if not sigma or math.isnan(sigma):
        return base
    base.z = (xv - mu) / sigma
    base.signal = clip(ind.direction * base.z) if ind.direction else None  # direction 0 = monitor only
    return base


def signal_history(ind: Indicator, raw: pd.Series, start: pd.Timestamp | None = None) -> pd.DataFrame:
    """z-score and signal over time (for charts), same rules as `compute_signal`.

    Uses a time-based rolling window of the indicator's window length (in days),
    so values can differ from `compute_signal` by a day at leap-year edges.
    Columns: transformed, z, percentile, signal.
    """
    raw = raw.dropna().sort_index()
    x = transform(raw, ind.transform, ind.frequency)
    if x.empty:
        return pd.DataFrame(columns=["transformed", "z", "percentile", "signal"])
    days = f"{int(round(365.25 * window_years(ind.frequency)))}D"
    roll = x.rolling(days, min_periods=MIN_WINDOW_OBS)
    out = pd.DataFrame({"transformed": x})
    if ind.transform == "pct_rank":
        def pr(w):
            last = w[-1]
            return (np.sum(w < last) + 0.5 * np.sum(w == last)) / len(w)
        p = roll.apply(pr, raw=True)
        out["z"] = np.nan
        out["percentile"] = p
        out["signal"] = (ind.direction * (4 * p - 2)).clip(-CLIP, CLIP) if ind.direction else np.nan
    else:
        mu, sd = roll.mean(), roll.std()
        z = (x - mu) / sd.replace(0, np.nan)
        out["z"] = z
        out["percentile"] = np.nan
        out["signal"] = (ind.direction * z).clip(-CLIP, CLIP) if ind.direction else np.nan
    if start is not None:
        out = out[out.index >= start]
    return out
