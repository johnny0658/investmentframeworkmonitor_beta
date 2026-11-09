"""Filesystem layout. Everything is relative to the repo root so the same code
runs locally, in tests (with a temporary root) and in GitHub Actions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent


@dataclass(frozen=True)
class Paths:
    root: Path = REPO_ROOT
    config_dir: Path = PACKAGE_DIR / "config"
    public_manual_dir: Path = PACKAGE_DIR / "manual"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "monitor.duckdb"

    @property
    def public_parquet(self) -> Path:
        """Committed history snapshots. Never holds restricted raw values."""
        return self.data_dir / "parquet" / "public"

    @property
    def private_dir(self) -> Path:
        """Gitignored. Travels between runs as an encrypted Actions artifact."""
        return self.data_dir / "private"

    @property
    def private_parquet(self) -> Path:
        return self.private_dir / "parquet"

    @property
    def private_manual_dir(self) -> Path:
        """Hand-entered values for restricted sources (e.g. FactSet forward P/E)."""
        return self.private_dir / "manual"

    @property
    def health_dir(self) -> Path:
        return self.data_dir / "health"

    @property
    def site_dir(self) -> Path:
        return self.root / "site"

    @property
    def public_paths(self) -> list[Path]:
        """Everything the licensing guard must keep free of restricted raw values."""
        return [self.public_parquet, self.health_dir, self.site_dir, self.public_manual_dir]
