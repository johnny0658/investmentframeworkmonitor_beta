"""Phase 3 outputs: alerts (FR-23/24), site (FR-16..22), Excel (FR-26), licensing on all of them."""

from __future__ import annotations

import datetime as dt
import json
import re

import httpx
import numpy as np
import pandas as pd
import pytest

from framework_monitor import licensing
from framework_monitor.engine.compute import compute, persist
from framework_monitor.fetchers.base import to_frame
from framework_monitor.outputs.alerts import GitHubIssues, desired_alerts, reconcile
from framework_monitor.outputs.site.build import build_site
from framework_monitor.store.db import Store

FETCHED = dt.datetime(2026, 11, 9, 22, 30)
END = dt.date(2026, 11, 6)


def _daily(n, f):
    return [(d.date(), f(i)) for i, d in enumerate(pd.bdate_range(end=END, periods=n))]


@pytest.fixture
def store():
    s = Store()
    n = 900
    hy = [3.2 + 0.1 * np.sin(i / 30) for i in range(n - 3)] + [4.05, 4.10, 4.20]  # crosses 4.0
    s.write_observations("hy_oas", to_frame(_daily(n, lambda i: hy[i])), "fred", FETCHED)
    s.write_observations("ust_10y", to_frame(_daily(n, lambda i: 4.0 + 0.2 * np.sin(i / 50))), "fred", FETCHED)
    s.write_observations("real_10y", to_frame(_daily(n, lambda i: 1.9)), "fred", FETCHED)
    walk = np.cumsum(np.random.default_rng(1).normal(0, 0.01, n))
    s.write_observations("spy", to_frame(_daily(n, lambda i: 500 * np.exp(walk[i]))), "prices:tiingo", FETCHED)
    s.write_observations("tlt", to_frame(_daily(n, lambda i: 90 * np.exp(-0.5 * walk[i]))), "prices:tiingo", FETCHED)
    yield s
    s.close()


def live(store, cfg, d=END, run_id="live"):
    r = compute(store, cfg, d, mode="known", knowledge_date=FETCHED.date())
    persist(store, cfg, r, run_id)
    return r


# ---------------------------------------------------------------- desired alerts
def test_desired_alerts_signpost_never_leaks_restricted_value(store, cfg):
    r = live(store, cfg)
    alerts = {a.key: a for a in desired_alerts(store, cfg, r)}
    a = alerts["signpost:hy_stress"]
    assert "4.2" not in a.body and "4.20" not in a.body  # raw ICE value never in a public issue
    assert "licence-restricted" in a.body and "Threshold 4 crossed" in a.body
    assert a.fingerprint == "active|stale=False"
    assert "signpost:hy_crisis" not in alerts


def test_scenario_move_uses_live_history_only(store, cfg):
    days = [d.date() for d in pd.bdate_range(end=END, periods=8)]
    # seeded history with a very different prior-like state must not count
    for d in days[:-1]:
        persist(store, cfg, compute(store, cfg, d, mode="latest"), run_id="seed-latest")
    r = live(store, cfg)
    assert not [a for a in desired_alerts(store, cfg, r) if a.kind == "scenario"]
    # now give it 5 live sessions before today with the base case 30 points higher
    for d in days[:-1]:
        store.con.execute("UPDATE scenario_probs SET run_id = 'live', final = final + 0.30 WHERE as_of = ? AND scenario_id = 'base'", [d])
    moves = {a.key: a for a in desired_alerts(store, cfg, r) if a.kind == "scenario"}
    assert moves["scenario-move:base"].fingerprint.startswith("down")  # 30 points lower than 5 live sessions ago
    # C genuinely moved: hy_stress is active today (LR 3.0) but was not 5 sessions ago
    assert moves["scenario-move:C"].fingerprint.startswith("up")


def test_row_and_source_alerts(store, cfg):
    r = live(store, cfg)
    for i in range(3):
        store.log_fetch(f"r{i}", "sofr", "fred", "error", message="HTTP 500", at=FETCHED + dt.timedelta(hours=i))
        store.log_fetch(f"r{i}", "dgs_x", "fred", "error", at=FETCHED + dt.timedelta(hours=i))  # not in config: ignored
    keys = {a.key: a for a in desired_alerts(store, cfg, r)}
    assert keys["source:fred"].fingerprint == "sofr" and "HTTP 500" in keys["source:fred"].body
    rows = [k for k in keys if k.startswith("row:")]
    assert all(abs(x.final_score) >= 1 for x in r.rows if f"row:{x.row_id}:{'above' if (x.final_score or 0) > 0 else 'below'}" in rows)


