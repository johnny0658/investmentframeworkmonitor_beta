"""Evaluate derived-indicator formulas and signpost conditions (FR-12).

Expressions are the strings in ``indicators.yaml`` (``formula``) and
``signposts.yaml`` (``condition``). They are parsed with ``ast`` and checked
against a whitelist in ``schemas.expression_names``, so they can never run
code. Evaluation rules:

* **Alignment.** Two series are aligned on the union of their dates and each
  is forward-filled. Dates before either series starts are dropped.
* **Windows** in ``change(x, n)`` / ``pct_change(x, n)`` / ``rolling_*`` count
  observations of the series they are applied to.
* **Units** are checked before arithmetic (data quality check 3). Adding or
  subtracting money amounts needs identical units, so millions minus billions
  raises `UnitError`. Multiplying or dividing a money amount by a constant
  rescales it, so ``on_rrp * 1000`` turns USD billions into USD millions. The
  result's units must match the derived indicator's declared units when
  either is a money unit.

Functions:
  pct_change(x, n)        x / x.shift(n) - 1
  change(x, n)            x - x.shift(n)
  rolling_corr(a, b, n)   n-observation rolling correlation
  rolling_beta(y, x, n)   n-observation rolling OLS beta of y on x
  basket_return(a, b, ...) equal-weight basket of daily returns, as an index (100 at start);
                          starts when every member has data
  impulse(x, n)           change over n observations of x's n-observation % growth
  abs(x), min(a, b), max(a, b)
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

MONEY_SCALES = {
    "usd": ("usd", 1.0),
    "usd_millions": ("usd", 1e6),
    "usd_billions": ("usd", 1e9),
    "eur_millions": ("eur", 1e6),
    "jpy_100m": ("jpy", 1e8),
}


def empty_series() -> pd.Series:
    return pd.Series(dtype=float, index=pd.DatetimeIndex([]))


class UnitError(ValueError):
    pass


class EvalError(ValueError):
    pass


@dataclass
class Val:
    """A series (or scalar) with its units."""

    data: pd.Series | float
    unit: str | None  # None for dimensionless constants

    @property
    def is_series(self) -> bool:
        return isinstance(self.data, pd.Series)


def _is_money(unit: str | None) -> bool:
    return unit in MONEY_SCALES


def _rescale(unit: str, factor: float) -> str:
    """Unit after multiplying a money amount's *number* by `factor`."""
    cur, scale = MONEY_SCALES[unit]
    target = scale / factor
    for name, (c, s) in MONEY_SCALES.items():
        if c == cur and math.isclose(s, target):
            return name
    return f"{unit}*{factor:g}"


def align(*series: pd.Series) -> list[pd.Series]:
    idx = series[0].index
    for s in series[1:]:
        idx = idx.union(s.index)
    out = [s.reindex(idx).ffill() for s in series]
    mask = np.ones(len(idx), dtype=bool)
    for s in out:
        mask &= s.notna().to_numpy()
    return [s[mask] for s in out]


def _binop_unit(op: ast.operator, a: Val, b: Val) -> str | None:
    ua, ub = a.unit, b.unit
    if isinstance(op, (ast.Add, ast.Sub)):
        if ua is None:
            return ub
        if ub is None:
            return ua
        if (_is_money(ua) or _is_money(ub)) and ua != ub:
            raise UnitError(f"cannot add/subtract {ua} and {ub}: convert units first")
        return ua
    if isinstance(op, ast.Mult):
        if ua is not None and ub is not None:
            return "ratio"
        unit, const = (ua, b.data) if ua is not None else (ub, a.data)
        return _rescale(unit, float(const)) if _is_money(unit) else unit
    if isinstance(op, ast.Div):
        if ua is not None and ub is None:
            return _rescale(ua, 1.0 / float(b.data)) if _is_money(ua) else ua
        return "ratio"
    raise EvalError(f"unsupported operator {type(op).__name__}")


_OPS = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide}
_CMP = {ast.Gt: np.greater, ast.GtE: np.greater_equal, ast.Lt: np.less, ast.LtE: np.less_equal}


