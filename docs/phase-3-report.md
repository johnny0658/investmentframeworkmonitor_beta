# Phase 3 report: outputs

Built 2026-11-09.

## What was built

| Area | Requirement | Where |
| --- | --- | --- |
| **Signpost hysteresis**: on after `confirm_days`, off only after the clear rule holds `clear_days` (default 3). Oil turns on above $110 and clears after 3 days below $105. Derived from the data alone, so it stays reproducible | Your decision | `engine/compute.py: hysteresis`, `signposts.yaml` |
| **Static dashboard** on GitHub Pages: home (scenarios now / 1w / 4w with a history chart, regime with your regime probabilities, five layer cards with score, arrow and confidence bar, active signposts, data-health strip); one page per row (indicator table with source link and as-of date, 5-year charts, override); signposts (condition, clear rule, current value, distance, last on/off, trigger history); data health | FR-16 to FR-19, FR-22 | `outputs/site/` |
| **CSV exports** (`data/`) and **Excel tracker** with Rows, Signposts, Scenarios and Theses sheets, plus Indicators, Scenario history and Signpost events | FR-9, FR-26 | `outputs/site/build.py`, `outputs/excel.py` |
| **GitHub-issue alerts** for signpost active/cleared, scenario moves of 10+ points in 5 sessions, rows beyond ±1, and sources failing 3 runs in a row. One issue per key; comment on change; close when cleared | FR-23, FR-24 | `outputs/alerts.py`, `config/alerts.yaml` |
| **Backfilled history never alerts.** Only the latest live result is evaluated, scenario moves compare against live sessions only, and backfilled events are labelled on the site | Your decision | `outputs/alerts.py` |
| **Licensing** now also covers the site (embedded JSON), CSVs, the Excel file and issue text. Restricted series show z-score and signal only, prices show indexed series, and the site build fails on any leak | Licensing | `licensing.py`, `outputs/` |
| Engine versioning: seeds made by older logic are recomputed automatically; live rows are never rewritten | | `engine/compute.py` |
| Workflow: build site → licensing check → commit → alerts → deploy to Pages; `force_signpost` input for the alert self-test | | `.github/workflows/framework-monitor.yml` |
| 113 tests, 12 new, including a fake-GitHub test of the PRD acceptance flow (forced signpost: opens one issue, comments on the next run, closes when cleared) | Testing | `tests/test_outputs.py` |

## Hysteresis effect (real data, signpost on/off events)

| Window | Before | After |
| --- | --- | --- |
| 2022, all signposts | ~60 | 34 |
| 2022, oil shock | 24 | 6 (3 episodes) |

## Comment policy

`comment_policy: on_change` (the default in `alerts.yaml`) comments on an open alert only when its state changes: data goes stale, a scenario move crosses another 5-point step, a row score moves half a point, or a different set of sources fails. A long-running signpost therefore doesn't email you every day. Set `every_run` to get a comment on every run instead. The forced self-test always comments, so you can check the comment step.

## Acceptance criteria (v1) status

| Criterion | Status |
| --- | --- |
| 10 consecutive unattended trading days | Starts once Phase 3 is on `main` (the Phase 3 exit test). |
| 40+ indicators across all five layers, each with source and as-of date | 80 with data in layers 1, 2, 3 and 5; every page shows source and as-of date. Layer 4 waits for Phase 4. |
| Scores and probabilities reproduce from a fresh rebuild | Pass (Phase 2) |
| Forced signpost opens one issue, comments later, closes when cleared | Pass in tests against a fake GitHub. Do it live with the steps below. |
| No restricted raw value in the public repo or site (automated) | Pass. The guard now scans the site, CSVs, Excel and every data commit. |
| Excel tracker opens with the four new sheets | Pass (Theses is empty until Phase 5) |

## What to expect on the first run after merging

- The first run recomputes the backfilled history with the hysteresis logic (about 1 minute).
- It opens **one issue per alert that is true today**. On the sandbox data that's 5: oil shock (still on, because Brent hasn't spent 3 days below $105), real-yield squeeze, chips lead down, laggards decouple, and options pricing below −1. After that, issues only open or close when something changes.
- Scenario-move alerts start after 5 live sessions.
