"""Pydantic schemas for every YAML config file, plus cross-file validation.

The indicator catalogue (indicators.yaml) is the only place a series is
defined (FR-2). Everything else refers to indicators by ID, and
`validate_cross_refs` fails on any unknown ID so CI catches typos.
"""

from __future__ import annotations

import ast
import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Source = Literal[
    # Phase 1 fetchers
    "fred",
    "alfred",
    "treasury_fiscal",
    "prices",
    "manual",
    # computed from other indicators (engine, Phase 2)
    "derived",
    # Phase 4 fetchers: declared now so rows and signposts can reference them
    "cboe",
    "cftc",
    "sec_edgar",
    "eia",
    "nsdl",
    "hkex",
    "atlanta_fed",
    "crash_tracker",
]

Frequency = Literal["daily", "weekly", "monthly", "quarterly", "annual", "per_auction", "irregular"]
Transform = Literal["level", "yoy", "ann_3m", "diff_4w", "diff_13w_pct", "pct_rank"]
Licence = Literal["public", "restricted"]

# Canonical unit names. Fetchers and `verify-series` map source unit strings onto
# these so arithmetic on mixed units (millions vs billions) can be asserted.
Units = Literal[
    "percent",
    "index",
    "ratio",
    "count",
    "thousands_persons",
    "usd",
    "usd_millions",
    "usd_billions",
    "eur_millions",
    "jpy_100m",
    "usd_per_barrel",
    "usd_per_share",
    "probability",
]

# Functions allowed inside derived formulas and signpost conditions. They are
# evaluated by the engine (Phase 2); Phase 1 only validates references.
FORMULA_FUNCTIONS = frozenset(
    {"pct_change", "change", "rolling_corr", "rolling_beta", "basket_return", "impulse", "abs", "min", "max"}
)
CONDITION_FUNCTIONS = frozenset({"pct_change", "change", "abs", "min", "max"})

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
    ast.UAdd,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
)