class Evaluator:
    """Evaluates one expression. `resolve(id)` returns (series, units) for an indicator ID."""

    def __init__(self, resolve: Callable[[str], Val]):
        self.resolve = resolve

    def eval(self, expr: str) -> Val:
        return self._node(ast.parse(expr, mode="eval").body)

    # ------------------------------------------------------------------ nodes
    def _node(self, n: ast.AST) -> Val:
        if isinstance(n, ast.Constant):
            return Val(float(n.value), None)
        if isinstance(n, ast.Name):
            return self.resolve(n.id)
        if isinstance(n, ast.UnaryOp):
            v = self._node(n.operand)
            if isinstance(n.op, ast.USub):
                return Val(-v.data, v.unit)
            if isinstance(n.op, ast.UAdd):
                return v
            if isinstance(n.op, ast.Not):
                return Val(~v.data.astype(bool) if v.is_series else not v.data, "bool")
        if isinstance(n, ast.BinOp):
            a, b = self._node(n.left), self._node(n.right)
            unit = _binop_unit(n.op, a, b)
            x, y = self._pair(a, b)
            with np.errstate(divide="ignore", invalid="ignore"):
                out = _OPS[type(n.op)](x, y)
            if isinstance(out, pd.Series):
                out = out.replace([np.inf, -np.inf], np.nan).dropna()
            return Val(out, unit)
        if isinstance(n, ast.Compare):
            if len(n.ops) != 1:
                raise EvalError("chained comparisons are not supported")
            a, b = self._node(n.left), self._node(n.comparators[0])
            x, y = self._pair(a, b)
            return Val(_CMP[type(n.ops[0])](x, y), "bool")
        if isinstance(n, ast.BoolOp):
            vals = [self._node(v) for v in n.values]
            series = [v.data.astype(float) for v in vals]
            aligned = align(*series)
            out = aligned[0].astype(bool)
            for s in aligned[1:]:
                out = (out & s.astype(bool)) if isinstance(n.op, ast.And) else (out | s.astype(bool))
            return Val(out, "bool")
        if isinstance(n, ast.Call):
            return self._call(n.func.id, [self._node(a) for a in n.args])
        raise EvalError(f"unsupported expression node {type(n).__name__}")

    @staticmethod
    def _pair(a: Val, b: Val):
        if a.is_series and b.is_series:
            return align(a.data, b.data)
        return a.data, b.data

    @staticmethod
    def _int(v: Val, fn: str) -> int:
        if v.is_series or float(v.data) != int(v.data) or v.data < 1:
            raise EvalError(f"{fn}: window must be a positive integer")
        return int(v.data)

    def _call(self, fn: str, args: list[Val]) -> Val:
        if fn in ("pct_change", "change", "impulse"):
            x, n = args[0], self._int(args[1], fn)
            s = x.data
            if fn == "pct_change":
                return Val((s / s.shift(n) - 1).dropna(), "ratio")
            if fn == "change":
                return Val((s - s.shift(n)).dropna(), x.unit)
            g = (s / s.shift(n) - 1) * 100
            return Val((g - g.shift(n)).dropna(), "percent")
        if fn in ("rolling_corr", "rolling_beta"):
            a, b = align(args[0].data, args[1].data)
            n = self._int(args[2], fn)
            if fn == "rolling_corr":
                out = a.rolling(n, min_periods=n).corr(b)
            else:
                out = a.rolling(n, min_periods=n).cov(b) / b.rolling(n, min_periods=n).var()
            return Val(out.replace([np.inf, -np.inf], np.nan).dropna(), "ratio")
        if fn == "basket_return":
            members = [a.data for a in args]
            if any(m.empty for m in members):
                return Val(empty_series(), "index")
            aligned = align(*members)
            rets = pd.concat([m.pct_change() for m in aligned], axis=1).mean(axis=1).fillna(0.0)
            return Val(100 * (1 + rets).cumprod(), "index")
        if fn == "abs":
            return Val(args[0].data.abs() if args[0].is_series else abs(args[0].data), args[0].unit)
        if fn in ("min", "max"):
            a, b = args
            x, y = self._pair(a, b)
            f = np.minimum if fn == "min" else np.maximum
            return Val(f(x, y), a.unit or b.unit)
        raise EvalError(f"unknown function {fn}")


def lhs_threshold(condition: str) -> tuple[str, str, float] | None:
    """For a simple ``<expr> <op> <number>`` condition, return (lhs source, op, threshold)."""
    node = ast.parse(condition, mode="eval").body
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
        return None
    rhs = node.comparators[0]
    sign = 1.0
    if isinstance(rhs, ast.UnaryOp) and isinstance(rhs.op, (ast.USub, ast.UAdd)):  # "-0.15" parses as -(0.15)
        sign = -1.0 if isinstance(rhs.op, ast.USub) else 1.0
        rhs = rhs.operand
    if not isinstance(rhs, ast.Constant):
        return None
    op = {ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<", ast.LtE: "<="}[type(node.ops[0])]
    return ast.unparse(node.left), op, sign * float(rhs.value)
