# Framework monitor, as of 2026-11-17

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **24.7%** | 15.1% | 22.3% | 45.0% | 0.63 |
| A: Orderly AI de-rating | **49.3%** | 55.1% | 21.8% | 25.0% | 3.20 |
| B: AI capex bust | **10.4%** | 10.5% | 6.9% | 12.0% | 1.20 |
| C: AI credit event | **4.7%** | 5.1% | 7.5% | 8.0% | 0.70 |
| D: Stagflation | **10.9%** | 14.2% | 41.5% | 10.0% | 1.60 |

## Regime

Classifier: **goldilocks** (growth up: wei 3.29 vs 6m avg 2.96; core PCE 3m annualised 2.90% vs 12m 3.12% → inflation down)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Real yield squeeze** (rates): `real_10y > 2.5`
- **Long-end break** (rates): `ust_10y > 5.0`
- **Laggards decouple** (flows): `pct_change(inda_qqq_ratio, 60) > 0.10 and hy_oas < 4.0`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **+0.20** | ↑ | 0.57 | 0.75 | +0.76 | 9 |  |
| 1 | rates_debt | **-0.62** | → | 0.23 | 1.00 | +0.23 | 15 |  |
| 1 | global_liquidity_inflation | **+0.28** | → | 0.44 | 0.85 | +0.52 | 11 |  |
| 2 | ai_stack | **+0.87** | → | 0.76 | 1.00 | +0.76 | 2 |  |
| 2 | ai_bottlenecks_credit | **-0.68** | → | 0.42 | 1.00 | +0.42 | 6 |  |
| 3 | options_pricing | **-1.43** | ↓ | 0.93 | 1.00 | +0.93 | 2 |  |
| 5 | defensives | **+0.38** | → | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | inactive | 0.995 | 1 | +0.005 |
| Bonds stop hedging | rates | inactive | 0.082 | 0.3 | +0.218 |
| Oil shock | oil | inactive | 92.140 | 110 | +17.860 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.920 | 2.5 | -0.420 |
| Long-end break | rates | active | 5.120 | 5 | -0.120 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.163 | 0.5 | +0.337 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | inactive | -0.125 | -0.15 | +0.025 |
| Laggards decouple | flows | active | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | 0.008 | -0.05 | +0.058 |
