# Data health, 2026-11-18

- Indicators enabled: **80**, with data: **80**
- With data by layer: L1: 41, L2: 21, L3: 11, L4: 0, L5: 7
- Stale: 3 bank_credit, core_pce, m2
- Failing this run: 0 
- Source alerts (failed 3+ runs in a row): none
- Values held out of scoring pending confirmation: 0

| Indicator | Source | Licence | First | Last | Obs | Age (d) | Stale | Revisions | Held | Fetch |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| `m2` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 78 | yes | 27844 |  | ok |
| `fed_assets` | fred | public | 2002-12-18 | 2026-11-11 | 1248 | 7 |  | 0 |  | ok |
| `tga` | fred | public | 2002-12-18 | 2026-11-11 | 1248 | 7 |  | 0 |  | ok |
| `on_rrp` | fred | public | 2003-02-07 | 2026-11-17 | 3369 | 1 |  | 0 |  | ok |
| `bank_reserves` | fred | public | 2002-12-18 | 2026-11-11 | 1248 | 7 |  | 0 |  | ok |
| `bank_credit` | fred | public | 1973-01-03 | 2026-11-04 | 2810 | 14 | yes | 13 |  | ok |
| `business_loans` | fred | public | 1947-01-01 | 2026-10-01 | 958 | 48 |  | 3 |  | ok |
| `nfci` | fred | public | 1971-01-08 | 2026-11-06 | 2914 | 12 |  | 12 |  | ok |
| `anfci` | fred | public | 1971-01-08 | 2026-11-06 | 2914 | 12 |  | 13 |  | ok |
| `stlfsi` | fred | public | 1993-12-31 | 2026-11-06 | 1715 | 12 |  | 11 |  | ok |
| `bill_3m` | fred | public | 1981-09-01 | 2026-11-16 | 11301 | 2 |  | 0 |  | ok |
| `sofr` | fred | public | 2018-04-03 | 2026-11-16 | 2153 | 2 |  | 0 |  | ok |
| `ust_2y` | fred | public | 1976-06-01 | 2026-11-16 | 12611 | 2 |  | 0 |  | ok |
| `ust_10y` | fred | public | 1962-01-02 | 2026-11-16 | 16203 | 2 |  | 0 |  | ok |
| `ust_30y` | fred | public | 1977-02-15 | 2026-11-16 | 12433 | 2 |  | 0 |  | ok |
| `curve_10y2y` | fred | public | 1976-06-01 | 2026-11-17 | 12612 | 1 |  | 0 |  | ok |
| `curve_10y3m` | fred | public | 1982-01-04 | 2026-11-17 | 11221 | 1 |  | 0 |  | ok |
| `real_5y` | fred | public | 2003-01-02 | 2026-11-16 | 5972 | 2 |  | 0 |  | ok |
| `real_10y` | fred | public | 2003-01-02 | 2026-11-16 | 5972 | 2 |  | 0 |  | ok |
| `breakeven_10y` | fred | public | 2003-01-02 | 2026-11-17 | 5973 | 1 |  | 0 |  | ok |
| `real_30y` | fred | public | 2010-02-22 | 2026-11-16 | 4187 | 2 |  | 0 |  | ok |
| `fwd_infl_5y5y` | fred | public | 2003-01-02 | 2026-11-17 | 5973 | 1 |  | 0 |  | ok |
| `term_premium_kw` | fred | public | 1990-01-02 | 2026-11-13 | 9203 | 5 |  | 0 |  | ok |
| `fed_funds` | fred | public | 1954-07-01 | 2026-11-16 | 26437 | 2 |  | 0 |  | ok |
| `fed_deficit` | fred | public | 1980-10-01 | 2026-10-01 | 553 | 48 |  | 0 |  | ok |
| `public_debt` | treasury_fiscal | public | 1993-04-01 | 2026-11-16 | 8435 | 2 |  | 0 |  | ok |
| `tga_daily` | treasury_fiscal | public | 2022-04-18 | 2026-11-16 | 1148 | 2 |  | 0 |  | ok |
| `auction_btc_10y` | treasury_fiscal | public | 1999-11-10 | 2026-10-07 | 278 | 42 |  | 0 |  | ok |
| `auction_btc_30y` | treasury_fiscal | public | 2001-02-08 | 2026-10-08 | 220 | 41 |  | 0 |  | ok |
| `cpi` | alfred | public | 1947-01-01 | 2026-10-01 | 957 | 48 |  | 2148 |  | ok |
| `core_cpi` | alfred | public | 1957-01-01 | 2026-10-01 | 837 | 48 |  | 1424 |  | ok |
| `core_pce` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 78 | yes | 7394 |  | ok |
| `wei` | fred | public | 2008-01-05 | 2026-11-07 | 984 | 11 |  | 1 |  | ok |
| `initial_claims` | fred | public | 1967-01-07 | 2026-11-07 | 3123 | 11 |  | 1 |  | ok |
| `payrolls` | alfred | public | 1939-01-01 | 2026-10-01 | 1054 | 48 |  | 12640 |  | ok |
| `unrate` | fred | public | 1948-01-01 | 2026-10-01 | 945 | 48 |  | 0 |  | ok |
| `ecb_assets` | fred | public | 1999-01-01 | 2026-11-13 | 1455 | 5 |  | 0 |  | ok |
| `boj_assets` | fred | public | 1998-04-01 | 2026-10-01 | 343 | 48 |  | 0 |  | ok |
| `usd_broad` | fred | public | 2006-01-02 | 2026-11-13 | 5231 | 5 |  | 0 |  | ok |
| `brent` | fred | public | 1987-05-20 | 2026-11-11 | 9128 | 7 |  | 0 |  | ok |
| `wti` | fred | public | 1986-01-02 | 2026-11-11 | 9543 | 7 |  | 0 |  | ok |
| `smh` | prices | restricted | 2000-06-05 | 2026-11-17 | 6654 | 1 |  | 0 |  | ok |
| `soxx` | prices | restricted | 2001-07-13 | 2026-11-17 | 6375 | 1 |  | 0 |  | ok |
| `nvda` | prices | restricted | 1999-01-22 | 2026-11-17 | 6999 | 1 |  | 0 |  | ok |
| `vrt` | prices | restricted | 2018-07-30 | 2026-11-17 | 2088 | 1 |  | 0 |  | ok |
| `ceg` | prices | restricted | 2022-02-02 | 2026-11-17 | 1203 | 1 |  | 0 |  | ok |
| `grid` | prices | restricted | 2009-11-17 | 2026-11-17 | 4276 | 1 |  | 0 |  | ok |
| `igv` | prices | restricted | 2001-07-13 | 2026-11-17 | 6375 | 1 |  | 0 |  | ok |
| `qqq` | prices | restricted | 1999-03-10 | 2026-11-17 | 6967 | 1 |  | 0 |  | ok |
| `spy` | prices | restricted | 1993-01-29 | 2026-11-17 | 8509 | 1 |  | 0 |  | ok |
| `rsp` | prices | restricted | 2003-04-30 | 2026-11-17 | 5927 | 1 |  | 0 |  | ok |
| `hy_oas` | fred | restricted | 2023-11-07 | 2026-11-16 | 793 | 2 |  | 0 |  | ok |
| `ccc_oas` | fred | restricted | 2023-11-07 | 2026-11-16 | 793 | 2 |  | 0 |  | ok |
| `bbb_oas` | fred | restricted | 2023-11-07 | 2026-11-16 | 793 | 2 |  | 0 |  | ok |
| `ig_oas` | fred | restricted | 2023-11-07 | 2026-11-16 | 792 | 2 |  | 0 |  | ok |
| `sloos_ci` | fred | public | 1990-04-01 | 2026-10-01 | 147 | 48 |  | 0 |  | ok |
| `hyg` | prices | restricted | 2007-04-11 | 2026-11-17 | 4934 | 1 |  | 0 |  | ok |
| `jnk` | prices | restricted | 2007-12-04 | 2026-11-17 | 4769 | 1 |  | 0 |  | ok |
| `lqd` | prices | restricted | 2002-07-26 | 2026-11-17 | 6118 | 1 |  | 0 |  | ok |
| `bkln` | prices | restricted | 2011-03-03 | 2026-11-17 | 3952 | 1 |  | 0 |  | ok |
| `crwv` | prices | restricted | 2025-03-28 | 2026-11-17 | 413 | 1 |  | 0 |  | ok |
| `orcl` | prices | restricted | 1990-01-02 | 2026-11-17 | 9288 | 1 |  | 0 |  | ok |
| `vix` | fred | restricted | 1990-01-02 | 2026-11-16 | 9318 | 2 |  | 0 |  | ok |
| `vix3m` | fred | restricted | 2007-12-04 | 2026-11-16 | 4768 | 2 |  | 0 |  | ok |
| `inda` | prices | restricted | 2012-02-03 | 2026-11-17 | 3719 | 1 |  | 0 |  | ok |
| `nifty` | prices | restricted | 2007-09-17 | 2026-11-18 | 4703 | 0 |  | 2 |  | ok |
| `hsi` | prices | restricted | 1990-01-02 | 2026-11-18 | 9102 | 0 |  | 5 |  | ok |
| `kweb` | prices | restricted | 2013-08-01 | 2026-11-17 | 3345 | 1 |  | 0 |  | ok |
| `tchi` | prices | restricted | 2022-02-01 | 2026-11-17 | 1204 | 1 |  | 0 |  | ok |
| `ewy` | prices | restricted | 2000-05-12 | 2026-11-17 | 6669 | 1 |  | 0 |  | ok |
| `ewt` | prices | restricted | 2000-06-23 | 2026-11-17 | 6640 | 1 |  | 120 |  | ok |
| `ewj` | prices | restricted | 1996-04-01 | 2026-11-17 | 7708 | 1 |  | 124 |  | ok |
| `ezu` | prices | restricted | 2001-01-02 | 2026-11-17 | 6508 | 1 |  | 124 |  | ok |
| `gld` | prices | restricted | 2004-11-18 | 2026-11-17 | 5534 | 1 |  | 126 |  | ok |
| `tlt` | prices | restricted | 2002-07-26 | 2026-11-17 | 6118 | 1 |  | 124 |  | ok |
| `xlp` | prices | restricted | 1998-12-22 | 2026-11-17 | 7019 | 1 |  | 124 |  | ok |
| `xlu` | prices | restricted | 1998-12-22 | 2026-11-17 | 7019 | 1 |  | 124 |  | ok |
| `iwd` | prices | restricted | 2000-05-26 | 2026-11-17 | 6659 | 1 |  | 126 |  | ok |
| `iwf` | prices | restricted | 2000-05-26 | 2026-11-17 | 6659 | 1 |  | 126 |  | ok |
| `qual` | prices | restricted | 2013-07-18 | 2026-11-17 | 3355 | 1 |  | 126 |  | ok |
