"""AI briefing / weekly digest (FR-25). Claude is replaced by a fake client: no API calls, no cost."""

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import httpx
import pytest

from framework_monitor.outputs import briefing as br
from framework_monitor.outputs.alerts import GitHubIssues

from .test_outputs import FakeGitHub, live, store  # noqa: F401  (fixture re-export)


class FakeClaude:
    def __init__(self, payload=None, stop_reason="end_turn", raise_exc=None):
        self.payload, self.stop_reason, self.raise_exc = payload, stop_reason, raise_exc
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if self.raise_exc:
            raise self.raise_exc
        text = json.dumps(self.payload) if isinstance(self.payload, dict) else self.payload
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=text)])


def good_payload(digest):
    a = next(s for s in digest["scenarios"] if s["id"] == "C")
    return {
        "headline": "High-yield stress switches on",
        "summary": f"Scenario C is at {a['now_pct']}% as the high-yield stress signpost turned active.",
        "key_changes": ["High-yield stress is active (condition hy_oas > 4.00).", "Regime unchanged."],
        "scenario_commentary": f"C has a likelihood ratio multiplier of {a['lr_multiplier']}.",
        "watch_list": ["Whether spreads hold above the threshold for 3 days."],
        "data_issues": [],
    }


def test_digest_is_licence_safe(store, cfg):  # noqa: F811
    r = live(store, cfg)
    d = br.build_digest(store, cfg, r, "daily")
    blob = json.dumps(d)
    assert "4.2" not in blob  # raw ICE value never enters the digest sent to the API
    hy = next(a for a in d["signposts"]["active"] if a["id"] == "hy_stress")
    assert "current" not in hy
    assert all(n["id"] not in {"hy_stress", "hy_crisis", "ccc_blowout", "ig_drift"} for n in d["signposts"]["close_to_triggering"])
    assert {s["id"] for s in d["scenarios"]} == {"base", "A", "B", "C", "D"}


def test_licence_check_blocks_leaky_digest(cfg):
    with pytest.raises(br.BriefingError, match="leak"):
        br.assert_licence_safe({"x": [{"indicator_id": "hy_oas", "value": 4.2}]}, cfg)


def test_ai_briefing_happy_path(store, cfg):  # noqa: F811
    r = live(store, cfg)
    digest = br.build_digest(store, cfg, r, "daily")
    claude = FakeClaude(good_payload(digest))
    res = br.produce(store, cfg, r, client=claude, kind="daily")
    assert res.ai and res.note is None
    call = claude.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["output_config"]["effort"] == "medium" and call["output_config"]["format"]["type"] == "json_schema"
    assert call["fallbacks"] == "default" and call["betas"] == [br.FALLBACK_BETA]
    assert "4.2" not in call["messages"][0]["content"]  # what is actually sent to the API
    assert res.title.startswith("Daily briefing 2026-11-06: High-yield stress switches on")
    assert "### What changed" in res.body and "### Facts (generated from the data, not by AI)" in res.body
    assert "<!-- briefing: daily 2026-11-06 -->" in res.body


def test_invented_number_is_caught_and_withheld(store, cfg):  # noqa: F811
    r = live(store, cfg)
    digest = br.build_digest(store, cfg, r, "daily")
    p = good_payload(digest)
    p["summary"] += " The S&P 500 fell 3.7% to 5,812.40."  # numbers not in the digest
    res = br.produce(store, cfg, r, client=FakeClaude(p), kind="daily")
    assert not res.ai and "withheld" in res.note and "5812.40" in res.note.replace(",", "")
    assert "### What changed" not in res.body and "### Facts" in res.body


def test_number_check_allows_rounding_percent_and_small_counts(store, cfg):  # noqa: F811
    r = live(store, cfg)
    digest = br.build_digest(store, cfg, r, "daily")
    c = next(s for s in digest["scenarios"] if s["id"] == "C")
    b = br.Briefing(headline="x", summary=f"C at {round(c['now_pct'])}%, two signposts, 3 days, layer 2.",
                    key_changes=[f"Prior was {c['confirmed_prior_pct']}%."], scenario_commentary="", watch_list=[],
                    data_issues=[f"as of {digest['as_of']}"])
    assert br.unverified_numbers(b, digest) == []
    b2 = b.model_copy(update={"summary": "on 2031-01-01 it was 77.7%"})
    assert set(br.unverified_numbers(b2, digest)) == {"2031-01-01", "77.7"}


@pytest.mark.parametrize("claude,expect", [
    (FakeClaude({"headline": "x"}, stop_reason="refusal"), "declined"),
    (FakeClaude("not json"), "invalid briefing JSON"),
    (FakeClaude({"headline": "x"}), "invalid briefing JSON"),  # schema mismatch
    (FakeClaude(raise_exc=httpx.ConnectError("down")), "API error"),
    (None, "no ANTHROPIC_API_KEY"),
])
def test_failures_fall_back_to_facts_only(store, cfg, claude, expect):  # noqa: F811
    r = live(store, cfg)
    res = br.produce(store, cfg, r, client=claude, kind="daily")
    assert not res.ai and expect in res.note and "### Facts" in res.body


def test_weekly_kind_and_prompt(store, cfg):  # noqa: F811
    assert br.kind_for(cfg, dt.date(2026, 11, 13)) == "weekly"  # Friday session -> Saturday-morning digest
    assert br.kind_for(cfg, dt.date(2026, 11, 12)) == "daily"
    r = live(store, cfg)
    digest = br.build_digest(store, cfg, r, "weekly")
    claude = FakeClaude(good_payload(digest))
    res = br.produce(store, cfg, r, client=claude, kind="weekly")
    assert "weekly digest" in claude.calls[0]["system"] and "upcoming_catalysts" in claude.calls[0]["messages"][0]["content"]
    assert res.title.startswith("Weekly digest, week to 2026-11-06")


def test_post_issue_one_per_kind(store, cfg):  # noqa: F811
    fake = FakeGitHub()
    gh = GitHubIssues(repo="o/r", token="t", client=httpx.Client(transport=httpx.MockTransport(fake)))
    r = live(store, cfg)
    res = br.produce(store, cfg, r, client=None, kind="daily")
    first = br.post_issue(gh, cfg, res, r.as_of)
    assert first.action == "opened"
    again = br.post_issue(gh, cfg, br.produce(store, cfg, r, client=None, kind="daily"), r.as_of)
    assert again.action == "updated" and again.issue_number == first.issue_number  # re-run edits, no duplicate
    nxt = br.produce(store, cfg, r, client=None, kind="daily")
    nxt.body = nxt.body.replace("2026-11-06 -->", "2026-11-09 -->")
    third = br.post_issue(gh, cfg, nxt, dt.date(2026, 11, 9))
    assert third.action == "opened" and fake.issues[first.issue_number]["state"] == "closed"
    weekly = br.post_issue(gh, cfg, br.produce(store, cfg, r, client=None, kind="weekly"), r.as_of)
    assert weekly.action == "opened" and fake.issues[third.issue_number]["state"] == "open"  # kinds are independent
    assert all("briefing" in i["labels"] for i in fake.issues.values())
