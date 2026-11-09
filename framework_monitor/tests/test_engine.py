"""Engine tests on hand-worked examples (FR-11).

Every expected number below is worked out by hand in the comments.
"""

from __future__ import annotations

import datetime as dt
import math

import numpy as np
import pandas as pd
import pytest

from framework_monitor.engine import scenarios as scen
from framework_monitor.engine.formulas import Evaluator, UnitError, Val, lhs_threshold
from framework_monitor.engine.regime import classify
from framework_monitor.engine.rows import active_override, score_row
from framework_monitor.engine.signals import Signal, compute_signal
from framework_monitor.engine.transforms import transform
from framework_monitor.schemas import Judgement, Signpost

from .conftest import make_indicator


def ser(values, dates):
    return pd.Series([float(v) for v in values], index=pd.DatetimeIndex(pd.to_datetime(dates)))


# ================================================================ transforms
def test_yoy_and_ann_3m_monthly():
    s = ser([100, 101, 102, 103, 104], ["2025-06-01", "2025-09-01", "2025-12-01", "2026-03-01", "2026-06-01"])
    # yoy at 2026-06-01: 104 / 100 - 1 = 4%
    assert transform(s, "yoy", "monthly").round(9).tolist() == [4.0]
    # ann_3m at 2025-09-01: (101/100)^4 - 1 = 4.060401%
    assert round(transform(s, "ann_3m", "monthly").iloc[0], 6) == 4.060401


def test_diff_4w_and_13w_pct_weekly():
    dates = pd.date_range("2026-01-07", periods=14, freq="7D")
    s = pd.Series(np.arange(100.0, 114.0), index=dates)
    d4 = transform(s, "diff_4w", "weekly")
    assert d4.iloc[0] == 4.0 and len(d4) == 10  # x_t - x_{t-4w} = 4 for a +1/week series
    p13 = transform(s, "diff_13w_pct", "weekly")
    assert round(p13.iloc[-1], 6) == 13.0  # 113 / 100 - 1


def test_lag_across_a_gap_is_nan():
    # monthly series with a 6-month hole: the 3-month lag falls inside the hole
    s = ser([100, 101, 110], ["2025-01-01", "2025-02-01", "2025-08-01"])
    assert transform(s, "ann_3m", "monthly").empty


# ================================================================ step 1: signal
def _weekly(n, start="2024-01-03"):
    return pd.date_range(start, periods=n, freq="7D")


def test_zscore_signal_hand_worked():
    # 30 weekly values 1..30: mean 15.5, sample std = sqrt(77.5) = 8.80341; z = 14.5 / 8.80341 = 1.647089
    s = pd.Series(np.arange(1.0, 31.0), index=_weekly(30))
    ind = make_indicator(frequency="weekly", direction=-1, stale_after_days=12)
    sig = compute_signal(ind, s, s.index[-1].date())
    assert math.isclose(sig.z, (30 - 15.5) / math.sqrt(77.5), rel_tol=1e-12)
    assert math.isclose(sig.signal, -1.647089, abs_tol=1e-6)
    assert sig.fresh


def test_signal_is_clipped():
    s = pd.Series([0.0] * 29 + [100.0], index=_weekly(30))
    sig = compute_signal(make_indicator(frequency="weekly", direction=1), s, s.index[-1].date())
    assert sig.z > 2 and sig.signal == 2.0


def test_pct_rank_signal():
    # last value is the max of 30: p = (29 + 0.5) / 30 = 0.98333, signal = 4p - 2 = 1.93333
    s = pd.Series(np.arange(1.0, 31.0), index=_weekly(30))
    sig = compute_signal(make_indicator(frequency="weekly", transform="pct_rank", direction=1), s, s.index[-1].date())
    assert math.isclose(sig.percentile, 29.5 / 30) and math.isclose(sig.signal, 4 * 29.5 / 30 - 2)


def test_window_is_3y_daily_and_10y_monthly():
    # monthly: 15 years of data, window keeps 10 years = 120 obs
    m = pd.Series(np.r_[np.full(60, 1000.0), np.arange(120.0)], index=pd.date_range("2011-01-01", periods=180, freq="MS"))
    sig = compute_signal(make_indicator(frequency="monthly", direction=1, stale_after_days=75), m, m.index[-1].date())
    w = np.arange(120.0)
    assert math.isclose(sig.z, (119 - w.mean()) / w.std(ddof=1))  # the 1000s are outside the window


def test_short_window_and_monitor_only():
    s = pd.Series(np.arange(10.0), index=_weekly(10))
    assert compute_signal(make_indicator(frequency="weekly"), s, s.index[-1].date()).signal is None  # < 20 obs
    s = pd.Series(np.arange(30.0), index=_weekly(30))
    sig = compute_signal(make_indicator(frequency="weekly", direction=0, weight=0), s, s.index[-1].date())
    assert sig.z is not None and sig.signal is None


