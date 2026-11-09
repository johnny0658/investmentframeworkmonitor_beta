"""Regenerate the synthetic fixtures (run from the repo root):

    python framework_monitor/tests/fixtures/make_synthetic.py

Synthetic fixtures stand in for (a) responses that need an API key we do not
have in CI, and (b) restricted sources, whose real values must not be
committed to this public repo (ICE BofA spreads, Tiingo prices). The values
are made up and follow each API's documented response format.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def bdays(start: dt.date, n: int) -> list[dt.date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def main() -> None:
    # FRED API JSON (series/observations) built from the real public DGS10 CSV.
    with (HERE / "fred" / "graph_DGS10.csv").open() as fh:
        rows = list(csv.reader(fh))[1:]
    obs = [{"realtime_start": "2026-11-09", "realtime_end": "2026-11-09", "date": d, "value": v or "."} for d, v in rows[-60:]]
    obs[5]["value"] = "."  # FRED's missing-value marker
    (HERE / "fred" / "api_DGS10.json").write_text(json.dumps({"count": len(obs), "observations": obs}, indent=1))

    # ALFRED vintages for M2SL, split over two pages (tests set PAGE_LIMIT=4).
    vint = [
        ("2026-07-01", "22000.1", "2026-08-26"),
        ("2026-07-01", "22010.5", "2026-09-23"),  # revision
        ("2026-08-01", "22100.0", "2026-09-23"),
        ("2026-08-01", "22095.2", "2026-10-28"),  # revision
        ("2026-09-01", "22200.7", "2026-10-28"),
        ("2026-09-01", "22205.0", "2026-11-25"),  # later revision (future vintage)
    ]
    pages = [vint[:4], vint[4:]]
    for i, page in enumerate(pages, 1):
        payload = {"count": len(vint), "offset": (i - 1) * 4, "limit": 4,
                   "observations": [{"realtime_start": rs, "realtime_end": "9999-12-31", "date": d, "value": v} for d, v, rs in page]}
        (HERE / "fred" / f"alfred_M2SL_p{i}.json").write_text(json.dumps(payload, indent=1))

    # Synthetic high-yield OAS in fredgraph.csv layout (restricted: no real values).
    days = bdays(dt.date(2024, 1, 2), 500)
    with (HERE / "fred" / "graph_BAMLH0A0HYM2_synthetic.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["observation_date", "BAMLH0A0HYM2"])
        for i, d in enumerate(days):
            w.writerow([d.isoformat(), "" if i == 10 else f"{3.2 + 0.4 * math.sin(i / 25):.2f}"])

    # Synthetic Tiingo daily prices (documented JSON list format).
    days = bdays(dt.date(2026, 6, 1), 80)
    bars = []
    for i, d in enumerate(days):
        close = 600 + 5 * math.sin(i / 7) + i * 0.3
        bars.append({"date": f"{d.isoformat()}T00:00:00.000Z", "close": round(close, 2), "high": round(close + 2, 2),
                     "low": round(close - 2, 2), "open": round(close - 0.5, 2), "volume": 50_000_000,
                     "adjClose": round(close * 0.99, 4), "adjHigh": 0, "adjLow": 0, "adjOpen": 0, "adjVolume": 0,
                     "divCash": 0.0, "splitFactor": 1.0})
    (HERE / "tiingo" / "SPY_synthetic.json").write_text(json.dumps(bars, indent=1))

    # Synthetic Stooq CSV.
    with (HERE / "stooq" / "spy_us_synthetic.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
        for i, d in enumerate(days):
            c = 500 + i
            w.writerow([d.isoformat(), c - 1, c + 1, c - 2, c, 1000])


if __name__ == "__main__":
    main()
