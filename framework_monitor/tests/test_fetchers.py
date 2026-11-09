"""Fetchers against recorded fixtures (offline)."""

from __future__ import annotations

import datetime as dt

import httpx
import pytest

from framework_monitor.fetchers import alfred, base, fred, manual, prices, treasury_fiscal
from framework_monitor.fetchers.base import FetchError, get_with_retry, make_client, redact

from .conftest import make_indicator


# ---------------------------------------------------------------- retries (FR-4)
def _client(handler):
    return make_client(transport=httpx.MockTransport(handler))


def test_retry_succeeds_after_transient_errors():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, text="ok")

    sleeps = []
    r = get_with_retry(_client(handler), "https://x.test/a", sleep=sleeps.append)
    assert r.text == "ok" and len(calls) == 3
    assert sleeps == [2.0, 4.0]  # exponential back-off


def test_retry_gives_up_after_three_attempts():
    calls = []

    def handler(req):
        calls.append(1)
        raise httpx.ConnectError("boom")

    with pytest.raises(FetchError, match="failed after 3 attempts"):
        get_with_retry(_client(handler), "https://x.test/a", sleep=lambda s: None)
    assert len(calls) == 3


def test_client_errors_are_not_retried():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(400, text="Bad Request. The series does not exist.")

    with pytest.raises(FetchError, match="HTTP 400"):
        get_with_retry(_client(handler), "https://x.test/a", sleep=lambda s: None)
    assert len(calls) == 1


def test_secrets_are_redacted_from_errors(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "abcdef123456")
    msg = redact("GET https://api.stlouisfed.org/fred?series_id=X&api_key=abcdef123456&file_type=json failed; key abcdef123456")
    assert "abcdef123456" not in msg and "api_key=***" in msg

    def handler(req):
        return httpx.Response(400, text="bad")

    with pytest.raises(FetchError) as exc:
        get_with_retry(_client(handler), "https://x.test/a", params={"api_key": "abcdef123456"}, sleep=lambda s: None)
    assert "abcdef123456" not in str(exc.value)


# ---------------------------------------------------------------- FRED
def test_fred_graph_csv_without_key(client, router):
    ind = make_indicator(series="DGS10")
    df = fred.fetch(ind, dt.date(2026, 1, 1), None, client=client)
    assert list(df.columns) == base.OBS_COLUMNS
    assert df["obs_date"].min() >= dt.date(2026, 1, 1)
    assert df["value"].notna().all() and df["vintage_date"].isna().all()
    assert router.requests[0].url.params["cosd"] == "2026-01-01"
    # holidays come through as blank values and are dropped
    assert dt.date(2025, 12, 25) not in set(fred.fetch(ind, None, None, client=client)["obs_date"])


