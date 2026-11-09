"""Command-line entry point: ``python -m framework_monitor.cli <command>``.

Phase 1 commands:

  validate        validate every YAML config file (pydantic + cross-references)
  should-run      exit 0 if this run's US session was an NYSE trading day, 78 otherwise
  rebuild         recreate data/monitor.duckdb from Parquet snapshots
  fetch           incremental fetch (last stored date minus 90 days)
  backfill        load full available history (FR-7)
  check           quality checks + data/health/health.{json,md}
  snapshot        write Parquet snapshots (public + private)
  guard           licensing guard; exit 1 on any restricted raw value in public paths
  verify-series   check FRED IDs, units, history length -> data/health/series-verification.md
  private-store   pack | unpack the encrypted private store
  compute         run the scoring engine for one date (default today) -> data/summary.md
  replay          run the engine over a date range (back-tests, history)
  publish         build the static site, CSVs and Excel tracker into site/ (then licensing guard)
  alert           open / comment / close GitHub issues for alerts (FR-23, FR-24)
  briefing        AI-written daily briefing / Saturday weekly digest as a GitHub issue (FR-25)
  run-all         rebuild -> fetch -> check -> compute -> snapshot -> publish -> guard
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from pathlib import Path

from framework_monitor import licensing, quality, trading_calendar, verify
from framework_monitor.config_loader import ConfigError, load_config
from framework_monitor.pipeline import run_fetch
from framework_monitor.settings import Paths
from framework_monitor.store import private_store, snapshots
from framework_monitor.store.db import Store

SKIP_EXIT = 78  # "neutral" exit code the workflow treats as "skip this run"


def _summary(text: str) -> None:
    """Print, and append to the GitHub Actions job summary when available."""
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as fh:
            fh.write(text + "\n\n")


def _open_store(paths: Paths, fresh: bool) -> Store:
    if fresh or not paths.db_path.exists():
        store, counts = snapshots.rebuild(paths)
        print(f"rebuilt {paths.db_path} from parquet: {counts or 'no snapshots yet'}")
        return store
    return Store(paths.db_path)


def cmd_validate(args, paths) -> int:
    cfg = load_config(args.config_dir)
    enabled = [i for i in cfg.indicators if i.enabled]
    print(f"config OK: {len(cfg.indicators)} indicators ({len(enabled)} enabled), "
          f"{len(cfg.rows.rows)} rows, {len(cfg.signposts)} signposts, {len(cfg.scenarios.scenarios)} scenarios, "
          f"{len(cfg.judgements)} judgements")
    return 0


def cmd_should_run(args, paths) -> int:
    now = dt.datetime.now(dt.UTC)
    ok, why = trading_calendar.should_run(args.mode, now)
    print(why)
    return 0 if ok else SKIP_EXIT


def cmd_rebuild(args, paths) -> int:
    _open_store(paths, fresh=True).close()
    return 0


def _do_fetch(args, paths, backfill: bool) -> int:
    cfg = load_config(args.config_dir)
    store = _open_store(paths, fresh=args.fresh)
    try:
        s = run_fetch(store, cfg, args.mode, backfill=backfill, only=args.only, paths=paths)
    finally:
        store.close()
    _summary("```\n" + s.text() + "\n```")
    # Partial failure is normal (FR-4) and surfaces on the health report; only
    # fail the step if nothing at all could be fetched.
    return 1 if s.failed and not s.ok else 0


def cmd_fetch(args, paths) -> int:
    return _do_fetch(args, paths, backfill=False)


def cmd_backfill(args, paths) -> int:
    return _do_fetch(args, paths, backfill=True)


def cmd_check(args, paths) -> int:
    cfg = load_config(args.config_dir)
    store = _open_store(paths, fresh=False)
    try:
        today = dt.date.today()
        report = quality.health_report(store, cfg, today)
        quality.write_health(report, paths, today)
        md = (paths.health_dir / "health.md").read_text()
    finally:
        store.close()
    _summary(md.split("| Indicator |")[0].strip())
    return 0


def cmd_snapshot(args, paths) -> int:
    cfg = load_config(args.config_dir)
    store = _open_store(paths, fresh=False)
    try:
        written = snapshots.export(store, cfg, paths)
    finally:
        store.close()
    print(f"snapshots written: {written}")
    return 0


def cmd_guard(args, paths) -> int:
    cfg = load_config(args.config_dir)
    v = licensing.scan_paths(paths.public_paths, cfg)
    v += licensing.scan_git_tracked(paths.root)
    v += licensing.scan_manual_dir(paths.public_manual_dir, cfg)
    if v:
        _summary("LICENSING GUARD FAILED:\n" + "\n".join(f"- {x}" for x in v))
        return 1
    print(f"licensing guard OK ({len(cfg.restricted_ids)} restricted indicators; scanned {[str(p) for p in paths.public_paths]})")
    return 0


def cmd_verify_series(args, paths) -> int:
    cfg = load_config(args.config_dir)
    today = dt.date.today()
    checks = verify.verify_fred(cfg, today=today)
    text = verify.render(checks, today)
    paths.health_dir.mkdir(parents=True, exist_ok=True)
    (paths.health_dir / "series-verification.md").write_text(text)
    bad = [c for c in checks if not c.ok]
    _summary(f"verify-series: {len(checks) - len(bad)}/{len(checks)} OK" +
             ("".join(f"\n- `{c.indicator_id}` ({c.series}): {'; '.join(c.issues)}" for c in bad)))
    return 0


def cmd_private_store(args, paths) -> int:
    f = Path(args.file)
    if args.action == "pack":
        n = private_store.pack(paths.private_dir, f)
        print(f"packed {n} files from {paths.private_dir} into {f}")
    else:
        n = private_store.unpack(f, paths.private_dir)
        print(f"restored {n} files into {paths.private_dir}")
    return 0


def cmd_compute(args, paths) -> int:
    from framework_monitor.engine.compute import compute, persist, seed_history
    from framework_monitor.outputs.summary import render

    cfg = load_config(args.config_dir)
    now = dt.datetime.now(dt.UTC)
    knowledge_date = now.date()
    if args.as_of:
        as_of = args.as_of
        knowledge_date = None if args.as_of < now.date() else knowledge_date  # past date: as known then
    elif args.for_run:
        as_of = trading_calendar.session_for_run(args.for_run, now)
    else:
        as_of = now.date()
    store = _open_store(paths, fresh=False)
    try:
        seeded = seed_history(store, cfg, as_of, args.seed_sessions) if args.seed_sessions else 0
        run_id = store.start_run("compute")
        r = compute(store, cfg, as_of, mode=args.mode, knowledge_date=knowledge_date)
        events = persist(store, cfg, r, run_id)
        store.finish_run(run_id)
        md = render(store, cfg, r)
    finally:
        store.close()
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    (paths.data_dir / "summary.md").write_text(md)
    if seeded:
        print(f"seeded {seeded} earlier sessions (latest-vintage mode)")
    for e in events:
        print(f"signpost {e['signpost_id']} {e['event']}")
    _summary(md.split("## Rows")[0].strip())
    return 0


def cmd_replay(args, paths) -> int:
    from framework_monitor.engine.compute import compute, persist, sessions_between

    cfg = load_config(args.config_dir)
    store = _open_store(paths, fresh=False)
    n = 0
    try:
        for d in sessions_between(args.start, args.end):
            persist(store, cfg, compute(store, cfg, d, mode=args.mode), run_id=f"replay-{args.mode}")
            n += 1
        trig = store.con.execute(
            "SELECT as_of, signpost_id, event FROM signpost_events WHERE as_of BETWEEN ? AND ? ORDER BY as_of",
            [args.start, args.end]).fetchall()
    finally:
        store.close()
    print(f"replayed {n} sessions {args.start}..{args.end} ({args.mode} vintages)")
    for d, sp, ev in trig:
        print(f"  {d} {sp} {ev}")
    return 0


def _latest_live(store, cfg):
    from framework_monitor.engine.compute import recompute

    row = store.con.execute(
        "SELECT max(as_of) FROM engine_runs WHERE run_id NOT LIKE 'seed%' AND run_id NOT LIKE 'replay%'").fetchone()
    if row[0] is None:
        raise SystemExit("no live engine result yet: run `compute` first")
    return recompute(store, cfg, row[0])


def cmd_publish(args, paths) -> int:
    import json

    from framework_monitor.outputs.site.build import build_site

    cfg = load_config(args.config_dir)
    store = _open_store(paths, fresh=False)
    try:
        r = _latest_live(store, cfg)
        hp = paths.health_dir / "health.json"
        health = json.loads(hp.read_text()) if hp.exists() else {}
        files = build_site(store, cfg, r, paths, health)
    finally:
        store.close()
    print(f"site built for {r.as_of}: {len(files)} files in {paths.site_dir}")
    v = licensing.scan_paths([paths.site_dir], cfg)
    if v:
        _summary("LICENSING GUARD FAILED on site:\n" + "\n".join(f"- {x}" for x in v))
        return 1
    return 0


def cmd_alert(args, paths) -> int:
    from framework_monitor.outputs.alerts import GitHubIssues, desired_alerts, reconcile

    cfg = load_config(args.config_dir)
    store = _open_store(paths, fresh=False)
    try:
        r = _latest_live(store, cfg)
        desired = desired_alerts(store, cfg, r, forced=tuple(args.force or ()))
        gh = None
        if not args.dry_run:
            gh = GitHubIssues()
        actions = reconcile(gh, cfg, desired, r.as_of, store=store, dry_run=args.dry_run)
    finally:
        store.close()
    lines = [f"alerts for {r.as_of}{' (dry run)' if args.dry_run else ''}: "
             + ", ".join(f"{k} {sum(a.action == k for a in actions)}" for k in ("open", "comment", "keep", "close"))]
    lines += [f"- {a.action}: {a.key}" + (f" (#{a.issue_number})" if a.issue_number else "") for a in actions]
    _summary("\n".join(lines))
    return 0


def cmd_briefing(args, paths) -> int:
    import json

    from framework_monitor.outputs import briefing as br
    from framework_monitor.outputs.alerts import GitHubIssues

    cfg = load_config(args.config_dir)
    client = None
    if not args.no_ai and os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic

        client = anthropic.Anthropic()
    store = _open_store(paths, fresh=False)
    try:
        r = _latest_live(store, cfg)
        hp = paths.health_dir / "health.json"
        health = json.loads(hp.read_text()) if hp.exists() else {}
        res = br.produce(store, cfg, r, client=client, kind=args.kind, health=health, use_ai=not args.no_ai)
    finally:
        store.close()
    text = f"# {res.title}\n\n{res.body}"
    if args.dry_run:
        out = Path(args.out) if args.out else None
        if out:
            out.write_text(text)
            print(f"dry run: briefing written to {out}")
        else:
            print(text)
        return 0
    archive = paths.data_dir / "briefings" / f"{r.as_of.isoformat()}-{res.kind}.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_text(text)
    res = br.post_issue(GitHubIssues(), cfg, res, r.as_of)
    _summary(f"{res.kind} briefing for {r.as_of}: issue #{res.issue_number} {res.action}; "
             + ("AI text included" if res.ai else f"facts only ({res.note})"))
    return 0


def cmd_run_all(args, paths) -> int:
    args.fresh = True
    args.as_of, args.seed_sessions = None, 0
    for step in (cmd_fetch, cmd_check, _compute_step, cmd_snapshot, cmd_publish, cmd_guard):
        rc = step(args, paths)
        if rc:
            return rc
    return 0


def _compute_step(args, paths) -> int:
    ns = argparse.Namespace(**{**vars(args), "mode": "known"})
    return cmd_compute(ns, paths)


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="framework-monitor", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", type=Path, default=None)
    p.add_argument("--root", type=Path, default=None, help="repo root (default: package parent)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.set_defaults(fn=fn)
        return sp

    add("validate", cmd_validate, "validate config files")
    sp = add("should-run", cmd_should_run, "exit 0 on NYSE trading days, 78 otherwise")
    sp.add_argument("--mode", choices=["main", "catchup"], default="main")
    add("rebuild", cmd_rebuild, "rebuild DuckDB from Parquet")
    for name, fn, h in (("fetch", cmd_fetch, "incremental fetch"), ("backfill", cmd_backfill, "full-history fetch"),
                        ("run-all", cmd_run_all, "rebuild, fetch, check, snapshot, guard")):
        sp = add(name, fn, h)
        sp.add_argument("--mode", choices=["main", "catchup"], default="main")
        sp.add_argument("--only", nargs="+", help="limit to these indicator ids")
        sp.add_argument("--fresh", action="store_true", help="rebuild DuckDB from Parquet first")
    add("check", cmd_check, "quality checks + health report")
    sp = add("compute", cmd_compute, "run the scoring engine")
    sp.add_argument("--as-of", type=_date, default=None, help="YYYY-MM-DD (default: today, UTC)")
    sp.add_argument("--for-run", choices=["main", "catchup"], default=None,
                    help="score the US session this scheduled run is for (catch-up = previous session)")
    sp.add_argument("--mode", choices=["known", "latest"], default="known",
                    help="known = only vintages known on as_of (reproducible); latest = today's values")
    sp.add_argument("--seed-sessions", type=int, default=0,
                    help="first fill this many earlier NYSE sessions that have no results yet")
    add("publish", cmd_publish, "build the static site + exports")
    sp = add("alert", cmd_alert, "GitHub issue alerts")
    sp.add_argument("--dry-run", action="store_true", help="print what would happen; touch nothing")
    sp.add_argument("--force", nargs="+", metavar="SIGNPOST", help="treat these signposts as active (alert self-test)")
    sp = add("briefing", cmd_briefing, "AI briefing / weekly digest as a GitHub issue")
    sp.add_argument("--kind", choices=["daily", "weekly"], default=None, help="default: weekly on the configured weekday")
    sp.add_argument("--dry-run", action="store_true", help="do not post; print or write the issue text")
    sp.add_argument("--out", default=None, help="with --dry-run: write the text to this file")
    sp.add_argument("--no-ai", action="store_true", help="facts only, no Claude call")
    sp = add("replay", cmd_replay, "run the engine over a date range")
    sp.add_argument("--start", type=_date, required=True)
    sp.add_argument("--end", type=_date, required=True)
    sp.add_argument("--mode", choices=["known", "latest"], default="latest")
    add("snapshot", cmd_snapshot, "write Parquet snapshots")
    add("guard", cmd_guard, "licensing guard")
    add("verify-series", cmd_verify_series, "verify FRED IDs, units, history")
    sp = add("private-store", cmd_private_store, "pack/unpack the encrypted private store")
    sp.add_argument("action", choices=["pack", "unpack"])
    sp.add_argument("--file", default="private-store.enc")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    paths = Paths(root=args.root.resolve()) if args.root else Paths()
    try:
        return args.fn(args, paths)
    except (ConfigError, private_store.PrivateStoreError, licensing.LicenceViolation) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
