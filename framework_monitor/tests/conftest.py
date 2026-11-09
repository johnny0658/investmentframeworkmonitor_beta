from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from framework_monitor.config_loader import load_config
from framework_monitor.fetchers.base import make_client
from framework_monitor.schemas import Indicator
from framework_monitor.settings import Paths

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_text(rel: str) -> str:
    return (FIXTURES / rel).read_text()


class Router:
    """httpx MockTransport handler that serves recorded fixtures by URL.

    Records every request so tests can assert on params, and can be told to
    fail specific hosts (to exercise retries and failure isolation).
    """

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.fail: dict[str, int] = {}  # host substring -> status code

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = request.url
        for host, status in self.fail.items():
            if host in str(url):
                return httpx.Response(status, text="forced failure")
        q = dict(url.params)
        if url.host == "fred.stlouisfed.org" and url.path == "/graph/fredgraph.csv":
            code = q["id"]
            for name in (f"fred/graph_{code}.csv", f"fred/graph_{code}_synthetic.csv"):
                if (FIXTURES / name).exists():
                    return httpx.Response(200, text=fixture_text(name))
            return httpx.Response(404, text="<html>Not found</html>")
        if url.host == "api.stlouisfed.org" and url.path == "/fred/series/observations":
            code = q["series_id"]
            if "realtime_start" in q:
                page = int(q.get("offset", 0)) // 4 + 1
                return httpx.Response(200, text=fixture_text(f"fred/alfred_{code}_p{page}.json"))
            return httpx.Response(200, text=fixture_text(f"fred/api_{code}.json"))
        if url.host == "api.fiscaldata.treasury.gov":
            if url.path.endswith("debt_to_penny"):
                return httpx.Response(200, text=fixture_text(f"treasury/debt_to_penny_p{q.get('page[number]', '1')}.json"))
            if url.path.endswith("auctions_query"):
                return httpx.Response(200, text=fixture_text("treasury/auctions_30y.json"))
            return httpx.Response(200, json={"error": "Invalid endpoint", "message": "bad endpoint"})
        if url.host == "api.tiingo.com":
            if request.headers.get("Authorization") != "Token test-tiingo-key":
                return httpx.Response(401, json={"detail": "Invalid token."})
            return httpx.Response(200, text=fixture_text("tiingo/SPY_synthetic.json"))
        if url.host == "stooq.com":
            return httpx.Response(200, text=fixture_text("stooq/spy_us_synthetic.csv"))
        return httpx.Response(404, text="no fixture")


@pytest.fixture
def router() -> Router:
    return Router()


@pytest.fixture
def client(router) -> httpx.Client:
    return make_client(transport=httpx.MockTransport(router))


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def paths(tmp_path) -> Paths:
    manual = tmp_path / "manual"
    manual.mkdir()
    return Paths(root=tmp_path, public_manual_dir=manual)


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    for k in ("FRED_API_KEY", "TIINGO_API_KEY", "PRIVATE_STORE_KEY"):
        monkeypatch.delenv(k, raising=False)


def make_indicator(**kw) -> Indicator:
    base = dict(id="x", name="X", source="fred", series="DGS10", units="percent", frequency="daily",
                direction=-1, row="rates_debt", layer=1, weight=0.1, stale_after_days=5, licence="public")
    base.update(kw)
    return Indicator(**base)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