def test_fred_api_with_key(client, router, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k" * 32)
    df = fred.fetch(make_indicator(series="DGS10"), None, None, client=client)
    import json

    from .conftest import fixture_text

    raw = json.loads(fixture_text("fred/api_DGS10.json"))["observations"]
    assert len(df) == sum(o["value"] != "." for o in raw) < len(raw)  # "." = missing, dropped
    assert router.requests[0].url.host == "api.stlouisfed.org"


def test_fred_unknown_series_raises(client):
    with pytest.raises(FetchError):
        fred.fetch(make_indicator(series="NOPE"), None, None, client=client)


def test_canonical_units():
    assert fred.canonical_units("Millions of U.S. Dollars") == "usd_millions"
    assert fred.canonical_units("Billions of US Dollars") == "usd_billions"
    assert fred.canonical_units("Index 1982-1984=100") == "index"
    assert fred.canonical_units("Percent") == "percent"
    assert fred.canonical_units("Furlongs") is None


# ---------------------------------------------------------------- ALFRED
def test_alfred_vintages_paginate(client, router, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "k" * 32)
    monkeypatch.setattr(alfred, "PAGE_LIMIT", 4)
    df = alfred.fetch(make_indicator(source="alfred", series="M2SL", frequency="monthly", units="usd_billions"), None, None, client=client)
    assert len(df) == 6
    assert df["vintage_date"].notna().all()
    jul = df[df["obs_date"] == dt.date(2026, 7, 1)]
    assert list(jul["value"]) == [22000.1, 22010.5]
    assert [r.url.params["offset"] for r in router.requests] == ["0", "4"]


def test_alfred_degrades_without_key(client):
    df = alfred.fetch(make_indicator(source="alfred", series="DGS10"), None, None, client=client)
    assert "degraded" in df.attrs and df["vintage_date"].isna().all()


# ---------------------------------------------------------------- Treasury
def _debt():
    return make_indicator(id="public_debt", source="treasury_fiscal", series="debt_to_penny", units="usd_millions",
                          params={"endpoint": "v2/accounting/od/debt_to_penny", "date_field": "record_date",
                                  "value_field": "tot_pub_debt_out_amt", "scale": 1e-6})


def test_treasury_paginates_and_scales(client, router):
    df = treasury_fiscal.fetch(_debt(), dt.date(2026, 10, 1), None, client=client)
    assert len(df) == 10
    assert 30e6 < df["value"].iloc[0] < 50e6  # dollars -> USD millions
    assert router.requests[0].url.params["filter"] == "record_date:gte:2026-10-01"
    assert [r.url.params["page[number]"] for r in router.requests] == ["1", "2"]


def test_treasury_filters_passed(client, router):
    ind = make_indicator(id="auction_btc_30y", source="treasury_fiscal", series="a", units="ratio",
                         params={"endpoint": "v1/accounting/od/auctions_query", "date_field": "auction_date",
                                 "value_field": "bid_to_cover_ratio",
                                 "filters": ["original_security_term:eq:30-Year", "security_type:eq:Bond"]})
    df = treasury_fiscal.fetch(ind, None, None, client=client)
    assert df["value"].between(1.5, 4).all()
    assert router.requests[0].url.params["filter"] == "original_security_term:eq:30-Year,security_type:eq:Bond"


def test_treasury_error_payload(client):
    ind = make_indicator(source="treasury_fiscal", series="x",
                         params={"endpoint": "v1/nope", "date_field": "record_date", "value_field": "v"})
    with pytest.raises(FetchError, match="bad endpoint"):
        treasury_fiscal.fetch(ind, None, None, client=client)


# ---------------------------------------------------------------- prices
def _spy(**kw):
    return make_indicator(id="spy", source="prices", series="SPY", units="index", licence="restricted",
                          direction=0, weight=0, **kw)


def test_tiingo_uses_header_auth(client, router, monkeypatch):
    monkeypatch.setenv("TIINGO_API_KEY", "test-tiingo-key")
    df = prices.fetch(_spy(), dt.date(2026, 6, 1), None, client=client)
    assert df.attrs["source"] == "prices:tiingo"
    assert len(df) == 80
    req = router.requests[0]
    assert "token" not in str(req.url).lower()  # key in header, never in the URL
    assert req.url.path == "/tiingo/daily/spy/prices"


def test_prices_fall_back_to_stooq(client, router):
    df = prices.fetch(_spy(params={"providers": ["tiingo", "stooq"]}), None, None, client=client)  # no Tiingo key
    assert df.attrs["source"] == "prices:stooq"
    assert router.requests[0].url.params["s"] == "spy.us"


def test_prices_all_providers_fail(client, router):
    router.fail["stooq.com"] = 503
    with pytest.raises(FetchError, match="all price providers failed"):
        prices.fetch(_spy(params={"providers": ["tiingo", "stooq"]}), None, None, client=client)


def test_chain_is_invariant_to_back_adjustment():
    import pandas as pd

    stored = pd.Series([100.0, 101.0, 102.0], index=[dt.date(2026, 1, d) for d in (5, 6, 7)])
    # same prices after a dividend back-adjusts history by 0.98, plus one new bar
    fetched = base.to_frame([(dt.date(2026, 1, 6), 101 * 0.98), (dt.date(2026, 1, 7), 102 * 0.98), (dt.date(2026, 1, 8), 103 * 0.98)])
    out = prices.chain(fetched, stored)
    assert out["value"].round(9).tolist() == [101.0, 102.0, 103.0]


def test_chain_without_overlap_raises():
    import pandas as pd

    stored = pd.Series([100.0], index=[dt.date(2020, 1, 2)])
    with pytest.raises(FetchError, match="no overlap"):
        prices.chain(base.to_frame([(dt.date(2026, 1, 6), 1.0)]), stored)


# ---------------------------------------------------------------- manual
def test_manual_public_and_restricted_dirs(paths):
    pub = make_indicator(id="tsmc", source="manual", series="tsmc_revenue", units="usd_millions")
    (paths.public_manual_dir / "tsmc_revenue.csv").write_text("# typed in\ndate,value\n2026-09-01,1000\n2026-10-01,1100\n")
    df = manual.fetch(pub, None, None, paths=paths)
    assert df["value"].tolist() == [1000.0, 1100.0]

    res = make_indicator(id="fwd_pe", source="manual", series="fwd_pe", units="ratio", licence="restricted")
    with pytest.raises(FetchError, match="not found"):
        manual.fetch(res, None, None, paths=paths)
    paths.private_manual_dir.mkdir(parents=True)
    (paths.private_manual_dir / "fwd_pe.csv").write_text("date,value,vintage_date\n2026-11-07,22.1,2026-11-08\n")
    assert manual.fetch(res, None, None, paths=paths)["vintage_date"].tolist() == [dt.date(2026, 11, 8)]
