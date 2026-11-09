"""End-to-end on fixtures: fetch -> store -> check -> snapshot -> guard."""

from __future__ import annotations

import datetime as dt

import pandas as pd

from framework_monitor import licensing, quality
from framework_monitor.pipeline import LOOKBACK_DAYS, run_fetch, select_indicators
from framework_monitor.store import snapshots
from framework_monitor.store.db import Store

ONLY = ["ust_10y", "fed_assets", "hy_oas", "public_debt", "auction_btc_30y", "spy", "sofr"]


def test_select_indicators(cfg):
    main = select_indicators(cfg, "main")
    assert all(i.enabled and i.source != "derived" for i in main)
    catchup = select_indicators(cfg, "catchup")
    assert {i.id for i in catchup} == {"hy_oas", "ccc_oas", "bbb_oas", "ig_oas"}


def test_end_to_end_on_fixtures(cfg, paths, client, router, monkeypatch):
    monkeypatch.setenv("TIINGO_API_KEY", "test-tiingo-key")
    store = Store(paths.db_path)
    s = run_fetch(store, cfg, "main", backfill=True, only=ONLY, client=client, paths=paths)

    # sofr has no fixture -> fails, and does not stop the others (FR-4)
    assert set(s.failed) == {"sofr"}
    assert set(s.ok) == set(ONLY) - {"sofr"}
    assert store.series("ust_10y").index.max() == dt.date(2026, 11, 5)
    assert store.latest_frame("spy")["source"].iloc[0] == "prices:tiingo"

    # second run is incremental: start = last stored date - 90 days (FR-3)
    router.requests.clear()
    s2 = run_fetch(store, cfg, "main", only=["ust_10y"], client=client, paths=paths)
    assert s2.rows_new == 0 and s2.rows_revised == 0
    cosd = router.requests[0].url.params["cosd"]
    assert cosd == (dt.date(2026, 11, 5) - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()

    # health + snapshot + guard
    report = quality.health_report(store, cfg, dt.date(2026, 11, 9))
    quality.write_health(report, paths, dt.date(2026, 11, 9))
    snapshots.export(store, cfg, paths)
    assert licensing.scan_paths(paths.public_paths, cfg) == []
    public = {p.stem for p in (paths.public_parquet / "observations").glob("*.parquet")}
    assert public == {"ust_10y", "fed_assets", "public_debt", "auction_btc_30y"}
    assert "hy_oas" not in public and "spy" not in public

    # rebuild from parquet reproduces the store exactly
    obs = store.table("observations")
    store.close()
    rebuilt, _ = snapshots.rebuild(paths)
    key = ["indicator_id", "obs_date", "vintage_date"]
    pd.testing.assert_frame_equal(
        obs.sort_values(key).reset_index(drop=True),
        rebuilt.table("observations").sort_values(key).reset_index(drop=True),
        check_dtype=False,
    )


def test_source_failing_three_runs_raises_alert(cfg, paths, client, router, monkeypatch):
    import framework_monitor.fetchers.base as base

    monkeypatch.setattr(base, "_sleep", lambda s: None)
    store = Store()
    router.fail["fred.stlouisfed.org"] = 500
    for _ in range(3):
        run_fetch(store, cfg, "main", only=["ust_10y"], client=client, paths=paths)
    h = {x.indicator_id: x for x in quality.health_report(store, cfg, dt.date(2026, 11, 9))}
    assert h["ust_10y"].consecutive_failures == 3 and h["ust_10y"].source_alert


def test_restricted_never_reaches_public_after_run(cfg, paths, client):
    store = Store()
    run_fetch(store, cfg, "catchup", backfill=True, only=["hy_oas"], client=client, paths=paths)
    snapshots.export(store, cfg, paths)
    assert not (paths.public_parquet / "observations" / "hy_oas.parquet").exists()
    assert (paths.private_parquet / "observations" / "hy_oas.parquet").exists()
    assert licensing.scan_paths(paths.public_paths, cfg) == []
