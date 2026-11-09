# Phase 1 report: data spine

Built 2026-11-09. Requirements referenced by PRD ID.

## What was built

| Area | Requirement | Where |
| --- | --- | --- |
| Config schemas for every YAML file, cross-file ID validation, safe expression parser for formulas and signpost conditions | FR-2, Testing/config validation | `framework_monitor/schemas.py`, `config/*.yaml` |
| Indicator catalogue: 111 indicators (93 enabled, 80 fetched directly, 13 derived for Phase 2), 18 rows, 5 layers, 17 signposts, 5 scenarios | FR-2 | `config/indicators.yaml`, `rows.yaml`, `signposts.yaml`, `scenarios.yaml` |
| Fetchers: `fred` (API, or keyless CSV fallback), `alfred` (all vintages, paginated), `treasury_fiscal` (generic, paginated), `prices` (Tiingo → Stooq → yfinance), `manual` | FR-1, FR-5, FR-6 | `framework_monitor/fetchers/` |
| Retries: 3 attempts, exponential back-off, no retry on 4xx, secrets redacted from every error | FR-4, FR-5 | `fetchers/base.py` |
| Bitemporal append-only store with `as_of` reconstruction, revision log, derived-table schemas | FR-8, FR-10 | `store/db.py` |
| Incremental fetch (last date − 90 days) and full backfill | FR-3, FR-7 | `pipeline.py`, `cli.py backfill` |
| Parquet snapshots split public/private; DuckDB rebuilt from Parquet every run | FR-9 | `store/snapshots.py` |
| Encrypted private store (Fernet) carried between runs as an Actions artifact | Licensing, open question 1 | `store/private_store.py`, workflow |
| Licensing guard (scanner + writer-side refusal + git-tracked check) | Licensing rules | `licensing.py`, `cli.py guard` |
| Quality checks: staleness, range (±20% of span), 6σ jumps with hold-until-confirmed, revision counts, consecutive source failures | Data quality 1–5 | `quality.py` |
| FRED ID / units / history verification | Kickoff prompt | `verify.py`, `cli.py verify-series` |
| Scheduled workflow (22:30 / 13:00 UTC, NYSE holidays skipped) and CI | Schedule | `.github/workflows/` |
| 74 offline tests on recorded fixtures (real responses for public sources, synthetic for restricted ones) | Testing | `framework_monitor/tests/` |

## Live first fetch (from the build sandbox, no API keys)

- **48 of 48 FRED, ALFRED and Treasury indicators loaded**: 223,751 observations in 15 seconds. That covers Layer 1 (41), Layer 2 (5) and Layer 3 (2).
- A rebuild from Parquet reproduced the store exactly. A second, incremental fetch added 0 duplicate rows.
- The licensing guard passed. The 6 restricted FRED series (4 ICE spreads, VIX, VIX3M) went to the private store only.
- **All 32 price indicators failed**, as expected, because no Tiingo key was available in the sandbox. They need `TIINGO_API_KEY`. See issue 2 below.
- So the **Phase 1 exit criterion (25 indicators stored with history and passing quality checks) is met** by the FRED and Treasury data alone.

### Series verification (all 44 FRED IDs, 2026-11-09)

Every series ID exists and is current, and **every unit matches the config**.
That includes the net-liquidity units the PRD warned about: `WALCL` and
`WTREGEN` are in USD millions, `RRPONTSYD` is in USD billions, so
`fed_assets − tga − on_rrp × 1000` is correct. Spreads are in percent, so
400bp is written `4.00` in conditions and CCC 1,500bp is `15.00`.

Issues found (reported, not guessed around):

