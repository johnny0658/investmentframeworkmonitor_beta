# Framework monitor, as of 2026-11-23

> Not investment advice. Priors and likelihood ratios are still the PRD placeholders; indicator weights and directions are first-pass defaults.

## Scenario probabilities

| Scenario | Now | 1 week ago | 4 weeks ago | Confirmed prior | LR multiplier |
| --- | ---: | ---: | ---: | ---: | ---: |
| base: Base | **11.8%** | 27.2% | 27.6% | 45.0% | 0.23 |
| A: Orderly AI de-rating | **63.0%** | 49.8% | 25.7% | 25.0% | 8.32 |
| B: AI capex bust | **10.8%** | 10.5% | 10.8% | 12.0% | 2.50 |
| C: AI credit event | **6.6%** | 4.7% | 8.8% | 8.0% | 2.24 |
| D: Stagflation | **7.8%** | 7.8% | 27.2% | 10.0% | 2.08 |

## Regime

Classifier: **goldilocks** (growth up: wei 3.29 vs 6m avg 2.96; core PCE 3m annualised 2.90% vs 12m 3.12% → inflation down)

My regime probabilities (6 months): goldilocks 25.0%, reflation 25.0%, stagflation 25.0%, deflationary_bust 25.0%

## Active signposts

- **Vol inversion** (volatility): `vix_term > 1.0`
- **Real yield squeeze** (rates): `real_10y > 2.5`
- **Long-end break** (rates): `ust_10y > 5.0`
- **Chips lead down** (ai_fundamentals): `pct_change(smh_spy_ratio, 60) < -0.15`
- **Laggards decouple** (flows): `pct_change(inda_qqq_ratio, 60) > 0.10 and hy_oas < 4.0`

## Rows

| Layer | Row | Score | vs 1w | Confidence | Fresh | Agree | Signals | Override |
| --- | --- | ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | us_liquidity | **+0.38** | → | 0.72 | 0.90 | +0.80 | 9 |  |
| 1 | rates_debt | **-0.45** | → | 0.19 | 1.00 | +0.19 | 15 |  |
| 1 | global_liquidity_inflation | **+0.24** | → | 0.37 | 0.70 | +0.53 | 11 |  |
| 2 | ai_stack | **+0.91** | → | 0.78 | 1.00 | +0.78 | 2 |  |
| 2 | ai_bottlenecks_credit | **-1.03** | ↓ | 0.40 | 1.00 | +0.40 | 6 |  |
| 3 | options_pricing | **-2.00** | ↓ | 1.00 | 1.00 | +1.00 | 2 |  |
| 5 | defensives | **+0.89** | ↑ | 1.00 | 1.00 | +1.00 | 1 |  |

Rows with no data yet (sources in later phases): ai_vs_non_ai, tech_competitiveness, value_capture_tax, future_tech, valuations, positioning, capital_flows, calendar, policy, crash_signals, portfolio

## Signposts

Distance = how far the value must still move to trigger (negative = past the threshold). Values of restricted series are not published.

| Signpost | Family | Status | Current | Threshold | Distance |
| --- | --- | --- | ---: | ---: | ---: |
| High-yield stress | credit | inactive | restricted | 4 | restricted |
| High-yield crisis | credit | inactive | restricted | 5 | restricted |
| CCC blowout | credit | inactive | restricted | 15 | restricted |
| Investment-grade drift | credit | inactive | restricted | 1.1 | restricted |
| Vol inversion | volatility | active | 1.160 | 1 | -0.160 |
| Bonds stop hedging | rates | inactive | -0.022 | 0.3 | +0.322 |
| Oil shock | oil | inactive | 92.940 | 110 | +17.060 |
| Hike priced | rates | unavailable | - | 0.7 | - |
| Real yield squeeze | rates | active | 2.770 | 2.5 | -0.270 |
| Long-end break | rates | active | 4.920 | 5 | +0.080 |
| Bear steepener | rates | inactive | - | - | - |
| Term premium jump | rates | inactive | 0.163 | 0.5 | +0.337 |
| Capex cut | ai_fundamentals | unavailable | - | 2 | - |
| Chips lead down | ai_fundamentals | active | -0.116 | -0.15 | +0.034 |
| Laggards decouple | flows | active | - | - | - |
| Everything falls | flows | inactive | - | - | - |
| Liquidity drain | liquidity | inactive | 0.006 | -0.05 | +0.056 |
