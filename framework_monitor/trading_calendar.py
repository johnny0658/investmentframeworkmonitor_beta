"""NYSE trading-day logic for the schedule (runs are skipped on NYSE holidays).

* main run, 22:30 UTC: runs if *today in New York* was a trading session.
* catch-up run, 13:00 UTC: picks up series published the next morning, so it
  runs if the *previous New York weekday* was a trading session.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

NY = ZoneInfo("America/New_York")


@lru_cache(maxsize=8)
def _sessions(year: int) -> frozenset[dt.date]:
    cal = mcal.get_calendar("NYSE")
    sched = cal.schedule(start_date=f"{year - 1}-12-01", end_date=f"{year + 1}-01-31")
    return frozenset(d.date() for d in sched.index)


def is_trading_day(d: dt.date) -> bool:
    return d in _sessions(d.year)


def previous_weekday(d: dt.date) -> dt.date:
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def session_for_run(mode: str, now_utc: dt.datetime) -> dt.date:
    """The US session a run is responsible for."""
    ny_date = now_utc.astimezone(NY).date()
    if mode == "catchup":
        return previous_weekday(ny_date)
    return ny_date


def should_run(mode: str, now_utc: dt.datetime) -> tuple[bool, str]:
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=dt.UTC)
    session = session_for_run(mode, now_utc)
    if is_trading_day(session):
        return True, f"{mode}: {session.isoformat()} was an NYSE session"
    return False, f"{mode}: {session.isoformat()} was not an NYSE session (weekend or holiday); skipping"
