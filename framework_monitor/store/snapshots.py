"""Parquet snapshots (FR-9): DuckDB is rebuilt from these on every run.

Layout::

    data/parquet/public/observations/<indicator_id>.parquet   committed
    data/parquet/public/{runs,fetch_log,quality_flags}.parquet committed
    data/private/parquet/observations/<indicator_id>.parquet  restricted, never committed
    data/private/parquet/quality_flags.parquet                restricted indicators' flags

Restricted indicators (and any indicator no longer in the catalogue) go to
the private side. Writing a restricted indicator to the public side raises
`LicenceViolation`, which is a second line of defence behind the licensing guard.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from framework_monitor.licensing import LicenceViolation, _table_violations
from framework_monitor.schemas import Config
from framework_monitor.settings import Paths
from framework_monitor.store.db import Store

PUBLIC_TABLES = ["runs", "fetch_log", "alerts", "engine_runs", "row_scores", "regime", "scenario_probs", "signpost_events"]
SPLIT_TABLES = ["quality_flags"]  # carry raw values -> split by indicator licence
# Engine tables with a `licence` column: restricted rows are published with these
# columns nulled (z-scores and signals stay public); full rows go to the private side.
REDACT_TABLES = {"signals": ["raw", "transformed"], "signpost_states": ["lhs_value", "distance"]}


def _public_ids(cfg: Config) -> set[str]:
    return {i.id for i in cfg.indicators if i.licence == "public"}


def _same(path: Path, df: pd.DataFrame) -> bool:
    if not path.exists():
        return False
    try:
        old = pd.read_parquet(path)
    except Exception:
        return False
    if list(old.columns) != list(df.columns) or len(old) != len(df):
        return False
    a = old.reset_index(drop=True).astype(str)
    b = df.reset_index(drop=True).astype(str)
    return a.equals(b)


def _write(path: Path, df: pd.DataFrame) -> bool:
    """Write only when content changed, so unchanged history makes no git diff."""
    if _same(path, df):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="zstd")
    return True


def _assert_public_safe(df: pd.DataFrame, public_ids: set[str], where: str) -> None:
    """Same rule as the licensing guard: no raw-value column for a non-public indicator.
    (Status-only tables such as fetch_log may name restricted indicators.)"""
    violations = _table_violations(df, public_ids, where)
    if violations:
        raise LicenceViolation(f"refusing to write to public {where}: {violations[0].detail}")


def export(store: Store, cfg: Config, paths: Paths) -> dict[str, int]:
    public_ids = _public_ids(cfg)
    written = {"public": 0, "private": 0, "removed": 0}

    obs = store.table("observations").sort_values(["indicator_id", "obs_date", "vintage_date", "fetched_at"])
    pub_dir = paths.public_parquet / "observations"
    priv_dir = paths.private_parquet / "observations"
    for ind_id, df in obs.groupby("indicator_id", sort=True):
        df = df.reset_index(drop=True)
        if ind_id in public_ids:
            _assert_public_safe(df, public_ids, "observations")
            written["public"] += _write(pub_dir / f"{ind_id}.parquet", df)
        else:
            written["private"] += _write(priv_dir / f"{ind_id}.parquet", df)

    # An indicator reclassified as restricted must disappear from the public side.
    if pub_dir.exists():
        for f in pub_dir.glob("*.parquet"):
            if f.stem not in public_ids:
                f.unlink()
                written["removed"] += 1

    for name in PUBLIC_TABLES:
        df = store.table(name)
        _assert_public_safe(df, public_ids, name)
        written["public"] += _write(paths.public_parquet / f"{name}.parquet", df)

    for name, cols in REDACT_TABLES.items():
        df = store.table(name)
        restricted = df["licence"].ne("public")
        pub = df.copy()
        pub.loc[restricted, cols] = None
        _assert_public_safe(pub, public_ids, name)
        written["public"] += _write(paths.public_parquet / f"{name}.parquet", pub)
        written["private"] += _write(paths.private_parquet / f"{name}.parquet", df[restricted].reset_index(drop=True))

    for name in SPLIT_TABLES:
        df = store.table(name)
        is_pub = df["indicator_id"].isin(public_ids) if not df.empty else pd.Series(dtype=bool)
        pub, priv = df[is_pub].reset_index(drop=True), df[~is_pub].reset_index(drop=True)
        _assert_public_safe(pub, public_ids, name)
        written["public"] += _write(paths.public_parquet / f"{name}.parquet", pub)
        written["private"] += _write(paths.private_parquet / f"{name}.parquet", priv)
    return written


def load(store: Store, paths: Paths) -> dict[str, int]:
    """Load every snapshot (public + private) into an empty store."""
    counts: dict[str, int] = {}
    frames = []
    for base in (paths.public_parquet, paths.private_parquet):
        d = base / "observations"
        if d.exists():
            frames.extend(pd.read_parquet(f) for f in sorted(d.glob("*.parquet")))
    if frames:
        obs = pd.concat(frames, ignore_index=True)
        store.load_table("observations", obs)
        counts["observations"] = len(obs)
    for name in REDACT_TABLES:
        pub_f, priv_f = paths.public_parquet / f"{name}.parquet", paths.private_parquet / f"{name}.parquet"
        if not pub_f.exists():
            continue
        pub = pd.read_parquet(pub_f)
        if priv_f.exists():  # full restricted rows replace their redacted public copies
            pub = pd.concat([pub[pub["licence"].eq("public")], pd.read_parquet(priv_f)], ignore_index=True)
        if not pub.empty:
            store.load_table(name, pub)
            counts[name] = len(pub)
    for name in PUBLIC_TABLES + SPLIT_TABLES:
        parts = [pd.read_parquet(p) for p in (paths.public_parquet / f"{name}.parquet", paths.private_parquet / f"{name}.parquet") if p.exists()]
        parts = [p for p in parts if not p.empty]
        if parts:
            df = pd.concat(parts, ignore_index=True)
            store.load_table(name, df)
            counts[name] = len(df)
    return counts


def rebuild(paths: Paths) -> tuple[Store, dict[str, int]]:
    """Recreate the DuckDB file from Parquet (DuckDB itself is gitignored)."""
    for suffix in ("", ".wal"):
        p = Path(str(paths.db_path) + suffix)
        if p.exists():
            p.unlink()
    store = Store(paths.db_path)
    return store, load(store, paths)
