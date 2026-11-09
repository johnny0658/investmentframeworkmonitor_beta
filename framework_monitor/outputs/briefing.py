"""AI-written daily briefing and weekly digest (FR-25), posted as GitHub issues.

Pipeline:
1. `build_digest`: a compact, licence-safe JSON of what changed (code, no AI).
   It holds no raw value of a restricted indicator: the same rule as the public site.
2. `write_briefing`: Claude turns the digest into a short structured briefing
   (headline, summary, key changes, scenario commentary, watch list, data issues).
3. `unverified_numbers`: every number in Claude's text must appear in the digest
   (allowing for rounding and percent/point forms). If any does not, the AI part
   is dropped for the day and a template note is used instead.
4. `render_issue`: AI part on top, then a facts section rendered by code, so the
   facts never depend on the model.
5. `post_issue`: one open issue per kind (daily / weekly). Re-running the same
   day edits that day's issue; a new day closes the previous one.

Failures never stop the pipeline: no key, an API error, a refusal or a failed
number check all fall back to the facts-only issue.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import math
import re
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from framework_monitor.engine.compute import EngineResult
from framework_monitor.licensing import _walk_json
from framework_monitor.schemas import Config
from framework_monitor.store.db import Store

log = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MARKER = "<!-- briefing: {kind} {as_of} -->"
MARKER_RE = re.compile(r"<!-- briefing: (daily|weekly) (\d{4}-\d{2}-\d{2}) -->")
NOT_LIVE = "run_id NOT LIKE 'replay%'"


class BriefingError(Exception):
    pass


class Briefing(BaseModel):
    headline: str
    summary: str
    key_changes: list[str]
    scenario_commentary: str
    watch_list: list[str]
    data_issues: list[str]


BRIEFING_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "One line, under 15 words."},
        "summary": {"type": "string", "description": "2-3 sentences: the most important things today."},
        "key_changes": {"type": "array", "items": {"type": "string"}, "description": "3-6 bullets, most important first."},
        "scenario_commentary": {"type": "string", "description": "What moved the scenario probabilities and what that implies."},
        "watch_list": {"type": "array", "items": {"type": "string"}, "description": "2-4 things to watch next: signposts close to triggering, stale data, upcoming risks named in the digest."},
        "data_issues": {"type": "array", "items": {"type": "string"}, "description": "Data problems from the digest that limit confidence; empty if none."},
    },
    "required": ["headline", "summary", "key_changes", "scenario_commentary", "watch_list", "data_issues"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You write the {kind} briefing for a personal investment-framework monitor. The reader built the \
framework and knows its vocabulary: five layers, rows scored from -2 (bearish for risk assets) to +2 (bullish), \
signposts that move five scenario probabilities through likelihood ratios, and a growth x inflation regime box.

Write about {words} words in total across the fields, in plain, direct English. Lead with what changed and why it \
matters for the scenarios; skip anything that did not move.

Rules:
- Use only facts and numbers that appear in the digest. Do not compute new numbers (no sums, averages or ratios of \
your own) and do not bring in outside market knowledge, prices or news.
- Quote probabilities as they appear (percent, or percentage-point changes) and scores with their sign.
- Say plainly when data is stale or missing and how that limits the reading.
- The scenario priors and likelihood ratios are placeholders the reader has not tuned yet; mention this once if the \
probabilities moved a lot.
- This is decision support, not advice: no buy/sell/position recommendations.{weekly_rules}"""

WEEKLY_RULES = """
- This is the weekly digest: describe the week as a whole (changes over 1 week), not just today. If the digest says \
upcoming catalysts are not tracked yet, say so in the watch list."""


# ---------------------------------------------------------------- digest
def _r(x, nd=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), nd)


def _pp(x):
    return None if x is None else round(100 * float(x), 1)


def _prev_date(store: Store, table: str, as_of: dt.date, days_back: int | None) -> dt.date | None:
    if days_back is None:  # previous computed session
        q = f"SELECT max(as_of) FROM {table} WHERE as_of < ? AND {NOT_LIVE}"
        return store.con.execute(q, [as_of]).fetchone()[0]
    q = f"SELECT max(as_of) FROM {table} WHERE as_of <= ? AND {NOT_LIVE}"
    return store.con.execute(q, [as_of - dt.timedelta(days=days_back)]).fetchone()[0]


