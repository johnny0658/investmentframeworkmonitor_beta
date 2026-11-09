"""One fetcher module per source (FR-1).

Phase 1 implements fred, alfred, treasury_fiscal, prices and manual. The
remaining sources (cboe, cftc, sec_edgar, eia, nsdl, hkex, atlanta_fed) land
in Phase 4; indicators that use them are declared with ``enabled: false``.
"""

from __future__ import annotations

from types import ModuleType

from framework_monitor.fetchers import alfred, fred, manual, prices, treasury_fiscal

FETCHERS: dict[str, ModuleType] = {
    "fred": fred,
    "alfred": alfred,
    "treasury_fiscal": treasury_fiscal,
    "prices": prices,
    "manual": manual,
}


def get_fetcher(source: str) -> ModuleType | None:
    return FETCHERS.get(source)
