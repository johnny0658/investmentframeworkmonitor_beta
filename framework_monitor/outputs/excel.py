"""Excel tracker (FR-26): Rows, Signposts, Scenarios and Theses sheets, plus
Indicators, Scenario history and Signpost events.

Built from the same licence-safe records as the site. The licensing guard
reads every sheet back and fails on a restricted raw value.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
HEADER_FONT = Font(color="FFFFFF", bold=True)

THESIS_COLUMNS = ["id", "opened", "regime_now", "regime_bet", "thesis", "priced_in", "variant_view", "earnings_link",
                  "catalyst", "catalyst_date", "expression", "size_pct", "signposts", "kill_switch", "kill_switch_tripped"]


def _sheet(wb: Workbook, title: str, df: pd.DataFrame, pct_cols: tuple[str, ...] = (), num_cols: tuple[str, ...] = ()) -> None:
    ws = wb.create_sheet(title)
    cols = list(df.columns)
    ws.append(cols)
    for c in ws[1]:
        c.fill, c.font = HEADER_FILL, HEADER_FONT
    for rec in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in rec])
    for j, col in enumerate(cols, start=1):
        letter = get_column_letter(j)
        width = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) if len(df) else len(str(col))
        ws.column_dimensions[letter].width = min(max(10, width + 2), 60)
        fmt = "0.0%" if col in pct_cols else "0.00" if col in num_cols else None
        if fmt:
            for cell in ws[letter][1:]:
                cell.number_format = fmt
    ws.freeze_panes = "A2"


def write_tracker(path: Path, as_of: dt.date, rows: list[dict], signposts: list[dict], scenarios: list[dict],
                  prob_history: pd.DataFrame, indicators: list[dict], events: list[dict]) -> None:
    wb = Workbook()
    about = wb.active
    about.title = "About"
    for line in [
        ["Investment Framework Monitor: tracker"],
        [f"As of {as_of.isoformat()}; generated {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC"],
        ["Not investment advice. Licence-restricted raw values (ICE BofA, Cboe, Tiingo prices) are not included."],
        ["Scores run from -2 (bearish for risk assets) to +2 (bullish); confidence 0..1 = freshness x agreement."],
    ]:
        about.append(line)
    about["A1"].font = Font(bold=True, size=14)
    about.column_dimensions["A"].width = 110
    for r in about.iter_rows():
        for c in r:
            c.alignment = Alignment(wrap_text=True)

    _sheet(wb, "Rows", pd.DataFrame(rows)[[
        "layer", "row_id", "name", "final_score", "score_1w", "final_confidence", "computed_score", "confidence",
        "freshness", "agreement", "n_signals", "override_active", "override_score", "override_reason", "override_expired"]],
        num_cols=("final_score", "score_1w", "final_confidence", "computed_score", "confidence", "freshness", "agreement", "override_score"))
    sp = pd.DataFrame(signposts)
    sp["lr"] = sp["lr"].map(lambda d: ", ".join(f"{k} {v:g}" for k, v in d.items()))
    sp["inputs"] = sp["inputs"].map(lambda v: "; ".join(v))
    _sheet(wb, "Signposts", sp[["signpost_id", "name", "family", "status", "stale", "condition", "clear_rule", "licence",
                                "lhs_value", "threshold", "distance", "last_triggered", "last_cleared", "lr", "inputs"]],
           num_cols=("lhs_value", "distance"))
    _sheet(wb, "Scenarios", pd.DataFrame(scenarios)[["scenario_id", "name", "now", "w1", "w4", "prior", "posterior", "multiplier", "description"]],
           pct_cols=("now", "w1", "w4", "prior", "posterior"), num_cols=("multiplier",))
    _sheet(wb, "Theses", pd.DataFrame(columns=THESIS_COLUMNS))  # filled in Phase 5 (theses/*.md)
    ind = pd.DataFrame(indicators)
    _sheet(wb, "Indicators", ind[["indicator_id", "name", "licence", "source_label", "obs_date", "raw", "z", "signal",
                                  "weight", "fresh", "transform", "frequency", "units"]], num_cols=("raw", "z", "signal"))
    if not prob_history.empty:
        piv = prob_history.pivot(index="as_of", columns="scenario_id", values="final").reset_index()
        piv["as_of"] = pd.to_datetime(piv["as_of"]).dt.date
        _sheet(wb, "Scenario history", piv, pct_cols=tuple(c for c in piv.columns if c != "as_of"))
    _sheet(wb, "Signpost events", pd.DataFrame(events, columns=["as_of", "signpost_id", "event", "backfilled"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
