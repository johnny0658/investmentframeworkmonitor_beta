# Framework monitor, as of 2026-11-09

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **15.1%** | 27.6% | 22.3% | 45.0% | 0.35 |
| A: Orderly AI de-rating | **55.1%** | 25.7% | 21.8% | 25.0% | 5.12 |
| B: AI capex bust | **10.5%** | 10.8% | 6.9% | 12.0% | 1.73 |
| C: AI credit event | **5.1%** | 8.8% | 7.5% | 8.0% | 1.12 |
| D: Stagflation | **14.2%** | 27.2% | 41.5% | 10.0% | 3.12 |

## Regime

Classifier: **goldilocks** (growth up: wei 3.47 vs 6m avg 2.93; core PCE 3m annualised 2.90% vs 12m 3.12% → inflation down)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Oil shock** (oil): `brent > 110`
- **Real yield squeeze** (rates): `real_10y > 2.5`
- **Chips lead down** (ai_fundamentals): `pct_change(smh_spy_ratio, 60) < -0.15`
- **Laggards decouple** (flows): `pct_change(inda_qqq_ratio, 60) > 0.10 and hy_oas < 4.0`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **-0.11** | → | 0.73 | 1.00 | +0.73 | 9 |  |
| 1 | rates_debt | **-0.52** | → | 0.30 | 1.00 | +0.30 | 15 |  |
| 1 | global_liquidity_inflation | **+0.33** | → | 0.44 | 1.00 | +0.44 | 11 |  |
| 2 | ai_stack | **+0.73** | ↓ | 0.63 | 1.00 | +0.63 | 2 |  |
| 2 | ai_bottlenecks_credit | **-0.67** | → | 0.45 | 1.00 | +0.45 | 6 |  |
| 3 | options_pricing | **-1.96** | ↓ | 0.98 | 1.00 | +0.98 | 2 |  |
| 5 | defensives | **+0.35** | → | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | inactive | 1.042 | 1 | -0.042 |
| Bonds stop hedging | rates | inactive | 0.090 | 0.3 | +0.210 |
| Oil shock | oil | active | 107.030 | 110 | +2.970 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.630 | 2.5 | -0.130 |
| Long-end break | rates | inactive | 4.860 | 5 | +0.140 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.041 | 0.5 | +0.459 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | active | -0.169 | -0.15 | -0.019 |
| Laggards decouple | flows | active | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | -0.008 | -0.05 | +0.042 |
