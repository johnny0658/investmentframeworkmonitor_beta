# Framework monitor, as of 2026-11-20

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **16.9%** | 34.1% | 22.3% | 45.0% | 0.38 |
| A: Orderly AI de-rating | **53.4%** | 32.9% | 21.8% | 25.0% | 4.16 |
| B: AI capex bust | **11.1%** | 12.5% | 6.9% | 12.0% | 1.56 |
| C: AI credit event | **6.8%** | 9.4% | 7.5% | 8.0% | 1.40 |
| D: Stagflation | **11.7%** | 11.1% | 41.5% | 10.0% | 2.08 |

## Regime

Classifier: **goldilocks** (growth up: wei 3.29 vs 6m avg 2.96; core PCE 3m annualised 2.90% vs 12m 3.12% → inflation down)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Vol inversion** (volatility): `vix_term > 1.0`
- **Real yield squeeze** (rates): `real_10y > 2.5`
- **Long-end break** (rates): `ust_10y > 5.0`
- **Laggards decouple** (flows): `pct_change(inda_qqq_ratio, 60) > 0.10 and hy_oas < 4.0`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **+0.38** | → | 0.72 | 0.90 | +0.80 | 9 |  |
| 1 | rates_debt | **-0.51** | → | 0.19 | 1.00 | +0.19 | 15 |  |
| 1 | global_liquidity_inflation | **+0.25** | → | 0.37 | 0.70 | +0.53 | 11 |  |
| 2 | ai_stack | **+0.98** | → | 0.86 | 1.00 | +0.86 | 2 |  |
| 2 | ai_bottlenecks_credit | **-0.84** | ↓ | 0.44 | 1.00 | +0.44 | 6 |  |
| 3 | options_pricing | **-2.00** | ↓ | 1.00 | 1.00 | +1.00 | 2 |  |
| 5 | defensives | **+0.81** | ↑ | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | active | 1.052 | 1 | -0.052 |
| Bonds stop hedging | rates | inactive | -0.006 | 0.3 | +0.306 |
| Oil shock | oil | inactive | 92.940 | 110 | +17.060 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.880 | 2.5 | -0.380 |
| Long-end break | rates | active | 5.040 | 5 | -0.040 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.163 | 0.5 | +0.337 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | inactive | -0.141 | -0.15 | +0.009 |
| Laggards decouple | flows | active | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | 0.006 | -0.05 | +0.056 |
