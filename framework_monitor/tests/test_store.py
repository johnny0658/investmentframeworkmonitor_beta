"""Bitemporal store (FR-8), snapshots (FR-9) and private store."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from framework_monitor.fetchers.base import to_frame
from framework_monitor.licensing import LicenceViolation
from framework_monitor.store import private_store, snapshots
from framework_monitor.store.db import Store

D = dt.date
T1 = dt.datetime(2026, 11, 2, 22, 30)
T2 = dt.datetime(2026, 11, 3, 22, 30)
T3 = dt.datetime(2026, 11, 4, 22, 30)


def frame(pairs):
    return to_frame(pairs)


def test_new_unchanged_and_revised():
    s = Store()
    r1 = s.write_observations("x", frame([(D(2026, 10, 1), 1.0), (D(2026, 10, 2), 2.0)]), "fred", T1)
    assert (r1.new, r1.revised) == (2, 0)
    r2 = s.write_observations("x", frame([(D(2026, 10, 1), 1.0), (D(2026, 10, 2), 2.0)]), "fred", T2)
    assert (r2.new, r2.revised) == (0, 0)  # identical re-fetch (90-day look-back) adds nothing
    r3 = s.write_observations("x", frame([(D(2026, 10, 2), 2.5), (D(2026, 10, 3), 3.0)]), "fred", T3)
    assert (r3.new, r3.revised) == (1, 1)
    assert len(s.table("observations")) == 4  # never overwritten
    assert s.series("x").tolist() == [1.0, 2.5, 3.0]


def test_as_of_reconstructs_what_was_known():
    s = Store()
    s.write_observations("x", frame([(D(2026, 10, 2), 2.0)]), "fred", T1)
    s.write_observations("x", frame([(D(2026, 10, 2), 2.5)]), "fred", T3)
    assert s.series("x", as_of=T2.date()).tolist() == [2.0]
    assert s.series("x", as_of=T3.date()).tolist() == [2.5]
    assert s.series("x", as_of=D(2026, 1, 1)).empty


def test_source_vintages_are_kept():
    s = Store()
    df = to_frame([(D(2026, 7, 1), 100.0, D(2026, 8, 26)), (D(2026, 7, 1), 101.0, D(2026, 9, 23)),
                   (D(2026, 8, 1), 110.0, D(2026, 9, 23))], has_vintage=True)
    r = s.write_observations("m2", df, "alfred", T1)
    assert (r.new, r.revised) == (2, 1)
    assert s.write_observations("m2", df, "alfred", T2).new == 0
    assert s.series("m2", as_of=D(2026, 9, 1)).tolist() == [100.0]
    assert s.series("m2").tolist() == [101.0, 110.0]
    rev = s.revisions("m2")
    assert len(rev) == 1 and rev.iloc[0]["old_value"] == 100.0 and rev.iloc[0]["new_value"] == 101.0
    assert s.revision_counts() == {"m2": 1}


def test_tiny_float_noise_is_not_a_revision():
    s = Store()
    s.write_observations("x", frame([(D(2026, 10, 1), 0.1 + 0.2)]), "fred", T1)
    assert s.write_observations("x", frame([(D(2026, 10, 1), 0.3)]), "fred", T2).revised == 0


def test_last_obs_date_and_failures():
    s = Store()
    assert s.last_obs_date("x") is None
    s.write_observations("x", frame([(D(2026, 10, 1), 1.0), (D(2026, 10, 9), 1.0)]), "fred", T1)
    assert s.last_obs_date("x") == D(2026, 10, 9)
    for i, status in enumerate(["ok", "error", "error", "error"]):
        s.log_fetch(f"r{i}", "x", "fred", status, at=T1 + dt.timedelta(days=i))
    assert s.consecutive_failures("x") == 3
    s.log_fetch("r9", "x", "fred", "ok", at=T1 + dt.timedelta(days=9))
    assert s.consecutive_failures("x") == 0


# ---------------------------------------------------------------- snapshots
def _store_with(cfg):
    s = Store()
    s.write_observations("ust_10y", frame([(D(2026, 11, 3), 4.1), (D(2026, 11, 4), 4.2)]), "fred", T1)
    s.write_observations("hy_oas", frame([(D(2026, 11, 3), 3.1)]), "fred", T1)
    s.write_observations("retired_id", frame([(D(2026, 11, 3), 9.9)]), "fred", T1)  # not in catalogue
    s.log_fetch("r1", "hy_oas", "fred", "ok", 1, 0, at=T1)
    s.con.execute("INSERT INTO quality_flags VALUES ('hy_oas', '2026-11-03', 'jump', 'd', 3.1, 'r1', ?, TRUE, NULL)", [T1])
    return s


def test_snapshot_splits_by_licence_and_round_trips(cfg, paths):
    s = _store_with(cfg)
    snapshots.export(s, cfg, paths)
    pub = paths.public_parquet / "observations"
    assert sorted(p.stem for p in pub.glob("*.parquet")) == ["ust_10y"]
    priv = sorted(p.stem for p in (paths.private_parquet / "observations").glob("*.parquet"))
    assert priv == ["hy_oas", "retired_id"]  # restricted AND unknown go private
    assert pd.read_parquet(paths.public_parquet / "quality_flags.parquet").empty
    assert len(pd.read_parquet(paths.private_parquet / "quality_flags.parquet")) == 1

    rebuilt, counts = snapshots.rebuild(paths)
    a = s.table("observations").sort_values(["indicator_id", "obs_date"]).reset_index(drop=True)
    b = rebuilt.table("observations").sort_values(["indicator_id", "obs_date"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)
    assert counts["fetch_log"] == 1 and counts["quality_flags"] == 1


def test_unchanged_snapshot_is_not_rewritten(cfg, paths):
    s = _store_with(cfg)
    snapshots.export(s, cfg, paths)
    f = paths.public_parquet / "observations" / "ust_10y.parquet"
    mtime = f.stat().st_mtime_ns
    w = snapshots.export(s, cfg, paths)
    assert f.stat().st_mtime_ns == mtime and w["public"] == 0


def test_reclassified_indicator_is_removed_from_public(cfg, paths):
    stale = paths.public_parquet / "observations" / "hy_oas.parquet"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old")
    snapshots.export(_store_with(cfg), cfg, paths)
    assert not stale.exists()


def test_writer_refuses_restricted_values_in_public_table(cfg):
    df = pd.DataFrame({"indicator_id": ["hy_oas"], "value": [3.1]})
    with pytest.raises(LicenceViolation):
        snapshots._assert_public_safe(df, {i.id for i in cfg.indicators if i.licence == "public"}, "test")


# ---------------------------------------------------------------- private store
def test_private_store_round_trip(tmp_path):
    key = private_store.Fernet.generate_key().decode()
    src = tmp_path / "private"
    (src / "parquet" / "observations").mkdir(parents=True)
    (src / "parquet" / "observations" / "hy_oas.parquet").write_bytes(b"secret-bytes")
    enc = tmp_path / "private-store.enc"
    assert private_store.pack(src, enc, key) == 1
    assert b"secret-bytes" not in enc.read_bytes()
    dst = tmp_path / "restored"
    assert private_store.unpack(enc, dst, key) == 1
    assert (dst / "parquet" / "observations" / "hy_oas.parquet").read_bytes() == b"secret-bytes"


def test_private_store_wrong_key(tmp_path):
    enc = tmp_path / "s.enc"
    private_store.pack(tmp_path / "missing", enc, private_store.Fernet.generate_key().decode())
    with pytest.raises(private_store.PrivateStoreError, match="cannot decrypt"):
        private_store.unpack(enc, tmp_path / "out", private_store.Fernet.generate_key().decode())


def test_private_store_requires_key(tmp_path):
    with pytest.raises(private_store.PrivateStoreError, match="PRIVATE_STORE_KEY"):
        private_store.pack(tmp_path, tmp_path / "x.enc")