# ---------------------------------------------------------------- reconcile against a fake GitHub
class FakeGitHub:
    """Minimal in-memory GitHub issues API behind httpx.MockTransport."""

    def __init__(self):
        self.issues: dict[int, dict] = {}
        self.comments: dict[int, list[str]] = {}
        self.labels: set[str] = set()
        self.calls: list[str] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path.split("/repos/o/r")[1]
        self.calls.append(f"{req.method} {path}")
        body = json.loads(req.content) if req.content else {}
        if path == "/labels":
            if body["name"] in self.labels:
                return httpx.Response(422, json={"message": "exists"})
            self.labels.add(body["name"])
            return httpx.Response(201, json={})
        if path == "/issues" and req.method == "GET":
            label = req.url.params["labels"]
            return httpx.Response(200, json=[i for i in self.issues.values() if i["state"] == "open" and label in i["labels"]])
        if path == "/issues" and req.method == "POST":
            n = len(self.issues) + 1
            self.issues[n] = {"number": n, "title": body["title"], "body": body["body"], "labels": body["labels"], "state": "open"}
            return httpx.Response(201, json={"number": n})
        m = re.fullmatch(r"/issues/(\d+)(/comments)?", path)
        n = int(m.group(1))
        if m.group(2):
            self.comments.setdefault(n, []).append(body["body"])
            return httpx.Response(201, json={})
        self.issues[n].update({k: v for k, v in body.items() if k in ("body", "state")})
        return httpx.Response(200, json=self.issues[n])


def gh_for(fake):
    return GitHubIssues(repo="o/r", token="t", client=httpx.Client(transport=httpx.MockTransport(fake)))


def test_forced_signpost_opens_comments_then_closes(store, cfg):
    """PRD acceptance: a test signpost forced to trigger opens ONE issue, comments on later runs,
    and closes when cleared."""
    fake = FakeGitHub()
    gh = gh_for(fake)
    r = live(store, cfg)
    base = [a for a in desired_alerts(store, cfg, r) if a.key != "signpost:oil_shock"]

    def run(forced, minute):
        d = [a for a in desired_alerts(store, cfg, r, forced=forced, now=FETCHED + dt.timedelta(minutes=minute))
             if a.key == "signpost:oil_shock"]
        return reconcile(gh, cfg, base + d, r.as_of, store=store)

    a1 = run(("oil_shock",), 0)
    assert [x.action for x in a1 if x.key == "signpost:oil_shock"] == ["open"]
    oil = [i for i in fake.issues.values() if "oil" in i["title"].lower()]
    assert len(oil) == 1 and oil[0]["title"].startswith("[TEST]")
    n = oil[0]["number"]

    a2 = run(("oil_shock",), 1)
    assert [x.action for x in a2 if x.key == "signpost:oil_shock"] == ["comment"]
    assert len([i for i in fake.issues.values() if "oil" in i["title"].lower()]) == 1  # no duplicate
    assert len(fake.comments[n]) == 1

    a3 = run((), 2)
    assert [x.action for x in a3 if x.key == "signpost:oil_shock"] == ["close"]
    assert fake.issues[n]["state"] == "closed" and "Cleared" in fake.comments[n][-1]
    logged = store.con.execute("SELECT closed_at IS NOT NULL FROM alerts WHERE issue_number = ?", [n]).fetchone()[0]
    assert logged


def test_reconcile_is_idempotent_and_ignores_foreign_issues(store, cfg):
    fake = FakeGitHub()
    fake.issues[1] = {"number": 1, "title": "unrelated", "body": "no marker", "labels": ["framework-monitor"], "state": "open"}
    gh = gh_for(fake)
    r = live(store, cfg)
    desired = desired_alerts(store, cfg, r)
    first = reconcile(gh, cfg, desired, r.as_of)
    second = reconcile(gh, cfg, desired, r.as_of)
    assert {a.action for a in first} == {"open"}
    assert {a.action for a in second} == {"keep"}  # on_change policy: nothing changed, no comment
    assert fake.issues[1]["state"] == "open"  # an issue without our marker is never touched
    assert sum(1 for i in fake.issues.values() if i["state"] == "open") == 1 + len(desired)


