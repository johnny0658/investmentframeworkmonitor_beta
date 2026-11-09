# PRD: Investment Framework Monitor

Nov 8, 2026 · @Jun Hao

## Overview

Build a daily monitor that turns my five-layer investment framework into scored indicators, scenario probabilities and alerts, using only free public data. It extends my existing crash-tracker repo rather than replacing it.

**Problem.** My framework names the right forces but is checked by gut feel, irregularly, and mixes up direction with what is priced in. I need one place that refreshes every US trading day, shows each framework row's state, and tells me when the odds of my scenarios change.

**Goals**

1. Track 40 to 60 public indicators mapped to the five framework layers, refreshed automatically after each US close.
2. Score every framework row from −2 (strongly bearish for risk assets) to +2 (strongly bullish), with a confidence level.
3. Maintain probabilities for four scenarios (A orderly AI de-rating, B AI capex bust, C AI credit event, D stagflation, plus a base case) and update them with explicit likelihood ratios.
4. Record my judgement calls and thesis entries so I can compare what I believed with what happened.
5. Alert me by GitHub issue and email when a signpost threshold trips or a scenario probability moves more than 10 points in a week.

**Non-goals**

- No trade execution, broker connection or order generation.
- No paid data feeds in v1 (no Bloomberg, EPFR, CDS feeds, options chains beyond free delayed data).
- No machine-learning forecasts. Scores are transparent rules plus my overrides.
- Not investment advice; it is a personal decision-support tool.

**Relationship to the crash tracker.** The existing repo already runs at each US close, publishes a web dashboard, CSV history and an Excel tracker, and raises GitHub issues that email me. This monitor adds a framework module inside that repo: the same scheduler, storage and alert path, plus new indicator, scoring, scenario and thesis components. The current crash signals become the Layer 4 (catalysts and signposts) feed.

**Users.** Me, as the only operator. The repo is public, so anything committed is visible to everyone (see Data quality, licensing and testing).

## Framework model

The monitor is organised by the five layers from the framework review. Every indicator belongs to exactly one row, and every row to one layer; layers 3 to 5 are new, so most of the build effort beyond the existing crash tracker sits there.

&#91;embedded content: framework model · 5 layers, 21 rows\]

Each row produces a score from −2 to +2 and a confidence; the five layers feed one set of scenario probabilities.

## Data sources by framework row

Every row can be fed from free public data, with FRED as the backbone. Three gaps have no good free source: fund flows (EPFR), credit default swaps, and live rate-futures odds. The monitor uses proxies for these and marks them as proxies. Series IDs are FRED unless stated; the build must verify each ID, unit and history length on first run.

### Layer 1: Regime