def test_signal_ignores_future_and_marks_stale():
    s = pd.Series(np.arange(1.0, 41.0), index=_weekly(40))
    as_of = s.index[29].date()
    sig = compute_signal(make_indicator(frequency="weekly", direction=1, stale_after_days=12), s, as_of)
    assert sig.raw == 30.0
    late = compute_signal(make_indicator(frequency="weekly", direction=1, stale_after_days=12), s.iloc[:30], as_of + dt.timedelta(days=30))
    assert not late.fresh


# ================================================================ step 2: row score
def S(i, v, fresh=True):
    return Signal(i, None, None, None, None, None, v, fresh)


def test_row_score_hand_worked():
    # weights a .5, b .3, c .2; signals a = +1 (fresh), b = -1 (stale), c missing
    # score = (.5*1 + .3*-1) / (.5 + .3) = 0.25
    # freshness = fresh weight / total weight = .5 / 1.0 = 0.5
    # agreement = 1 - pstdev([1, -1]) / 2 = 1 - 1/2 = 0.5  -> confidence 0.25
    score, fresh, agree, n = score_row({"a": .5, "b": .3, "c": .2}, {"a": S("a", 1.0), "b": S("b", -1.0, fresh=False)})
    assert (round(score, 12), fresh, agree, n) == (0.25, 0.5, 0.5, 2)
    assert fresh * agree == 0.25


def test_row_agreement_floors_at_zero_and_single_signal():
    _, _, agree, _ = score_row({"a": 1, "b": 1}, {"a": S("a", 2.0), "b": S("b", -2.0)})
    assert agree == 0.0  # pstdev 2 -> 1 - 1 = 0
    assert score_row({"a": 1}, {"a": S("a", 1.5)}) == (1.5, 1.0, 1.0, 1)
    assert score_row({"a": 1}, {}) == (None, 0.0, None, 0)


def test_overrides_and_expiry():
    j = [Judgement(row="r", score=-1, confidence=0.6, reason="x", expires=dt.date(2026, 12, 31))]
    assert active_override("r", j, dt.date(2026, 12, 31))[0] is j[0]
    assert active_override("r", j, dt.date(2027, 1, 1)) == (None, True)  # dropped and flagged
    assert active_override("other", j, dt.date(2026, 11, 1)) == (None, False)


# ================================================================ step 3: scenarios
def SP(i, fam, lr):
    return Signpost(id=i, name=i, family=fam, condition="x > 1", lr=lr)


def test_two_scenario_three_signpost_hand_worked():
    """X 0.6, Y 0.4. s1, s2 in family 'credit'; s3 in 'rates'.
    Family cap (credit): X -> 0.5 (|ln .5| > |ln .8|), Y -> 3.0 (|ln 3| > |ln 2|).
    Multipliers: X = 0.5 * 1.0 = 0.5, Y = 3.0 * 1.5 = 4.5.
    Posterior: X = .3 / (.3 + 1.8) = 1/7 = 0.142857, Y = 6/7 = 0.857143.
    Shrinkage 0.2: X = .8/7 + .12 = 0.234286, Y = .8*6/7 + .08 = 0.765714."""
    active = [SP("s1", "credit", {"X": 0.5, "Y": 2.0}), SP("s2", "credit", {"X": 0.8, "Y": 3.0}),
              SP("s3", "rates", {"X": 1.0, "Y": 1.5})]
    u = scen.update({"X": 0.6, "Y": 0.4}, active, 0.2)
    assert u.multiplier == {"X": 0.5, "Y": 4.5}
    assert math.isclose(u.posterior["X"], 1 / 7) and math.isclose(u.posterior["Y"], 6 / 7)
    assert math.isclose(u.final["X"], 0.8 / 7 + 0.12) and math.isclose(u.final["Y"], 0.8 * 6 / 7 + 0.08)
    assert math.isclose(sum(u.final.values()), 1.0)


def test_family_cap_counts_correlated_signals_once():
    one = scen.update({"X": .5, "Y": .5}, [SP("a", "credit", {"X": 1, "Y": 3})], 0)
    two = scen.update({"X": .5, "Y": .5}, [SP("a", "credit", {"X": 1, "Y": 3}), SP("b", "credit", {"X": 1, "Y": 3})], 0)
    assert one.posterior == two.posterior  # 0.25 / 0.75 either way
    assert math.isclose(one.posterior["Y"], 0.75)


def test_no_active_signposts_returns_prior_and_shrinkage_bounds():
    prior = {"base": .45, "A": .25, "B": .12, "C": .08, "D": .10}
    u = scen.update(prior, [], 0.2)
    assert all(math.isclose(u.final[k], prior[k]) for k in prior)
    full = scen.update({"X": .5, "Y": .5}, [SP("a", "credit", {"X": 1, "Y": 3})], 1.0)
    assert full.final == {"X": .5, "Y": .5}  # lambda = 1 -> always the prior


# ================================================================ formulas, units
def book(series: dict[str, tuple[pd.Series, str]]):
    return Evaluator(lambda i: Val(*series[i]))