def _values(store: Store, table: str, key: str, col: str, d: dt.date | None) -> dict:
    if d is None:
        return {}
    return dict(store.con.execute(f"SELECT {key}, {col} FROM {table} WHERE as_of = ?", [d]).fetchall())


def build_digest(store: Store, cfg: Config, r: EngineResult, kind: str, health: dict | None = None) -> dict:
    bc = cfg.briefing
    window_days = 7 if kind == "weekly" else 1
    d_prev = _prev_date(store, "scenario_probs", r.as_of, None)
    d_week = _prev_date(store, "scenario_probs", r.as_of, 7)
    p_prev = _values(store, "scenario_probs", "scenario_id", "final", d_prev)
    p_week = _values(store, "scenario_probs", "scenario_id", "final", d_week)
    s_prev = _values(store, "row_scores", "row_id", "final_score", d_prev)
    s_week = _values(store, "row_scores", "row_id", "final_score", d_week)
    names = {s.id: s.name for s in cfg.scenarios.scenarios}
    u = r.scenarios

    scenarios = []
    for k in u.prior:
        now = u.final[k]
        scenarios.append({
            "id": k, "name": names[k], "now_pct": _pp(now),
            "previous_session_pct": _pp(p_prev.get(k)), "one_week_ago_pct": _pp(p_week.get(k)),
            "change_since_previous_pts": _pp(now - p_prev[k]) if k in p_prev else None,
            "change_1w_pts": _pp(now - p_week[k]) if k in p_week else None,
            "confirmed_prior_pct": _pp(u.prior[k]), "lr_multiplier": _r(u.multiplier[k]),
        })

    prev_box = None
    if d_prev:
        row = store.con.execute("SELECT box FROM regime WHERE as_of = ?", [d_prev]).fetchone()
        prev_box = row[0] if row else None
    g = r.regime
    regime = {"box": g.box, "previous_box": prev_box, "growth_up": g.growth_up, "inflation_up": g.inflation_up,
              "growth_detail": g.growth_detail, "core_pce_3m_annualised_pct": _r(g.core_pce_3m_ann),
              "core_pce_12m_pct": _r(g.core_pce_12m)}

    sp_by = {s.id: s for s in cfg.signposts}
    start = r.as_of - dt.timedelta(days=window_days)
    events = store.con.execute(
        f"SELECT as_of, signpost_id, event FROM signpost_events WHERE as_of > ? AND as_of <= ? AND {NOT_LIVE} ORDER BY as_of",
        [start, r.as_of]).fetchall()
    since = dict(store.con.execute(
        "SELECT signpost_id, max(as_of) FROM signpost_events WHERE event = 'triggered' AND as_of <= ? GROUP BY 1", [r.as_of]).fetchall())
    active, near, unavailable = [], [], []
    for st in r.signposts:
        sp = sp_by[st.signpost_id]
        if st.status == "unavailable":
            unavailable.append(sp.name)
        elif st.active:
            active.append({"id": sp.id, "name": sp.name, "family": sp.family, "condition": sp.condition,
                           "since": since.get(sp.id).isoformat() if since.get(sp.id) else None, "stale_data": st.stale,
                           "lr": {k: float(v) for k, v in sp.lr.items()}})
        elif (st.licence == "public" and st.distance is not None and st.threshold
              and 0 <= st.distance <= bc.near_trigger_fraction * abs(st.threshold)):
            near.append({"id": sp.id, "name": sp.name, "condition": sp.condition, "current": _r(st.lhs_value, 3),
                         "threshold": st.threshold, "distance_to_trigger": _r(st.distance, 3)})

    rows, movers = [], []
    for x in r.rows:
        if x.final_score is None:
            continue
        rec = {"id": x.row_id, "layer": x.layer, "score": _r(x.final_score),
               "change_since_previous": _r(x.final_score - s_prev[x.row_id]) if s_prev.get(x.row_id) is not None else None,
               "change_1w": _r(x.final_score - s_week[x.row_id]) if s_week.get(x.row_id) is not None else None,
               "confidence": _r(x.final_confidence), "override": x.override_active}
        rows.append(rec)
        ch = rec["change_1w"] if kind == "weekly" else rec["change_since_previous"]
        if ch is not None and abs(ch) >= bc.mover_threshold:
            movers.append(rec["id"])
    no_data_rows = [x.row_id for x in r.rows if x.final_score is None]

    opened = [t for (t,) in store.con.execute(
        "SELECT detail FROM alerts WHERE CAST(opened_at AS DATE) > ? ORDER BY opened_at", [start]).fetchall()]
    closed = [t for (t,) in store.con.execute(
        "SELECT detail FROM alerts WHERE closed_at IS NOT NULL AND CAST(closed_at AS DATE) > ? ORDER BY closed_at", [start]).fetchall()]
    hs = (health or {}).get("summary", {})
    digest = {
        "kind": kind, "as_of": r.as_of.isoformat(),
        "compared_with": {"previous_session": d_prev.isoformat() if d_prev else None,
                          "one_week_ago": d_week.isoformat() if d_week else None},
        "scenarios": scenarios,
        "regime": regime,
        "my_regime_probabilities_pct": {k: _pp(v) for k, v in (cfg.scenarios.regime_probs or {}).items()},
        "signposts": {
            "active": active,
            "events_in_window": [{"date": d.isoformat(), "id": s, "name": sp_by[s].name, "event": e} for d, s, e in events if s in sp_by],
            "close_to_triggering": near,
            "unavailable_sources_pending": unavailable,
        },
        "rows": rows, "row_movers": movers, "rows_without_data_yet": no_data_rows,
        "alerts": {"opened": opened, "closed": closed},
        "data_health": {"stale": hs.get("stale", []), "failing": hs.get("failing", []),
                        "source_alerts": hs.get("source_alerts", []), "held_values": hs.get("held_values", 0)},
        "caveats": ["Scenario priors and likelihood ratios are placeholders, not yet tuned.",
                    "Licence-restricted raw values (ICE BofA spreads, Cboe VIX, prices) are deliberately excluded."],
    }
    if kind == "weekly":
        digest["upcoming_catalysts"] = "Not tracked yet: the catalyst calendar arrives in Phase 4."
    if r.notes:
        digest["engine_notes"] = r.notes
    assert_licence_safe(digest, cfg)
    return digest


