"""Shared HTTP plumbing for fetchers: retries with exponential back-off (FR-4),
secret redaction, and the standard observation frame.

Every fetcher module exposes::

    fetch(series: Indicator, start: date | None, end: date | None, *, client=None) -> DataFrame

returning columns ``obs_date`` (datetime.date), ``value`` (float) and
``vintage_date`` (datetime.date or None; None means "as fetched today").
"""

from __future__ import annotations

import datetime as dt
import os
import re
import time
from typing import Callable

import httpx
import pandas as pd

USER_AGENT = "framework-monitor/0.1 (personal research tool; +https://github.com/johnny0658/investmentframeworkmonitor_beta)"
OBS_COLUMNS = ["obs_date", "value", "vintage_date"]

# Query params / headers whose values must never appear in logs or errors.
_SECRET_PARAMS = ("api_key", "token", "apikey", "key")
_SECRET_ENV = ("FRED_API_KEY", "TIINGO_API_KEY", "EIA_API_KEY", "CONGRESS_API_KEY", "PRIVATE_STORE_KEY")


class FetchError(Exception):
    """A source could not be fetched. The message is safe to log (secrets redacted)."""


def redact(text: str) -> str:
    for p in _SECRET_PARAMS:
        text = re.sub(rf"({p}=)[^&\s'\"]+", r"\1***", text, flags=re.IGNORECASE)
    for name in _SECRET_ENV:
        val = os.environ.get(name)
        if val and len(val) >= 6:
            text = text.replace(val, "***")
    return text


def make_client(transport: httpx.BaseTransport | None = None, timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        transport=transport,
    )


RETRY_STATUSES = {429, 500, 502, 503, 504}
_sleep = time.sleep  # module hook so tests can skip real back-off waits


def get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    attempts: int = 3,
    backoff: float = 2.0,
    sleep: Callable[[float], None] | None = None,
) -> httpx.Response:
    """GET with up to `attempts` tries, sleeping backoff, 2*backoff, ... between them.

    Retries transport errors and 429/5xx; other 4xx fail immediately (a bad
    series ID will not get better by asking again).
    """
    sleep = sleep or _sleep
    last: str = ""
    for i in range(attempts):
        try:
            resp = client.get(url, params=params, headers=headers)
        except httpx.TransportError as exc:
            last = f"{type(exc).__name__}: {exc}"
        else:
            if resp.status_code < 400:
                return resp
            body = resp.text[:200].replace("\n", " ")
            last = f"HTTP {resp.status_code} for {resp.request.url}: {body}"
            if resp.status_code not in RETRY_STATUSES:
                raise FetchError(redact(last))
        if i < attempts - 1:
            sleep(backoff * (2**i))
    raise FetchError(redact(f"failed after {attempts} attempts: {last}"))


def to_frame(rows: list[tuple], *, has_vintage: bool = False) -> pd.DataFrame:
    """Build a clean observation frame: numeric values only, sorted, de-duplicated."""
    df = pd.DataFrame(rows, columns=OBS_COLUMNS if has_vintage else OBS_COLUMNS[:2])
    if not has_vintage:
        df["vintage_date"] = None
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    df["obs_date"] = pd.to_datetime(df["obs_date"]).dt.date
    if has_vintage:
        df["vintage_date"] = pd.to_datetime(df["vintage_date"]).dt.date
    keys = ["obs_date", "vintage_date"] if has_vintage else ["obs_date"]
    df = df.drop_duplicates(subset=keys, keep="last").sort_values(keys).reset_index(drop=True)
    return df[OBS_COLUMNS]


def clip_dates(df: pd.DataFrame, start: dt.date | None, end: dt.date | None) -> pd.DataFrame:
    if start is not None:
        df = df[df["obs_date"] >= start]
    if end is not None:
        df = df[df["obs_date"] <= end]
    return df.reset_index(drop=True)