| Row | Indicator | Source and series / endpoint | Freq | Notes |
| --- | --- | --- | --- | --- |
| US liquidity | M2, level and 3-month annualised growth | FRED `M2SL`; ALFRED for vintages | Monthly | Revised after release; store vintages |
| US liquidity | Net Fed liquidity = Fed assets − Treasury General Account − overnight reverse repo | FRED `WALCL`, `WTREGEN`, `RRPONTSYD` | Weekly / daily | Normalise units (millions vs billions) before subtracting |
| US liquidity | Bank reserves | FRED `WRESBAL` | Weekly |  |
| US liquidity | Bank credit growth (credit impulse proxy) | FRED `TOTBKCR`, `BUSLOANS` (Fed H.8) | Weekly | Impulse = change in 13-week credit growth |
| US liquidity | Financial conditions and stress | FRED `NFCI`, `ANFCI`, `STLFSI4` | Weekly | Positive NFCI = tighter than average |
| Rates and debt | Short-term rates: 3-month bill and SOFR | FRED `DGS3MO`, `SOFR` | Daily | The cash yield stocks compete with; SOFR sets floating-rate loan costs |
| Rates and debt | 2y, 10y, 30y yields; curve | FRED `DGS2`, `DGS10`, `DGS30`, `T10Y2Y`, `T10Y3M` | Daily |  |
| Rates and debt | Real yields and breakevens | FRED `DFII5`, `DFII10`, `T10YIE` | Daily |  |
| Rates and debt | 30-year real yield and long-run inflation expectations | FRED `DFII30`, `T5YIFR` (5-year, 5-year forward breakeven) | Daily | Cleanest gauges of long-run inflation fear; ties to the US debt thesis |
| Rates and debt | 10y term premium | FRED `THREEFYTP10` (Kim-Wright); NY Fed ACM CSV | Daily | Two models; show both |
| Rates and debt | Deficit, debt and Treasury cash | [Treasury Fiscal Data API](https://fiscaldata.treasury.gov/api-documentation/) (Monthly and Daily Treasury Statements, debt to the penny) | Daily / monthly | Free, no key |
| Rates and debt | Auction demand (bid-to-cover, tail) | Treasury Fiscal Data auction results | Per auction | Weak long-bond auctions feed term premium |
| Rates and debt | Rate expectations | [Atlanta Fed Market Probability Tracker](https://www.atlantafed.org/cenfis/market-probability-tracker); FRED `DFF` | Daily | CME FedWatch has no free API; do not scrape |
| Global liquidity and inflation | US inflation | FRED `CPIAUCSL`, `CPILFESL`, `PCEPILFE`; Cleveland Fed inflation nowcast | Monthly / daily |  |
| Global liquidity and inflation | Growth nowcasts | Atlanta Fed GDPNow; FRED `WEI` (NY Fed Weekly Economic Index), `ICSA`, `PAYEMS`, `UNRATE` | Weekly / monthly |  |
| Global liquidity and inflation | Other central bank balance sheets | FRED `ECBASSETSW`, `JPNASSETS`; ECB Data Portal API | Weekly / monthly | China data is patchy; mark low confidence |
| Global liquidity and inflation | Dollar | FRED `DTWEXBGS` (broad dollar index) | Daily |  |
| Global liquidity and inflation | Oil | FRED `DCOILBRENTEU`, `DCOILWTICO`; [EIA API](https://www.eia.gov/opendata/) | Daily |  |
| Global liquidity and inflation | Global leading indicators | OECD Composite Leading Indicators (OECD Data API) | Monthly | Free substitute for paid PMIs |

### Layer 2: Structural themes

| Row | Indicator | Source and series / endpoint | Freq | Notes |
| --- | --- | --- | --- | --- |
| AI stack | Hyperscaler capex (Microsoft, Alphabet, Amazon, Meta, Oracle) | [SEC EDGAR XBRL API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) `companyconcept` for `PaymentsToAcquirePropertyPlantAndEquipment` | Quarterly | Free; requires a descriptive User-Agent; reuses aibubble.info work |
| AI stack | Chip demand | TSMC monthly revenue (investor relations page); Korea semiconductor exports (Korea Customs Service / KITA releases) | Monthly / 10-day | Manual or light scraping; check terms |
| AI stack | Power demand | EIA API (electricity sales, generation); LBNL "Queued Up" interconnection queue | Monthly / annual |  |
| AI stack | AI beta and relative strength | Daily prices for SMH, SOXX, NVDA, VRT, CEG, GRID, XLU, IGV, QQQ, SPY, RSP | Daily | Computed in-house (see Scoring engine) |
| AI bottlenecks and credit | Credit spreads: high yield, CCC, BBB, investment grade | FRED `BAMLH0A0HYM2`, `BAMLH0A3HYC`, `BAMLC0A4CBBB`, `BAMLC0A0CM` (ICE BofA) | Daily | ICE licence limits history and redistribution; see licensing |
| AI bottlenecks and credit | Credit ETF prices and AI-credit proxies | HYG, JNK, LQD, BKLN; CRWV, ORCL equity as stress proxies | Daily | Free CDS data does not exist; proxy only |
| AI bottlenecks and credit | Bank lending standards | FRED `DRTSCILM` (Senior Loan Officer survey) | Quarterly |  |
| Tech competitiveness | Frontier AI capability and compute | Epoch AI public datasets; Stanford AI Index | Irregular | Manual quarterly update |
| Value capture and tax | Corporate tax rates; governance | OECD Corporate Tax Statistics; World Bank Worldwide Governance Indicators | Annual | Manual |
| Value capture and tax | Shareholder payouts | S&P Dow Jones Indices quarterly buyback and dividend releases | Quarterly | Manual |
| Future tech | Research and developer momentum | arXiv API (papers by category), GitHub search API, USPTO PatentsView API | Weekly | Google Trends via `pytrends` is unofficial; optional |

### Layer 3: Pricing (what is priced in)

| Row | Indicator | Source and series / endpoint | Freq | Notes |
| --- | --- | --- | --- | --- |
| Valuations | S&P 500 forward P/E, earnings revisions | FactSet Earnings Insight (free weekly PDF); S&P DJI `sp-500-eps-est.xlsx` | Weekly | Parse PDF or enter manually |
| Valuations | Equity risk premium | Damodaran implied ERP (NYU Stern, monthly); computed earnings yield − `DFII10` | Monthly / daily |  |
| Valuations | Long-run valuation | Shiller CAPE data | Monthly |  |
| Options pricing | VIX, VIX9D, VIX3M, VIX6M, SKEW, put/call | Cboe historical index CSVs; FRED `VIXCLS`, `VXVCLS` | Daily | Term structure: VIX ÷ VIX3M |
| Positioning | Futures positioning (S&P, Nasdaq, Treasuries, dollar) | CFTC Commitments of Traders, Traders in Financial Futures (CFTC Public Reporting API) | Weekly |  |
| Positioning | Sentiment | AAII Sentiment Survey; NAAIM Exposure Index | Weekly | Check AAII download terms |
| Positioning | Leverage and short interest | FINRA margin statistics; FINRA equity short interest | Monthly / twice monthly |  |
| Capital flows | Money market fund assets | ICI weekly money market fund report | Weekly |  |
| Capital flows | Cross-border flows into US assets | Treasury International Capital (TIC) data | Monthly | 6-week lag |
| Capital flows | India foreign portfolio flows | NSDL FPI daily data | Daily | Prefer NSDL over NSE pages, which block scrapers |
| Capital flows | Hong Kong southbound flows, short-selling share | HKEX Stock Connect and short-selling daily statistics | Daily |  |
| Capital flows | Regional index performance | Prices for INDA, ^NSEI, ^HSI, KWEB, TCHI, EWY, EWT, EWJ, EZU | Daily |  |

### Layer 4: Catalysts and signposts

| Row | Indicator | Source and series / endpoint | Freq | Notes |
| --- | --- | --- | --- | --- |
| Calendar | FOMC dates, data releases | federalreserve.gov FOMC calendar; BLS and BEA release schedules | As published | Drives "days to next catalyst" |
| Calendar | Earnings dates for watched names | Company IR pages; free earnings calendars | Weekly | Manual fallback |
| Policy | AI, data-centre and permitting legislation | [Congress.gov API](https://api.congress.gov/) (free key); Federal Register API | Daily | Keyword watchlist |
| Crash signals | Existing crash-tracker outputs | Current repo | Daily | Reused as-is |

### Layer 5: Expression and risk

| Row | Indicator | Source and series / endpoint | Freq | Notes |
| --- | --- | --- | --- | --- |
| Portfolio | Positions, cost, option legs | Manual `positions.yaml` (from moomoo export) | On change | Public repo: see licensing on what to publish |
| Portfolio | Scenario payoffs, correlation, drawdown | Computed from prices and positions | Daily |  |
| Defensives | Gold, long Treasuries, staples, utilities, value vs growth | GLD, TLT, XLP, XLU, IWD vs IWF, QUAL prices | Daily | Gold is not on FRED any more; use GLD |
| Defensives | Stock–bond correlation | Computed: 60-day rolling correlation of SPY and TLT daily returns | Daily | Sign flip is a regime signal |

**Price data provider.** Use [Tiingo](https://www.tiingo.com/) (free key, licensed end-of-day data) or Stooq CSVs as primary, with `yfinance` only as a fallback: it is unofficial and can break without notice.

## Judgement and probabilities per row

Data tells me *what is*; each row also needs a judgement about *what it means* and a probability about *what happens next*. The monitor keeps these three apart: data is fetched, judgements are entered by me with a confidence, and probabilities are stored with a date so they can be scored later.

Three rules apply to every row:

1. **State the probability as a number** (for example "35% chance high-yield spreads exceed 450bp by 30 June 2027"), never as "likely".
2. **Anchor on a base rate first**, then adjust. The base rate is how often this has happened historically in similar conditions.
3. **Score yourself.** Every probability gets a resolution date; the monitor computes a Brier score (mean squared error of probabilities, lower is better) so I can see whether my 70% calls come true about 70% of the time.

| Row | Judgement call I must make | Probabilities to estimate | Base-rate anchor | Common error to guard against |
| --- | --- | --- | --- | --- |
| US liquidity | Is liquidity a tailwind or a headwind for risk appetite over 3 to 6 months? | P(net Fed liquidity higher in 3 months); P(financial conditions tighten past their 1-year average) | Share of past 3-month windows with rising net liquidity since 2020 | Reading M2 levels as buying power (Myth 1) |
| Rates and debt | Are yields moving on growth, on inflation, or on supply and term premium? | P(Fed hikes at next meeting) from the Atlanta Fed tracker; P(10y above a set level by date) | Market-implied odds; historical 6-month 10y range | Using levels instead of real yields and surprises |
| Tech competitiveness | Will the US keep capturing most AI profits, and does the price already assume it? | P(US share of global market cap falls by 3+ points in 12 months) | Historical drift of the US share | Equating best technology with best investment (Myth 6) |
| Global liquidity and inflation | Which regime box are we in, and which box are we moving to? | P(each of the four regime boxes in 6 months), summing to 100% | Frequency of each box since 1970, by growth and inflation trend | Treating all inflation as good for stocks (Myth 3) |
| Capital flows | Are flows leading price, or chasing it? | P(this week's top-inflow market outperforms over the next 4 weeks) | Historical hit rate of flow momentum | Mistaking a short squeeze or oil move for a structural shift |
| Value capture and tax | Is a market's shareholder treatment improving or worsening? | P(policy change that cuts payout or raises tax by date) | Frequency of such changes per decade | Ideological framing over measurable payout and governance data |
| AI vs non-AI | How much hidden AI exposure does each holding carry? | None directly; measured as AI beta with a confidence band | Rolling 120-day regression | Trusting sector labels (Myth 8) |
| AI bottlenecks and credit | Where is the binding constraint now, and is it priced in? Is credit stress idiosyncratic or spreading? | P(high-yield OAS above 450bp within 12 months); P(a large AI-infrastructure borrower defaults or restructures within 12 months) | High-yield spread episodes since 1997; default rates by rating | Ignoring how much of the bottleneck the price already reflects |
| Future tech | Which frontier has real adoption rather than hype? | P(this theme has investable listed exposure within 3 years) | Historical survival of hyped themes | Lottery-ticket sizing (Myth 9) |
| Defensives / lost decade | Which defensive works in the regime I expect? | P(stock–bond correlation stays positive for 6 months) | Share of years since 1970 with positive correlation | Choosing one hedge for two opposite regimes (Myth 7) |

**Scenario probabilities.** On top of the row-level calls, I keep one set of probabilities across the scenarios below, always summing to 100%. The defaults are placeholders for me to overwrite on first run, not forecasts:

| Scenario | What it means | Default prior |
| --- | --- | --- |
| Base | AI spending continues, growth holds, no credit stress | 45% |
| A | Orderly AI de-rating: valuations compress, economy and credit hold | 25% |
| B | AI capex bust: hyperscalers cut spending, US slows | 12% |
| C | AI credit event: data-centre debt reprices, spreads blow out | 8% |
| D | Stagflation: AI scare plus oil spike plus Fed hikes | 10% |

## Scoring and scenario probability engine

The engine is plain arithmetic in three steps: indicators become standardised signals, signals roll up into row scores, and tripped signposts move scenario probabilities by likelihood ratios. Every number on the dashboard must be traceable back to its inputs.

### Step 1: Indicator signal

Each indicator gets a z-score against its own trailing 3-year history (or 10 years for monthly series), multiplied by a direction sign from config (+1 if higher is good for risk assets, −1 if bad), then clipped to ±2.

```latex
s_i = \mathrm{clip}\left( d_i \cdot \frac{x_i - \mu_i}{\sigma_i},\ -2,\ 2 \right)
```

For series where the change matters more than the level (M2, net liquidity, credit), the transform in config is applied first: `level`, `yoy`, `ann_3m` (3-month annualised), `diff_4w`, or `pct_rank` (percentile against history, mapped to −2…+2).

### Step 2: Row score and confidence

Row score = weighted mean of its indicator signals, weights from config. Confidence (0 to 1) = freshness × agreement:

- **Freshness** = share of the row's weight whose data arrived within its expected window (a monthly series older than 45 days counts as stale).
- **Agreement** = 1 − (standard deviation of the row's signals ÷ 2), floored at 0.

I can set a manual override for any row in `judgements.yaml` (score, confidence, reason, expiry date). The dashboard shows the computed score, my override and the gap between them. An override past its expiry is dropped and flagged.

### Step 3: Scenario probabilities

Each signpost has a condition and a likelihood ratio (LR) per scenario: how much more likely the condition is in that scenario than on average. When a signpost is active, the engine multiplies each scenario's probability by its LR and renormalises.

```latex
P'(S_k) = \frac{P(S_k) \prod_{f} L_f(S_k)}{\sum_j P(S_j) \prod_{f} L_f(S_j)}
```

Two guards stop the probabilities from running away:

1. **Family cap.** Signposts are grouped into families (credit, rates, AI fundamentals, oil, flows). Within a family only the strongest LR per scenario counts, because correlated signals are not independent evidence.
2. **Shrinkage.** Each weekly update blends back toward my last confirmed priors: final = 0.8 × posterior + 0.2 × prior. The engine proposes; I confirm by editing `scenarios.yaml`, which becomes the new prior.

**Starter signposts.** Default LRs are illustrative and must be tuned by me before use.

| Signpost | Family | Condition | LR Base | LR A | LR B | LR C | LR D |
| --- | --- | --- | --- | --- | --- | --- | --- |
| High-yield stress | Credit | `BAMLH0A0HYM2` > 400bp | 0.5 | 0.9 | 1.5 | 3.0 | 1.5 |
| High-yield crisis | Credit | `BAMLH0A0HYM2` > 500bp | 0.2 | 0.6 | 1.5 | 5.0 | 1.5 |
| CCC blowout | Credit | `BAMLH0A3HYC` > 1,500bp | 0.4 | 0.8 | 1.3 | 3.0 | 1.3 |
| Investment-grade drift | Credit | `BAMLC0A0CM` > 110bp | 0.6 | 1.0 | 1.4 | 2.0 | 1.3 |
| Vol inversion | Volatility | VIX ÷ VIX3M > 1.0 for 3 days | 0.6 | 1.3 | 1.3 | 2.0 | 1.3 |
| Bonds stop hedging | Rates | 60-day SPY–TLT correlation > +0.3 | 0.9 | 0.9 | 0.8 | 0.8 | 2.5 |
| Oil shock | Oil | Brent > $110 | 0.8 | 0.8 | 0.9 | 1.0 | 3.0 |
| Hike priced | Rates | Next-meeting hike probability > 70% | 0.9 | 1.2 | 0.8 | 1.1 | 1.8 |
| Real yield squeeze | Rates | `DFII10` > 2.5% | 0.8 | 1.6 | 1.2 | 1.4 | 1.3 |
| Long-end break | Rates | `DGS10` > 5.0% for 3 days | 0.7 | 1.4 | 0.9 | 1.3 | 2.0 |
| Bear steepener | Rates | `T10Y2Y` up > 40bp in 60 days while `DGS10` rises | 0.8 | 1.2 | 0.9 | 1.2 | 2.0 |
| Term premium jump | Rates | `THREEFYTP10` up > 50bp in 63 trading days | 0.7 | 1.3 | 1.0 | 1.4 | 2.2 |
| Capex cut | AI fundamentals | Hyperscaler quarterly capex guidance down q/q (2+ firms) | 0.5 | 1.5 | 3.0 | 1.8 | 1.0 |
| Chips lead down | AI fundamentals | SMH ÷ SPY down > 15% in 60 days | 0.6 | 2.0 | 1.6 | 1.6 | 1.0 |
| Laggards decouple | Flows | INDA ÷ QQQ up > 10% in 60 days and HY < 400bp | 0.9 | 2.0 | 1.0 | 0.5 | 0.8 |
| Everything falls | Flows | INDA, ^HSI and QQQ all down > 8% in 20 days | 0.4 | 0.6 | 1.3 | 2.5 | 1.5 |
| Liquidity drain | Liquidity | Net Fed liquidity down > 5% in 13 weeks | 0.7 | 1.1 | 1.2 | 1.6 | 1.3 |

Signposts and LRs live in `signposts.yaml` so I can add, remove or retune them without code changes.

## Functional requirements

Requirements are numbered so Claude Code can reference them in commits and tests. "Must" items are v1; "Should" items can slip to v2.

### Ingestion

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-1 | Must | One fetcher module per source (`fred`, `alfred`, `treasury_fiscal`, `cboe`, `cftc`, `sec_edgar`, `eia`, `prices`, `nsdl`, `hkex`, `atlanta_fed`, `manual`), each exposing `fetch(series, start, end) -> DataFrame`. |
| FR-2 | Must | The indicator catalogue (`indicators.yaml`) is the only place a series is defined: ID, source, endpoint or series code, units, frequency, transform, direction, weight, row, layer, staleness window, licence flag. |
| FR-3 | Must | Incremental fetch: only pull observations after the last stored date, plus a 90-day look-back window to catch revisions. |
| FR-4 | Must | Retries with exponential back-off (3 attempts); a failed source never stops the other fetchers. Failures are logged and shown on the dashboard. |
| FR-5 | Must | API keys (FRED, EIA, Congress.gov, Tiingo) come from GitHub Actions secrets, never from committed files. |
| FR-6 | Should | Manual-entry path: a `manual/*.csv` folder for figures I type in (FactSet forward P/E, TSMC revenue, Korea chip exports, hyperscaler capex guidance). |
| FR-7 | Must | One-off backfill command that loads full available history for every indicator. |

### Storage

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-8 | Must | Bitemporal observations table: `indicator_id, obs_date, value, vintage_date, fetched_at, source`. A revised value is a new row, never an overwrite, so I can reconstruct what I knew on any past date. |
| FR-9 | Must | Storage in DuckDB for computation, with Parquet snapshots committed for history; CSV exports for the dashboard and Excel. |
| FR-10 | Must | Derived tables: `signals`, `row_scores`, `scenario_probs`, `signpost_events`, `alerts`, `theses`, `forecasts`. |

### Computation

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-11 | Must | Implement the three engine steps exactly as specified in the Scoring section, with unit tests on hand-worked examples. |
| FR-12 | Must | Derived indicators: net Fed liquidity, credit impulse, VIX ÷ VIX3M, earnings yield minus real yield, 60-day SPY–TLT correlation, relative-strength ratios, rolling 120-day AI beta per holding versus an equal-weight AI basket (SMH, NVDA, VRT, CEG). |
| FR-13 | Must | Regime classifier: growth trend (GDPNow and WEI vs 6-month average) × inflation trend (core PCE 3-month annualised vs 12-month) gives one of four boxes, shown with my own regime probabilities beside it. |
| FR-14 | Should | Portfolio module: from `positions.yaml`, compute exposure by layer, AI beta of the book, and a payoff estimate for each scenario using simple shock assumptions in `scenarios.yaml`. |
| FR-15 | Must | Forecast scoring: every probability I log carries a resolution date and condition; on resolution the monitor records the outcome and updates my Brier score. |

### Dashboard

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-16 | Must | Static site on GitHub Pages, rebuilt each run. No server. |
| FR-17 | Must | Home view: scenario probabilities (current, 1 week ago, 4 weeks ago), regime box, five layer cards with row scores, confidence and arrows, active signposts, data-health strip. |
| FR-18 | Must | Row view: each indicator's chart (5 years), current z-score, signal, weight, freshness, and my override with reason. |
| FR-19 | Must | Signposts view: each signpost's condition, current value, distance to trigger, and trigger history. |
| FR-20 | Should | Thesis view: open theses from the one-page template, with their signposts and kill-switch status highlighted when tripped. |
| FR-21 | Should | Calibration view: Brier score over time and a reliability chart (my stated probability vs actual hit rate, in 10-point buckets). |
| FR-22 | Must | Every number on the page links to or shows its source and as-of date. |

### Alerts and reporting

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-23 | Must | Open a GitHub issue (which emails me) when: a signpost triggers or clears; any scenario probability moves ≥ 10 points over 5 trading days; a row score crosses ±1; a thesis kill switch trips; a source fails 3 runs in a row. |
| FR-24 | Must | De-duplicate: one open issue per alert key; later runs comment on it instead of opening new ones; close it when the condition clears. |
| FR-25 | Should | Weekly digest issue every Saturday (Singapore time): changes in scenario probabilities, row scores, signposts and upcoming catalysts for the next 10 days. |
| FR-26 | Must | Refresh the existing Excel tracker with new sheets: Rows, Signposts, Scenarios, Theses. |

### Thesis log

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-27 | Must | Each thesis is a Markdown file in `theses/` with YAML front matter matching the ten-point template: regime, thesis, priced in, variant view, earnings link, catalyst and date, expression, size, signposts (indicator IDs and thresholds), kill switch. |
| FR-28 | Must | The monitor validates every thesis file on each run and evaluates its signposts and kill switch. |

## Architecture, repo layout and config

One Python package inside the crash-tracker repo, run by GitHub Actions, writing to DuckDB and Parquet, and publishing a static site to GitHub Pages. No servers, no paid infrastructure.

**Stack.** Python 3.12; `pandas`, `duckdb`, `pyarrow`, `httpx`, `pydantic` (config validation), `pandas_market_calendars` (US holidays), `plotly` (charts in static HTML), `jinja2` (site templates), `openpyxl` (Excel), `pytest`. The GitHub CLI or REST API for issues.

**Schedule.** Two runs per US trading day, skipped on NYSE holidays:

- **Main run** at 22:30 UTC (6:30 am Singapore next day), about 90 minutes after the US close in winter and 150 in summer. Fetches prices, Cboe, Treasury and most FRED series.
- **Catch-up run** at 13:00 UTC for series published the next morning (ICE BofA spreads on FRED, NSDL and HKEX daily data). It recomputes only what changed.
- **Weekly digest** Saturday 01:00 UTC.

**Repo layout**

```text
framework_monitor/
  config/
    indicators.yaml      # one entry per series (FR-2)
    rows.yaml            # framework rows, layers, weights
    signposts.yaml       # conditions, families, likelihood ratios
    scenarios.yaml       # confirmed priors and shock assumptions
    judgements.yaml      # my row overrides with expiry
    positions.yaml       # optional, see licensing
  fetchers/              # one module per source (FR-1)
  engine/
    transforms.py  signals.py  rows.py  scenarios.py  regime.py  portfolio.py  calibration.py
  store/                 # DuckDB access, bitemporal writes (FR-8)
  outputs/
    site/  excel.py  alerts.py  digest.py
  manual/                # hand-entered CSVs (FR-6)
  theses/                # one Markdown file per thesis (FR-27)
  tests/
  cli.py                 # fetch | compute | publish | backfill | alert | run-all
data/
  monitor.duckdb         # gitignored; rebuilt from parquet
  parquet/               # committed history snapshots
.github/workflows/framework-monitor.yml
```

**Config examples**

```yaml
# indicators.yaml
- id: hy_oas
  name: High-yield option-adjusted spread
  source: fred
  series: BAMLH0A0HYM2
  units: percent
  frequency: daily
  transform: level
  direction: -1          # wider spreads are bad for risk assets
  row: ai_bottlenecks_credit
  layer: 2
  weight: 0.30
  stale_after_days: 4
  licence: restricted    # do not publish raw values
- id: net_fed_liquidity
  name: Net Fed liquidity
  source: derived
  formula: WALCL - WTREGEN - RRPONTSYD*1000   # all in USD millions
  frequency: weekly
  transform: diff_13w_pct
  direction: 1
  row: us_liquidity
  layer: 1
  weight: 0.35
  stale_after_days: 10
  licence: public
```

```yaml
# signposts.yaml
- id: hy_stress
  family: credit
  condition: "hy_oas > 4.00"
  confirm_days: 2
  lr: {base: 0.5, A: 0.9, B: 1.5, C: 3.0, D: 1.5}
```

```yaml
# judgements.yaml
- row: global_liquidity_inflation
  score: -1
  confidence: 0.6
  reason: "Oil back above $100 if Iran talks fail; inflation trend turning up"
  expires: 2026-12-31
```

```yaml
# theses/2026-11-india-rotation.md front matter
id: india-rotation
opened: 2026-11-08
regime_now: goldilocks
regime_bet: deflationary_bust
thesis: "Foreign money keeps rotating from AI-heavy North Asia into India while credit holds"
priced_in: "Nifty at nine-month high after an 8% week; FII flows at multi-year highs"
variant_view: "Rotation persists for 3 months unless high-yield spreads break 400bp"
catalyst: {event: "Hyperscaler Q4 capex guidance", date: 2027-02-05}
expression: "Long INDA"
size_pct: 10
signposts: [{indicator: hy_oas, op: ">", value: 4.0}, {indicator: brent, op: ">", value: 100}]
kill_switch: "INDA falls with QQQ for 10 days while HY OAS > 400bp"
```

## Data quality, licensing and testing

The biggest non-technical risk is licensing: the repo is public, and several free sources forbid redistributing their raw numbers. The monitor must publish scores and signals for those series, not the raw values.

### Licensing rules

| Source | Can the public site show raw values? | Rule for the build |
| --- | --- | --- |
| FRED (Fed, BLS, BEA, Treasury series) | Yes | Cite FRED and the original source |
| ICE BofA spreads on FRED | No | Store raw values outside the public repo; publish z-scores, signals and thresholds crossed only |
| Cboe indices (VIX family, SKEW) | Check terms | Default to derived values only until confirmed |
| FactSet, S&P DJI, Damodaran, Shiller | Limited | Publish derived ratios with citation; no raw table dumps |
| AAII, NAAIM | Check terms | Default to derived values only |
| Tiingo price data | No raw redistribution on the free tier | Publish returns, ratios and charts of indexed series, not price tables |
| SEC EDGAR, Treasury Fiscal Data, CFTC, EIA, Congress.gov | Yes | Public-domain US government data |

Each indicator carries a `licence` flag (`public` or `restricted`). Raw restricted values live in a private store: either a private companion repo or an encrypted GitHub Actions artifact, pulled at the start of each run. The publish step must fail if a restricted raw value would be written to `site/` or committed Parquet.

**Positions.** I chose to make positions public. To limit what that reveals, the site shows weights as a share of the book and option structures by strike as % of spot, not dollar amounts or account size.

### Data quality checks (run every time)

1. **Staleness:** flag any indicator older than its `stale_after_days`; lower the row's confidence.
2. **Range and jumps:** flag a value outside its historical min–max by more than 20%, or a one-day move above 6 standard deviations, and hold it out of scoring until confirmed by the next run.
3. **Units:** assert units match config before any arithmetic (the net liquidity formula mixes millions and billions).
4. **Revisions:** log every revised value with old and new vintage; show revision count per indicator.
5. **Source health:** a source failing three runs in a row raises an alert (FR-23).

### Testing

- **Unit tests** for every transform and for each engine step against hand-worked examples (a two-scenario, three-signpost case with known answer; family cap; shrinkage).
- **Recorded fixtures** for each fetcher (saved API responses), so tests run offline and in CI.
- **Config validation**: pydantic schemas for every YAML file; CI fails on an unknown indicator ID in `rows.yaml`, `signposts.yaml` or a thesis.
- **End-to-end smoke test** on fixtures: fetch → compute → publish produces a site, CSVs and Excel with no restricted raw values.
- **Back-test check**: replay 2020, 2022 and April 2025 from stored history and confirm the signposts and alerts would have fired on the expected days.

### Acceptance criteria for v1

- [ ] The scheduled workflow runs on 10 consecutive trading days with no manual fix.
- [ ] At least 40 indicators populated across all five layers, each showing source and as-of date.
- [ ] Row scores, confidence and scenario probabilities reproduce exactly from a fresh rebuild of stored data.
- [ ] A test signpost forced to trigger opens one GitHub issue, comments on later runs, and closes when cleared.
- [ ] No restricted raw value appears anywhere in the public repo or site (automated check passes).
- [ ] One thesis file validates, displays, and trips its kill switch when its condition is met in a fixture.
- [ ] The Excel tracker opens with the four new sheets populated.

## Milestones, open questions and Claude Code kickoff

Build in five phases, each ending in something that runs on its own. Phase 1 alone already replaces my manual weekly checks.

### Milestones

1. **Phase 1: Data spine.** Config schemas, FRED, ALFRED, Treasury and price fetchers, bitemporal store, backfill, staleness checks. Exit: 25 indicators stored with history and passing quality checks.
2. **Phase 2: Engine.** Transforms, signals, row scores, confidence, overrides, regime classifier, signposts and scenario updates with family cap and shrinkage. Exit: hand-worked tests pass; row scores reproduce from a rebuild.
3. **Phase 3: Outputs.** Static site (home, row, signpost views), CSV and Excel export, GitHub issue alerts with de-duplication, licensing guard. Exit: the 10-day unattended run criterion.
4. **Phase 4: Remaining sources.** Cboe, CFTC, SEC EDGAR capex, EIA, NSDL, HKEX, Congress.gov, manual CSVs. Exit: 40+ indicators across all five layers.
5. **Phase 5: Judgement layer.** Thesis files, forecast logging, Brier score and calibration view, weekly digest, portfolio exposure and scenario payoffs. Exit: all v1 acceptance criteria ticked.

### Open questions

- [ ] Private store for restricted raw data: a private companion repo or encrypted Actions artifacts?
- [ ] Price provider: Tiingo free tier or Stooq as primary?
- [ ] Which positions, if any, should the public site show, and at what level of detail?
- [ ] My first set of scenario priors and signpost likelihood ratios, replacing the defaults.
- [ ] Should the monitor also cover Singapore-specific indicators (SGD, STI, MAS policy)?

### Kickoff prompt for Claude Code

Paste this into Claude Code from the root of the crash-tracker repo, with this PRD saved as `docs/framework-monitor-prd.md`.

```markdown
You are building the "Investment Framework Monitor" described in docs/framework-monitor-prd.md, inside this existing crash-tracker repo.

Before writing code:
1. Read the PRD in full and the current repo (workflows, dashboard, Excel tracker, alert code).
2. Propose how the new framework_monitor package plugs into the existing scheduler, storage and GitHub-issue alerts without breaking them. Wait for my approval.

Then work phase by phase (PRD "Milestones"), one pull request per phase:
- Start with Phase 1 only. Reference requirement IDs (FR-n) in commit messages.
- Every fetcher gets recorded fixtures and tests that run offline.
- Verify each FRED series ID, its units and history length on first fetch; report any that are wrong or discontinued instead of guessing a replacement.
- Never commit API keys; read them from environment variables backed by GitHub Actions secrets.
- Enforce the licensing rules: indicators flagged `licence: restricted` must never have raw values written to site/ or committed Parquet. Add the automated check in Phase 1, not later.
- Keep all scoring logic transparent and configurable through the YAML files; no hidden constants.

At the end of each phase, report: what was built, which acceptance criteria now pass, any data sources that failed or need my decision, and the open questions from the PRD that block the next phase.
```