| Indicator | Series | Finding |
| --- | --- | --- |
| `hy_oas`, `ccc_oas`, `bbb_oas`, `ig_oas` | ICE BofA OAS | **FRED now serves only ~3 years of history (from 2023-11-07).** That only just fills the 3-year z-score window, and it makes the 2020 and 2022 back-tests impossible from FRED. The private store accumulates history from now on. |
| `business_loans` | `BUSLOANS` | Monthly, not weekly as the PRD table says. `TOTCI` is the weekly H.8 equivalent if you want weekly. |
| `tga_daily` | DTS operating cash balance | The "TGA Closing Balance" line starts on 2022-04-18 (earlier account names differ), and the DTS reports it in `open_today_bal`. `WTREGEN` carries the long history. |
| `fed_deficit` | `MTSDS133FMS` | I used FRED's Monthly Treasury Statement series rather than parsing MTS table 1, which repeats rows per report. It's monitor-only until a 12-month-sum transform exists. |

## Design decisions to review

1. **Prices are stored as a total-return index, not the raw adjusted close.** Tiingo and Stooq back-adjust history on every dividend. Storing that as-is with a 90-day look-back would splice two adjustment bases and create a fake jump. The fetcher instead chains each fetch onto the stored series at the first overlapping date. History never changes and provider switches stay seamless. Returns, ratios and correlations, which are all the signposts use, are unaffected.
2. **Restricted manual CSVs** (FactSet forward P/E, CAPE, AAII) go in `data/private/manual/`, not the committed `framework_monitor/manual/`. The guard fails if one is committed.
3. **Cboe VIX/VIX3M are restricted** until the terms are confirmed, as the PRD says. `vix_term` (the ratio) is public.
4. **Rows:** the PRD's embedded framework model (21 rows) wasn't in the markdown. I reconstructed 18 rows from the tables. Please send the missing three.
5. **Direction and weights** in `indicators.yaml` are first-pass defaults. They're not used until Phase 2, so please review them before then.
6. **The private store lives in artifacts with 90-day retention.** If the workflow stops for 90 days, the restricted history (including ICE spreads FRED no longer serves) is lost. The workflow refuses to start a fresh private store when earlier runs exist, unless you explicitly allow it. Consider downloading a backup now and then, or moving to a private repo later.

## Acceptance criteria (v1) status

| Criterion | Status |
| --- | --- |
| 10 consecutive unattended trading days | Not yet. The workflow is ready; this is the Phase 3 exit test. |
| 40+ indicators across all five layers, with source and as-of date | 48 live in layers 1–3, plus 32 price series once `TIINGO_API_KEY` is set (layers 2, 3, 5). Layer 4 has none until the crash tracker is attached or the Phase 4 calendar and policy fetchers land. |
| Row scores, confidence and probabilities reproduce from a fresh rebuild | The storage half passes (exact rebuild, with a test). Scores come in Phase 2. |
| Forced signpost opens, comments on and closes a GitHub issue | Phase 3 |
| No restricted raw value in the public repo or site (automated check) | **Passes.** Runs in CI and before every data commit. |
| Thesis file validates and trips its kill switch | Phase 5 |
| Excel tracker with four new sheets | Phase 3 |

## Needs your decision or action

1. **Add secrets** `PRIVATE_STORE_KEY` (required; back it up), `FRED_API_KEY` and `TIINGO_API_KEY`. Then run the workflow once with mode `backfill`.
2. **Default branch:** scheduled workflows run only on the default branch. Merge this branch into `main` (or whichever branch you make the default).
3. **Index prices:** Tiingo has no index data, and Stooq now returns an HTML page instead of CSV (tested from the sandbox), so it's effectively dead as a fallback. `^NSEI` and `^HSI` therefore depend on yfinance (unofficial). Should I keep that, or swap in ETF proxies (`INDA` already exists; `EWH` for Hong Kong)?
4. **The three missing framework rows** (see above).
5. **ICE history gap:** accept starting the credit history now, or add HYG/LQD-based proxies for the 2020/2022 back-tests?

## Open PRD questions that block Phase 2

- **Scenario priors and signpost LRs:** Phase 2 can be built and tested with the placeholder values, but the live probabilities are meaningless until you replace them.
- The other open questions (positions detail, Singapore indicators) don't block Phase 2.
