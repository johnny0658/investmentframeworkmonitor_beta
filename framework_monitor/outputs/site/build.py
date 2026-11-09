"""Static dashboard for GitHub Pages (FR-16 to FR-19, FR-22), plus CSV and Excel exports (FR-9, FR-26).

Pages:
  index.html          home: scenarios (now / 1w / 4w), regime, five layer cards, active signposts, health strip
  rows/<row>.html     each indicator: 5-year chart, z-score, signal, weight, freshness, source, as-of; override
  signposts.html      condition, current value, distance to trigger, trigger history
  health.html         data health per indicator
  data/*.csv          exports; framework-tracker.xlsx  Excel tracker

Licensing: every page's numbers come from "records" that are also embedded on
the page as ``<script type="application/json">``, which the licensing guard
scans. Restricted indicators publish no raw value. Their charts show the
z-score and signal, and for prices an indexed series (rebased to 100), which
the Tiingo terms allow.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from framework_monitor.engine.compute import EngineResult, SeriesBook
from framework_monitor.engine.rows import can_produce
from framework_monitor.engine.signals import signal_history
from framework_monitor.outputs import excel
from framework_monitor.outputs.alerts import LIVE_RUN_FILTER
from framework_monitor.schemas import Config, Indicator
from framework_monitor.settings import Paths
from framework_monitor.store.db import Store

TEMPLATES = Path(__file__).parent / "templates"
CHART_YEARS = 5
LAYER_NAMES_FALLBACK = {1: "Regime", 2: "Structural themes", 3: "Pricing", 4: "Catalysts and signposts", 5: "Expression and risk"}


# ---------------------------------------------------------------- helpers
def _clean(x):
    """JSON-safe scalar: NaN/inf -> None, numpy -> python, dates -> ISO."""
    if x is None:
        return None
    if isinstance(x, (np.floating, float)):
        return None if (math.isnan(x) or math.isinf(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, (dt.date, pd.Timestamp)):
        return x.isoformat()[:10]
    return x


def _clean_rec(d: dict) -> dict:
    return {k: (_clean_rec(v) if isinstance(v, dict) else [_clean(i) for i in v] if isinstance(v, list) else _clean(v)) for k, v in d.items()}


def source_link(ind: Indicator, provider: str | None) -> tuple[str, str | None]:
    if ind.source in ("fred", "alfred"):
        return f"FRED {ind.series}" + (" (ALFRED vintages)" if ind.source == "alfred" else ""), f"https://fred.stlouisfed.org/series/{ind.series}"
    if ind.source == "treasury_fiscal":
        return "Treasury Fiscal Data", "https://fiscaldata.treasury.gov/api-documentation/"
    if ind.source == "prices":
        name = (provider or "prices").split(":")[-1].capitalize()
        return f"{name} {ind.series}", None
    if ind.source == "derived":
        return f"derived: {ind.formula}", None
    if ind.source == "manual":
        return "manual entry", None
    return ind.source, None


def _weekly(s: pd.Series) -> pd.Series:
    return s.resample("W-FRI").last().dropna() if len(s) > 400 else s


# ---------------------------------------------------------------- data assembly
class SiteData:
    def __init__(self, store: Store, cfg: Config, r: EngineResult):
        self.store, self.cfg, self.r = store, cfg, r
        self.by = cfg.by_id
        self.raw = store.all_series(as_of=r.as_of)
        self.book = SeriesBook(cfg, self.raw, r.as_of)
        self.providers = dict(store.con.execute(
            "SELECT indicator_id, arg_max(source, fetched_at) FROM observations GROUP BY indicator_id").fetchall())
        self.start = pd.Timestamp(r.as_of) - pd.DateOffset(years=CHART_YEARS)

    # history ---------------------------------------------------------------
    def prob_history(self) -> pd.DataFrame:
        return self.store.con.execute(
            "SELECT as_of, scenario_id, final, run_id LIKE 'seed%' AS seeded FROM scenario_probs "
            "WHERE as_of <= ? AND run_id NOT LIKE 'replay%' ORDER BY as_of",  # back-test replays are not history
            [self.r.as_of]).df()

    def _at(self, table: str, col: str, key: str, days: int) -> dict:
        d = self.store.con.execute(f"SELECT max(as_of) FROM {table} WHERE as_of <= ? AND run_id NOT LIKE 'replay%'",
                                   [self.r.as_of - dt.timedelta(days=days)]).fetchone()[0]
        if d is None:
            return {}
        return dict(self.store.con.execute(f"SELECT {key}, {col} FROM {table} WHERE as_of = ?", [d]).fetchall())

    # records ---------------------------------------------------------------
    def indicator_record(self, ind: Indicator) -> dict:
        s = self.r.signals.get(ind.id)
        label, url = source_link(ind, self.providers.get(ind.id))
        restricted = ind.licence == "restricted"
        return _clean_rec({
            "indicator_id": ind.id, "name": ind.name, "licence": ind.licence, "source_label": label, "source_url": url,
            "obs_date": s.obs_date if s else None,
            "raw": None if (restricted or not s) else s.raw,
            "transformed": None if (restricted or not s) else s.transformed,
            "z": s.z if s else None, "percentile": s.percentile if s else None, "signal": s.signal if s else None,
            "weight": ind.weight, "direction": ind.direction, "transform": ind.transform, "frequency": ind.frequency,
            "units": ind.units, "fresh": s.fresh if s else False, "enabled": ind.enabled and can_produce(ind, self.cfg),
            "proxy": ind.proxy, "notes": ind.notes,
        })

    def chart_payload(self, ind: Indicator) -> dict | None:
        series = self.book.resolve(ind.id).data
        if series.empty or not can_produce(ind, self.cfg):
            return None
        hist = signal_history(ind, series, self.start)
        lvl = series[series.index >= self.start]
        payload = {"indicator_id": ind.id, "licence": ind.licence, "units": ind.units}
        frame = pd.DataFrame({"z": hist["z"], "signal": hist["signal"], "percentile": hist["percentile"]})
        if ind.licence == "public":
            frame = frame.join(lvl.rename("raw"), how="outer")
        elif ind.source == "prices" and not lvl.empty:
            frame = frame.join((100 * lvl / lvl.iloc[0]).rename("indexed"), how="outer")
        frame = frame[frame.index >= self.start]
        if len(frame) > 400:
            frame = frame.resample("W-FRI").last()
        frame = frame.dropna(how="all")
        if "indexed" in frame and frame["indexed"].notna().any():  # rebase after downsampling: first point = 100
            frame["indexed"] = 100 * frame["indexed"] / frame["indexed"].dropna().iloc[0]
        payload["dates"] = [d.date().isoformat() for d in frame.index]
        for col in frame.columns:
            payload[col] = [_clean(v) for v in frame[col].to_numpy()]
        return payload

    def row_records(self) -> list[dict]:
        w1 = self._at("row_scores", "final_score", "row_id", 7)
        rows = []
        for x in self.r.rows:
            row = next(rw for rw in self.cfg.rows.rows if rw.id == x.row_id)
            before = w1.get(x.row_id)
            arrow = ""
            if x.final_score is not None and before is not None and not pd.isna(before):
                d = x.final_score - before
                arrow = "up" if d >= 0.25 else ("down" if d <= -0.25 else "flat")
            rows.append(_clean_rec({
                "row_id": x.row_id, "name": row.name, "layer": x.layer, "question": row.question,
                "final_score": x.final_score, "computed_score": x.computed_score, "final_confidence": x.final_confidence,
                "confidence": x.confidence, "freshness": x.freshness, "agreement": x.agreement, "n_signals": x.n_signals,
                "override_active": x.override_active, "override_score": x.override_score,
                "override_confidence": x.override_confidence, "override_reason": x.override_reason,
                "override_expired": x.override_expired, "score_1w": before, "arrow": arrow,
                "gap": (x.override_score - x.computed_score) if (x.override_active and x.computed_score is not None) else None,
            }))
        return rows

    def scenario_records(self) -> list[dict]:
        w1 = self._at("scenario_probs", "final", "scenario_id", 7)
        w4 = self._at("scenario_probs", "final", "scenario_id", 28)
        u = self.r.scenarios
        return [_clean_rec({
            "scenario_id": s.id, "name": s.name, "description": s.description, "now": u.final[s.id], "posterior": u.posterior[s.id],
            "w1": w1.get(s.id), "w4": w4.get(s.id), "prior": u.prior[s.id], "multiplier": u.multiplier[s.id],
        }) for s in self.cfg.scenarios.scenarios]

    def signpost_records(self) -> list[dict]:
        ev = self.store.con.execute(
            "SELECT signpost_id, event, max(as_of) FROM signpost_events WHERE as_of <= ? GROUP BY 1, 2", [self.r.as_of]).fetchall()
        last = {(a, b): c for a, b, c in ev}
        sp_by = {s.id: s for s in self.cfg.signposts}
        out = []
        for st in self.r.signposts:
            sp = sp_by[st.signpost_id]
            pub = st.licence == "public"
            inputs = sorted(sp.indicators)
            out.append(_clean_rec({
                "signpost_id": sp.id, "name": sp.name, "family": sp.family, "condition": sp.condition,
                "clear_rule": f"{sp.clear_condition or 'not (' + sp.condition + ')'} for {sp.clear_days} day(s)",
                "confirm_days": sp.confirm_days, "status": st.status, "active": st.active, "stale": st.stale,
                "licence": st.licence, "lhs_value": st.lhs_value if pub else None, "threshold": st.threshold,
                "distance": st.distance if pub else None, "restricted_value": (not pub) and st.lhs_value is not None,
                "lr": {k: float(v) for k, v in sp.lr.items()},
                "last_triggered": last.get((sp.id, "triggered")), "last_cleared": last.get((sp.id, "cleared")),
                "inputs": [f"{i} {self.r.signals[i].obs_date}" if i in self.r.signals and self.r.signals[i].obs_date else i for i in inputs],
                "note": st.note,
            }))
        return out

    def event_records(self, limit: int = 200) -> list[dict]:
        df = self.store.con.execute(
            f"SELECT as_of, signpost_id, event, run_id LIKE 'seed%' OR run_id LIKE 'replay%' AS backfilled "
            f"FROM signpost_events WHERE as_of <= ? ORDER BY as_of DESC LIMIT ?", [self.r.as_of, limit]).df()
        return [_clean_rec(r) for r in df.to_dict("records")]


# ---------------------------------------------------------------- render
def _json_script(obj) -> Markup:
    """JSON for a <script type="application/json"> block: not HTML-escaped (the guard must
    parse it), with "</" escaped so the data cannot close the script tag."""
    return Markup(json.dumps(obj, default=_clean, allow_nan=False).replace("</", "<\\/"))


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))

    def num(x, nd=2, signed=False):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "–"
        return f"{x:+.{nd}f}" if signed else f"{x:.{nd}f}"

    def pct(x, nd=1):
        return "–" if x is None else f"{100 * x:.{nd}f}%"

    def tone(x):
        if x is None:
            return "none"
        return "pos2" if x >= 1 else "pos1" if x >= 0.25 else "neg2" if x <= -1 else "neg1" if x <= -0.25 else "neutral"

    env.filters.update(num=num, pct=pct, tone=tone, tojson_safe=_json_script)
    return env


def build_site(store: Store, cfg: Config, r: EngineResult, paths: Paths, health: dict | None = None) -> list[Path]:
    out_dir = paths.site_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "rows").mkdir(parents=True)
    (out_dir / "data").mkdir()
    sd = SiteData(store, cfg, r)
    env = _env()
    health = health or {}
    rows = sd.row_records()
    scenarios = sd.scenario_records()
    signposts = sd.signpost_records()
    events = sd.event_records()
    probs = sd.prob_history()
    prob_chart = {"dates": sorted({d.isoformat()[:10] for d in pd.to_datetime(probs["as_of"])}) if not probs.empty else [],
                  "series": {}, "seeded_until": None}
    if not probs.empty:
        piv = probs.pivot(index="as_of", columns="scenario_id", values="final").sort_index()
        prob_chart["dates"] = [pd.Timestamp(d).date().isoformat() for d in piv.index]
        prob_chart["series"] = {k: [_clean(v) for v in piv[k].to_numpy()] for k in piv.columns}
        seeded = probs[probs["seeded"]]
        prob_chart["seeded_until"] = _clean(pd.Timestamp(seeded["as_of"].max()).date()) if not seeded.empty else None
    layer_names = {lay.id: lay.name for lay in cfg.rows.layers} or LAYER_NAMES_FALLBACK
    layers = [{"id": lid, "name": layer_names[lid], "rows": [x for x in rows if x["layer"] == lid]} for lid in sorted(layer_names)]
    summary = health.get("summary", {})
    ctx = {
        "as_of": r.as_of.isoformat(), "knowledge_date": r.knowledge_date.isoformat() if r.knowledge_date else None,
        "mode": r.mode, "built_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "regime": r.regime, "regime_probs": cfg.scenarios.regime_probs or {}, "health": summary,
        "notes": r.notes, "dashboard_url": cfg.alerts.dashboard_url,
    }
    written = []

    def render(tpl: str, path: Path, depth: int = 0, **kw):
        html = env.get_template(tpl).render(root="../" * depth, **ctx, **kw)
        path.write_text(html)
        written.append(path)

    active = [s for s in signposts if s["active"]]
    render("index.html", out_dir / "index.html", scenarios=scenarios, layers=layers, active=active,
           prob_chart=prob_chart, page_data={"scenarios": scenarios, "rows": rows, "signposts": active})
    for row in cfg.rows.rows:
        inds = [i for i in cfg.indicators if i.row == row.id]
        recs = [sd.indicator_record(i) for i in inds]
        charts = [c for c in (sd.chart_payload(i) for i in inds if i.enabled) if c]
        rec = next(x for x in rows if x["row_id"] == row.id)
        judgement = [j for j in cfg.judgements if j.row == row.id]
        render("row.html", out_dir / "rows" / f"{row.id}.html", depth=1, row=rec, indicators=recs, charts=charts,
               judgement=judgement[-1] if judgement else None, page_data={"row": rec, "indicators": recs})
    render("signposts.html", out_dir / "signposts.html", signposts=signposts, events=events,
           page_data={"signposts": signposts, "events": events})
    render("health.html", out_dir / "health.html", indicators=health.get("indicators", []), page_data={"health": summary})

    # exports -------------------------------------------------------------
    pd.DataFrame(rows).to_csv(out_dir / "data" / "rows_latest.csv", index=False)
    pd.DataFrame(signposts).drop(columns=["lr", "inputs"]).to_csv(out_dir / "data" / "signposts_latest.csv", index=False)
    pd.DataFrame(scenarios).to_csv(out_dir / "data" / "scenarios_latest.csv", index=False)
    probs.to_csv(out_dir / "data" / "scenario_probs_history.csv", index=False)
    store.con.execute("SELECT as_of, row_id, layer, final_score, final_confidence, computed_score, override_active, run_id "
                      "FROM row_scores ORDER BY as_of, row_id").df().to_csv(out_dir / "data" / "row_scores_history.csv", index=False)
    inds = [sd.indicator_record(i) for i in cfg.indicators]
    pd.DataFrame(inds).to_csv(out_dir / "data" / "indicators_latest.csv", index=False)
    excel.write_tracker(out_dir / "framework-tracker.xlsx", r.as_of, rows, signposts, scenarios, probs, inds, events)
    csvs = sorted((out_dir / "data").glob("*.csv"))
    links = "".join(f'<li><a href="{f.name}">{f.name}</a></li>' for f in csvs)
    (out_dir / "data" / "index.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>Exports</title><body style='font-family:sans-serif'>"
        f"<h1>CSV exports (as of {r.as_of})</h1><ul>{links}</ul><p><a href='../index.html'>Back</a></p>")
    written += csvs + [out_dir / "framework-tracker.xlsx"]
    (out_dir / ".nojekyll").write_text("")
    return written
