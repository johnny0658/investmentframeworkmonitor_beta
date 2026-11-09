"""Engine end to end on a synthetic store: compute -> persist -> snapshot -> rebuild -> recompute."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from framework_monitor import licensing
from framework_monitor.engine.compute import compute, persist, recompute, seed_history
from framework_monitor.fetchers.base import to_frame
from framework_monitor.outputs.summary import render
from framework_monitor.store import snapshots
from framework_monitor.store.db import Store

FETCHED = dt.datetime(2026, 11, 9, 22, 30)
END = dt.date(2026, 11, 6)


def _daily(n_days: int, f):
    days = pd.bdate_range(end=END, periods=n_days)
    return [(d.date(), f(i)) for i, d in enumerate(days)]


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "data" / "monitor.duckdb")
    rng = np.random.default_rng(7)
    n = 900
    # hy_oas rises through 4.0 for the last three days (restricted: ICE)
    hy = [3.2 + 0.1 * np.sin(i / 30) for i in range(n - 3)] + [4.05, 4.10, 4.20]
    s.write_observations("hy_oas", to_frame(_daily(n, lambda i: hy[i])), "fred", FETCHED)
    s.write_observations("real_10y", to_frame(_daily(n, lambda i: 1.8 + 0.0005 * i)), "fred", FETCHED)
    s.write_observations("ust_10y", to_frame(_daily(n, lambda i: 4.0 + 0.2 * np.sin(i / 50))), "fred", FETCHED)
    walk = np.cumsum(rng.normal(0, 0.01, n))
    s.write_observations("spy", to_frame(_daily(n, lambda i: 500 * np.exp(walk[i]))), "prices:tiingo", FETCHED)
    s.write_observations("tlt", to_frame(_daily(n, lambda i: 90 * np.exp(-0.5 * walk[i]))), "prices:tiingo", FETCHED)
    yield s
    s.close()


def test_compute_scores_and_signposts(store, cfg):
    r = compute(store, cfg, END, mode="latest")
    hy = next(x for x in r.signposts if x.signpost_id == "hy_stress")
    assert hy.active and hy.licence == "restricted" and math_close(hy.distance, 4.0 - 4.20)
    crisis = next(x for x in r.signposts if x.signpost_id == "hy_crisis")
    assert crisis.status == "inactive" and math_close(crisis.distance, 5.0 - 4.20)  # still 0.8 to go
    assert next(x for x in r.signposts if x.signpost_id == "capex_cut").status == "unavailable"
    # stocks and bonds anti-correlated by construction -> bonds still hedge
    assert r.signals["spy_tlt_corr_60d"].raw < -0.9
    # only hy_stress is active: posterior follows its LRs
    lr = cfg.signposts[0].lr
    prior = {s.id: s.prior for s in cfg.scenarios.scenarios}
    z = sum(prior[k] * lr[k] for k in prior)
    for k in prior:
        assert math_close(r.scenarios.final[k], 0.8 * prior[k] * lr[k] / z + 0.2 * prior[k])
    credit = next(x for x in r.rows if x.row_id == "ai_bottlenecks_credit")
    assert credit.n_signals == 1 and credit.computed_score < 0  # wide spreads are bad


def math_close(a, b):
    return abs(a - b) < 1e-9


def test_known_mode_respects_vintages(store, cfg):
    # every value has vintage 2026-11-09, so nothing was "known" on 2026-11-06
    assert compute(store, cfg, END, mode="known").signals["hy_oas"].raw is None
    assert compute(store, cfg, END, mode="known", knowledge_date=FETCHED.date()).signals["hy_oas"].raw == 4.20


def test_confirm_days(store, cfg):
    # hy_stress needs 2 consecutive days above 4.0: the first day above is not enough
    first_above = pd.bdate_range(end=END, periods=3)[0].date()
    r = compute(store, cfg, first_above, mode="latest")
    assert not next(x for x in r.signposts if x.signpost_id == "hy_stress").active


def test_persist_events_snapshot_redaction_and_exact_rebuild(store, cfg, paths):
    days = [d.date() for d in pd.bdate_range(end=END, periods=4)]
    events = []
    for d in days:
        events += persist(store, cfg, compute(store, cfg, d, mode="known", knowledge_date=FETCHED.date()), run_id=f"r{d}")
    assert [(e["signpost_id"], e["event"]) for e in events if e["signpost_id"] == "hy_stress"] == [("hy_stress", "triggered")]
    assert events[[e["signpost_id"] for e in events].index("hy_stress")]["as_of"] == days[-2]  # 2nd day above 4.0

    snapshots.export(store, cfg, paths)
    assert licensing.scan_paths(paths.public_paths, cfg) == []
    pub = pd.read_parquet(paths.public_parquet / "signals.parquet")
    hy = pub[pub["indicator_id"] == "hy_oas"]
    assert hy["raw"].isna().all() and hy["transformed"].isna().all() and hy["signal"].notna().all()
    assert pub.loc[pub["indicator_id"] == "ust_10y", "raw"].notna().all()  # public raw stays
    st = pd.read_parquet(paths.public_parquet / "signpost_states.parquet")
    assert st.loc[st["signpost_id"] == "hy_stress", "lhs_value"].isna().all()
    assert st.loc[st["signpost_id"] == "long_end_break", "lhs_value"].notna().all()

    tables = ["signals", "row_scores", "regime", "signpost_states", "scenario_probs"]
    before = {t: store.con.execute(f"SELECT * EXCLUDE (run_id) FROM {t} ORDER BY ALL").df() for t in tables}
    store.close()
    rebuilt, _ = snapshots.rebuild(paths)
    try:
        # restricted raw values come back from the private side
        assert rebuilt.con.execute("SELECT raw FROM signals WHERE indicator_id='hy_oas' AND as_of=?", [days[-1]]).fetchone()[0] == 4.20
        for d in days:
            persist(rebuilt, cfg, recompute(rebuilt, cfg, d), run_id="again")
        for t in tables:
            after = rebuilt.con.execute(f"SELECT * EXCLUDE (run_id) FROM {t} ORDER BY ALL").df()
            pd.testing.assert_frame_equal(before[t], after, check_dtype=False)
    finally:
        rebuilt.close()


def test_recompute_is_idempotent(store, cfg):
    for _ in range(2):
        persist(store, cfg, compute(store, cfg, END, mode="latest"), run_id="x")
    assert store.con.execute("SELECT count(*) FROM scenario_probs").fetchone()[0] == 5
    assert store.con.execute("SELECT count(*) FROM engine_runs").fetchone()[0] == 1


def test_seed_history_and_summary(store, cfg):
    n = seed_history(store, cfg, dt.date(2026, 11, 9), 10)
    assert n == 10
    assert seed_history(store, cfg, dt.date(2026, 11, 9), 10) == 0  # already there
    r = compute(store, cfg, dt.date(2026, 11, 9), mode="latest")
    persist(store, cfg, r, "today")
    md = render(store, cfg, r)
    assert "## Scenario probabilities" in md and "High-yield stress" in md
    hy_line = next(line for line in md.splitlines() if line.startswith("| High-yield stress"))
    assert "restricted" in hy_line and "4.2" not in hy_line  # raw ICE value never printed
