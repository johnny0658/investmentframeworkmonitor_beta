"""Fetch orchestration: incremental fetch (FR-3), isolation of failures (FR-4),
backfill (FR-7) and quality checks after every write."""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

import httpx

from framework_monitor import quality
from framework_monitor.fetchers import get_fetcher, prices
from framework_monitor.fetchers.base import make_client, redact
from framework_monitor.schemas import Config, Indicator
from framework_monitor.settings import Paths
from framework_monitor.store.db import Store

log = logging.getLogger(__name__)

LOOKBACK_DAYS = 90  # re-fetch window to catch revisions (FR-3)


@dataclass
class RunSummary:
    run_id: str
    mode: str
    ok: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    rows_new: int = 0
    rows_revised: int = 0
    flags: int = 0
    degraded: dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        lines = [
            f"run {self.run_id} ({self.mode}): {len(self.ok)} ok, {len(self.failed)} failed, "
            f"{self.rows_new} new rows, {self.rows_revised} revised, {self.flags} quality flags"
        ]
        lines += [f"  FAILED {k}: {v}" for k, v in sorted(self.failed.items())]
        lines += [f"  degraded {k}: {v}" for k, v in sorted(self.degraded.items())]
        return "\n".join(lines)


def select_indicators(cfg: Config, mode: str, only: list[str] | None = None) -> list[Indicator]:
    """Enabled indicators that have a fetcher, filtered by run mode / explicit IDs."""
    if only:
        unknown = set(only) - set(cfg.by_id)
        if unknown:
            raise ValueError(f"unknown indicator ids: {sorted(unknown)}")
    inds = [i for i in cfg.indicators if i.enabled and get_fetcher(i.source) is not None]
    if only:
        inds = [i for i in inds if i.id in set(only)]
    elif mode == "catchup":
        inds = [i for i in inds if i.catchup]
    return inds


def fetch_start(store: Store, ind: Indicator, backfill: bool) -> dt.date | None:
    if backfill:
        return None
    last = store.last_obs_date(ind.id)
    return last - dt.timedelta(days=LOOKBACK_DAYS) if last else None


def run_fetch(
    store: Store,
    cfg: Config,
    mode: str,
    *,
    backfill: bool = False,
    only: list[str] | None = None,
    client: httpx.Client | None = None,
    paths: Paths | None = None,
) -> RunSummary:
    paths = paths or Paths()
    client = client or make_client()
    run_id = store.start_run("backfill" if backfill else mode)
    summary = RunSummary(run_id=run_id, mode="backfill" if backfill else mode)

    for ind in select_indicators(cfg, mode, only):
        fetcher = get_fetcher(ind.source)
        start = fetch_start(store, ind, backfill)
        try:
            kwargs = {"client": client}
            if ind.source == "manual":
                kwargs["paths"] = paths
            df = fetcher.fetch(ind, start, None, **kwargs)
            if ind.source == "prices":  # store a back-adjustment-proof total-return index
                df = prices.chain(df, store.series(ind.id))
            source = df.attrs.get("source", ind.source)
            res = store.write_observations(ind.id, df, source)
            flags = quality.check_new_values(store, ind, res.dates, run_id)
            msg = df.attrs.get("degraded")
            if msg:
                summary.degraded[ind.id] = msg
            store.log_fetch(run_id, ind.id, source, "ok", res.new, res.revised, start, msg)
            summary.ok.append(ind.id)
            summary.rows_new += res.new
            summary.rows_revised += res.revised
            summary.flags += len(flags)
        except Exception as exc:  # FR-4: one failed source never stops the others
            msg = redact(f"{type(exc).__name__}: {exc}")[:500]
            log.warning("fetch failed for %s: %s", ind.id, msg)
            store.log_fetch(run_id, ind.id, ind.source, "error", None, None, start, msg)
            summary.failed[ind.id] = msg

    quality.confirm_held_values(store, run_id)
    store.finish_run(run_id)
    return summary
