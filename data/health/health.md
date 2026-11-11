# Data health, 2026-11-11

- Indicators enabled: **80**, with data: **80**
- With data by layer: L1: 41, L2: 21, L3: 11, L4: 0, L5: 7
- Stale: 1 bank_credit
- Failing this run: 0 
- Source alerts (failed 3+ runs in a row): none
- Values held out of scoring pending confirmation: 0

| Indicator | Source | Licence | First | Last | Obs | Age (d) | Stale | Revisions | Held | Fetch |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| `m2` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 71 |  | 27844 |  | ok |
| `fed_assets` | fred | public | 2002-12-18 | 2026-11-04 | 1247 | 7 |  | 0 |  | ok |
| `tga` | fred | public | 2002-12-18 | 2026-11-04 | 1247 | 7 |  | 0 |  | ok |
| `on_rrp` | fred | public | 2003-02-07 | 2026-11-10 | 3365 | 1 |  | 0 |  | ok |
| `bank_reserves` | fred | public | 2002-12-18 | 2026-11-04 | 1247 | 7 |  | 0 |  | ok |
| `bank_credit` | fred | public | 1973-01-03 | 2026-10-28 | 2809 | 14 | yes | 0 |  | ok |
| `business_loans` | fred | public | 1947-01-01 | 2026-09-01 | 957 | 71 |  | 0 |  | ok |
| `nfci` | fred | public | 1971-01-08 | 2026-10-30 | 2913 | 12 |  | 0 |  | ok |
| `anfci` | fred | public | 1971-01-08 | 2026-10-30 | 2913 | 12 |  | 0 |  | ok |
| `stlfsi` | fred | public | 1993-12-31 | 2026-10-30 | 1714 | 12 |  | 0 |  | ok |
| `bill_3m` | fred | public | 1981-09-01 | 2026-11-09 | 11297 | 2 |  | 0 |  | ok |
| `sofr` | fred | public | 2018-04-03 | 2026-11-09 | 2149 | 2 |  | 0 |  | ok |
| `ust_2y` | fred | public | 1976-06-01 | 2026-11-09 | 12607 | 2 |  | 0 |  | ok |
| `ust_10y` | fred | public | 1962-01-02 | 2026-11-09 | 16199 | 2 |  | 0 |  | ok |
| `ust_30y` | fred | public | 1977-02-15 | 2026-11-09 | 12429 | 2 |  | 0 |  | ok |
| `curve_10y2y` | fred | public | 1976-06-01 | 2026-11-10 | 12608 | 1 |  | 0 |  | ok |
| `curve_10y3m` | fred | public | 1982-01-04 | 2026-11-10 | 11217 | 1 |  | 0 |  | ok |
| `real_5y` | fred | public | 2003-01-02 | 2026-11-09 | 5968 | 2 |  | 0 |  | ok |
| `real_10y` | fred | public | 2003-01-02 | 2026-11-09 | 5968 | 2 |  | 0 |  | ok |
| `breakeven_10y` | fred | public | 2003-01-02 | 2026-11-10 | 5969 | 1 |  | 0 |  | ok |
| `real_30y` | fred | public | 2010-02-22 | 2026-11-09 | 4183 | 2 |  | 0 |  | ok |
| `fwd_infl_5y5y` | fred | public | 2003-01-02 | 2026-11-10 | 5969 | 1 |  | 0 |  | ok |
| `term_premium_kw` | fred | public | 1990-01-02 | 2026-11-06 | 9199 | 5 |  | 0 |  | ok |
| `fed_funds` | fred | public | 1954-07-01 | 2026-11-09 | 26430 | 2 |  | 0 |  | ok |
| `fed_deficit` | fred | public | 1980-10-01 | 2026-09-01 | 552 | 71 |  | 0 |  | ok |
| `public_debt` | treasury_fiscal | public | 1993-04-01 | 2026-11-09 | 8431 | 2 |  | 0 |  | ok |
| `tga_daily` | treasury_fiscal | public | 2022-04-18 | 2026-11-09 | 1144 | 2 |  | 0 |  | ok |
| `auction_btc_10y` | treasury_fiscal | public | 1999-11-10 | 2026-10-07 | 278 | 35 |  | 0 |  | ok |
| `auction_btc_30y` | treasury_fiscal | public | 2001-02-08 | 2026-10-08 | 220 | 34 |  | 0 |  | ok |
| `cpi` | alfred | public | 1947-01-01 | 2026-10-01 | 957 | 41 |  | 2148 |  | ok |
| `core_cpi` | alfred | public | 1957-01-01 | 2026-10-01 | 837 | 41 |  | 1424 |  | ok |
| `core_pce` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 71 |  | 7394 |  | ok |
| `wei` | fred | public | 2008-01-05 | 2026-10-31 | 983 | 11 |  | 0 |  | ok |
| `initial_claims` | fred | public | 1967-01-07 | 2026-10-31 | 3122 | 11 |  | 0 |  | ok |
| `payrolls` | alfred | public | 1939-01-01 | 2026-10-01 | 1054 | 41 |  | 12640 |  | ok |
| `unrate` | fred | public | 1948-01-01 | 2026-10-01 | 945 | 41 |  | 0 |  | ok |
| `ecb_assets` | fred | public | 1999-01-01 | 2026-11-06 | 1454 | 5 |  | 0 |  | ok |
| `boj_assets` | fred | public | 1998-04-01 | 2026-10-01 | 343 | 41 |  | 0 |  | ok |
| `usd_broad` | fred | public | 2006-01-02 | 2026-11-06 | 5227 | 5 |  | 0 |  | ok |
| `brent` | fred | public | 1987-05-20 | 2026-11-03 | 9122 | 8 |  | 0 |  | ok |
| `wti` | fred | public | 1986-01-02 | 2026-11-03 | 9537 | 8 |  | 0 |  | ok |
| `smh` | prices | restricted | 2000-06-05 | 2026-11-10 | 6649 | 1 |  | 0 |  | ok |
| `soxx` | prices | restricted | 2001-07-13 | 2026-11-10 | 6370 | 1 |  | 0 |  | ok |
| `nvda` | prices | restricted | 1999-01-22 | 2026-11-10 | 6994 | 1 |  | 0 |  | ok |
| `vrt` | prices | restricted | 2018-07-30 | 2026-11-10 | 2083 | 1 |  | 0 |  | ok |
| `ceg` | prices | restricted | 2022-02-02 | 2026-11-10 | 1198 | 1 |  | 0 |  | ok |
| `grid` | prices | restricted | 2009-11-17 | 2026-11-10 | 4271 | 1 |  | 0 |  | ok |
| `igv` | prices | restricted | 2001-07-13 | 2026-11-10 | 6370 | 1 |  | 0 |  | ok |
| `qqq` | prices | restricted | 1999-03-10 | 2026-11-10 | 6962 | 1 |  | 0 |  | ok |
| `spy` | prices | restricted | 1993-01-29 | 2026-11-10 | 8504 | 1 |  | 0 |  | ok |
| `rsp` | prices | restricted | 2003-04-30 | 2026-11-10 | 5922 | 1 |  | 0 |  | ok |
| `hy_oas` | fred | restricted | 2023-11-07 | 2026-11-09 | 788 | 2 |  | 0 |  | ok |
| `ccc_oas` | fred | restricted | 2023-11-07 | 2026-11-09 | 788 | 2 |  | 0 |  | ok |
| `bbb_oas` | fred | restricted | 2023-11-07 | 2026-11-09 | 788 | 2 |  | 0 |  | ok |
| `ig_oas` | fred | restricted | 2023-11-07 | 2026-11-09 | 787 | 2 |  | 0 |  | ok |
| `sloos_ci` | fred | public | 1990-04-01 | 2026-10-01 | 147 | 41 |  | 0 |  | ok |
| `hyg` | prices | restricted | 2007-04-11 | 2026-11-10 | 4929 | 1 |  | 0 |  | ok |
| `jnk` | prices | restricted | 2007-12-04 | 2026-11-10 | 4764 | 1 |  | 0 |  | ok |
| `lqd` | prices | restricted | 2002-07-26 | 2026-11-10 | 6113 | 1 |  | 0 |  | ok |
| `bkln` | prices | restricted | 2011-03-03 | 2026-11-10 | 3947 | 1 |  | 0 |  | ok |
| `crwv` | prices | restricted | 2025-03-28 | 2026-11-10 | 408 | 1 |  | 0 |  | ok |
| `orcl` | prices | restricted | 1990-01-02 | 2026-11-10 | 9283 | 1 |  | 0 |  | ok |
| `vix` | fred | restricted | 1990-01-02 | 2026-11-09 | 9313 | 2 |  | 0 |  | ok |
| `vix3m` | fred | restricted | 2007-12-04 | 2026-11-09 | 4763 | 2 |  | 0 |  | ok |
| `inda` | prices | restricted | 2012-02-03 | 2026-11-10 | 3714 | 1 |  | 0 |  | ok |
| `nifty` | prices | restricted | 2007-09-17 | 2026-11-09 | 4697 | 2 |  | 1 |  | ok |
| `hsi` | prices | restricted | 1990-01-02 | 2026-11-11 | 9097 | 0 |  | 1 |  | ok |
| `kweb` | prices | restricted | 2013-08-01 | 2026-11-10 | 3340 | 1 |  | 0 |  | ok |
| `tchi` | prices | restricted | 2022-02-01 | 2026-11-10 | 1199 | 1 |  | 0 |  | ok |
| `ewy` | prices | restricted | 2000-05-12 | 2026-11-10 | 6664 | 1 |  | 0 |  | ok |
| `ewt` | prices | restricted | 2000-06-23 | 2026-11-10 | 6635 | 1 |  | 120 |  | ok |
| `ewj` | prices | restricted | 1996-04-01 | 2026-11-10 | 7703 | 1 |  | 124 |  | ok |
| `ezu` | prices | restricted | 2001-01-02 | 2026-11-10 | 6503 | 1 |  | 124 |  | ok |
| `gld` | prices | restricted | 2004-11-18 | 2026-11-10 | 5529 | 1 |  | 126 |  | ok |
| `tlt` | prices | restricted | 2002-07-26 | 2026-11-10 | 6113 | 1 |  | 124 |  | ok |
| `xlp` | prices | restricted | 1998-12-22 | 2026-11-10 | 7014 | 1 |  | 124 |  | ok |
| `xlu` | prices | restricted | 1998-12-22 | 2026-11-10 | 7014 | 1 |  | 124 |  | ok |
| `iwd` | prices | restricted | 2000-05-26 | 2026-11-10 | 6654 | 1 |  | 126 |  | ok |
| `iwf` | prices | restricted | 2000-05-26 | 2026-11-10 | 6654 | 1 |  | 126 |  | ok |
| `qual` | prices | restricted | 2013-07-18 | 2026-11-10 | 3350 | 1 |  | 126 |  | ok |
