# Phase 2 report: scoring engine

Built 2026-11-09. Uses the PRD placeholder priors and likelihood ratios, as agreed.

## What was built

| Area | Requirement | Where |
| --- | --- | --- |
| Transforms: `level`, `yoy`, `ann_3m`, `diff_4w`, `diff_13w_pct`, `pct_rank`; calendar-based lags with gap detection | Step 1 | `engine/transforms.py` |
| Indicator signal: z-score against a trailing 3-year window (10 years for monthly and slower), × direction, clipped to ±2; percentile mapped to −2…+2 for `pct_rank` | Step 1, FR-11 | `engine/signals.py` |
| Derived indicators: net Fed liquidity, credit impulse, VIX ÷ VIX3M, SPY–TLT 60-day correlation, relative-strength ratios, equal-weight AI basket, rolling 120-day AI beta. Units are asserted before arithmetic, and each series is put on its declared frequency's calendar | FR-12, data quality check 3 | `engine/formulas.py`, `engine/compute.py` |
| Row score, freshness, agreement, confidence; overrides with expiry | Step 2 | `engine/rows.py` |
| Regime classifier (WEI vs 6-month average × core PCE 3m vs 12m), shown beside my regime probabilities | FR-13 | `engine/regime.py`, `scenarios.yaml: regime_probs` |
| Signpost evaluation with `confirm_days`, current value and distance to trigger; triggered/cleared events | Step 3, FR-19 data | `engine/compute.py` |
| Scenario update with likelihood ratios, family cap and shrinkage | Step 3 | `engine/scenarios.py` |
| Engine tables, idempotent per date, with the knowledge date recorded | FR-10 | `store/db.py` |
| Licensing for the new tables: restricted rows are published with raw values and distances nulled; z-scores and signals stay public | Licensing | `store/snapshots.py`, `licensing.py` |
| `compute`, `replay` and `run-all` commands; workflow step; public `data/summary.md` | | `cli.py`, `outputs/summary.py` |
| 27 new tests, 101 in total, including the PRD's hand-worked cases (two scenarios / three signposts, family cap, shrinkage) | FR-11, Testing | `tests/test_engine*.py` |

## Exit criteria

| Criterion | Status |
| --- | --- |
| Hand-worked tests pass | **Pass.** Every expected number is derived in the test comments. |
| Row scores reproduce from a rebuild | **Pass.** On real data (2026-11-09) and in CI: a fresh rebuild from Parquet followed by a recompute gives identical signals, row scores, regime, signpost states and scenario probabilities. |

## Back-test replay (PRD testing), real data, latest vintages

| Window | What fired | Matches history? |
| --- | --- | --- |
| Feb–Jun 2020 | Vol inversion 2020-02-26; "everything falls" from 2020-03-09; vol inversion cleared 2020-04-24 | Yes (VIX term structure inverted in the last week of February) |
| 2022 | Oil shock (Brent > $110) from 2022-03-01; liquidity drain from February; term-premium jump in May–June; chips lead down from April | Yes |
| Mar–May 2025 | HY stress and vol inversion 2025-04-04; IG drift 2025-04-07; HY stress cleared 2025-04-22 | Yes |

The **credit signposts cannot fire in 2020 or 2022**, because FRED only serves ICE spreads from 2023-11-07. They do fire correctly in April 2025.

## Things you should know

1. **The placeholder LRs move the probabilities a lot.** On 2026-11-09 three signposts were active (real yield squeeze, chips lead down, laggards decouple), and scenario A went from a 25% prior to about 63%. Four weeks earlier, D (stagflation) was about 42%, driven by the oil-shock LR of 3.0. That's what the placeholder LRs do; **tuning them is the next important judgement call.** `replay` lets you test a change against history before committing it.
2. **Signposts flap.** In 2022 `oil_shock` triggered and cleared a dozen times as Brent crossed $110. `confirm_days` stops a signpost from triggering on a single day, but clearing is immediate. Before Phase 3 alerts open GitHub issues, I propose **hysteresis**: clear only after the condition has been false for N days (default 3). Phase 3 needs your OK on this.
3. **Seeded history uses latest vintages.** The first run fills the previous 130 sessions so that "1 week ago" and "4 weeks ago" exist. Most series have one vintage (the day they were first fetched), so these rows use today's values, revisions included, and are tagged `seed-latest`. From now on each day is scored with only what was known then.
4. **Knowledge date.** The 13:00 UTC catch-up run rescores the *previous* session with spreads published that morning, so it uses the run date as its knowledge date. This is recorded per date and reused by recomputation, which is what makes the results reproducible.
5. **Rows with no score yet:** valuations (FactSet P/E is manual), positioning, capital flows (NSDL/HKEX), calendar, policy, crash signals, portfolio, tech competitiveness, value capture, future tech and AI vs non-AI. These are all Phase 4–5 sources or weight-0 rows; capital flows has data but only monitor-only indicators.
6. **Direction choices to review:** `initial_claims` is at a 3-year low, so it gets +2 (good for risk assets). `vix_term` at 1.10 gets −2. Both are reasonable but strong; check them alongside the weights.

## Needs your decision before Phase 3

1. Hysteresis for clearing signposts: OK with 3 days?
2. Should seeded and replayed events be ignored by alerts? (I'll assume yes.)
3. When you're ready: your own priors, LRs and regime probabilities. They can change any time, and nothing in the code depends on the values.
