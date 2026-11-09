"""DuckDB store with bitemporal observations (FR-8) and derived tables (FR-10).

``observations(indicator_id, obs_date, value, vintage_date, fetched_at, source)``
is append-only. A revised value is a new row with a later ``vintage_date``;
nothing is ever overwritten, so ``series(id, as_of=d)`` reconstructs what was
known on any past date.

``vintage_date`` is the source's real-time date when it has one (ALFRED,
manual vintages); otherwise the date the value was first fetched.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    indicator_id VARCHAR NOT NULL,
    obs_date     DATE NOT NULL,
    value        DOUBLE NOT NULL,
    vintage_date DATE NOT NULL,
    fetched_at   TIMESTAMP NOT NULL,
    source       VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id      VARCHAR PRIMARY KEY,
    mode        VARCHAR NOT NULL,
    started_at  TIMESTAMP NOT NULL,
    finished_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS fetch_log (
    run_id       VARCHAR NOT NULL,
    indicator_id VARCHAR NOT NULL,
    source       VARCHAR NOT NULL,
    status       VARCHAR NOT NULL,      -- ok | error
    rows_new     INTEGER,
    rows_revised INTEGER,
    start_date   DATE,
    message      VARCHAR,
    logged_at    TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_flags (
    indicator_id VARCHAR NOT NULL,
    obs_date     DATE NOT NULL,
    check_name   VARCHAR NOT NULL,      -- range | jump
    detail       VARCHAR,
    value        DOUBLE,
    run_id       VARCHAR NOT NULL,
    flagged_at   TIMESTAMP NOT NULL,
    held         BOOLEAN NOT NULL,      -- held out of scoring until confirmed
    confirmed_at TIMESTAMP
);

-- Derived tables (FR-10). Created now so the schema is fixed; filled from Phase 2.
CREATE TABLE IF NOT EXISTS signals (
    indicator_id VARCHAR, as_of DATE, raw DOUBLE, transformed DOUBLE, z DOUBLE, signal DOUBLE, run_id VARCHAR);
CREATE TABLE IF NOT EXISTS row_scores (
    row_id VARCHAR, as_of DATE, score DOUBLE, confidence DOUBLE, freshness DOUBLE, agreement DOUBLE,
    override_score DOUBLE, override_confidence DOUBLE, run_id VARCHAR);
CREATE TABLE IF NOT EXISTS scenario_probs (
    as_of DATE, scenario_id VARCHAR, prior DOUBLE, posterior DOUBLE, final DOUBLE, run_id VARCHAR);
CREATE TABLE IF NOT EXISTS signpost_events (
    signpost_id VARCHAR, as_of DATE, active BOOLEAN, event VARCHAR, run_id VARCHAR);
CREATE TABLE IF NOT EXISTS alerts (
    alert_key VARCHAR, kind VARCHAR, opened_at TIMESTAMP, closed_at TIMESTAMP, issue_number INTEGER, detail VARCHAR);
CREATE TABLE IF NOT EXISTS theses (
    thesis_id VARCHAR, path VARCHAR, opened DATE, status VARCHAR, kill_switch_tripped BOOLEAN, as_of DATE);
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id VARCHAR, row_id VARCHAR, statement VARCHAR, probability DOUBLE, made_on DATE,
    resolves_on DATE, outcome BOOLEAN, resolved_on DATE);
"""

TABLES = [
    "observations", "runs", "fetch_log", "quality_flags",
    "signals", "row_scores", "scenario_probs", "signpost_events", "alerts", "theses", "forecasts",
]


@dataclass
class WriteResult:
    new: int = 0
    revised: int = 0
    dates: set = field(default_factory=set)  # obs_dates inserted (new or revised)


