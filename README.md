# Investment Framework Monitor

A daily monitor that turns my five-layer investment framework into scored
indicators, scenario probabilities and alerts, using free public data only.
The spec is [docs/framework-monitor-prd.md](docs/framework-monitor-prd.md).

Not investment advice. This is a personal decision-support tool.

**Status: Phase 1 (data spine).** See [docs/phase-1-report.md](docs/phase-1-report.md).

## How it works (Phase 1)

```
indicators.yaml ──► fetchers (fred, alfred, treasury_fiscal, prices, manual)
                       │  retries + back-off, one failure never stops the rest
                       ▼
                 DuckDB bitemporal store  ◄── rebuilt from Parquet every run
                       │  quality checks: staleness, range, jumps, revisions, source health
                       ▼
     data/parquet/public/   (committed: public indicators only)
     data/private/          (restricted raw values: encrypted Actions artifact, never committed)
     data/health/           (health report: dates, counts, statuses, no values)
                       │
                       ▼
                 licensing guard: fails the run if a restricted raw value is public
```

## Setup

1. **Secrets** (Settings → Secrets and variables → Actions):
   | Secret | Needed for | How to get it |
   | --- | --- | --- |
   | `PRIVATE_STORE_KEY` | encrypting restricted data (required) | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. **Back it up**: without it the private history cannot be decrypted. |
   | `FRED_API_KEY` | FRED API + ALFRED vintages | free at fred.stlouisfed.org → My Account → API Keys. Without it FRED falls back to the public CSV download (no vintages). |
   | `TIINGO_API_KEY` | ETF / stock prices | free at tiingo.com |
2. **First run:** Actions → *framework-monitor* → Run workflow → mode `backfill`.
   This loads full history, verifies every FRED series and commits the public
   snapshots.
3. After that, the schedule runs by itself: 22:30 UTC (main) and 13:00 UTC
   (catch-up) on NYSE trading days.

## Commands

```bash
pip install -e ".[dev]"
```

```bash
framework-monitor validate          # check every YAML config
```

```bash
framework-monitor backfill --fresh  # full history into data/monitor.duckdb
```

```bash
framework-monitor run-all           # rebuild -> fetch -> check -> snapshot -> guard
```

```bash
python -m pytest -q                 # offline tests on recorded fixtures
```

Other commands: `fetch`, `check`, `snapshot`, `guard`, `verify-series`,
`rebuild`, `should-run`, `private-store pack|unpack`. Run `framework-monitor -h` for the full list.

## Layout

```
framework_monitor/
  config/        indicators.yaml (the only place a series is defined), rows, signposts, scenarios, judgements
  fetchers/      one module per source: fetch(series, start, end) -> DataFrame
  store/         DuckDB bitemporal store, Parquet snapshots, encrypted private store
  quality.py     data-quality checks + health report
  licensing.py   licensing guard
  verify.py      FRED series / units / history verification
  pipeline.py    incremental fetch orchestration
  cli.py
  manual/        hand-entered CSVs for PUBLIC indicators (restricted ones go in data/private/manual/)
  tests/         offline tests + recorded fixtures
data/
  parquet/public/   committed history (public indicators only)
  health/           health.md / health.json / series-verification.md
```

## Licensing

The repo is public. Every indicator has `licence: public | restricted`.
Restricted indicators (ICE BofA spreads, Cboe VIX family, Tiingo prices,
FactSet, S&P DJI, AAII ...) may only appear publicly as derived values
(z-scores, signals, ratios, thresholds crossed). Their raw values live in
`data/private/`, which is gitignored and travels between runs as a
Fernet-encrypted GitHub Actions artifact. Artifacts on a public repo can be
downloaded by any signed-in GitHub user, so the encryption is not optional.
`framework-monitor guard` fails the run before anything is committed.
