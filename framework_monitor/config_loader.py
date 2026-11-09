"""Load and validate the YAML config files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from framework_monitor.schemas import Config
from framework_monitor.settings import PACKAGE_DIR

DEFAULT_CONFIG_DIR = PACKAGE_DIR / "config"


class ConfigError(Exception):
    pass


def _read(path: Path):
    if not path.exists():
        raise ConfigError(f"missing config file: {path}")
    with path.open() as fh:
        return yaml.safe_load(fh)


def load_config(config_dir: Path | None = None) -> Config:
    d = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    indicators = _read(d / "indicators.yaml") or []
    if isinstance(indicators, dict):  # top-level `_defaults` anchors + `indicators` list
        indicators = indicators.get("indicators") or []
    raw = {
        "indicators": indicators,
        "rows": _read(d / "rows.yaml"),
        "signposts": _read(d / "signposts.yaml") or [],
        "scenarios": _read(d / "scenarios.yaml"),
        "judgements": _read(d / "judgements.yaml") or [],
    }
    for name in ("alerts", "briefing"):
        if (d / f"{name}.yaml").exists():
            raw[name] = _read(d / f"{name}.yaml") or {}
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
