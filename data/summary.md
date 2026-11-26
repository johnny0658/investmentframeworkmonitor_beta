# Framework monitor, as of 2026-11-25

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **12.3%** | 24.7% | 27.6% | 45.0% | 0.26 |
| A: Orderly AI de-rating | **64.2%** | 49.3% | 25.7% | 25.0% | 8.32 |
| B: AI capex bust | **10.9%** | 10.4% | 10.8% | 12.0% | 2.50 |
| C: AI credit event | **6.7%** | 4.7% | 8.8% | 8.0% | 2.24 |
| D: Stagflation | **5.8%** | 10.9% | 27.2% | 10.0% | 1.35 |

## Regime

Classifier: **reflation** (growth up: wei 3.36 vs 6m avg 2.97; core PCE 3m annualised 3.63% vs 12m 3.26% → inflation up)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Vol inversion** (volatility): `vix_term > 1.0`
- **Real yield squeeze** (rates): `real_10y > 2.5`
- **Chips lead down** (ai_fundamentals): `pct_change(smh_spy_ratio, 60) < -0.15`
- **Laggards decouple** (flows): `pct_change(inda_qqq_ratio, 60) > 0.10 and hy_oas < 4.0`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **+0.09** | → | 0.48 | 0.85 | +0.56 | 9 |  |
| 1 | rates_debt | **-0.42** | → | 0.21 | 1.00 | +0.21 | 15 |  |
| 1 | global_liquidity_inflation | **+0.25** | → | 0.46 | 1.00 | +0.46 | 11 |  |
| 2 | ai_stack | **+0.50** | ↓ | 0.66 | 1.00 | +0.66 | 2 |  |
| 2 | ai_bottlenecks_credit | **-1.16** | ↓ | 0.38 | 1.00 | +0.38 | 6 |  |
| 3 | options_pricing | **-2.00** | → | 1.00 | 1.00 | +1.00 | 2 |  |
| 5 | defensives | **+0.92** | ↑ | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | active | 1.035 | 1 | -0.035 |
| Bonds stop hedging | rates | inactive | -0.030 | 0.3 | +0.330 |
| Oil shock | oil | inactive | 91.800 | 110 | +18.200 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.790 | 2.5 | -0.290 |
| Long-end break | rates | inactive | 4.910 | 5 | +0.090 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.041 | 0.5 | +0.459 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | active | -0.178 | -0.15 | -0.028 |
| Laggards decouple | flows | active | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | 0.006 | -0.05 | +0.056 |
