"""Treasury Fiscal Data API fetcher (free, no key).

Generic over endpoints: the indicator's ``params`` give the endpoint, the date
and value fields, optional filters (``field:op:value``) and an optional scale
(e.g. 1e-6 to turn dollars into millions).
"""

from __future__ import annotations

import datetime as dt

import httpx
import pandas as pd

from framework_monitor.fetchers.base import FetchError, get_with_retry, make_client, to_frame
from framework_monitor.schemas import Indicator

BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
PAGE_SIZE = 10_000


def fetch(series: Indicator, start: dt.date | None = None, end: dt.date | None = None, *, client: httpx.Client | None = None) -> pd.DataFrame:
    client = client or make_client()
    p = series.params
    date_field, value_field = str(p["date_field"]), str(p["value_field"])
    filters = [str(f) for f in p.get("filters", [])]
    if start:
        filters.append(f"{date_field}:gte:{start.isoformat()}")
    if end:
        filters.append(f"{date_field}:lte:{end.isoformat()}")
    scale = float(p.get("scale", 1.0))

    rows: list[tuple] = []
    page = 1
    while True:
        params = {
            "fields": f"{date_field},{value_field}",
            "sort": date_field,
            "page[size]": PAGE_SIZE,
            "page[number]": page,
        }
        if filters:
            params["filter"] = ",".join(filters)
        payload = get_with_retry(client, BASE_URL + str(p["endpoint"]), params=params).json()
        if "data" not in payload:
            raise FetchError(f"Treasury Fiscal Data error for {series.id}: {payload.get('message', payload)}"[:300])
        for rec in payload["data"]:
            v = rec.get(value_field)
            rows.append((rec[date_field], None if v in (None, "null", "") else v))
        total_pages = int(payload.get("meta", {}).get("total-pages", 1) or 1)
        if page >= total_pages:
            break
        page += 1

    df = to_frame(rows)
    df["value"] = df["value"] * scale
    return df