def test_every_run_policy_comments(store, cfg):
    fake = FakeGitHub()
    gh = gh_for(fake)
    cfg2 = cfg.model_copy(update={"alerts": cfg.alerts.model_copy(update={"comment_policy": "every_run"})})
    r = live(store, cfg2)
    d = desired_alerts(store, cfg2, r)
    reconcile(gh, cfg2, d, r.as_of)
    assert {a.action for a in reconcile(gh, cfg2, d, r.as_of)} == {"comment"}


def test_dry_run_touches_nothing(store, cfg):
    r = live(store, cfg)
    acts = reconcile(None, cfg, desired_alerts(store, cfg, r), r.as_of, dry_run=True)
    assert acts and all(a.action == "open" for a in acts)


# ---------------------------------------------------------------- site + excel
def test_site_builds_and_passes_licensing(store, cfg, paths):
    r = live(store, cfg)
    files = build_site(store, cfg, r, paths, {"summary": {"as_of": "2026-11-09", "indicators_enabled": 80}, "indicators": []})
    names = {f.name for f in files}
    assert {"index.html", "signposts.html", "health.html", "framework-tracker.xlsx", "rows_latest.csv"} <= names
    assert (paths.site_dir / "rows" / "ai_bottlenecks_credit.html").exists()
    assert licensing.scan_paths([paths.site_dir], cfg) == []

    html = (paths.site_dir / "rows" / "ai_bottlenecks_credit.html").read_text()
    data = json.loads(re.search(r'id="chart-data">(.*?)</script>', html, re.S).group(1))
    hy = next(c for c in data if c["indicator_id"] == "hy_oas")
    assert "raw" not in hy and "indexed" not in hy and any(v is not None for v in hy["z"])
    pages = (paths.site_dir / "rows" / "defensives.html").read_text()
    spy_like = json.loads(re.search(r'id="chart-data">(.*?)</script>', pages, re.S).group(1))
    tlt = next(c for c in spy_like if c["indicator_id"] == "tlt")
    assert "raw" not in tlt and tlt["indexed"][0] == 100.0  # prices: indexed only
    ust = json.loads(re.search(r'id="chart-data">(.*?)</script>', (paths.site_dir / "rows" / "rates_debt.html").read_text(), re.S).group(1))
    assert "raw" in next(c for c in ust if c["indicator_id"] == "ust_10y")  # public raw shown

    xl = pd.read_excel(paths.site_dir / "framework-tracker.xlsx", sheet_name=None)
    assert {"Rows", "Signposts", "Scenarios", "Theses"} <= set(xl)
    assert len(xl["Rows"]) == len(cfg.rows.rows) and len(xl["Signposts"]) == len(cfg.signposts)
    ind = xl["Indicators"]
    assert ind.loc[ind["indicator_id"] == "hy_oas", "raw"].isna().all()
    assert ind.loc[ind["indicator_id"] == "ust_10y", "raw"].notna().all()


def test_guard_catches_leak_in_html_and_xlsx(cfg, paths):
    paths.site_dir.mkdir(parents=True)
    (paths.site_dir / "p.html").write_text(
        '<script type="application/json" id="chart-data">[{"indicator_id": "hy_oas", "licence": "restricted", "raw": [4.2]}]</script>')
    pd.DataFrame({"indicator_id": ["spy"], "licence": ["restricted"], "raw": [600.0]}).to_excel(paths.site_dir / "x.xlsx", index=False)
    pd.DataFrame({"signpost_id": ["hy_stress"], "licence": ["restricted"], "lhs_value": [4.2]}).to_csv(paths.site_dir / "s.csv", index=False)
    found = {v.path.split("/")[-1].split(" ")[0] for v in licensing.scan_paths([paths.site_dir], cfg)}
    assert found == {"p.html", "x.xlsx", "s.csv"}
