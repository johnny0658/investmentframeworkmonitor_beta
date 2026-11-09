"""Verify FRED/ALFRED series IDs, units and history length.

The PRD requires every series ID, unit and history length to be checked on
first fetch, with wrong or discontinued series reported rather than guessed
around. Metadata comes from the FRED API when ``FRED_API_KEY`` is set,
otherwise from the public series page. History length is measured from
the data itself (fredgraph.csv / API).
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

import httpx

from framework_monitor.fetchers import fred
from framework_monitor.fetchers.base import FetchError, get_with_retry, make_client
from framework_monitor.schemas import Config

# z-scores use 3 years of history (10 for monthly series), so flag anything shorter.
MIN_YEARS = {"daily": 3, "weekly": 3, "monthly": 10, "quarterly": 10}
STALE_SERIES_DAYS = 400  # last observation older than this = probably discontinued


@dataclass
class SeriesCheck:
    indicator_id: str
    series: str
    ok: bool
    source_units: str | None
    config_units: str
    first_obs: str | None
    last_obs: str | None
    observations: int
    issues: list[str]


def _page_metadata(code: str, client: httpx.Client) -> dict:
    html = get_with_retry(client, f"https://fred.stlouisfed.org/series/{code}").text
    m = re.search(r'series-meta-value-units">\s*(.*?)</span>', html, re.S)
    if not m:
        raise FetchError(f"could not read units for {code} from its FRED page")
    return {"units": re.sub(r"\s+", " ", m.group(1)).strip()}


def verify_fred(cfg: Config, *, client: httpx.Client | None = None, today: dt.date | None = None) -> list[SeriesCheck]:
    client = client or make_client()
    today = today or dt.date.today()
    out: list[SeriesCheck] = []
    for ind in cfg.indicators:
        if ind.source not in {"fred", "alfred"} or not ind.enabled:
            continue
        issues: list[str] = []
        units = first = last = None
        n = 0
        try:
            try:
                meta = fred.series_metadata(ind.series, client=client)
            except FetchError:
                meta = _page_metadata(ind.series, client)
            units = meta["units"]
            canon = fred.canonical_units(units)
            if canon is None:
                issues.append(f"unrecognised source units {units!r}")
            elif canon != ind.units:
                issues.append(f"units mismatch: source {units!r} -> {canon}, config says {ind.units}")
            df = fred.fetch(ind, None, None, client=client)
            n = len(df)
            if n == 0:
                issues.append("no observations")
            else:
                first, last = df["obs_date"].min(), df["obs_date"].max()
                years = (last - first).days / 365.25
                need = MIN_YEARS.get(ind.frequency)
                if need and years < need:
                    issues.append(f"only {years:.2f} years of history (scoring window needs {need})")
                if (today - last).days > STALE_SERIES_DAYS:
                    issues.append(f"last observation {last} - possibly discontinued")
                first, last = first.isoformat(), last.isoformat()
        except FetchError as exc:
            issues.append(f"fetch failed: {exc}")
        out.append(SeriesCheck(ind.id, ind.series, not issues, units, ind.units, first, last, n, issues))
    return out


def render(checks: list[SeriesCheck], today: dt.date) -> str:
    bad = [c for c in checks if not c.ok]
    lines = [
        f"# FRED series verification, {today.isoformat()}",
        "",
        f"{len(checks)} series checked, {len(checks) - len(bad)} OK, {len(bad)} with issues.",
        "",
        "| Indicator | Series | Source units | Config units | First | Last | Obs | Issues |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for c in checks:
        lines.append(
            f"| `{c.indicator_id}` | {c.series} | {c.source_units or '-'} | {c.config_units} | {c.first_obs or '-'} | "
            f"{c.last_obs or '-'} | {c.observations} | {'; '.join(c.issues) or 'OK'} |"
        )
    return "\n".join(lines) + "\n"