def test_net_liquidity_units_and_hand_value():
    d = pd.DatetimeIndex(["2026-11-04"])
    ev = book({"fed_assets": (pd.Series([6_748_145.0], index=d), "usd_millions"),
               "tga": (pd.Series([957_175.0], index=d), "usd_millions"),
               "on_rrp": (pd.Series([0.225], index=d), "usd_billions")})
    v = ev.eval("fed_assets - tga - on_rrp * 1000")
    assert v.unit == "usd_millions" and v.data.iloc[0] == 5_790_745.0
    with pytest.raises(UnitError, match="usd_millions and usd_billions"):
        ev.eval("fed_assets - on_rrp")  # forgot the conversion


def test_alignment_forward_fills_and_drops_before_start():
    a = ser([1, 2, 3], ["2026-01-01", "2026-01-02", "2026-01-03"])
    b = ser([10], ["2026-01-02"])
    v = book({"a": (a, "ratio"), "b": (b, "ratio")}).eval("a + b")
    assert v.data.tolist() == [12.0, 13.0]  # 01-01 dropped (b not started), b ffilled to 01-03


def test_functions_hand_worked():
    idx = pd.date_range("2026-01-01", periods=6, freq="D")
    x = pd.Series([100.0, 110, 121, 133.1, 146.41, 161.051], index=idx)  # +10% a day
    ev = book({"x": (x, "index"), "y": (x * 2, "index")})
    assert np.allclose(ev.eval("pct_change(x, 1)").data, 0.1)
    assert ev.eval("change(x, 2)").data.iloc[0] == 21.0
    assert np.allclose(ev.eval("rolling_corr(x, y, 3)").data, 1.0)
    # impulse(x, 1): growth g = 10% every day -> change in growth = 0
    assert np.allclose(ev.eval("impulse(x, 1)").data, 0.0)
    basket = ev.eval("basket_return(x, y)").data
    assert math.isclose(basket.iloc[-1], 100 * 1.1**5)


def test_rolling_beta_hand_worked():
    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    xr = pd.Series([0.01, -0.02, 0.03, 0.0, 0.01], index=idx)
    ev = book({"xr": (xr, "ratio"), "yr": (2 * xr + 0.001, "ratio")})
    assert np.allclose(ev.eval("rolling_beta(yr, xr, 3)").data, 2.0)  # y = 2x + c -> beta 2


def test_condition_and_lhs_threshold():
    idx = pd.date_range("2026-01-01", periods=4, freq="D")
    ev = book({"hy": (pd.Series([3.9, 4.1, 4.2, 3.8], index=idx), "percent"),
               "q": (pd.Series([1.0, 1.0, 0.0, 0.0], index=idx), "ratio")})
    assert ev.eval("hy > 4.0").data.tolist() == [False, True, True, False]
    assert ev.eval("hy > 4.0 and q > 0.5").data.tolist() == [False, True, False, False]
    assert lhs_threshold("hy_oas > 4.00") == ("hy_oas", ">", 4.0)
    assert lhs_threshold("pct_change(smh, 60) < -0.15") == ("pct_change(smh, 60)", "<", -0.15)
    assert lhs_threshold("a > 1 and b < 2") is None


# ================================================================ regime
def test_regime_boxes():
    wei = pd.Series(np.r_[np.full(25, 2.0), 3.0], index=pd.date_range("2026-01-07", periods=26, freq="7D"))
    # core PCE: steady 0.25%/month for a year, then a jump -> 3m annualised > 12m
    pce = pd.Series(100 * 1.0025 ** np.arange(16), index=pd.date_range("2025-06-01", periods=16, freq="MS"))
    pce.iloc[-3:] *= [1.005, 1.010, 1.015]
    r = classify({"wei": wei, "core_pce": pce}, dt.date(2026, 12, 31))
    assert (r.growth_up, r.inflation_up, r.box) == (True, True, "reflation")
    r = classify({"wei": -wei, "core_pce": pce}, dt.date(2026, 12, 31))
    assert r.box == "stagflation"
    assert classify({}, dt.date(2026, 1, 1)).box is None


# ================================================================ hysteresis
def test_hysteresis_confirm_and_clear_days():
    from framework_monitor.engine.compute import hysteresis

    idx = pd.date_range("2026-01-01", periods=10, freq="D")
    cond = pd.Series([0, 1, 1, 0, 1, 0, 0, 0, 1, 0], index=idx).astype(bool)
    # confirm 2: on at day 3 (two in a row). clear 3: the single day off (day 4) does not clear;
    # three off in a row (days 6-8) clears on day 8.
    assert hysteresis(cond, None, 2, 3).astype(int).tolist() == [0, 0, 1, 1, 1, 1, 1, 0, 0, 0]
    # without hysteresis (clear 1) it flaps
    assert hysteresis(cond, None, 1, 1).astype(int).tolist() == [0, 1, 1, 0, 1, 0, 0, 0, 1, 0]


def test_hysteresis_level_based_clear():
    from framework_monitor.engine.compute import hysteresis

    idx = pd.date_range("2026-01-01", periods=7, freq="D")
    brent = pd.Series([108, 112, 107, 106, 104, 104, 104.0], index=idx)
    # on above 110; between 105 and 110 it stays on; clears after 3 days below 105
    h = hysteresis(brent > 110, brent < 105, 1, 3)
    assert h.astype(int).tolist() == [0, 1, 1, 1, 1, 1, 0]
