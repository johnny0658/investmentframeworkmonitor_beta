"""ALFRED fetcher: FRED observations with every vintage (real-time period).

Uses the FRED API with ``realtime_start=1776-07-04`` and
``realtime_end=9999-12-31``, which returns one row per (date, vintage) where
the value changed. Each row's ``realtime_start`` becomes ``vintage_date`` so
the bitemporal store can answer "what did I know on date X" (FR-8).

Without ``FRED_API_KEY`` it degrades to the plain FRED fetcher (current
values, vintage = fetch date) and says so in the returned frame's attrs.
"""

from __future__ import annotations

import datetime as dt
import os

import httpx
import pandas as pd

from framework_monitor.fetchers import fred
from framework_monitor.fetchers.base import FetchError, get_with_retry, make_client, to_frame
from framework_monitor.schemas import Indicator

API_URL = fred.API_URL
PAGE_LIMIT = 100_000  # FRED API maximum per request


def fetch(series: Indicator, start: dt.date | None = None, end: dt.date | None = None, *, client: httpx.Client | None = None) -> pd.DataFrame:
    client = client or make_client()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        df = fred.fetch(series, start, end, client=client)
        df.attrs["degraded"] = "no FRED_API_KEY: current values only, no vintages"
        return df

    rows: list[tuple] = []
    offset = 0
    while True:
        params = {
            "series_id": series.series,
            "api_key": key,
            "file_type": "json",
            "realtime_start": "1776-07-04",
            "realtime_end": "9999-12-31",
            "limit": PAGE_LIMIT,
            "offset": offset,
            "sort_order": "asc",
        }
        if start:
            params["observation_start"] = start.isoformat()
        if end:
            params["observation_end"] = end.isoformat()
        payload = get_with_retry(client, API_URL, params=params).json()
        if "observations" not in payload:
            raise FetchError(f"ALFRED returned no observations for {series.series}: {payload.get('error_message', '')}")
        obs = payload["observations"]
        rows.extend((o["date"], o["value"], o["realtime_start"]) for o in obs)
        total = int(payload.get("count", len(obs)))
        offset += len(obs)
        if not obs or offset >= total:
            break
    return to_frame(rows, has_vintage=True)
