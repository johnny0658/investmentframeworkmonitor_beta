"""Quality checks and the NYSE schedule."""

from __future__ import annotations

import datetime as dt
import json

from framework_monitor import quality, trading_calendar
from framework_monitor.fetchers.base import to_frame
from framework_monitor.store.db import Store

from .conftest import make_indicator

D = dt.date
T = dt.datetime(2026, 11, 2, 22, 30)


def _history(n=100):
    start = D(2026, 1, 1)
    return [(start + dt.timedelta(days=i), 4.0 + 0.01 * (i % 7)) for i in range(n)]


def _store():
    s = Store()
    s.write_observations("x", to_frame(_history()), "fred", T)
    return s


def test_normal_value_not_flagged():
    s = _store()
    ind = make_indicator(id="x")
    r = s.write_observations("x", to_frame([(D(2026, 4, 11), 4.03)]), "fred", T)
    assert quality.check_new_values(s, ind, r.dates, "run2") == []


def test_jump_and_range_flagged_and_held():
    s = _store()
    ind = make_indicator(id="x")
    r = s.write_observations("x", to_frame([(D(2026, 4, 11), 9.0)]), "fred", T)
    flags = quality.check_new_values(s, ind, r.dates, "run2")
    assert {f["check_name"] for f in flags} == {"jump", "range"}
    assert quality.held_dates(s, "x") == {D(2026, 4, 11)}


def test_held_value_confirmed_by_next_run():
    s = _store()
    ind = make_indicator(id="x")
    r = s.write_observations("x", to_frame([(D(2026, 4, 11), 9.0)]), "fred", T)
    quality.check_new_values(s, ind, r.dates, "run2")
    assert quality.confirm_held_values(s, "run2") == {"confirmed": 0, "superseded": 0}  # same run: still held
    assert quality.confirm_held_values(s, "run3") == {"confirmed": 2, "superseded": 0}  # range + jump flags
    assert quality.held_dates(s, "x") == set()


def test_held_value_superseded_by_revision():
    s = _store()
    ind = make_indicator(id="x")
    r = s.write_observations("x", to_frame([(D(2026, 4, 11), 9.0)]), "fred", T)
    quality.check_new_values(s, ind, r.dates, "run2")
    s.write_observations("x", to_frame([(D(2026, 4, 11), 4.02)]), "fred", T + dt.timedelta(days=1))
    assert quality.confirm_held_values(s, "run3") == {"confirmed": 0, "superseded": 2}


def test_short_history_skips_checks():
    s = Store()
    s.write_observations("x", to_frame(_history(10)), "fred", T)
    r = s.write_observations("x", to_frame([(D(2026, 2, 1), 100.0)]), "fred", T)
    assert quality.check_new_values(s, make_indicator(id="x"), r.dates, "r") == []


def test_health_report_staleness_and_files(cfg, paths):
    s = Store()
    s.write_observations("ust_10y", to_frame([(D(2026, 11, 5), 4.1)]), "fred", T)
    s.write_observations("brent", to_frame([(D(2026, 10, 1), 80.0)]), "fred", T)
    for i in range(3):
        s.log_fetch(f"r{i}", "sofr", "fred", "error", message="boom", at=T + dt.timedelta(hours=i))
    report = {h.indicator_id: h for h in quality.health_report(s, cfg, D(2026, 11, 9))}
    assert not report["ust_10y"].stale
    assert report["brent"].stale and report["brent"].days_since_last_obs == 39
    assert report["sofr"].stale and report["sofr"].source_alert
    assert "net_fed_liquidity" not in report  # derived: computed, not fetched

    quality.write_health(list(report.values()), paths, D(2026, 11, 9))
    data = json.loads((paths.health_dir / "health.json").read_text())
    assert "sofr" in data["summary"]["source_alerts"]
    assert all("value" not in row for row in data["indicators"])  # public file: no values
    assert "| `ust_10y` |" in (paths.health_dir / "health.md").read_text()


# ---------------------------------------------------------------- schedule
def utc(*a):
    return dt.datetime(*a, tzinfo=dt.UTC)


def test_main_run_on_trading_day():
    assert trading_calendar.should_run("main", utc(2026, 11, 9, 22, 30))[0]  # Monday


def test_main_run_skips_thanksgiving():
    ok, why = trading_calendar.should_run("main", utc(2026, 11, 26, 22, 30))
    assert not ok and "2026-11-26" in why


def test_catchup_covers_previous_session():
    assert trading_calendar.should_run("catchup", utc(2026, 11, 14, 13, 0))[0]  # Sat -> Fri 13th
    assert not trading_calendar.should_run("catchup", utc(2026, 11, 27, 13, 0))[0]  # Fri -> Thanksgiving
    assert trading_calendar.session_for_run("catchup", utc(2026, 11, 10, 13, 0)) == D(2026, 11, 9)


def test_main_run_uses_new_york_date():
    # 22:30 UTC is 17:30 New York (EST): same calendar day
    assert trading_calendar.session_for_run("main", utc(2026, 12, 4, 22, 30)) == D(2026, 12, 4)
