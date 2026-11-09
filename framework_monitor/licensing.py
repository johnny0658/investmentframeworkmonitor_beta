"""Licensing guard: no restricted raw value may reach the public repo or site.

The repo is public. Indicators flagged ``licence: restricted`` (ICE BofA
spreads, Cboe indices, Tiingo prices, FactSet ...) may appear publicly only
as derived values: z-scores, signals, ratios, thresholds crossed. This module
scans every public path and fails on:

1. a Parquet/CSV/JSON table (or JSON embedded in HTML) holding a raw-value
   column for a restricted or unknown indicator;
2. a public ``observations/<id>.parquet`` file for a restricted indicator;
3. anything under ``data/private/`` (or the encrypted archive) tracked by git.

`framework-monitor guard` runs it; CI and the scheduled workflow fail on any
violation before anything is committed or published.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from framework_monitor.schemas import Config

# Columns that carry raw source values. Derived columns (z, signal, score,
# transformed, distance_pct ...) are allowed for restricted indicators.
RAW_VALUE_COLUMNS = {
    "value", "raw", "raw_value", "close", "adj_close", "adjclose", "old_value", "new_value", "price", "level",
    # engine tables: a level-transformed value or a signpost's current value / distance
    # to its threshold reveals the raw number just as well
    "transformed", "lhs_value", "distance",
}
TABLE_SUFFIXES = {".parquet", ".csv", ".json"}
_JSON_SCRIPT = re.compile(r"<script[^>]*type=[\"']application/json[\"'][^>]*>(.*?)</script>", re.S | re.I)


class LicenceViolation(Exception):
    pass


@dataclass(frozen=True)
class Violation:
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}: {self.detail}"


def _table_violations(df: pd.DataFrame, public_ids: set[str], where: str) -> list[Violation]:
    """Rows for a non-public indicator (by `indicator_id`) or marked `licence != public`
    must not carry any raw-value column."""
    if "indicator_id" not in df.columns and "licence" not in df.columns:
        return []
    raw_cols = [c for c in df.columns if c.lower() in RAW_VALUE_COLUMNS]
    if not raw_cols:
        return []
    mask = pd.Series(False, index=df.index)
    if "indicator_id" in df.columns:
        mask |= ~df["indicator_id"].isin(public_ids)
    if "licence" in df.columns:
        mask |= df["licence"].ne("public")
    bad = df[mask]
    if bad.empty:
        return []
    has_raw = bad[raw_cols].notna().any(axis=1)
    if not has_raw.any():
        return []
    key = "indicator_id" if "indicator_id" in df.columns else ("signpost_id" if "signpost_id" in df.columns else None)
    ids = sorted(bad.loc[has_raw, key].astype(str).unique()) if key else [f"{int(has_raw.sum())} rows"]
    return [Violation(where, f"raw values {raw_cols} for restricted/unknown {ids}")]


def _walk_json(obj, public_ids: set[str], where: str, out: list[Violation]) -> None:
    if isinstance(obj, dict):
        ind = obj.get("indicator_id")
        if (isinstance(ind, str) and ind not in public_ids) or obj.get("licence") == "restricted":
            raw = [k for k, v in obj.items() if k.lower() in RAW_VALUE_COLUMNS and v is not None]
            if raw:
                out.append(Violation(where, f"raw values {raw} for restricted/unknown {ind or obj.get('signpost_id')}"))
        for v in obj.values():
            _walk_json(v, public_ids, where, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_json(v, public_ids, where, out)


def scan_file(path: Path, public_ids: set[str], restricted_ids: set[str]) -> list[Violation]:
    where = str(path)
    out: list[Violation] = []
    if path.parent.name == "observations" and path.suffix == ".parquet" and path.stem not in public_ids:
        out.append(Violation(where, f"public observations file for restricted/unknown indicator {path.stem}"))
    try:
        if path.suffix == ".parquet":
            out += _table_violations(pd.read_parquet(path), public_ids, where)
        elif path.suffix == ".csv":
            out += _table_violations(pd.read_csv(path), public_ids, where)
        elif path.suffix == ".json":
            _walk_json(json.loads(path.read_text()), public_ids, where, out)
        elif path.suffix == ".xlsx":
            for sheet, df in pd.read_excel(path, sheet_name=None, engine="openpyxl").items():
                out += _table_violations(df, public_ids, f"{where} [{sheet}]")
        elif path.suffix in {".html", ".htm"}:
            for block in _JSON_SCRIPT.findall(path.read_text(errors="ignore")):
                try:
                    _walk_json(json.loads(block), public_ids, where, out)
                except json.JSONDecodeError:
                    out.append(Violation(where, "unparseable embedded JSON block (cannot verify licensing)"))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        out.append(Violation(where, f"cannot read file to verify licensing: {exc}"))
    return out


def scan_paths(paths: list[Path], cfg: Config) -> list[Violation]:
    public_ids = {i.id for i in cfg.indicators if i.licence == "public"}
    restricted_ids = cfg.restricted_ids
    out: list[Violation] = []
    for base in paths:
        if not base.exists():
            continue
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
        for f in files:
            if f.suffix in TABLE_SUFFIXES | {".html", ".htm", ".xlsx"}:
                out += scan_file(f, public_ids, restricted_ids)
    return out


def scan_git_tracked(repo_root: Path) -> list[Violation]:
    """Fail if any private-store file is tracked by git."""
    try:
        res = subprocess.run(
            ["git", "ls-files", "--", "data/private", "private-store.enc", "private-store"],
            cwd=repo_root, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []  # not a git checkout (e.g. installed package); nothing to check
    return [Violation(f, "private-store file is tracked by git") for f in res.stdout.split()]


def scan_manual_dir(manual_dir: Path, cfg: Config) -> list[Violation]:
    """Committed manual CSVs must belong to public indicators."""
    out: list[Violation] = []
    restricted_series = {i.series: i.id for i in cfg.indicators if i.source == "manual" and i.licence == "restricted"}
    if manual_dir.exists():
        for f in manual_dir.glob("*.csv"):
            if f.stem in restricted_series:
                out.append(Violation(str(f), f"manual CSV for restricted indicator {restricted_series[f.stem]}; move it to data/private/manual/"))
    return out
