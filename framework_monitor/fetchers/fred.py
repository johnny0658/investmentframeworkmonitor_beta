"""FRED fetcher.

With ``FRED_API_KEY`` set it uses the official API (series/observations).
Without a key it falls back to FRED's public ``fredgraph.csv`` download, which
needs no key. That way local runs and first CI runs work before the secret
is configured. Both return current values only; see ``alfred`` for vintages.
"""

from __future__ import annotations

import datetime as dt
import io
import os

import httpx
import pandas as pd

from framework_monitor.fetchers.base import FetchError, clip_dates, get_with_retry, make_client, to_frame
from framework_monitor.schemas import Indicator

API_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_URL = "https://api.stlouisfed.org/fred/series"
GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def fetch(series: Indicator, start: dt.date | None = None, end: dt.date | None = None, *, client: httpx.Client | None = None) -> pd.DataFrame:
    client = client or make_client()
    key = os.environ.get("FRED_API_KEY")
    if key:
        return _fetch_api(client, series.series, key, start, end)
    return _fetch_graph_csv(client, series.series, start, end)


def _fetch_api(client, code, key, start, end) -> pd.DataFrame:
    params = {"series_id": code, "api_key": key, "file_type": "json"}
    if start:
        params["observation_start"] = start.isoformat()
    if end:
        params["observation_end"] = end.isoformat()
    payload = get_with_retry(client, API_URL, params=params).json()
    if "observations" not in payload:
        raise FetchError(f"FRED API returned no observations for {code}: {payload.get('error_message', '')}")
    rows = [(o["date"], o["value"]) for o in payload["observations"]]  # "." = missing, dropped by to_frame
    return to_frame(rows)


def _fetch_graph_csv(client, code, start, end) -> pd.DataFrame:
    params = {"id": code}
    if start:
        params["cosd"] = start.isoformat()
    if end:
        params["coed"] = end.isoformat()
    resp = get_with_retry(client, GRAPH_URL, params=params)
    text = resp.text
    if not text.strip() or "<html" in text[:200].lower():
        raise FetchError(f"fredgraph.csv returned no CSV for {code}")
    df = pd.read_csv(io.StringIO(text), dtype=str)
    if df.shape[1] < 2:
        raise FetchError(f"unexpected fredgraph.csv layout for {code}: {list(df.columns)}")
    rows = list(zip(df.iloc[:, 0], df.iloc[:, 1]))
    return clip_dates(to_frame(rows), start, end)


def series_metadata(code: str, *, client: httpx.Client | None = None) -> dict:
    """Title, units, frequency and observation range for `verify-series`."""
    client = client or make_client()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise FetchError("FRED_API_KEY is required for series metadata")
    payload = get_with_retry(client, SERIES_URL, params={"series_id": code, "api_key": key, "file_type": "json"}).json()
    s = payload["seriess"][0]
    return {
        "title": s["title"],
        "units": s["units"],
        "frequency": s["frequency"],
        "observation_start": s["observation_start"],
        "observation_end": s["observation_end"],
        "last_updated": s["last_updated"],
    }


# FRED unit strings -> canonical units in schemas.Units
_UNIT_MAP = [
    ("millions of u.s. dollars", "usd_millions"),
    ("millions of dollars", "usd_millions"),
    ("billions of u.s. dollars", "usd_billions"),
    ("billions of us dollars", "usd_billions"),
    ("billions of dollars", "usd_billions"),
    ("millions of euros", "eur_millions"),
    ("100 million yen", "jpy_100m"),
    ("dollars per barrel", "usd_per_barrel"),
    ("thousands of persons", "thousands_persons"),
    ("percent", "percent"),
    ("index", "index"),
    ("number", "count"),
]


def canonical_units(fred_units: str) -> str | None:
    u = fred_units.strip().lower()
    for prefix, canon in _UNIT_MAP:
        if u.startswith(prefix):
            return canon
    return None
