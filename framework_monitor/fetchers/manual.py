"""Manual-entry fetcher (FR-6): figures I type into CSV files.

File: ``<dir>/<series>.csv`` with header ``date,value`` and an optional
``vintage_date`` column. Public indicators live in ``framework_monitor/manual/``
(committed); restricted ones (FactSet, S&P DJI, AAII ...) live in
``data/private/manual/``, which travels inside the encrypted private store
and is never committed.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from framework_monitor.fetchers.base import FetchError, clip_dates, to_frame
from framework_monitor.schemas import Indicator
from framework_monitor.settings import Paths


def fetch(series: Indicator, start: dt.date | None = None, end: dt.date | None = None, *, client=None, paths: Paths | None = None) -> pd.DataFrame:
    paths = paths or Paths()
    folder: Path = paths.private_manual_dir if series.licence == "restricted" else paths.public_manual_dir
    path = folder / f"{series.series}.csv"
    if not path.exists():
        raise FetchError(f"manual file not found: {path}")
    raw = pd.read_csv(path, dtype=str, comment="#")
    if not {"date", "value"} <= set(raw.columns):
        raise FetchError(f"{path} needs columns date,value (got {list(raw.columns)})")
    if "vintage_date" in raw.columns:
        df = to_frame(list(zip(raw["date"], raw["value"], raw["vintage_date"])), has_vintage=True)
    else:
        df = to_frame(list(zip(raw["date"], raw["value"])))
    return clip_dates(df, start, end)
