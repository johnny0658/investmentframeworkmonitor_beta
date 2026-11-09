"""Data quality checks, run every time (PRD "Data quality checks").

1. Staleness: latest observation older than ``stale_after_days``.
2. Range and jumps: a new value outside the historical min-max by more than
   20% of that range, or a one-period move above 6 standard deviations of
   historical moves. Flagged values are *held* out of scoring until a later
   run sees the same value again (confirmation), or are dropped when revised.
3. Units: ``verify-series`` asserts config units against source metadata;
   derived formulas assert units before arithmetic (engine, Phase 2).
4. Revisions: counted per indicator from the bitemporal table.
5. Source health: consecutive failed fetches per indicator (alert at 3, FR-23).

Thresholds are module constants here so they are visible and testable.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass

import pandas as pd

from framework_monitor.schemas import Config, Indicator
from framework_monitor.store.db import Store, _utcnow

RANGE_TOLERANCE = 0.20  # fraction of the historical min-max span
JUMP_SIGMAS = 6.0
MIN_HISTORY = 30  # observations needed before range/jump checks apply
SOURCE_FAILURE_ALERT = 3


@dataclass
class IndicatorHealth:
    indicator_id: str
    name: str
    source: str
    licence: str
    row: str
    layer: int
    enabled: bool
    first_obs_date: str | None
    last_obs_date: str | None
    observations: int
    days_since_last_obs: int | None
    stale_after_days: int
    stale: bool
    revisions: int
    held_values: int
    last_fetch_status: str | None
    last_fetch_at: str | None
    last_fetch_message: str | None
    consecutive_failures: int
    source_alert: bool


def check_new_values(store: Store, ind: Indicator, new_dates: set[dt.date], run_id: str, now: dt.datetime | None = None) -> list[dict]:
    """Range and jump checks on observations added this run. Returns the flags written."""
    if not new_dates:
        return []
    s = store.series(ind.id)
    hist = s[~s.index.isin(list(new_dates))]
    if len(hist) < MIN_HISTORY:
        return []
    lo, hi = hist.min(), hist.max()
    span = hi - lo
    diffs = hist.diff().dropna()
    sigma = diffs.std()
    flags = []
    full = s.sort_index()
    for d in sorted(new_dates):
        if d not in full.index:
            continue
        v = float(full.loc[d])
        if span > 0 and (v > hi + RANGE_TOLERANCE * span or v < lo - RANGE_TOLERANCE * span):
            flags.append(dict(check_name="range", obs_date=d, value=v,
                              detail=f"outside historical range by more than {RANGE_TOLERANCE:.0%} of span"))
        prev = full[full.index < d]
        if len(prev) and sigma and sigma > 0:
            move = v - float(prev.iloc[-1])
            if abs(move) > JUMP_SIGMAS * sigma:
                flags.append(dict(check_name="jump", obs_date=d, value=v,
                                  detail=f"one-period move of {abs(move) / sigma:.1f} sigma (> {JUMP_SIGMAS:g})"))
    at = now or _utcnow()
    for f in flags:
        store.con.execute(
            "INSERT INTO quality_flags VALUES (?, ?, ?, ?, ?, ?, ?, TRUE, NULL)",
            [ind.id, f["obs_date"], f["check_name"], f["detail"], f["value"], run_id, at],
        )
    return flags


def confirm_held_values(store: Store, run_id: str, now: dt.datetime | None = None) -> dict[str, int]:
    """Release held values that a later run still sees unchanged; drop flags whose value was revised."""
    at = now or _utcnow()
    held = store.con.execute(
        "SELECT rowid, indicator_id, obs_date, value FROM quality_flags WHERE held AND run_id <> ?", [run_id]
    ).fetchall()
    confirmed = superseded = 0
    for rowid, ind_id, obs_date, value in held:
        s = store.series(ind_id)
        current = s.get(obs_date)
        if current is not None and abs(float(current) - float(value)) <= 1e-9 * max(1.0, abs(value)):
            store.con.execute("UPDATE quality_flags SET held = FALSE, confirmed_at = ? WHERE rowid = ?", [at, rowid])
            confirmed += 1
        else:
            store.con.execute("UPDATE quality_flags SET held = FALSE, detail = detail || ' [superseded by revision]' WHERE rowid = ?", [rowid])
            superseded += 1
    return {"confirmed": confirmed, "superseded": superseded}


def held_dates(store: Store, indicator_id: str) -> set[dt.date]:
    """Observation dates the engine must exclude from scoring."""
    return {r[0] for r in store.con.execute(
        "SELECT obs_date FROM quality_flags WHERE held AND indicator_id = ?", [indicator_id]).fetchall()}


def health_report(store: Store, cfg: Config, today: dt.date) -> list[IndicatorHealth]:
    revs = store.revision_counts()
    counts = store.observation_counts()
    firsts = store.first_obs_dates()
    held = dict(store.con.execute("SELECT indicator_id, count(*) FROM quality_flags WHERE held GROUP BY indicator_id").fetchall())
    out = []
    for ind in cfg.indicators:
        if ind.source == "derived":
            continue
        last = store.last_obs_date(ind.id)
        age = (today - last).days if last else None
        lf = store.last_fetch(ind.id)
        fails = store.consecutive_failures(ind.id)
        out.append(IndicatorHealth(
            indicator_id=ind.id, name=ind.name, source=ind.source, licence=ind.licence, row=ind.row, layer=ind.layer,
            enabled=ind.enabled,
            first_obs_date=firsts[ind.id].isoformat() if ind.id in firsts else None,
            last_obs_date=last.isoformat() if last else None,
            observations=counts.get(ind.id, 0),
            days_since_last_obs=age,
            stale_after_days=ind.stale_after_days,
            stale=ind.enabled and (age is None or age > ind.stale_after_days),
            revisions=revs.get(ind.id, 0),
            held_values=int(held.get(ind.id, 0)),
            last_fetch_status=lf["status"] if lf else None,
            last_fetch_at=lf["at"].isoformat(timespec="seconds") if lf else None,
            last_fetch_message=lf["message"] if lf else None,
            consecutive_failures=fails,
            source_alert=fails >= SOURCE_FAILURE_ALERT,
        ))
    return out


def write_health(report: list[IndicatorHealth], paths, today: dt.date) -> None:
    """Public health files. They contain dates, counts and statuses only, never values."""
    paths.health_dir.mkdir(parents=True, exist_ok=True)
    enabled = [h for h in report if h.enabled]
    summary = {
        "as_of": today.isoformat(),
        "indicators_enabled": len(enabled),
        "indicators_with_data": sum(1 for h in enabled if h.observations > 0),
        "stale": sorted(h.indicator_id for h in enabled if h.stale),
        "failing": sorted(h.indicator_id for h in enabled if h.last_fetch_status == "error"),
        "source_alerts": sorted(h.indicator_id for h in enabled if h.source_alert),
        "held_values": sum(h.held_values for h in enabled),
        "by_layer": {str(l): sum(1 for h in enabled if h.layer == l and h.observations > 0) for l in range(1, 6)},
    }
    (paths.health_dir / "health.json").write_text(
        json.dumps({"summary": summary, "indicators": [asdict(h) for h in report]}, indent=2, default=str) + "\n"
    )
    (paths.health_dir / "health.md").write_text(render_markdown(report, summary))


def render_markdown(report: list[IndicatorHealth], summary: dict) -> str:
    lines = [
        f"# Data health, {summary['as_of']}",
        "",
        f"- Indicators enabled: **{summary['indicators_enabled']}**, with data: **{summary['indicators_with_data']}**",
        f"- With data by layer: " + ", ".join(f"L{k}: {v}" for k, v in summary["by_layer"].items()),
        f"- Stale: {len(summary['stale'])} {', '.join(summary['stale'])}",
        f"- Failing this run: {len(summary['failing'])} {', '.join(summary['failing'])}",
        f"- Source alerts (failed {SOURCE_FAILURE_ALERT}+ runs in a row): {', '.join(summary['source_alerts']) or 'none'}",
        f"- Values held out of scoring pending confirmation: {summary['held_values']}",
        "",
        "| Indicator | Source | Licence | First | Last | Obs | Age (d) | Stale | Revisions | Held | Fetch |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for h in report:
        if not h.enabled:
            continue
        fetch = h.last_fetch_status or "-"
        if h.consecutive_failures:
            fetch += f" ({h.consecutive_failures}x)"
        lines.append(
            f"| `{h.indicator_id}` | {h.source} | {h.licence} | {h.first_obs_date or '-'} | {h.last_obs_date or '-'} | "
            f"{h.observations} | {h.days_since_last_obs if h.days_since_last_obs is not None else '-'} | "
            f"{'yes' if h.stale else ''} | {h.revisions} | {h.held_values or ''} | {fetch} |"
        )
    failing = [h for h in report if h.enabled and h.last_fetch_status == "error"]
    if failing:
        lines += ["", "## Fetch errors", ""]
        lines += [f"- `{h.indicator_id}`: {h.last_fetch_message}" for h in failing]
    return "\n".join(lines) + "\n"
