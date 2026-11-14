# Framework monitor, as of 2026-11-13

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **34.1%** | 15.1% | 22.3% | 45.0% | 0.80 |
| A: Orderly AI de-rating | **32.9%** | 55.1% | 21.8% | 25.0% | 1.60 |
| B: AI capex bust | **12.5%** | 10.5% | 6.9% | 12.0% | 1.20 |
| C: AI credit event | **9.4%** | 5.1% | 7.5% | 8.0% | 1.40 |
| D: Stagflation | **11.1%** | 14.2% | 41.5% | 10.0% | 1.30 |

## Regime

Classifier: **goldilocks** (growth up: wei 3.29 vs 6m avg 2.96; core PCE 3m annualised 2.90% vs 12m 3.12% → inflation down)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Real yield squeeze** (rates): `real_10y > 2.5`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **+0.20** | ↑ | 0.76 | 1.00 | +0.76 | 9 |  |
| 1 | rates_debt | **-0.62** | → | 0.26 | 1.00 | +0.26 | 15 |  |
| 1 | global_liquidity_inflation | **+0.29** | → | 0.53 | 1.00 | +0.53 | 11 |  |
| 2 | ai_stack | **+0.94** | → | 0.80 | 1.00 | +0.80 | 2 |  |
| 2 | ai_bottlenecks_credit | **-0.35** | ↑ | 0.44 | 1.00 | +0.44 | 6 |  |
| 3 | options_pricing | **-0.48** | ↑ | 0.93 | 1.00 | +0.93 | 2 |  |
| 5 | defensives | **+0.37** | → | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | inactive | 0.932 | 1 | +0.068 |
| Bonds stop hedging | rates | inactive | 0.085 | 0.3 | +0.215 |
| Oil shock | oil | inactive | 92.140 | 110 | +17.860 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.860 | 2.5 | -0.360 |
| Long-end break | rates | inactive | 5.100 | 5 | -0.100 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.048 | 0.5 | +0.452 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | inactive | -0.128 | -0.15 | +0.022 |
| Laggards decouple | flows | inactive | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | 0.008 | -0.05 | +0.058 |