def assert_licence_safe(digest: dict, cfg: Config) -> None:
    out = []
    _walk_json(digest, {i.id for i in cfg.indicators if i.licence == "public"}, "digest", out)
    if out:
        raise BriefingError(f"digest would leak restricted values: {out[0]}")


# ---------------------------------------------------------------- Claude
def write_briefing(client, cfg: Config, digest: dict) -> Briefing:
    """One Claude call with structured output. Raises BriefingError on refusal or bad output."""
    bc = cfg.briefing
    system = SYSTEM_PROMPT.format(kind=digest["kind"], words=bc.target_words,
                                  weekly_rules=WEEKLY_RULES if digest["kind"] == "weekly" else "")
    resp = client.beta.messages.create(
        model=bc.model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": "<digest>\n" + json.dumps(digest, indent=1, default=str)
                   + "\n</digest>\n\nWrite the " + digest["kind"] + " briefing from this digest."}],
        output_config={"effort": bc.effort, "format": {"type": "json_schema", "schema": BRIEFING_SCHEMA}},
        betas=[FALLBACK_BETA],
        fallbacks="default",  # on a safety decline, the API re-runs the request on a fallback model
    )
    if resp.stop_reason == "refusal":
        raise BriefingError("model declined the request")
    if resp.stop_reason == "max_tokens":
        raise BriefingError("briefing was cut off (max_tokens)")
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if not text:
        raise BriefingError("no text in response")
    try:
        return Briefing.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise BriefingError(f"invalid briefing JSON: {exc}") from exc