def _utcnow() -> dt.datetime:
    """Naive UTC timestamp (DuckDB TIMESTAMP has no zone)."""
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def _rel_close(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


class Store:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(self.path)
        self.con.execute(SCHEMA)

    def close(self) -> None:
        self.con.close()

    # ------------------------------------------------------------ runs & logs
    def start_run(self, mode: str, now: dt.datetime | None = None) -> str:
        run_id = (now or _utcnow()).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.con.execute("INSERT INTO runs VALUES (?, ?, ?, NULL)", [run_id, mode, now or _utcnow()])
        return run_id

    def finish_run(self, run_id: str, now: dt.datetime | None = None) -> None:
        self.con.execute("UPDATE runs SET finished_at = ? WHERE run_id = ?", [now or _utcnow(), run_id])

    def log_fetch(self, run_id, indicator_id, source, status, rows_new=None, rows_revised=None, start_date=None, message=None, at=None):
        self.con.execute(
            "INSERT INTO fetch_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [run_id, indicator_id, source, status, rows_new, rows_revised, start_date, message, at or _utcnow()],
        )

    def consecutive_failures(self, indicator_id: str) -> int:
        """Number of most recent runs in a row where this indicator's fetch failed."""
        statuses = [r[0] for r in self.con.execute(
            "SELECT status FROM fetch_log WHERE indicator_id = ? ORDER BY logged_at DESC", [indicator_id]).fetchall()]
        n = 0
        for s in statuses:
            if s != "error":
                break
            n += 1
        return n

    def last_fetch(self, indicator_id: str) -> dict | None:
        row = self.con.execute(
            "SELECT status, message, logged_at FROM fetch_log WHERE indicator_id = ? ORDER BY logged_at DESC LIMIT 1", [indicator_id]
        ).fetchone()
        return None if row is None else {"status": row[0], "message": row[1], "at": row[2]}

    # ------------------------------------------------------------ observations
    def last_obs_date(self, indicator_id: str) -> dt.date | None:
        return self.con.execute("SELECT max(obs_date) FROM observations WHERE indicator_id = ?", [indicator_id]).fetchone()[0]

    def latest_frame(self, indicator_id: str, as_of: dt.date | None = None) -> pd.DataFrame:
        """Latest known value per obs_date (optionally as known on `as_of`)."""
        q = """
            SELECT obs_date, value, vintage_date, source FROM (
                SELECT *, row_number() OVER (PARTITION BY obs_date ORDER BY vintage_date DESC, fetched_at DESC) AS rn
                FROM observations
                WHERE indicator_id = ? {as_of}
            ) WHERE rn = 1 ORDER BY obs_date
        """.format(as_of="AND vintage_date <= ?" if as_of else "")
        params = [indicator_id, as_of] if as_of else [indicator_id]
        df = self.con.execute(q, params).df()
        if not df.empty:
            df["obs_date"] = pd.to_datetime(df["obs_date"]).dt.date
            df["vintage_date"] = pd.to_datetime(df["vintage_date"]).dt.date
        return df

    def series(self, indicator_id: str, as_of: dt.date | None = None) -> pd.Series:
        df = self.latest_frame(indicator_id, as_of)
        return pd.Series(df["value"].to_numpy(), index=pd.Index(df["obs_date"], name="obs_date"), name=indicator_id, dtype=float)

    def write_observations(self, indicator_id: str, df: pd.DataFrame, source: str, fetched_at: dt.datetime | None = None) -> WriteResult:
        """Append new and revised observations; unchanged ones are skipped."""
        fetched_at = fetched_at or _utcnow()
        if df.empty:
            return WriteResult()
        incoming = df[["obs_date", "value", "vintage_date"]].copy()
        has_vintage = incoming["vintage_date"].notna().all()
        incoming["vintage_date"] = incoming["vintage_date"].where(incoming["vintage_date"].notna(), fetched_at.date())

        existing = self.con.execute(
            "SELECT obs_date, value, vintage_date FROM observations WHERE indicator_id = ?", [indicator_id]
        ).df()
        known_dates: set = set()
        if not existing.empty:
            existing["obs_date"] = pd.to_datetime(existing["obs_date"]).dt.date
            existing["vintage_date"] = pd.to_datetime(existing["vintage_date"]).dt.date
            known_dates = set(existing["obs_date"])

        if has_vintage:
            # Source supplies vintages: insert any (obs_date, vintage) pair not stored yet.
            seen = set(zip(existing["obs_date"], existing["vintage_date"])) if not existing.empty else set()
            mask = [(d, v) not in seen for d, v in zip(incoming["obs_date"], incoming["vintage_date"])]
            to_add = incoming[mask]
        else:
            # Snapshot source: insert when the value differs from the latest stored one.
            latest = {}
            if not existing.empty:
                ex = existing.sort_values(["obs_date", "vintage_date"])
                latest = dict(zip(ex["obs_date"], ex["value"]))  # last wins = latest vintage
            mask = [d not in latest or not _rel_close(latest[d], v) for d, v in zip(incoming["obs_date"], incoming["value"])]
            to_add = incoming[mask]

        if to_add.empty:
            return WriteResult()
        # A revision is a new row for an obs_date we already had, or a later
        # vintage within this batch.
        firsts = ~to_add["obs_date"].duplicated(keep="first")
        is_new = to_add["obs_date"].map(lambda d: d not in known_dates) & firsts
        result = WriteResult(new=int(is_new.sum()), revised=int((~is_new).sum()), dates=set(to_add["obs_date"]))

        rows = to_add.assign(indicator_id=indicator_id, fetched_at=fetched_at, source=source)[
            ["indicator_id", "obs_date", "value", "vintage_date", "fetched_at", "source"]
        ]
        self.con.register("_incoming", rows)
        self.con.execute("INSERT INTO observations SELECT * FROM _incoming")
        self.con.unregister("_incoming")
        return result

    def revisions(self, indicator_id: str | None = None) -> pd.DataFrame:
        """Every revised value with its old and new vintage (data quality check 4)."""
        where = "WHERE indicator_id = ?" if indicator_id else ""
        q = f"""
            SELECT * FROM (
                SELECT indicator_id, obs_date,
                       lag(value) OVER w AS old_value, value AS new_value,
                       lag(vintage_date) OVER w AS old_vintage, vintage_date AS new_vintage
                FROM observations {where}
                WINDOW w AS (PARTITION BY indicator_id, obs_date ORDER BY vintage_date, fetched_at)
            ) WHERE old_vintage IS NOT NULL
            ORDER BY indicator_id, obs_date, new_vintage
        """
        return self.con.execute(q, [indicator_id] if indicator_id else []).df()

    def revision_counts(self) -> dict[str, int]:
        q = """SELECT indicator_id, count(*) - count(DISTINCT obs_date) FROM observations GROUP BY indicator_id"""
        return {k: int(v) for k, v in self.con.execute(q).fetchall()}

    def observation_counts(self) -> dict[str, int]:
        return {k: int(v) for k, v in self.con.execute(
            "SELECT indicator_id, count(DISTINCT obs_date) FROM observations GROUP BY indicator_id").fetchall()}

    def first_obs_dates(self) -> dict[str, dt.date]:
        return dict(self.con.execute("SELECT indicator_id, min(obs_date) FROM observations GROUP BY indicator_id").fetchall())

    # ------------------------------------------------------------ table I/O for snapshots
    def table(self, name: str) -> pd.DataFrame:
        if name not in TABLES:
            raise ValueError(name)
        return self.con.execute(f"SELECT * FROM {name}").df()

    def load_table(self, name: str, df: pd.DataFrame) -> None:
        if name not in TABLES:
            raise ValueError(name)
        if df.empty:
            return
        cols = [c[0] for c in self.con.execute(f"DESCRIBE {name}").fetchall()]
        self.con.register("_load", df[cols])
        self.con.execute(f"INSERT INTO {name} SELECT * FROM _load")
        self.con.unregister("_load")
