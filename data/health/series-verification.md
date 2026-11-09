# FRED series verification, 2026-11-09

44 series checked, 40 OK, 4 with issues.

| Indicator | Series | Source units | Config units | First | Last | Obs | Issues |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| `m2` | M2SL | Billions of Dollars | usd_billions | 1959-01-01 | 2026-09-01 | 813 | OK |
| `fed_assets` | WALCL | Millions of U.S. Dollars | usd_millions | 2002-12-18 | 2026-11-04 | 1247 | OK |
| `tga` | WTREGEN | Millions of U.S. Dollars | usd_millions | 2002-12-18 | 2026-11-04 | 1247 | OK |
| `on_rrp` | RRPONTSYD | Billions of US Dollars | usd_billions | 2003-02-07 | 2026-11-06 | 3363 | OK |
| `bank_reserves` | WRESBAL | Millions of U.S. Dollars | usd_millions | 2002-12-18 | 2026-11-04 | 1247 | OK |
| `bank_credit` | TOTBKCR | Billions of U.S. Dollars | usd_billions | 1973-01-03 | 2026-10-28 | 2809 | OK |
| `business_loans` | BUSLOANS | Billions of U.S. Dollars | usd_billions | 1947-01-01 | 2026-09-01 | 957 | OK |
| `nfci` | NFCI | Index | index | 1971-01-08 | 2026-10-30 | 2913 | OK |
| `anfci` | ANFCI | Index | index | 1971-01-08 | 2026-10-30 | 2913 | OK |
| `stlfsi` | STLFSI4 | Index | index | 1993-12-31 | 2026-10-30 | 1714 | OK |
| `bill_3m` | DGS3MO | Percent | percent | 1981-09-01 | 2026-11-05 | 11295 | OK |
| `sofr` | SOFR | Percent | percent | 2018-04-03 | 2026-11-05 | 2147 | OK |
| `ust_2y` | DGS2 | Percent | percent | 1976-06-01 | 2026-11-05 | 12605 | OK |
| `ust_10y` | DGS10 | Percent | percent | 1962-01-02 | 2026-11-05 | 16197 | OK |
| `ust_30y` | DGS30 | Percent | percent | 1977-02-15 | 2026-11-05 | 12427 | OK |
| `curve_10y2y` | T10Y2Y | Percent | percent | 1976-06-01 | 2026-11-06 | 12606 | OK |
| `curve_10y3m` | T10Y3M | Percent | percent | 1982-01-04 | 2026-11-06 | 11215 | OK |
| `real_5y` | DFII5 | Percent | percent | 2003-01-02 | 2026-11-05 | 5966 | OK |
| `real_10y` | DFII10 | Percent | percent | 2003-01-02 | 2026-11-05 | 5966 | OK |
| `breakeven_10y` | T10YIE | Percent | percent | 2003-01-02 | 2026-11-06 | 5967 | OK |
| `real_30y` | DFII30 | Percent | percent | 2010-02-22 | 2026-11-05 | 4181 | OK |
| `fwd_infl_5y5y` | T5YIFR | Percent | percent | 2003-01-02 | 2026-11-06 | 5967 | OK |
| `term_premium_kw` | THREEFYTP10 | Percent | percent | 1990-01-02 | 2026-10-30 | 9194 | OK |
| `fed_funds` | DFF | Percent | percent | 1954-07-01 | 2026-11-05 | 26426 | OK |
| `fed_deficit` | MTSDS133FMS | Millions of Dollars | usd_millions | 1980-10-01 | 2026-09-01 | 552 | OK |
| `cpi` | CPIAUCSL | Index 1982-1984=100 | index | 1947-01-01 | 2026-09-01 | 956 | OK |
| `core_cpi` | CPILFESL | Index 1982-1984=100 | index | 1957-01-01 | 2026-09-01 | 836 | OK |
| `core_pce` | PCEPILFE | Index 2017=100 | index | 1959-01-01 | 2026-09-01 | 813 | OK |
| `wei` | WEI | Index | index | 2008-01-05 | 2026-10-31 | 983 | OK |
| `initial_claims` | ICSA | Number | count | 1967-01-07 | 2026-10-31 | 3122 | OK |
| `payrolls` | PAYEMS | Thousands of Persons | thousands_persons | 1939-01-01 | 2026-10-01 | 1054 | OK |
| `unrate` | UNRATE | Percent | percent | 1948-01-01 | 2026-10-01 | 945 | OK |
| `ecb_assets` | ECBASSETSW | Millions of Euros | eur_millions | 1999-01-01 | 2026-10-30 | 1453 | OK |
| `boj_assets` | JPNASSETS | 100 Million Yen | jpy_100m | 1998-04-01 | 2026-10-01 | 343 | OK |
| `usd_broad` | DTWEXBGS | Index Jan 2006=100 | index | 2006-01-02 | 2026-10-30 | 5222 | OK |
| `brent` | DCOILBRENTEU | Dollars per Barrel | usd_per_barrel | 1987-05-20 | 2026-11-03 | 9122 | OK |
| `wti` | DCOILWTICO | Dollars per Barrel | usd_per_barrel | 1986-01-02 | 2026-11-03 | 9537 | OK |
| `hy_oas` | BAMLH0A0HYM2 | Percent | percent | 2023-11-07 | 2026-11-05 | 786 | only 3.00 years of history (scoring window needs 3) |
| `ccc_oas` | BAMLH0A3HYC | Percent | percent | 2023-11-07 | 2026-11-05 | 786 | only 3.00 years of history (scoring window needs 3) |
| `bbb_oas` | BAMLC0A4CBBB | Percent | percent | 2023-11-07 | 2026-11-05 | 786 | only 3.00 years of history (scoring window needs 3) |
| `ig_oas` | BAMLC0A0CM | Percent | percent | 2023-11-07 | 2026-11-05 | 785 | only 3.00 years of history (scoring window needs 3) |
| `sloos_ci` | DRTSCILM | Percent | percent | 1990-04-01 | 2026-10-01 | 147 | OK |
| `vix` | VIXCLS | Index | index | 1990-01-02 | 2026-11-05 | 9311 | OK |
| `vix3m` | VXVCLS | Index | index | 2007-12-04 | 2026-11-05 | 4761 | OK |
