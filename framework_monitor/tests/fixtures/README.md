# Test fixtures

Saved API responses, so every fetcher test runs offline and in CI.

| File | Kind | Notes |
| --- | --- | --- |
| `fred/graph_DGS10.csv` | recorded | Real `fredgraph.csv` response, DGS10 2025-01-02..2026-11-05 (public: Treasury via FRED) |
| `fred/graph_WALCL.csv` | recorded | Real `fredgraph.csv` response, WALCL 2024..2026 (public: Fed H.4.1) |
| `fred/api_DGS10.json` | synthetic format, real values | FRED API `series/observations` layout built from the DGS10 CSV; one value replaced by `"."` |
| `fred/alfred_M2SL_p{1,2}.json` | synthetic | ALFRED real-time-period layout, two pages, with revisions |
| `fred/graph_BAMLH0A0HYM2_synthetic.csv` | synthetic | ICE BofA data is restricted, so these values are made up |
| `treasury/debt_to_penny_p{1,2}.json` | recorded, trimmed | Real responses (page size 5); `meta.total-pages` edited to 2 |
| `treasury/auctions_30y.json` | recorded | Real 30-year bond auctions since 2025-06 |
| `tiingo/SPY_synthetic.json` | synthetic | Tiingo prices are restricted (no redistribution on the free tier) |
| `stooq/spy_us_synthetic.csv` | synthetic | Stooq CSV layout |

Regenerate the synthetic files with `python framework_monitor/tests/fixtures/make_synthetic.py`.
Never commit real values for an indicator flagged `licence: restricted`.
