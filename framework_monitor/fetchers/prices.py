"""Daily price fetcher: Tiingo first, then Stooq, then yfinance as last resort.

Providers return adjusted closes (Tiingo ``adjClose``; Stooq ``Close``, which
is split/dividend adjusted; yfinance ``Close`` with ``auto_adjust``). Adjusted
closes are *back-adjusted*: every dividend rescales all earlier history. If
they were stored as-is, a 90-day look-back would mix old and new adjustment
bases and create a fake jump at the window edge. So `chain()` stores a
**total-return index** instead. It equals the adjusted close on the first
fetch, and every later fetch is rescaled to agree with the stored value on the
first overlapping date. Day-to-day returns are invariant to back-adjustment,
so stored history never changes, and switching provider does not break the
series either.

The provider chain can be overridden per indicator with
``params.providers`` (e.g. indices that Tiingo does not carry), and provider
symbols with ``params.tiingo`` / ``params.stooq`` / ``params.yfinance``.

The returned frame records which provider actually answered in
``df.attrs["source"]`` so every stored row stays traceable (FR-22). Mixing
providers inside one series can create spurious jumps; the quality checks
will flag those and hold them out of scoring.

Tiingo free-tier price data may not be redistributed, so every price
indicator is ``licence: restricted``.
"""

from __future__ import annotations

import datetime as dt
import io
import os

import httpx
import pandas as pd

from framework_monitor.fetchers.base import FetchError, clip_dates, get_with_retry, make_client, to_frame
from framework_monitor.schemas import Indicator

TIINGO_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"
STOOQ_URL = "https://stooq.com/q/d/l/"
DEFAULT_PROVIDERS = ("tiingo", "stooq", "yfinance")
DEFAULT_START = dt.date(1990, 1, 1)  # Tiingo returns only the latest bar without a start date


def fetch(series: Indicator, start: dt.date | None = None, end: dt.date | None = None, *, client: httpx.Client | None = None) -> pd.DataFrame:
    client = client or make_client()
    providers = list(series.params.get("providers", DEFAULT_PROVIDERS))
    errors: list[str] = []
    for name in providers:
        fn = _PROVIDERS[name]
        try:
            df = fn(series, start, end, client)
        except FetchError as exc:
            errors.append(f"{name}: {exc}")
            continue
        if df.empty and start is None:
            errors.append(f"{name}: no rows")
            continue
        df.attrs["source"] = f"prices:{name}"
        return df
    raise FetchError(f"all price providers failed for {series.series}: " + " | ".join(errors))


def _tiingo(series: Indicator, start, end, client) -> pd.DataFrame:
    key = os.environ.get("TIINGO_API_KEY")
    if not key:
        raise FetchError("TIINGO_API_KEY not set")
    ticker = str(series.params.get("tiingo", series.series)).lower()
    params = {"startDate": (start or DEFAULT_START).isoformat(), "format": "json", "resampleFreq": "daily"}
    if end:
        params["endDate"] = end.isoformat()
    resp = get_with_retry(client, TIINGO_URL.format(ticker=ticker), params=params, headers={"Authorization": f"Token {key}"})
    data = resp.json()
    if isinstance(data, dict):  # error payloads are objects: {"detail": "..."}
        raise FetchError(f"Tiingo error for {ticker}: {data.get('detail', data)}")
    rows = [(bar["date"][:10], bar.get("adjClose", bar.get("close"))) for bar in data]
    return to_frame(rows)


def _stooq(series: Indicator, start, end, client) -> pd.DataFrame:
    sym = str(series.params.get("stooq", f"{series.series}.us")).lower()
    params = {"s": sym, "i": "d"}
    if start:
        params["d1"] = start.strftime("%Y%m%d")
    if end:
        params["d2"] = end.strftime("%Y%m%d")
    text = get_with_retry(client, STOOQ_URL, params=params).text
    if not text.startswith("Date"):
        raise FetchError(f"Stooq returned no data for {sym}: {text[:80]!r}")
    df = pd.read_csv(io.StringIO(text))
    return clip_dates(to_frame(list(zip(df["Date"], df["Close"]))), start, end)


def _yfinance(series: Indicator, start, end, client) -> pd.DataFrame:
    try:
        import yfinance as yf  # optional, unofficial: last resort only
    except ImportError as exc:
        raise FetchError("yfinance not installed") from exc
    sym = str(series.params.get("yfinance", series.series))
    try:
        hist = yf.Ticker(sym).history(
            start=(start or DEFAULT_START).isoformat(),
            end=(end + dt.timedelta(days=1)).isoformat() if end else None,
            auto_adjust=True,
        )
    except Exception as exc:  # yfinance raises a zoo of exception types
        raise FetchError(f"yfinance failed for {sym}: {exc}") from exc
    if hist.empty:
        raise FetchError(f"yfinance returned no rows for {sym}")
    rows = [(idx.date(), v) for idx, v in hist["Close"].items()]
    return to_frame(rows)


def chain(df: pd.DataFrame, stored: pd.Series) -> pd.DataFrame:
    """Rescale a fetched adjusted-close frame onto the stored total-return index."""
    if stored.empty or df.empty:
        return df
    overlap = [d for d in df["obs_date"] if d in stored.index]
    if not overlap:
        raise FetchError(
            f"no overlap between fetched prices (from {df['obs_date'].min()}) and stored index "
            f"(to {stored.index.max()}); run a backfill for this ticker"
        )
    anchor = overlap[0]
    fetched_anchor = float(df.loc[df["obs_date"] == anchor, "value"].iloc[0])
    out = df.copy()
    out["value"] = out["value"] * (float(stored.loc[anchor]) / fetched_anchor)
    out.attrs = dict(df.attrs)
    return out


_PROVIDERS = {"tiingo": _tiingo, "stooq": _stooq, "yfinance": _yfinance}
