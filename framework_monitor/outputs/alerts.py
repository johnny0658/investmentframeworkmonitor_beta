"""GitHub-issue alerts (FR-23) with de-duplication (FR-24).

Alerts are reconciled against state, not fired as one-off events:

1. `desired_alerts` works out which alert keys *should* be open right now:
   * ``signpost:<id>``             while a signpost is active (after hysteresis)
   * ``scenario-move:<id>``        while a scenario's probability is >= 10 points away
                                   from its value 5 *live* sessions earlier
   * ``row:<id>:above|below``      while a row's final score is beyond +/-1
   * ``source:<fetcher>``          while any indicator of a source has failed 3+ runs in a row
2. `reconcile` compares that with the open issues carrying the alert label:
   * key wanted, no open issue          -> open one (this is "triggers")
   * key wanted, issue open             -> comment, if the state fingerprint changed
                                           (or on every run with comment_policy: every_run)
   * issue open, key no longer wanted   -> comment "cleared" and close it

So there is always at most one open issue per key, and a re-run never
duplicates anything. GitHub itself is the record of what is open.

Seeded or replayed history never raises alerts: only the latest *live*
engine result is evaluated, and scenario moves compare against live rows only.

Issue text is public. It never contains a restricted raw value; signposts on
restricted inputs say only which threshold was crossed.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
from dataclasses import dataclass, field

import httpx

from framework_monitor.engine.compute import EngineResult
from framework_monitor.schemas import Config
from framework_monitor.store.db import Store, _utcnow

log = logging.getLogger(__name__)

KEY_RE = re.compile(r"<!-- alert-key: (\S+) -->")
FP_RE = re.compile(r"<!-- fingerprint: (.*?) -->")
LIVE_RUN_FILTER = "run_id NOT LIKE 'seed%' AND run_id NOT LIKE 'replay%'"


@dataclass
class DesiredAlert:
    key: str
    kind: str
    title: str
    body: str
    fingerprint: str


@dataclass
class Action:
    action: str  # open | comment | close | keep
    key: str
    issue_number: int | None = None
    title: str = ""


# ---------------------------------------------------------------- what should be open
def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _live_prob_n_sessions_ago(store: Store, as_of: dt.date, n: int) -> tuple[dt.date | None, dict[str, float]]:
    dates = [r[0] for r in store.con.execute(
        f"SELECT DISTINCT as_of FROM scenario_probs WHERE as_of < ? AND {LIVE_RUN_FILTER} ORDER BY as_of DESC LIMIT ?",
        [as_of, n]).fetchall()]
    if len(dates) < n:
        return None, {}
    d = dates[-1]
    return d, dict(store.con.execute("SELECT scenario_id, final FROM scenario_probs WHERE as_of = ?", [d]).fetchall())


def _episode_start(store: Store, signpost_id: str, as_of: dt.date) -> dt.date | None:
    row = store.con.execute(
        "SELECT max(as_of) FROM signpost_events WHERE signpost_id = ? AND event = 'triggered' AND as_of <= ?",
        [signpost_id, as_of]).fetchone()
    return row[0] if row else None


def desired_alerts(store: Store, cfg: Config, r: EngineResult, forced: tuple[str, ...] = (), now: dt.datetime | None = None) -> list[DesiredAlert]:
    ac = cfg.alerts
    link = f"\n\nDashboard: {ac.dashboard_url}" if ac.dashboard_url else ""
    sp_by = {s.id: s for s in cfg.signposts}
    names = {s.id: s.name for s in cfg.scenarios.scenarios}
    out: list[DesiredAlert] = []

    # signposts -----------------------------------------------------------
    for st in r.signposts:
        is_forced = st.signpost_id in forced
        if not (st.active or is_forced):
            continue
        sp = sp_by[st.signpost_id]
        since = _episode_start(store, sp.id, r.as_of)
        inputs = sorted(sp.indicators)
        as_ofs = ", ".join(f"`{i}` {r.signals[i].obs_date}" for i in inputs if i in r.signals and r.signals[i].obs_date)
        if st.licence == "public" and st.lhs_value is not None:
            current = f"Current value **{st.lhs_value:.3f}** vs threshold {st.threshold:g} (distance {st.distance:+.3f})."
        elif st.threshold is not None:
            current = f"Threshold {st.threshold:g} crossed. The raw value is licence-restricted and not published."
        else:
            current = "Compound condition met."
        lrs = ", ".join(f"{k} {v:g}" for k, v in sp.lr.items())
        clear = sp.clear_condition or f"not ({sp.condition})"
        test = "[TEST] " if is_forced and not st.active else ""
        body = (
            f"**{sp.name}** ({sp.family}) is active as of {r.as_of}"
            f"{f', since {since}' if since else ''}.\n\n"
            f"- Condition: `{sp.condition}` (confirm {sp.confirm_days} day(s))\n"
            f"- Clears when `{clear}` holds for {sp.clear_days} day(s)\n"
            f"- {current}\n"
            f"- Likelihood ratios: {lrs}\n"
            f"- Data as of: {as_ofs or '-'}{' (stale)' if st.stale else ''}\n"
        )
        fp = f"active|stale={st.stale}"
        if test:
            body = "Forced test alert (workflow input `force_signpost`); the signpost is not really active.\n\n" + body
            fp = f"forced|{(now or _utcnow()).isoformat(timespec='minutes')}"  # comments on every forced run
        out.append(DesiredAlert(f"signpost:{sp.id}", "signpost", f"{test}Signpost active: {sp.name}", body + link, fp))

    # scenario moves (live history only) ----------------------------------
    then, old = _live_prob_n_sessions_ago(store, r.as_of, ac.scenario_move_sessions)
    for k, now_p in r.scenarios.final.items():
        if k not in old:
            continue
        delta = now_p - old[k]
        if abs(delta) >= ac.scenario_move_points:
            bucket = int(abs(delta) * 100 // 5 * 5)
            body = (f"Scenario **{k}: {names[k]}** moved **{delta * 100:+.1f} points** over {ac.scenario_move_sessions} sessions: "
                    f"{_pct(old[k])} on {then} -> {_pct(now_p)} on {r.as_of}.\n\n"
                    f"Active signposts: {', '.join(s.signpost_id for s in r.signposts if s.active) or 'none'}.")
            out.append(DesiredAlert(f"scenario-move:{k}", "scenario",
                                    f"Scenario {k} moved {delta * 100:+.0f} pts in {ac.scenario_move_sessions} sessions",
                                    body + link, f"{'up' if delta > 0 else 'down'}{bucket}"))

    # rows beyond +/-1 ------------------------------------------------------
    for x in r.rows:
        s = x.final_score
        if s is None or abs(s) < ac.row_cross_threshold:
            continue
        side = "above" if s > 0 else "below"
        src = "override" if x.override_active else "computed"
        body = (f"Row **{x.row_id}** (layer {x.layer}) score is **{s:+.2f}** ({src}) as of {r.as_of}, "
                f"{side} {'+' if s > 0 else '-'}{ac.row_cross_threshold:g}.\n\n"
                f"Confidence {x.final_confidence:.2f} (freshness {x.freshness:.2f}, agreement "
                f"{'-' if x.agreement is None else f'{x.agreement:.2f}'}), {x.n_signals} signals.")
        out.append(DesiredAlert(f"row:{x.row_id}:{side}", "row", f"Row {x.row_id} score {s:+.1f} ({side} {'+' if s > 0 else '-'}{ac.row_cross_threshold:g})",
                                body + link, f"{round(s * 2) / 2:+.1f}"))

    # failing sources -------------------------------------------------------
    failing: dict[str, list[str]] = {}
    for ind in cfg.indicators:
        if ind.enabled and ind.source != "derived" and store.consecutive_failures(ind.id) >= ac.source_failure_runs:
            failing.setdefault(ind.source, []).append(ind.id)
    for src, ids in sorted(failing.items()):
        msgs = []
        for i in ids:
            lf = store.last_fetch(i)
            msgs.append(f"- `{i}` ({store.consecutive_failures(i)} runs): {(lf or {}).get('message') or '-'}")
        body = (f"Source **{src}** has {len(ids)} indicator(s) that failed {ac.source_failure_runs}+ runs in a row:\n\n"
                + "\n".join(msgs))
        out.append(DesiredAlert(f"source:{src}", "source", f"Source failing: {src} ({len(ids)} indicators)",
                                body + link, ",".join(sorted(ids))))
    return out


# ---------------------------------------------------------------- GitHub
class GitHubIssues:
    def __init__(self, repo: str | None = None, token: str | None = None, client: httpx.Client | None = None):
        self.repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
        token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not self.repo or not token:
            raise RuntimeError("GITHUB_REPOSITORY and GITHUB_TOKEN are required for alerts (or use --dry-run)")
        self.http = client or httpx.Client(timeout=30)
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"}
        self.base = f"https://api.github.com/repos/{self.repo}"

    def _req(self, method: str, path: str, **kw) -> httpx.Response:
        resp = self.http.request(method, self.base + path, headers=self.headers, **kw)
        if resp.status_code >= 400 and not (method == "POST" and path == "/labels" and resp.status_code == 422):
            raise RuntimeError(f"GitHub {method} {path} -> {resp.status_code}: {resp.text[:200]}")
        return resp

    def ensure_label(self, name: str, color: str = "b60205") -> None:
        self._req("POST", "/labels", json={"name": name, "color": color})  # 422 = already exists

    def open_issues(self, label: str) -> list[dict]:
        out, page = [], 1
        while True:
            batch = self._req("GET", "/issues", params={"labels": label, "state": "open", "per_page": 100, "page": page}).json()
            out += [i for i in batch if "pull_request" not in i]
            if len(batch) < 100:
                return out
            page += 1

    def create(self, title: str, body: str, labels: list[str]) -> int:
        return self._req("POST", "/issues", json={"title": title, "body": body, "labels": labels}).json()["number"]

    def comment(self, number: int, body: str) -> None:
        self._req("POST", f"/issues/{number}/comments", json={"body": body})

    def update_body(self, number: int, body: str) -> None:
        self._req("PATCH", f"/issues/{number}", json={"body": body})

    def close(self, number: int) -> None:
        self._req("PATCH", f"/issues/{number}", json={"state": "closed", "state_reason": "completed"})


def _issue_body(d: DesiredAlert) -> str:
    return f"{d.body}\n\n<!-- alert-key: {d.key} -->\n<!-- fingerprint: {d.fingerprint} -->\n"


def reconcile(gh: GitHubIssues | None, cfg: Config, desired: list[DesiredAlert], as_of: dt.date,
              store: Store | None = None, dry_run: bool = False, open_issues: list[dict] | None = None) -> list[Action]:
    label = cfg.alerts.label
    if open_issues is None:
        open_issues = gh.open_issues(label) if gh else []
    by_key: dict[str, dict] = {}
    for issue in open_issues:
        m = KEY_RE.search(issue.get("body") or "")
        if m:
            by_key.setdefault(m.group(1), issue)  # ignore issues without our marker
    actions: list[Action] = []
    if gh and not dry_run:
        gh.ensure_label(label)
    wanted = {d.key for d in desired}
    for d in desired:
        issue = by_key.get(d.key)
        if issue is None:
            actions.append(Action("open", d.key, title=d.title))
            if not dry_run:
                gh.ensure_label(f"alert:{d.kind}", color="fbca04")
                num = gh.create(d.title, _issue_body(d), [label, f"alert:{d.kind}"])
                actions[-1].issue_number = num
                if store:
                    store.con.execute("INSERT INTO alerts VALUES (?, ?, ?, NULL, ?, ?)", [d.key, d.kind, _utcnow(), num, d.title])
            continue
        m = FP_RE.search(issue.get("body") or "")
        changed = (m.group(1) if m else None) != d.fingerprint
        if changed or cfg.alerts.comment_policy == "every_run":
            actions.append(Action("comment", d.key, issue["number"], d.title))
            if not dry_run:
                gh.comment(issue["number"], f"Update {as_of}:\n\n{d.body}")
                gh.update_body(issue["number"], _issue_body(d))
        else:
            actions.append(Action("keep", d.key, issue["number"], d.title))
    for key, issue in by_key.items():
        if key in wanted:
            continue
        actions.append(Action("close", key, issue["number"], issue.get("title", "")))
        if not dry_run:
            gh.comment(issue["number"], f"Cleared as of {as_of}. Closing.")
            gh.close(issue["number"])
            if store:
                store.con.execute("UPDATE alerts SET closed_at = ? WHERE issue_number = ? AND closed_at IS NULL",
                                  [_utcnow(), issue["number"]])
    return actions
