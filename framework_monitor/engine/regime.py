"""Regime classifier (FR-13): growth trend x inflation trend -> one of four boxes.

* Growth trend: each growth nowcast's latest value against its trailing
  6-month average (GDPNow and the NY Fed WEI). Each one votes up or down.
  The majority wins, and a tie goes to WEI. GDPNow is used once its fetcher
  lands (Phase 4).
* Inflation trend: core PCE, 3-month annualised against 12-month (year on
  year). Up if the 3-month rate is higher.

    growth up,   inflation down -> goldilocks
    growth up,   inflation up   -> reflation
    growth down, inflation up   -> stagflation
    growth down, inflation down -> deflationary_bust
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from framework_monitor.engine.transforms import transform

GROWTH_INDICATORS = ["wei", "gdpnow"]  # first one breaks ties
INFLATION_INDICATOR = "core_pce"
TREND_WINDOW = pd.DateOffset(months=6)

BOXES = {(True, False): "goldilocks", (True, True): "reflation", (False, True): "stagflation", (False, False): "deflationary_bust"}


@dataclass
class Regime:
    box: str | None
    growth_up: bool | None
    inflation_up: bool | None
    growth_detail: str
    core_pce_3m_ann: float | None
    core_pce_12m: float | None


def classify(series: dict[str, pd.Series], as_of: dt.date) -> Regime:
    ts = pd.Timestamp(as_of)
    votes: list[tuple[str, bool]] = []
    details = []
    for gid in GROWTH_INDICATORS:
        s = series.get(gid)
        if s is None:
            continue
        s = s[s.index <= ts].dropna()
        if len(s) < 2:
            continue
        window = s[s.index > s.index[-1] - TREND_WINDOW]
        avg = float(window.mean())
        up = float(s.iloc[-1]) > avg
        votes.append((gid, up))
        details.append(f"{gid} {s.iloc[-1]:.2f} vs 6m avg {avg:.2f}")
    growth_up = None
    if votes:
        ups = sum(v for _, v in votes)
        downs = len(votes) - ups
        growth_up = votes[0][1] if ups == downs else ups > downs

    inflation_up = a3 = a12 = None
    pce = series.get(INFLATION_INDICATOR)
    if pce is not None:
        pce = pce[pce.index <= ts].dropna()
        t3 = transform(pce, "ann_3m", "monthly")
        t12 = transform(pce, "yoy", "monthly")
        if not t3.empty and not t12.empty and t3.index[-1] == t12.index[-1]:
            a3, a12 = float(t3.iloc[-1]), float(t12.iloc[-1])
            inflation_up = a3 > a12

    box = BOXES.get((growth_up, inflation_up)) if growth_up is not None and inflation_up is not None else None
    return Regime(box, growth_up, inflation_up, "; ".join(details), a3, a12)
