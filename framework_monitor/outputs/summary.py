"""Plain-Markdown engine summary (``data/summary.md``), until the Phase 3 site exists.

Public file: shows scores, signals, probabilities and thresholds, and shows
current values and distances only for signposts on public inputs.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from framework_monitor.engine.compute import EngineResult
from framework_monitor.engine.rows import fmt
from framework_monitor.schemas import Config
from framework_monitor.store.db import Store

ARROW_STEP = 0.25


def _prob_at(store: Store, on_or_before: dt.date) -> dict[str, float]:
    row = store.con.execute("SELECT max(as_of) FROM scenario_probs WHERE as_of <= ?", [on_or_before]).fetchone()[0]
    if row is None:
        return {}
    return dict(store.con.execute("SELECT scenario_id, final FROM scenario_probs WHERE as_of = ?", [row]).fetchall())


def _rows_at(store: Store, on_or_before: dt.date) -> dict[str, float]:
    row = store.con.execute("SELECT max(as_of) FROM row_scores WHERE as_of <= ?", [on_or_before]).fetchone()[0]
    if row is None:
        return {}
    return {k: v for k, v in store.con.execute("SELECT row_id, final_score FROM row_scores WHERE as_of = ?", [row]).fetchall()}


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def _arrow(now: float | None, before: float | None) -> str:
    if now is None or before is None or pd.isna(now) or pd.isna(before):
        return ""
    d = now - before
    return "↑" if d >= ARROW_STEP else ("↓" if d <= -ARROW_STEP else "→")


def render(store: Store, cfg: Config, r: EngineResult) -> str:
    d = r.as_of
    w1, w4 = _prob_at(store, d - dt.timedelta(days=7)), _prob_at(store, d - dt.timedelta(days=28))
    rows_w1 = _rows_at(store, d - dt.timedelta(days=7))
    names = {s.id: s.name for s in cfg.scenarios.scenarios}
    sp_by = {s.id: s for s in cfg.signposts}
    out = [
        f"# Framework monitor, as of {d.isoformat()}",
        "",
        "> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; "
        "indicator weights and directions are first-pass defaults.",
        "",
        "## Scenario probabilities",
        "",
        "| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    u = r.scenarios
    for k in u.prior:
        out.append(f"| {k}: {names[k]} | **{_pct(u.final[k])}** | {_pct(w1.get(k))} | {_pct(w4.get(k))} | "
                   f"{_pct(u.prior[k])} | {u.multiplier[k]:.2f} |")
    g = r.regime
    out += ["", "## Regime", ""]
    if g.box:
        out.append(f"Classifier: **{g.box}** (growth {'up' if g.growth_up else 'down'}: {g.growth_detail}; "
                   f"core PCE 3m annualised {g.core_pce_3m_ann:.2f}% vs 12m {g.core_pce_12m:.2f}% → "
                   f"inflation {'up' if g.inflation_up else 'down'})")
    else:
        out.append("Classifier: not enough data")
    if cfg.scenarios.regime_probs:
        out.append("")
        out.append("My regime probabilities (6 months): " + ", ".join(f"{k} {_pct(v)}" for k, v in cfg.scenarios.regime_probs.items()))

    out += ["", "## Active signposts", ""]
    active = [s for s in r.signposts if s.active]
    if not active:
        out.append("None.")
    for s in active:
        sp = sp_by[s.signpost_id]
        stale = " (stale data)" if s.stale else ""
        out.append(f"- **{sp.name}** ({sp.family}): `{sp.condition}`{stale}")

    out += ["", "## Rows", "", "| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |",
            "| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |"]
    for x in r.rows:
        if x.n_signals == 0 and not x.override_active:
            continue
        ov = f"{x.override_score:+.1f} ({x.override_reason})" if x.override_active else ("expired, dropped" if x.override_expired else "")
        out.append(f"| {x.layer} | {x.row_id} | **{fmt(x.final_score)}** | {_arrow(x.final_score, rows_w1.get(x.row_id))} | "
                   f"{x.final_confidence:.2f} | {x.freshness:.2f} | {fmt(x.agreement)} | {x.n_signals} | {ov} |")
    empty = [x.row_id for x in r.rows if x.n_signals == 0 and not x.override_active]
    if empty:
        out += ["", f"Rows with no data yet (sources in later phases): {', '.join(empty)}"]

    out += ["", "## Signposts", "", "Distance = how far the value must still move to trigger (negative = past the threshold). "
            "Values of restricted series are not published.", "", "| Signpost | Family | Status | Current | Threshold | Distance |",
            "| --- | --- | --- | ---: | ---: | ---: |"]
    for s in r.signposts:
        show = s.licence == "public" and s.lhs_value is not None
        cur = f"{s.lhs_value:.3f}" if show else ("restricted" if s.lhs_value is not None else "-")
        dist = f"{s.distance:+.3f}" if show and s.distance is not None else ("restricted" if s.distance is not None else "-")
        thr = "-" if s.threshold is None else f"{s.threshold:g}"
        out.append(f"| {sp_by[s.signpost_id].name} | {s.family} | {s.status}{' (stale)' if s.stale else ''} | {cur} | {thr} | {dist} |")
    if r.notes:
        out += ["", "## Engine notes", ""] + [f"- {n}" for n in r.notes]
    return "\n".join(out) + "\n"
