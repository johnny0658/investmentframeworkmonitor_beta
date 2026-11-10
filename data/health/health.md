# Data health, 2026-11-10

- Indicators enabled: **80**, with data: **80**
- With data by layer: L1: 41, L2: 21, L3: 11, L4: 0, L5: 7
- Stale: 1 bank_credit
- Failing this run: 0 
- Source alerts (failed 3+ runs in a row): none
- Values held out of scoring pending confirmation: 31

| Indicator | Source | Licence | First | Last | Obs | Age (d) | Stale | Revisions | Held | Fetch |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| `m2` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 70 |  | 27844 |  | ok |
| `fed_assets` | fred | public | 2002-12-18 | 2026-11-04 | 1247 | 6 |  | 0 |  | ok |
| `tga` | fred | public | 2002-12-18 | 2026-11-04 | 1247 | 6 |  | 0 |  | ok |
| `on_rrp` | fred | public | 2003-02-07 | 2026-11-09 | 3364 | 1 |  | 0 |  | ok |
| `bank_reserves` | fred | public | 2002-12-18 | 2026-11-04 | 1247 | 6 |  | 0 |  | ok |
| `bank_credit` | fred | public | 1973-01-03 | 2026-10-28 | 2809 | 13 | yes | 0 |  | ok |
| `business_loans` | fred | public | 1947-01-01 | 2026-09-01 | 957 | 70 |  | 0 |  | ok |
| `nfci` | fred | public | 1971-01-08 | 2026-10-30 | 2913 | 11 |  | 0 |  | ok |
| `anfci` | fred | public | 1971-01-08 | 2026-10-30 | 2913 | 11 |  | 0 |  | ok |
| `stlfsi` | fred | public | 1993-12-31 | 2026-10-30 | 1714 | 11 |  | 0 |  | ok |
| `bill_3m` | fred | public | 1981-09-01 | 2026-11-06 | 11296 | 4 |  | 0 |  | ok |
| `sofr` | fred | public | 2018-04-03 | 2026-11-06 | 2148 | 4 |  | 0 |  | ok |
| `ust_2y` | fred | public | 1976-06-01 | 2026-11-06 | 12606 | 4 |  | 0 |  | ok |
| `ust_10y` | fred | public | 1962-01-02 | 2026-11-06 | 16198 | 4 |  | 0 |  | ok |
| `ust_30y` | fred | public | 1977-02-15 | 2026-11-06 | 12428 | 4 |  | 0 |  | ok |
| `curve_10y2y` | fred | public | 1976-06-01 | 2026-11-09 | 12607 | 1 |  | 0 |  | ok |
| `curve_10y3m` | fred | public | 1982-01-04 | 2026-11-09 | 11216 | 1 |  | 0 |  | ok |
| `real_5y` | fred | public | 2003-01-02 | 2026-11-06 | 5967 | 4 |  | 0 |  | ok |
| `real_10y` | fred | public | 2003-01-02 | 2026-11-06 | 5967 | 4 |  | 0 |  | ok |
| `breakeven_10y` | fred | public | 2003-01-02 | 2026-11-09 | 5968 | 1 |  | 0 |  | ok |
| `real_30y` | fred | public | 2010-02-22 | 2026-11-06 | 4182 | 4 |  | 0 |  | ok |
| `fwd_infl_5y5y` | fred | public | 2003-01-02 | 2026-11-09 | 5968 | 1 |  | 0 |  | ok |
| `term_premium_kw` | fred | public | 1990-01-02 | 2026-10-30 | 9194 | 11 |  | 0 |  | ok |
| `fed_funds` | fred | public | 1954-07-01 | 2026-11-06 | 26427 | 4 |  | 0 |  | ok |
| `fed_deficit` | fred | public | 1980-10-01 | 2026-09-01 | 552 | 70 |  | 0 |  | ok |
| `public_debt` | treasury_fiscal | public | 1993-04-01 | 2026-11-06 | 8430 | 4 |  | 0 |  | ok |
| `tga_daily` | treasury_fiscal | public | 2022-04-18 | 2026-11-06 | 1143 | 4 |  | 0 |  | ok |
| `auction_btc_10y` | treasury_fiscal | public | 1999-11-10 | 2026-10-07 | 278 | 34 |  | 0 |  | ok |
| `auction_btc_30y` | treasury_fiscal | public | 2001-02-08 | 2026-10-08 | 220 | 33 |  | 0 |  | ok |
| `cpi` | alfred | public | 1947-01-01 | 2026-09-01 | 956 | 70 |  | 2148 |  | ok |
| `core_cpi` | alfred | public | 1957-01-01 | 2026-09-01 | 836 | 70 |  | 1424 |  | ok |
| `core_pce` | alfred | public | 1959-01-01 | 2026-09-01 | 813 | 70 |  | 7394 |  | ok |
| `wei` | fred | public | 2008-01-05 | 2026-10-31 | 983 | 10 |  | 0 |  | ok |
| `initial_claims` | fred | public | 1967-01-07 | 2026-10-31 | 3122 | 10 |  | 0 |  | ok |
| `payrolls` | alfred | public | 1939-01-01 | 2026-10-01 | 1054 | 40 |  | 12640 |  | ok |
| `unrate` | fred | public | 1948-01-01 | 2026-10-01 | 945 | 40 |  | 0 |  | ok |
| `ecb_assets` | fred | public | 1999-01-01 | 2026-10-30 | 1453 | 11 |  | 0 |  | ok |
| `boj_assets` | fred | public | 1998-04-01 | 2026-10-01 | 343 | 40 |  | 0 |  | ok |
| `usd_broad` | fred | public | 2006-01-02 | 2026-11-06 | 5227 | 4 |  | 0 |  | ok |
| `brent` | fred | public | 1987-05-20 | 2026-11-03 | 9122 | 7 |  | 0 |  | ok |
| `wti` | fred | public | 1986-01-02 | 2026-11-03 | 9537 | 7 |  | 0 |  | ok |
| `smh` | prices | restricted | 2000-06-05 | 2026-11-09 | 6648 | 1 |  | 0 | 1 | ok |
| `soxx` | prices | restricted | 2001-07-13 | 2026-11-09 | 6369 | 1 |  | 0 | 1 | ok |
| `nvda` | prices | restricted | 1999-01-22 | 2026-11-09 | 6993 | 1 |  | 0 |  | ok |
| `vrt` | prices | restricted | 2018-07-30 | 2026-11-09 | 2082 | 1 |  | 0 |  | ok |
| `ceg` | prices | restricted | 2022-02-02 | 2026-11-09 | 1197 | 1 |  | 0 |  | ok |
| `grid` | prices | restricted | 2009-11-17 | 2026-11-09 | 4270 | 1 |  | 0 | 1 | ok |
| `igv` | prices | restricted | 2001-07-13 | 2026-11-09 | 6369 | 1 |  | 0 |  | ok |
| `qqq` | prices | restricted | 1999-03-10 | 2026-11-09 | 6961 | 1 |  | 0 | 1 | ok |
| `spy` | prices | restricted | 1993-01-29 | 2026-11-09 | 8503 | 1 |  | 0 | 1 | ok |
| `rsp` | prices | restricted | 2003-04-30 | 2026-11-09 | 5921 | 1 |  | 0 |  | ok |
| `hy_oas` | fred | restricted | 2023-11-07 | 2026-11-06 | 787 | 4 |  | 0 |  | ok |
| `ccc_oas` | fred | restricted | 2023-11-07 | 2026-11-06 | 787 | 4 |  | 0 |  | ok |
| `bbb_oas` | fred | restricted | 2023-11-07 | 2026-11-06 | 787 | 4 |  | 0 |  | ok |
| `ig_oas` | fred | restricted | 2023-11-07 | 2026-11-06 | 786 | 4 |  | 0 |  | ok |
| `sloos_ci` | fred | public | 1990-04-01 | 2026-10-01 | 147 | 40 |  | 0 |  | ok |
| `hyg` | prices | restricted | 2007-04-11 | 2026-11-09 | 4928 | 1 |  | 0 |  | ok |
| `jnk` | prices | restricted | 2007-12-04 | 2026-11-09 | 4763 | 1 |  | 0 |  | ok |
| `lqd` | prices | restricted | 2002-07-26 | 2026-11-09 | 6112 | 1 |  | 0 |  | ok |
| `bkln` | prices | restricted | 2011-03-03 | 2026-11-09 | 3946 | 1 |  | 0 |  | ok |
| `crwv` | prices | restricted | 2025-03-28 | 2026-11-09 | 407 | 1 |  | 0 |  | ok |
| `orcl` | prices | restricted | 1990-01-02 | 2026-11-09 | 9282 | 1 |  | 0 |  | ok |
| `vix` | fred | restricted | 1990-01-02 | 2026-11-06 | 9312 | 4 |  | 0 |  | ok |
| `vix3m` | fred | restricted | 2007-12-04 | 2026-11-06 | 4762 | 4 |  | 0 |  | ok |
| `inda` | prices | restricted | 2012-02-03 | 2026-11-09 | 3713 | 1 |  | 0 |  | ok |
| `nifty` | prices | restricted | 2007-09-17 | 2026-11-09 | 4697 | 1 |  | 1 |  | ok |
| `hsi` | prices | restricted | 1990-01-02 | 2026-11-10 | 9096 | 0 |  | 0 |  | ok |
| `kweb` | prices | restricted | 2013-08-01 | 2026-11-09 | 3339 | 1 |  | 0 |  | ok |
| `tchi` | prices | restricted | 2022-02-01 | 2026-11-09 | 1198 | 1 |  | 0 |  | ok |
| `ewy` | prices | restricted | 2000-05-12 | 2026-11-09 | 6663 | 1 |  | 0 |  | ok |
| `ewt` | prices | restricted | 2000-06-23 | 2026-11-09 | 6634 | 1 |  | 120 | 13 | ok |
| `ewj` | prices | restricted | 1996-04-01 | 2026-11-09 | 7702 | 1 |  | 124 | 1 | ok |
| `ezu` | prices | restricted | 2001-01-02 | 2026-11-09 | 6502 | 1 |  | 124 |  | ok |
| `gld` | prices | restricted | 2004-11-18 | 2026-11-09 | 5528 | 1 |  | 126 | 4 | ok |
| `tlt` | prices | restricted | 2002-07-26 | 2026-11-09 | 6112 | 1 |  | 124 |  | ok |
| `xlp` | prices | restricted | 1998-12-22 | 2026-11-09 | 7013 | 1 |  | 124 | 2 | ok |
| `xlu` | prices | restricted | 1998-12-22 | 2026-11-09 | 7013 | 1 |  | 124 |  | ok |
| `iwd` | prices | restricted | 2000-05-26 | 2026-11-09 | 6653 | 1 |  | 126 | 2 | ok |
| `iwf` | prices | restricted | 2000-05-26 | 2026-11-09 | 6653 | 1 |  | 126 | 3 | ok |
| `qual` | prices | restricted | 2013-07-18 | 2026-11-09 | 3349 | 1 |  | 126 | 1 | ok |
