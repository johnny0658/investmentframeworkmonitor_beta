"""Run the engine for one as_of date and persist the results (FR-10, FR-11).

Two data modes:

* ``known`` (default for daily runs): only values whose vintage was known on
  the *knowledge date* (default: as_of), i.e. what the monitor could have seen.
  The 13:00 UTC catch-up run scores the previous session with data that
  arrived this morning, so its knowledge date is the run date. Each result
  records its knowledge date in ``engine_runs``, so recomputing gives exactly
  the same numbers (acceptance: "reproduce exactly from a fresh rebuild").
* ``latest``: today's best values, truncated at as_of. Used to seed history
  and for back-tests, because most series have only one vintage (the day they
  were first fetched). It carries look-ahead from later revisions, so seeded
  rows are tagged with a ``seed-latest`` run_id.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from framework_monitor import trading_calendar
from framework_monitor.engine import regime as regime_mod
from framework_monitor.engine import scenarios as scen_mod
from framework_monitor.engine.formulas import EvalError, Evaluator, UnitError, Val, _is_money, align, empty_series, lhs_threshold
from framework_monitor.engine.rows import RowScore, can_produce, score_rows
from framework_monitor.engine.signals import Signal, compute_signal
from framework_monitor.schemas import Config, Indicator, Signpost
from framework_monitor.store.db import Store

log = logging.getLogger(__name__)

# Bump whenever scoring logic changes, so seeded history computed by older logic
# is recomputed (live rows are kept as they were: that is what the monitor said).
# 3 = signpost hysteresis (clear_days / clear_condition).
ENGINE_VERSION = "3"


@dataclass
class SignpostState:
    signpost_id: str
    family: str
    status: str  # active | inactive | unavailable
    active: bool
    stale: bool
    lhs_value: float | None
    threshold: float | None
    distance: float | None
    licence: str
    note: str = ""


@dataclass
class EngineResult:
    as_of: dt.date
    mode: str
    knowledge_date: dt.date | None
    signals: dict[str, Signal]
    rows: list[RowScore]
    regime: regime_mod.Regime
    signposts: list[SignpostState]
    scenarios: scen_mod.ScenarioUpdate
    notes: list[str] = field(default_factory=list)


class SeriesBook:
    """Raw series as of a date, plus lazily evaluated derived series."""

    def __init__(self, cfg: Config, raw: dict[str, pd.Series], as_of: dt.date):
        self.cfg, self.raw, self.as_of = cfg, raw, as_of
        self.by = cfg.by_id
        self._derived: dict[str, Val] = {}
        self.notes: list[str] = []
        self.ev = Evaluator(self.resolve)

    def resolve(self, ind_id: str) -> Val:
        ind = self.by[ind_id]
        if ind.source != "derived":
            return Val(self.raw.get(ind_id, empty_series()), ind.units)
        if ind_id not in self._derived:
            self._derived[ind_id] = self._eval_derived(ind)
        return self._derived[ind_id]

    def _eval_derived(self, ind: Indicator) -> Val:
        empty = Val(empty_series(), ind.units)
        if not can_produce(ind, self.cfg):
            return empty
        try:
            v = self.ev.eval(ind.formula)
        except (UnitError, EvalError) as exc:
            self.notes.append(f"{ind.id}: {exc}")
            return empty
        if (_is_money(v.unit) or _is_money(ind.units)) and v.unit != ind.units:
            self.notes.append(f"{ind.id}: formula yields {v.unit}, config declares {ind.units}")
            return empty
        return Val(self._anchor(ind, v.data), ind.units)

    def _anchor(self, ind: Indicator, s: pd.Series) -> pd.Series:
        """Put a derived series on the calendar of its inputs with the same frequency.

        Alignment forward-fills onto the union of input dates, so weekly WALCL
        combined with daily RRP would otherwise come out daily, and windows like
        pct_change(net_fed_liquidity, 13) would count days instead of weeks.
        """
        same = [self.resolve(i).data.index for i in ind.formula_inputs if self.by[i].frequency == ind.frequency]
        if not same or s.empty:
            return s
        anchor = same[0]
        for idx in same[1:]:
            anchor = anchor.union(idx)
        anchor = anchor[(anchor >= s.index[0]) & (anchor <= s.index[-1])]
        return s.reindex(s.index.union(anchor)).ffill().reindex(anchor).dropna()

    def leaves(self, ind_id: str) -> set[str]:
        ind = self.by[ind_id]
        if ind.source != "derived":
            return {ind_id}
        out: set[str] = set()
        for i in ind.formula_inputs:
            out |= self.leaves(i)
        return out

    def is_fresh(self, ind_id: str) -> bool:
        ts = pd.Timestamp(self.as_of)
        for leaf in self.leaves(ind_id):
            s = self.raw.get(leaf)
            if s is None or s.empty or (ts - s.index[-1]).days > self.by[leaf].stale_after_days:
                return False
        return True


def _held(store: Store) -> dict[str, set]:
    rows = store.con.execute("SELECT indicator_id, obs_date FROM quality_flags WHERE held").fetchall()
    out: dict[str, set] = {}
    for i, d in rows:
        out.setdefault(i, set()).add(pd.Timestamp(d))
    return out


def hysteresis(cond: pd.Series, clear: pd.Series | None, confirm_days: int, clear_days: int) -> pd.Series:
    """Active/inactive state over time.

    Inactive -> active when `cond` has held for `confirm_days` consecutive
    observations. Active -> inactive when `clear` (default: not `cond`) has held
    for `clear_days` consecutive observations. The state is derived from the data
    alone (walked from the first observation), so recomputing any date gives the
    same answer without stored state.
    """
    c = cond.astype(bool)
    if clear is None:
        k = ~c
    else:
        c, k = align(c.astype(float), clear.astype(float))
        c, k = c.astype(bool), k.astype(bool)
    out = np.zeros(len(c), dtype=bool)
    active, run_on, run_off = False, 0, 0
    for i, (on, off) in enumerate(zip(c.to_numpy(), k.to_numpy())):
        if not active:
            run_on = run_on + 1 if on else 0
            if run_on >= confirm_days:
                active, run_off = True, 0
        else:
            run_off = run_off + 1 if off else 0
            if run_off >= clear_days:
                active, run_on = False, 0
        out[i] = active
    return pd.Series(out, index=c.index)


def evaluate_signpost(sp: Signpost, book: SeriesBook) -> SignpostState:
    cfg = book.cfg
    simple = lhs_threshold(sp.condition)
    lhs_src, op, threshold = simple if simple else (None, None, None)
    restricted = lhs_src is not None and lhs_src in cfg.by_id and cfg.by_id[lhs_src].licence == "restricted"
    licence = "restricted" if restricted else "public"
    base = SignpostState(sp.id, sp.family, "unavailable", False, False, None, threshold, None, licence)
    if not all(can_produce(cfg.by_id[i], cfg) for i in sp.indicators):
        base.note = "input not available yet (disabled source)"
        return base
    try:
        cond = book.ev.eval(sp.condition).data
    except (UnitError, EvalError) as exc:
        base.note = str(exc)
        return base
    cond = cond[cond.index <= pd.Timestamp(book.as_of)]
    if cond.empty:
        base.note = "no data"
        return base
    clear = None
    if sp.clear_condition:
        try:
            clear = book.ev.eval(sp.clear_condition).data
        except (UnitError, EvalError) as exc:
            base.note = f"clear_condition: {exc}"
            return base
        clear = clear[clear.index <= pd.Timestamp(book.as_of)]
    base.active = bool(hysteresis(cond, clear, sp.confirm_days, sp.clear_days).iloc[-1])
    base.status = "active" if base.active else "inactive"
    base.stale = not all(book.is_fresh(i) for i in sp.indicators)
    if lhs_src is not None:
        lhs = book.ev.eval(lhs_src).data
        lhs = lhs[lhs.index <= pd.Timestamp(book.as_of)]
        if not lhs.empty:
            base.lhs_value = float(lhs.iloc[-1])
            # how far the value must still move to trigger; negative = already past the threshold
            base.distance = threshold - base.lhs_value if op in (">", ">=") else base.lhs_value - threshold
    return base


def compute(store: Store, cfg: Config, as_of: dt.date, mode: str = "known", knowledge_date: dt.date | None = None) -> EngineResult:
    if mode not in ("known", "latest"):
        raise ValueError(mode)
    kd = (knowledge_date or as_of) if mode == "known" else None
    raw = store.all_series(as_of=as_of, vintage_as_of=kd)
    held = _held(store)
    for i, dates in held.items():
        if i in raw:
            raw[i] = raw[i][~raw[i].index.isin(list(dates))]
    book = SeriesBook(cfg, raw, as_of)

    signals: dict[str, Signal] = {}
    for ind in cfg.indicators:
        if not can_produce(ind, cfg):
            continue
        series = book.resolve(ind.id).data
        fresh = book.is_fresh(ind.id) if ind.source == "derived" else None
        signals[ind.id] = compute_signal(ind, series, as_of, stale_override=fresh)

    rows = score_rows(cfg, signals, as_of)
    reg = regime_mod.classify({k: book.resolve(k).data for k in ("wei", "gdpnow", "core_pce") if k in cfg.by_id}, as_of)
    states = [evaluate_signpost(sp, book) for sp in cfg.signposts]
    active = [sp for sp, st in zip(cfg.signposts, states) if st.active]
    prior = {s.id: s.prior for s in cfg.scenarios.scenarios}
    upd = scen_mod.update(prior, active, cfg.scenarios.shrinkage_to_prior)
    return EngineResult(as_of, mode, kd, signals, rows, reg, states, upd, book.notes)


def recompute(store: Store, cfg: Config, as_of: dt.date) -> EngineResult:
    """Recompute a stored date with the same mode and knowledge date it was computed with."""
    row = store.con.execute("SELECT mode, knowledge_date FROM engine_runs WHERE as_of = ?", [as_of]).fetchone()
    if row is None:
        raise ValueError(f"no stored engine run for {as_of}")
    return compute(store, cfg, as_of, mode=row[0], knowledge_date=row[1])


# ---------------------------------------------------------------- persistence
def persist(store: Store, cfg: Config, r: EngineResult, run_id: str) -> list[dict]:
    """Write one as_of's rows to the engine tables. Returns signpost events (triggered/cleared)."""
    by = cfg.by_id
    d = r.as_of
    store.replace_rows("engine_runs", d, pd.DataFrame([{"as_of": d, "knowledge_date": r.knowledge_date, "mode": r.mode,
                                                         "run_id": run_id, "engine_version": ENGINE_VERSION}]))
    store.replace_rows("signals", d, pd.DataFrame([{
        "as_of": d, "indicator_id": s.indicator_id, "row_id": by[s.indicator_id].row, "obs_date": s.obs_date,
        "raw": s.raw, "transformed": s.transformed, "percentile": s.percentile, "z": s.z, "signal": s.signal,
        "weight": by[s.indicator_id].weight, "fresh": s.fresh, "licence": by[s.indicator_id].licence, "run_id": run_id,
    } for s in r.signals.values()]))
    store.replace_rows("row_scores", d, pd.DataFrame([{
        "as_of": d, "row_id": x.row_id, "layer": x.layer, "computed_score": x.computed_score, "confidence": x.confidence,
        "freshness": x.freshness, "agreement": x.agreement, "n_signals": x.n_signals,
        "override_score": x.override_score, "override_confidence": x.override_confidence,
        "override_reason": x.override_reason, "override_active": x.override_active,
        "override_expired": x.override_expired, "final_score": x.final_score,
        "final_confidence": x.final_confidence, "run_id": run_id,
    } for x in r.rows]))
    g = r.regime
    store.replace_rows("regime", d, pd.DataFrame([{
        "as_of": d, "box": g.box, "growth_up": g.growth_up, "inflation_up": g.inflation_up,
        "growth_detail": g.growth_detail, "core_pce_3m_ann": g.core_pce_3m_ann, "core_pce_12m": g.core_pce_12m,
        "run_id": run_id,
    }]))

    prev = dict(store.con.execute("""
        SELECT signpost_id, active FROM (
            SELECT signpost_id, active, row_number() OVER (PARTITION BY signpost_id ORDER BY as_of DESC) rn
            FROM signpost_states WHERE as_of < ?) WHERE rn = 1""", [d]).fetchall())
    store.replace_rows("signpost_states", d, pd.DataFrame([{
        "as_of": d, "signpost_id": s.signpost_id, "family": s.family, "status": s.status, "active": s.active,
        "stale": s.stale, "lhs_value": s.lhs_value, "threshold": s.threshold, "distance": s.distance,
        "licence": s.licence, "run_id": run_id,
    } for s in r.signposts]))
    events = []
    for s in r.signposts:
        was = bool(prev.get(s.signpost_id, False))
        if s.active and not was:
            events.append({"as_of": d, "signpost_id": s.signpost_id, "event": "triggered", "run_id": run_id})
        elif was and not s.active:
            events.append({"as_of": d, "signpost_id": s.signpost_id, "event": "cleared", "run_id": run_id})
    store.replace_rows("signpost_events", d, pd.DataFrame(events, columns=["as_of", "signpost_id", "event", "run_id"]))

    u = r.scenarios
    store.replace_rows("scenario_probs", d, pd.DataFrame([{
        "as_of": d, "scenario_id": k, "prior": u.prior[k], "multiplier": u.multiplier[k],
        "posterior": u.posterior[k], "final": u.final[k], "run_id": run_id,
    } for k in u.prior]))
    return events


def sessions_between(start: dt.date, end: dt.date) -> list[dt.date]:
    days, d = [], start
    while d <= end:
        if trading_calendar.is_trading_day(d):
            days.append(d)
        d += dt.timedelta(days=1)
    return days


def seed_history(store: Store, cfg: Config, before: dt.date, n_sessions: int) -> int:
    """Fill the engine tables for the n NYSE sessions before `before` (latest-vintage mode),
    skipping dates already computed."""
    # keep live results and seeds made by the current engine; redo seeds from older logic
    have = {r[0] for r in store.con.execute(
        "SELECT as_of FROM engine_runs WHERE run_id NOT LIKE 'seed%' OR engine_version = ?", [ENGINE_VERSION]).fetchall()}
    start = before - dt.timedelta(days=int(n_sessions * 1.5) + 10)
    dates = [d for d in sessions_between(start, before - dt.timedelta(days=1))[-n_sessions:] if d not in have]
    for d in dates:
        persist(store, cfg, compute(store, cfg, d, mode="latest"), run_id="seed-latest")
    return len(dates)