def expression_names(expr: str, functions: frozenset[str]) -> set[str]:
    """Parse a formula/condition and return the indicator IDs it references.

    Only arithmetic, comparisons, boolean logic, numeric constants and the
    whitelisted functions are allowed, so these strings can never run code.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"cannot parse expression {expr!r}: {exc.msg}") from exc
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"{type(node).__name__} is not allowed in expression {expr!r}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError(f"only numeric constants are allowed in {expr!r}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in functions:
                fname = getattr(node.func, "id", "?")
                raise ValueError(f"function {fname!r} is not allowed in {expr!r}; allowed: {sorted(functions)}")
            if node.keywords:
                raise ValueError(f"keyword arguments are not allowed in {expr!r}")
    call_names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in call_names:
            names.add(node.id)
    return names


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Indicator(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    source: Source
    series: str | None = None
    params: dict[str, object] = Field(default_factory=dict)
    formula: str | None = None
    units: Units
    frequency: Frequency
    transform: Transform = "level"
    direction: Literal[-1, 0, 1]
    row: str
    layer: int = Field(ge=1, le=5)
    weight: float = Field(ge=0)
    stale_after_days: int = Field(gt=0)
    licence: Licence
    enabled: bool = True
    catchup: bool = False
    proxy: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def _source_fields(self) -> "Indicator":
        if self.source == "derived":
            if not self.formula:
                raise ValueError(f"{self.id}: derived indicators need a formula")
            expression_names(self.formula, FORMULA_FUNCTIONS)
        elif self.formula:
            raise ValueError(f"{self.id}: only derived indicators take a formula")
        if self.source in {"fred", "alfred", "prices", "manual"} and not self.series:
            raise ValueError(f"{self.id}: source {self.source} needs `series`")
        if self.source == "treasury_fiscal":
            for key in ("endpoint", "date_field", "value_field"):
                if key not in self.params:
                    raise ValueError(f"{self.id}: treasury_fiscal needs params.{key}")
        if self.weight > 0 and self.direction == 0:
            raise ValueError(f"{self.id}: an indicator with weight > 0 needs direction +1 or -1")
        return self

    @property
    def formula_inputs(self) -> set[str]:
        return expression_names(self.formula, FORMULA_FUNCTIONS) if self.formula else set()


class Row(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    layer: int = Field(ge=1, le=5)
    question: str | None = None


class Layer(_Strict):
    id: int = Field(ge=1, le=5)
    name: str


class RowsFile(_Strict):
    layers: list[Layer]
    rows: list[Row]


class Signpost(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    family: Literal["credit", "volatility", "rates", "oil", "ai_fundamentals", "flows", "liquidity"]
    condition: str
    confirm_days: int = Field(default=1, ge=1)
    lr: dict[str, float]
    notes: str | None = None

    @field_validator("condition")
    @classmethod
    def _parse(cls, v: str) -> str:
        expression_names(v, CONDITION_FUNCTIONS)
        return v

    @field_validator("lr")
    @classmethod
    def _positive(cls, v: dict[str, float]) -> dict[str, float]:
        for k, x in v.items():
            if x <= 0:
                raise ValueError(f"likelihood ratio for {k} must be > 0")
        return v

    @property
    def indicators(self) -> set[str]:
        return expression_names(self.condition, CONDITION_FUNCTIONS)


class Scenario(_Strict):
    id: str
    name: str
    description: str
    prior: float = Field(ge=0, le=1)
    shocks: dict[str, float] = Field(default_factory=dict)


REGIME_BOXES = ("goldilocks", "reflation", "stagflation", "deflationary_bust")


class ScenariosFile(_Strict):
    confirmed_on: dt.date
    shrinkage_to_prior: float = Field(ge=0, le=1)
    scenarios: list[Scenario]
    # My P(each regime box in 6 months), shown beside the classifier (FR-13).
    regime_probs: dict[str, float] | None = None

    @field_validator("regime_probs")
    @classmethod
    def _regime(cls, v):
        if v is None:
            return v
        if set(v) != set(REGIME_BOXES):
            raise ValueError(f"regime_probs keys must be {list(REGIME_BOXES)}")
        if abs(sum(v.values()) - 1.0) > 1e-6:
            raise ValueError("regime_probs must sum to 1.0")
        return v

    @model_validator(mode="after")
    def _sum_to_one(self) -> "ScenariosFile":
        total = sum(s.prior for s in self.scenarios)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"scenario priors must sum to 1.0, got {total:.6f}")
        ids = [s.id for s in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate scenario id")
        return self


class Judgement(_Strict):
    row: str
    score: float = Field(ge=-2, le=2)
    confidence: float = Field(ge=0, le=1)
    reason: str
    expires: dt.date


class Config(_Strict):
    indicators: list[Indicator]
    rows: RowsFile
    signposts: list[Signpost]
    scenarios: ScenariosFile
    judgements: list[Judgement]

    @model_validator(mode="after")
    def _cross_refs(self) -> "Config":
        errors = validate_cross_refs(self)
        if errors:
            raise ValueError("config cross-reference errors:\n  - " + "\n  - ".join(errors))
        return self

    # convenience lookups -------------------------------------------------
    @property
    def by_id(self) -> dict[str, Indicator]:
        return {i.id: i for i in self.indicators}

    @property
    def restricted_ids(self) -> set[str]:
        return {i.id for i in self.indicators if i.licence == "restricted"}


def validate_cross_refs(cfg: Config) -> list[str]:
    errors: list[str] = []
    ids = [i.id for i in cfg.indicators]
    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        errors.append(f"duplicate indicator ids: {sorted(dupes)}")
    known = set(ids)

    layer_ids = {layer.id for layer in cfg.rows.layers}
    rows = {r.id: r for r in cfg.rows.rows}
    if len(rows) != len(cfg.rows.rows):
        errors.append("duplicate row ids in rows.yaml")
    for r in cfg.rows.rows:
        if r.layer not in layer_ids:
            errors.append(f"row {r.id}: unknown layer {r.layer}")

    for ind in cfg.indicators:
        row = rows.get(ind.row)
        if row is None:
            errors.append(f"indicator {ind.id}: unknown row {ind.row!r}")
        elif row.layer != ind.layer:
            errors.append(f"indicator {ind.id}: layer {ind.layer} but row {ind.row} is in layer {row.layer}")
        if ind.source == "derived":
            missing = ind.formula_inputs - known
            if missing:
                errors.append(f"derived {ind.id}: formula references unknown indicators {sorted(missing)}")
            elif ind.licence == "public":
                restricted_inputs = ind.formula_inputs & {i.id for i in cfg.indicators if i.licence == "restricted"}
                # A derived ratio of restricted inputs can be public (the PRD allows
                # publishing ratios/returns), but flag pass-through formulas.
                if ind.formula and ind.formula.strip() in restricted_inputs:
                    errors.append(f"derived {ind.id}: public pass-through of restricted {ind.formula.strip()}")

    errors.extend(_derived_cycles(cfg))

    scen_ids = {s.id for s in cfg.scenarios.scenarios}
    for sp in cfg.signposts:
        unknown = sp.indicators - known
        if unknown:
            errors.append(f"signpost {sp.id}: unknown indicators {sorted(unknown)}")
        if set(sp.lr) != scen_ids:
            errors.append(f"signpost {sp.id}: lr keys {sorted(sp.lr)} must equal scenario ids {sorted(scen_ids)}")
    sp_ids = [s.id for s in cfg.signposts]
    if len(sp_ids) != len(set(sp_ids)):
        errors.append("duplicate signpost ids")

    for j in cfg.judgements:
        if j.row not in rows:
            errors.append(f"judgement: unknown row {j.row!r}")
    return errors


def _derived_cycles(cfg: Config) -> list[str]:
    graph = {i.id: i.formula_inputs for i in cfg.indicators if i.source == "derived"}
    errors: list[str] = []
    state: dict[str, int] = {}

    def visit(node: str, path: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            errors.append("derived formula cycle: " + " -> ".join(path + [node]))
            return
        state[node] = 1
        for nxt in graph.get(node, ()):
            visit(nxt, path + [node])
        state[node] = 2

    for n in graph:
        visit(n, [])
    return errors