# ---------------------------------------------------------------- number check
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# 5,812.40 / -3.7 / +29.4 / 55 ; thousands separators allowed
_NUM_RE = re.compile(r"(?<![\w.])[-+−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
SMALL_INTS = set(range(0, 13))  # counts and ordinals ("three signposts", "layer 2", "5 sessions")


def _numbers(text: str) -> list[float]:
    out = []
    for m in _NUM_RE.findall(text):
        s = m.replace("−", "-").replace(",", "")
        try:
            out.append(float(s))
        except ValueError:
            pass
    return out


def unverified_numbers(briefing: Briefing, digest: dict) -> list[str]:
    """Numbers in the briefing that do not appear in the digest (allowing rounding, sign and percent forms)."""
    blob = json.dumps(digest, default=str)
    allowed_dates = set(_DATE_RE.findall(blob))
    digest_nums = set(_numbers(_DATE_RE.sub(" ", blob)))
    forms = set()
    for d in digest_nums:
        for v in (d, abs(d), d * 100, abs(d) * 100):
            forms.add(v)
    bad = []
    text = " ".join([briefing.headline, briefing.summary, briefing.scenario_commentary,
                     *briefing.key_changes, *briefing.watch_list, *briefing.data_issues])
    for date in _DATE_RE.findall(text):
        if date not in allowed_dates:
            bad.append(date)
    for raw in _NUM_RE.findall(_DATE_RE.sub(" ", text)):
        s = raw.replace("−", "-").replace(",", "")
        try:
            x = float(s)
        except ValueError:
            continue
        if abs(x) in SMALL_INTS and float(x).is_integer():
            continue
        decimals = len(s.split(".")[1]) if "." in s else 0
        if not any(math.isclose(round(f, decimals), abs(x), abs_tol=1e-9) or math.isclose(round(f, decimals), x, abs_tol=1e-9)
                   for f in forms):
            bad.append(raw)
    return bad


# ---------------------------------------------------------------- rendering
def _fmt(x, suffix="", signed=False):
    if x is None:
        return "–"
    if signed and x == 0:
        return "0" + suffix
    return (f"{x:+g}" if signed else f"{x:g}") + suffix


def render_issue(cfg: Config, digest: dict, briefing: Briefing | None, note: str | None) -> tuple[str, str]:
    kind, as_of = digest["kind"], digest["as_of"]
    title = (f"Weekly digest, week to {as_of}" if kind == "weekly" else f"Daily briefing {as_of}")
    if briefing:
        title += f": {briefing.headline}"
    lines = []
    if briefing:
        lines += [f"**{briefing.summary}**", "", "### What changed"] + [f"- {k}" for k in briefing.key_changes]
        lines += ["", "### Scenarios", briefing.scenario_commentary, "", "### Watch"] + [f"- {w}" for w in briefing.watch_list]
        if briefing.data_issues:
            lines += ["", "### Data issues"] + [f"- {d}" for d in briefing.data_issues]
    else:
        lines += [f"_AI briefing unavailable today ({note}). The facts below are complete._"]

    lines += ["", "---", "", "### Facts (generated from the data, not by AI)", "",
              f"Compared with {digest['compared_with']['previous_session'] or '–'} (previous session) "
              f"and {digest['compared_with']['one_week_ago'] or '–'} (1 week ago).", "",
              "| Scenario | Now | Δ prev | Δ 1w | Prior |", "| --- | ---: | ---: | ---: | ---: |"]
    for s in digest["scenarios"]:
        lines.append(f"| {s['id']}: {s['name']} | **{_fmt(s['now_pct'], '%')}** | {_fmt(s['change_since_previous_pts'], ' pts', True)} | "
                     f"{_fmt(s['change_1w_pts'], ' pts', True)} | {_fmt(s['confirmed_prior_pct'], '%')} |")
    g = digest["regime"]
    changed = f" (was {g['previous_box']})" if g["previous_box"] and g["previous_box"] != g["box"] else ""
    lines += ["", f"- **Regime:** {g['box'] or 'n/a'}{changed}"]
    sp = digest["signposts"]
    lines += ["- **Active signposts:** " + (", ".join(f"{a['name']} (since {a['since'] or '–'})" for a in sp["active"]) or "none")]
    if sp["events_in_window"]:
        lines.append("- **Signpost changes:** " + ", ".join(f"{e['name']} {e['event']} {e['date']}" for e in sp["events_in_window"]))
    if sp["close_to_triggering"]:
        lines.append("- **Close to triggering:** " + ", ".join(
            f"{n['name']} (`{n['condition']}`, now {n['current']:g})" for n in sp["close_to_triggering"]))
    movers = [r for r in digest["rows"] if r["id"] in digest["row_movers"]]
    if movers:
        key = "change_1w" if kind == "weekly" else "change_since_previous"
        lines.append("- **Row movers:** " + ", ".join(f"{r['id']} {r['score']:+.2f} ({r[key]:+.2f})" for r in movers))
    dh = digest["data_health"]
    if dh["stale"] or dh["failing"]:
        lines.append(f"- **Data health:** {len(dh['stale'])} stale, {len(dh['failing'])} failing")
    if digest.get("upcoming_catalysts"):
        lines.append(f"- **Upcoming catalysts:** {digest['upcoming_catalysts']}")
    if cfg.alerts.dashboard_url:
        lines += ["", f"Dashboard: {cfg.alerts.dashboard_url}"]
    who = f"Written by {cfg.briefing.model} from licence-safe data; every number checked against the digest." if briefing else ""
    lines += ["", f"<sub>{who} Not investment advice. Priors and likelihood ratios are placeholders.</sub>", "",
              MARKER.format(kind=kind, as_of=as_of)]
    return title[:250], "\n".join(lines) + "\n"


# ---------------------------------------------------------------- orchestration
@dataclass
class BriefingResult:
    kind: str
    title: str
    body: str
    ai: bool
    note: str | None
    issue_number: int | None = None
    action: str | None = None


def kind_for(cfg: Config, as_of: dt.date) -> str:
    return "weekly" if as_of.weekday() == cfg.briefing.weekly_on_weekday else "daily"


def produce(store: Store, cfg: Config, r: EngineResult, client=None, kind: str | None = None,
            health: dict | None = None, use_ai: bool = True) -> BriefingResult:
    kind = kind or kind_for(cfg, r.as_of)
    digest = build_digest(store, cfg, r, kind, health)
    briefing, note = None, None
    if not use_ai:
        note = "AI disabled for this run"
    elif client is None:
        note = "no ANTHROPIC_API_KEY configured"
    else:
        try:
            b = write_briefing(client, cfg, digest)
            bad = unverified_numbers(b, digest)
            if bad:
                note = f"the AI text contained numbers not in the data ({', '.join(bad[:5])}), so it was withheld"
            else:
                briefing = b
        except BriefingError as exc:
            note = str(exc)
        except Exception as exc:  # API/network errors: never break the pipeline
            note = f"API error: {type(exc).__name__}"
            log.warning("briefing API call failed: %s", exc)
    title, body = render_issue(cfg, digest, briefing, note)
    return BriefingResult(kind, title, body, briefing is not None, note)


def post_issue(gh, cfg: Config, res: BriefingResult, as_of: dt.date) -> BriefingResult:
    """One open issue per kind: re-runs edit today's issue; a new day closes the previous one."""
    label = cfg.briefing.label
    gh.ensure_label(label, color="0e8a16")
    mine, older = None, []
    for issue in gh.open_issues(label):
        m = MARKER_RE.search(issue.get("body") or "")
        if not m or m.group(1) != res.kind:
            continue
        if m.group(2) == as_of.isoformat():
            mine = issue
        else:
            older.append(issue)
    if mine:
        gh.update_body(mine["number"], res.body)
        gh._req("PATCH", f"/issues/{mine['number']}", json={"title": res.title})
        res.issue_number, res.action = mine["number"], "updated"
    else:
        res.issue_number, res.action = gh.create(res.title, res.body, [label, f"briefing:{res.kind}"]), "opened"
    for issue in older:
        gh.comment(issue["number"], f"Superseded by #{res.issue_number}.")
        gh.close(issue["number"])
    return res
