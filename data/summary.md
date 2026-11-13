# Framework monitor, as of 2026-11-12

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **16.0%** | 15.1% | 22.3% | 45.0% | 0.43 |
| A: Orderly AI de-rating | **62.7%** | 55.1% | 21.8% | 25.0% | 6.40 |
| B: AI capex bust | **10.7%** | 10.5% | 6.9% | 12.0% | 1.92 |
| C: AI credit event | **4.8%** | 5.1% | 7.5% | 8.0% | 1.12 |
| D: Stagflation | **5.8%** | 14.2% | 41.5% | 10.0% | 1.04 |

## Regime

Classifier: **goldilocks** (growth up: wei 3.29 vs 6m avg 2.96; core PCE 3m annualised 2.90% vs 12m 3.12% → inflation down)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Real yield squeeze** (rates): `real_10y > 2.5`
- **Chips lead down** (ai_fundamentals): `pct_change(smh_spy_ratio, 60) < -0.15`
- **Laggards decouple** (flows): `pct_change(inda_qqq_ratio, 60) > 0.10 and hy_oas < 4.0`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **+0.13** | → | 0.63 | 0.85 | +0.74 | 9 |  |
| 1 | rates_debt | **-0.58** | → | 0.27 | 1.00 | +0.27 | 15 |  |
| 1 | global_liquidity_inflation | **+0.29** | → | 0.53 | 1.00 | +0.53 | 11 |  |
| 2 | ai_stack | **+1.06** | ↑ | 0.85 | 1.00 | +0.85 | 2 |  |
| 2 | ai_bottlenecks_credit | **-0.36** | ↑ | 0.45 | 1.00 | +0.45 | 6 |  |
| 3 | options_pricing | **-0.16** | ↑ | 0.95 | 1.00 | +0.95 | 2 |  |
| 5 | defensives | **+0.31** | → | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | inactive | 0.909 | 1 | +0.091 |
| Bonds stop hedging | rates | inactive | 0.097 | 0.3 | +0.203 |
| Oil shock | oil | inactive | 92.140 | 110 | +17.860 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.780 | 2.5 | -0.280 |
| Long-end break | rates | inactive | 4.980 | 5 | +0.020 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.048 | 0.5 | +0.452 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | active | -0.094 | -0.15 | +0.056 |
| Laggards decouple | flows | active | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | 0.008 | -0.05 | +0.058 |
