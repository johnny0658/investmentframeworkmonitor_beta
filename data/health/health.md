# Data health, 2026-11-25

- Indicators enabled: **80**, with data: **80**
- With data by layer: L1: 41, L2: 21, L3: 11, L4: 0, L5: 7
- Stale: 2 bank_credit, core_pce
- Failing this run: 0 
- Source alerts (failed 3+ runs in a row): none
- Values held out of scoring pending confirmation: 4

| Indicator | Source | Licence | First | Last | Obs | Age (d) | Stale | Revisions | Held | Fetch |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| `m2` | alfred | public | 1959-01-01 | 2026-10-01 | 814 | 55 |  | 27848 |  | ok |
| `fed_assets` | fred | public | 2002-12-18 | 2026-11-18 | 1249 | 7 |  | 0 |  | ok |
| `tga` | fred | public | 2002-12-18 | 2026-11-18 | 1249 | 7 |  | 0 |  | ok |
| `on_rrp` | fred | public | 2003-02-07 | 2026-11-24 | 3374 | 1 |  | 0 |  | ok |
| `bank_reserves` | fred | public | 2002-12-18 | 2026-11-18 | 1249 | 7 |  | 0 |  | ok |
| `bank_credit` | fred | public | 1973-01-03 | 2026-11-11 | 2811 | 14 | yes | 26 |  | ok |
| `business_loans` | fred | public | 1947-01-01 | 2026-10-01 | 958 | 55 |  | 7 |  | ok |
| `nfci` | fred | public | 1971-01-08 | 2026-11-13 | 2915 | 12 |  | 21 |  | ok |
| `anfci` | fred | public | 1971-01-08 | 2026-11-13 | 2915 | 12 |  | 26 |  | ok |
| `stlfsi` | fred | public | 1993-12-31 | 2026-11-13 | 1716 | 12 |  | 24 |  | ok |
| `bill_3m` | fred | public | 1981-09-01 | 2026-11-23 | 11306 | 2 |  | 0 |  | ok |
| `sofr` | fred | public | 2018-04-03 | 2026-11-23 | 2158 | 2 |  | 0 |  | ok |
| `ust_2y` | fred | public | 1976-06-01 | 2026-11-23 | 12616 | 2 |  | 0 |  | ok |
| `ust_10y` | fred | public | 1962-01-02 | 2026-11-23 | 16208 | 2 |  | 0 |  | ok |
| `ust_30y` | fred | public | 1977-02-15 | 2026-11-23 | 12438 | 2 |  | 0 |  | ok |
| `curve_10y2y` | fred | public | 1976-06-01 | 2026-11-24 | 12617 | 1 |  | 0 |  | ok |
| `curve_10y3m` | fred | public | 1982-01-04 | 2026-11-24 | 11226 | 1 |  | 0 |  | ok |
| `real_5y` | fred | public | 2003-01-02 | 2026-11-23 | 5977 | 2 |  | 0 |  | ok |
| `real_10y` | fred | public | 2003-01-02 | 2026-11-23 | 5977 | 2 |  | 0 |  | ok |
| `breakeven_10y` | fred | public | 2003-01-02 | 2026-11-24 | 5978 | 1 |  | 0 |  | ok |
| `real_30y` | fred | public | 2010-02-22 | 2026-11-23 | 4192 | 2 |  | 0 |  | ok |
| `fwd_infl_5y5y` | fred | public | 2003-01-02 | 2026-11-24 | 5978 | 1 |  | 0 |  | ok |
| `term_premium_kw` | fred | public | 1990-01-02 | 2026-11-20 | 9208 | 5 |  | 0 |  | ok |
| `fed_funds` | fred | public | 1954-07-01 | 2026-11-23 | 26444 | 2 |  | 0 |  | ok |
| `fed_deficit` | fred | public | 1980-10-01 | 2026-10-01 | 553 | 55 |  | 0 |  | ok |
| `public_debt` | treasury_fiscal | public | 1993-04-01 | 2026-11-23 | 8440 | 2 |  | 0 |  | ok |
| `tga_daily` | treasury_fiscal | public | 2022-04-18 | 2026-11-23 | 1153 | 2 |  | 0 |  | ok |
| `auction_btc_10y` | treasury_fiscal | public | 1999-11-10 | 2026-10-07 | 278 | 49 |  | 0 |  | ok |
| `auction_btc_30y` | treasury_fiscal | public | 2001-02-08 | 2026-10-08 | 220 | 48 |  | 0 |  | ok |
| `cpi` | alfred | public | 1947-01-01 | 2026-10-01 | 957 | 55 |  | 2148 |  | ok |
| `core_cpi` | alfred | public | 1957-01-01 | 2026-10-01 | 837 | 55 |  | 1424 |  | ok |
| `core_pce` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 85 | yes | 7394 |  | ok |
| `wei` | fred | public | 2008-01-05 | 2026-11-14 | 985 | 11 |  | 2 |  | ok |
| `initial_claims` | fred | public | 1967-01-07 | 2026-11-14 | 3124 | 11 |  | 2 |  | ok |
| `payrolls` | alfred | public | 1939-01-01 | 2026-10-01 | 1054 | 55 |  | 12640 |  | ok |
| `unrate` | fred | public | 1948-01-01 | 2026-10-01 | 945 | 55 |  | 0 |  | ok |
| `ecb_assets` | fred | public | 1999-01-01 | 2026-11-20 | 1456 | 5 |  | 0 |  | ok |
| `boj_assets` | fred | public | 1998-04-01 | 2026-10-01 | 343 | 55 |  | 0 |  | ok |
| `usd_broad` | fred | public | 2006-01-02 | 2026-11-20 | 5236 | 5 |  | 0 |  | ok |
| `brent` | fred | public | 1987-05-20 | 2026-11-17 | 9132 | 8 |  | 0 |  | ok |
| `wti` | fred | public | 1986-01-02 | 2026-11-17 | 9547 | 8 |  | 0 |  | ok |
| `smh` | prices | restricted | 2000-06-05 | 2026-11-24 | 6659 | 1 |  | 0 | 1 | ok |
| `soxx` | prices | restricted | 2001-07-13 | 2026-11-24 | 6380 | 1 |  | 0 | 1 | ok |
| `nvda` | prices | restricted | 1999-01-22 | 2026-11-24 | 7004 | 1 |  | 0 | 1 | ok |
| `vrt` | prices | restricted | 2018-07-30 | 2026-11-24 | 2093 | 1 |  | 0 |  | ok |
| `ceg` | prices | restricted | 2022-02-02 | 2026-11-24 | 1208 | 1 |  | 0 |  | ok |
| `grid` | prices | restricted | 2009-11-17 | 2026-11-24 | 4281 | 1 |  | 0 |  | ok |
| `igv` | prices | restricted | 2001-07-13 | 2026-11-24 | 6380 | 1 |  | 0 |  | ok |
| `qqq` | prices | restricted | 1999-03-10 | 2026-11-24 | 6972 | 1 |  | 0 |  | ok |
| `spy` | prices | restricted | 1993-01-29 | 2026-11-24 | 8514 | 1 |  | 0 |  | ok |
| `rsp` | prices | restricted | 2003-04-30 | 2026-11-24 | 5932 | 1 |  | 0 |  | ok |
| `hy_oas` | fred | restricted | 2023-11-07 | 2026-11-23 | 798 | 2 |  | 0 |  | ok |
| `ccc_oas` | fred | restricted | 2023-11-07 | 2026-11-23 | 798 | 2 |  | 0 |  | ok |
| `bbb_oas` | fred | restricted | 2023-11-07 | 2026-11-23 | 798 | 2 |  | 0 |  | ok |
| `ig_oas` | fred | restricted | 2023-11-07 | 2026-11-23 | 797 | 2 |  | 0 |  | ok |
| `sloos_ci` | fred | public | 1990-04-01 | 2026-10-01 | 147 | 55 |  | 0 |  | ok |
| `hyg` | prices | restricted | 2007-04-11 | 2026-11-24 | 4939 | 1 |  | 0 |  | ok |
| `jnk` | prices | restricted | 2007-12-04 | 2026-11-24 | 4774 | 1 |  | 0 |  | ok |
| `lqd` | prices | restricted | 2002-07-26 | 2026-11-24 | 6123 | 1 |  | 0 |  | ok |
| `bkln` | prices | restricted | 2011-03-03 | 2026-11-24 | 3957 | 1 |  | 26 |  | ok |
| `crwv` | prices | restricted | 2025-03-28 | 2026-11-24 | 418 | 1 |  | 0 |  | ok |
| `orcl` | prices | restricted | 1990-01-02 | 2026-11-24 | 9293 | 1 |  | 0 |  | ok |
| `vix` | fred | restricted | 1990-01-02 | 2026-11-23 | 9323 | 2 |  | 0 |  | ok |
| `vix3m` | fred | restricted | 2007-12-04 | 2026-11-23 | 4773 | 2 |  | 0 |  | ok |
| `inda` | prices | restricted | 2012-02-03 | 2026-11-24 | 3724 | 1 |  | 0 |  | ok |
| `nifty` | prices | restricted | 2007-09-17 | 2026-11-25 | 4707 | 0 |  | 4 |  | ok |
| `hsi` | prices | restricted | 1990-01-02 | 2026-11-25 | 9107 | 0 |  | 9 |  | ok |
| `kweb` | prices | restricted | 2013-08-01 | 2026-11-24 | 3350 | 1 |  | 0 |  | ok |
| `tchi` | prices | restricted | 2022-02-01 | 2026-11-24 | 1209 | 1 |  | 0 |  | ok |
| `ewy` | prices | restricted | 2000-05-12 | 2026-11-24 | 6674 | 1 |  | 0 |  | ok |
| `ewt` | prices | restricted | 2000-06-23 | 2026-11-24 | 6645 | 1 |  | 120 | 1 | ok |
| `ewj` | prices | restricted | 1996-04-01 | 2026-11-24 | 7713 | 1 |  | 124 |  | ok |
| `ezu` | prices | restricted | 2001-01-02 | 2026-11-24 | 6513 | 1 |  | 124 |  | ok |
| `gld` | prices | restricted | 2004-11-18 | 2026-11-24 | 5539 | 1 |  | 126 |  | ok |
| `tlt` | prices | restricted | 2002-07-26 | 2026-11-24 | 6123 | 1 |  | 124 |  | ok |
| `xlp` | prices | restricted | 1998-12-22 | 2026-11-24 | 7024 | 1 |  | 124 |  | ok |
| `xlu` | prices | restricted | 1998-12-22 | 2026-11-24 | 7024 | 1 |  | 124 |  | ok |
| `iwd` | prices | restricted | 2000-05-26 | 2026-11-24 | 6664 | 1 |  | 126 |  | ok |
| `iwf` | prices | restricted | 2000-05-26 | 2026-11-24 | 6664 | 1 |  | 126 |  | ok |
| `qual` | prices | restricted | 2013-07-18 | 2026-11-24 | 3360 | 1 |  | 126 |  | ok |
