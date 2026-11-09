"""Licensing guard: no restricted raw value in public paths."""

from __future__ import annotations

import pandas as pd

from framework_monitor import licensing

from .conftest import write_json


def test_clean_public_tree_passes(cfg, paths):
    d = paths.public_parquet / "observations"
    d.mkdir(parents=True)
    pd.DataFrame({"indicator_id": ["ust_10y"], "value": [4.1]}).to_parquet(d / "ust_10y.parquet")
    # restricted indicators may appear with derived values only
    write_json(paths.site_dir / "signals.json", [{"indicator_id": "hy_oas", "z": 1.2, "signal": -1.2}])
    # status-only tables may name restricted indicators
    paths.health_dir.mkdir(parents=True)
    pd.DataFrame({"indicator_id": ["hy_oas"], "status": ["ok"]}).to_csv(paths.health_dir / "log.csv", index=False)
    assert licensing.scan_paths(paths.public_paths, cfg) == []


def test_restricted_parquet_file_fails(cfg, paths):
    d = paths.public_parquet / "observations"
    d.mkdir(parents=True)
    pd.DataFrame({"indicator_id": ["hy_oas"], "value": [3.1]}).to_parquet(d / "hy_oas.parquet")
    v = licensing.scan_paths(paths.public_paths, cfg)
    assert len(v) == 2  # restricted file name + raw value column
    assert any("hy_oas" in str(x) for x in v)


def test_restricted_values_in_csv_and_json_fail(cfg, paths):
    paths.site_dir.mkdir(parents=True)
    pd.DataFrame({"indicator_id": ["ust_10y", "spy"], "close": [4.1, 600.0]}).to_csv(paths.site_dir / "p.csv", index=False)
    write_json(paths.site_dir / "d.json", {"rows": [{"indicator_id": "vix", "value": 17.2}]})
    v = licensing.scan_paths(paths.public_paths, cfg)
    assert {x.path.split("/")[-1] for x in v} == {"p.csv", "d.json"}


def test_unknown_indicator_is_treated_as_restricted(cfg, paths):
    paths.site_dir.mkdir(parents=True)
    write_json(paths.site_dir / "d.json", [{"indicator_id": "mystery", "value": 1}])
    assert licensing.scan_paths(paths.public_paths, cfg)


def test_json_embedded_in_html_is_scanned(cfg, paths):
    paths.site_dir.mkdir(parents=True)
    (paths.site_dir / "index.html").write_text(
        '<html><script type="application/json" id="data">[{"indicator_id": "hy_oas", "value": 3.1}]</script></html>')
    assert licensing.scan_paths(paths.public_paths, cfg)


def test_restricted_manual_csv_in_public_dir_fails(cfg, paths):
    (paths.public_manual_dir / "fwd_pe.csv").write_text("date,value\n2026-11-07,22\n")
    assert licensing.scan_manual_dir(paths.public_manual_dir, cfg)


def test_git_tracked_private_files_fail(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "data" / "private").mkdir(parents=True)
    (tmp_path / "data" / "private" / "x.parquet").write_bytes(b"x")
    subprocess.run(["git", "add", "-f", "data/private/x.parquet"], cwd=tmp_path, check=True)
    assert [v.path for v in licensing.scan_git_tracked(tmp_path)] == ["data/private/x.parquet"]


def test_repo_itself_passes_guard(cfg):
    from framework_monitor.settings import Paths

    p = Paths()
    v = licensing.scan_paths(p.public_paths, cfg) + licensing.scan_git_tracked(p.root) + licensing.scan_manual_dir(p.public_manual_dir, cfg)
    assert v == []
