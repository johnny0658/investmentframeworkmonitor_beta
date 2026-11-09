"""Config validation (PRD Testing: pydantic schemas; CI fails on unknown IDs)."""

from __future__ import annotations

import shutil

import pytest
import yaml

from framework_monitor.config_loader import ConfigError, load_config
from framework_monitor.schemas import expression_names, FORMULA_FUNCTIONS
from framework_monitor.settings import PACKAGE_DIR


@pytest.fixture
def cfg_dir(tmp_path):
    d = tmp_path / "config"
    shutil.copytree(PACKAGE_DIR / "config", d)
    return d


def edit(path, fn):
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_shipped_config_is_valid(cfg):
    assert len([i for i in cfg.indicators if i.enabled and i.source != "derived"]) >= 40
    assert {i.layer for i in cfg.indicators} == {1, 2, 3, 4, 5}
    assert abs(sum(s.prior for s in cfg.scenarios.scenarios) - 1) < 1e-9


def test_every_prd_signpost_is_configured(cfg):
    assert len(cfg.signposts) == 17


def test_ice_cboe_and_prices_are_restricted(cfg):
    by = cfg.by_id
    for i in ("hy_oas", "ccc_oas", "bbb_oas", "ig_oas", "vix", "vix3m", "spy", "nvda"):
        assert by[i].licence == "restricted", i
    assert all(i.licence == "restricted" for i in cfg.indicators if i.source == "prices")


def test_unknown_row_fails(cfg_dir):
    edit(cfg_dir / "indicators.yaml", lambda d: d["indicators"][0].update(row="nope"))
    with pytest.raises(ConfigError, match="unknown row 'nope'"):
        load_config(cfg_dir)


def test_layer_mismatch_fails(cfg_dir):
    edit(cfg_dir / "indicators.yaml", lambda d: d["indicators"][0].update(layer=3))
    with pytest.raises(ConfigError, match="layer 3 but row"):
        load_config(cfg_dir)


def test_unknown_indicator_in_signpost_fails(cfg_dir):
    edit(cfg_dir / "signposts.yaml", lambda d: d[0].update(condition="hy_oass > 4"))
    with pytest.raises(ConfigError, match=r"signpost hy_stress: unknown indicators \['hy_oass'\]"):
        load_config(cfg_dir)


def test_unknown_formula_input_fails(cfg_dir):
    def f(d):
        for i in d["indicators"]:
            if i["id"] == "vix_term":
                i["formula"] = "vix / vix6m"
    edit(cfg_dir / "indicators.yaml", f)
    with pytest.raises(ConfigError, match="vix6m"):
        load_config(cfg_dir)


def test_signpost_lr_keys_must_match_scenarios(cfg_dir):
    edit(cfg_dir / "signposts.yaml", lambda d: d[0]["lr"].pop("D"))
    with pytest.raises(ConfigError, match="lr keys"):
        load_config(cfg_dir)


def test_priors_must_sum_to_one(cfg_dir):
    edit(cfg_dir / "scenarios.yaml", lambda d: d["scenarios"][0].update(prior=0.5))
    with pytest.raises(ConfigError, match="sum to 1.0"):
        load_config(cfg_dir)


def test_unknown_field_rejected(cfg_dir):
    edit(cfg_dir / "indicators.yaml", lambda d: d["indicators"][0].update(wieght=0.2))
    with pytest.raises(ConfigError, match="wieght"):
        load_config(cfg_dir)


def test_judgement_unknown_row_and_range(cfg_dir):
    (cfg_dir / "judgements.yaml").write_text(
        "- {row: nope, score: -1, confidence: 0.6, reason: r, expires: 2026-12-31}\n")
    with pytest.raises(ConfigError, match="judgement: unknown row"):
        load_config(cfg_dir)
    (cfg_dir / "judgements.yaml").write_text(
        "- {row: us_liquidity, score: -3, confidence: 0.6, reason: r, expires: 2026-12-31}\n")
    with pytest.raises(ConfigError, match="score"):
        load_config(cfg_dir)


def test_weighted_indicator_needs_direction(cfg_dir):
    edit(cfg_dir / "indicators.yaml", lambda d: d["indicators"][0].update(direction=0, weight=0.5))
    with pytest.raises(ConfigError, match="needs direction"):
        load_config(cfg_dir)


def test_derived_cycle_detected(cfg_dir):
    def f(d):
        d["indicators"].append({"id": "loop_a", "name": "a", "source": "derived", "formula": "loop_b * 2", "units": "ratio",
                                "frequency": "daily", "direction": 0, "row": "ai_stack", "layer": 2, "weight": 0,
                                "stale_after_days": 5, "licence": "public"})
        d["indicators"].append({**d["indicators"][-1], "id": "loop_b", "formula": "loop_a + 1"})
    edit(cfg_dir / "indicators.yaml", f)
    with pytest.raises(ConfigError, match="cycle"):
        load_config(cfg_dir)


@pytest.mark.parametrize("expr", ["__import__('os')", "x.y", "x[0]", "lambda: 1", "open(x)", "'a' > x", "f(x=1)"])
def test_expressions_cannot_run_code(expr):
    with pytest.raises(ValueError):
        expression_names(expr, FORMULA_FUNCTIONS)


def test_expression_names():
    assert expression_names("rolling_corr(pct_change(spy, 1), pct_change(tlt, 1), 60)", FORMULA_FUNCTIONS) == {"spy", "tlt"}
